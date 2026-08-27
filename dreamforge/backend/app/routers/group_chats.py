import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.telegram_auth import get_current_user
from app.schemas import GroupChatIn, GroupMessageIn
from app.services.llm import build_group_system_prompt, stream_reply
from app.services.store import store

router = APIRouter(prefix="/api/group-chats", tags=["group-chats"], dependencies=[Depends(get_current_user)])

_chat_locks: dict[str, asyncio.Lock] = {}


def _get_lock(chat_id: str) -> asyncio.Lock:
    if chat_id not in _chat_locks:
        _chat_locks[chat_id] = asyncio.Lock()
    return _chat_locks[chat_id]



def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _populate(chat: dict) -> dict:
    characters = []
    for cid in chat["character_ids"]:
        c = await store.get_character(cid)
        if c:
            characters.append(c)
    return {**chat, "characters": characters}


@router.get("")
async def list_group_chats():
    chats = await store.list_group_chats()
    return [await _populate(c) for c in chats]


@router.post("")
async def create_group_chat(payload: GroupChatIn):
    for cid in payload.character_ids:
        if not await store.get_character(cid):
            raise HTTPException(404, f"Персонаж {cid} не найден")
    chat = await store.create_group_chat(payload.name, payload.character_ids)
    return await _populate(chat)


@router.get("/{chat_id}")
async def get_group_chat(chat_id: str):
    chat = await store.get_group_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Групповой чат не найден")
    return await _populate(chat)


@router.delete("/{chat_id}")
async def delete_group_chat(chat_id: str):
    await store.delete_group_chat(chat_id)
    return {"status": "ok"}


@router.post("/{chat_id}/clear")
async def clear_group_chat(chat_id: str):
    chat = await store.get_group_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Групповой чат не найден")
    await store.clear_group_chat(chat_id)
    return {"status": "ok"}


@router.post("/{chat_id}/message")
async def send_group_message(chat_id: str, payload: GroupMessageIn):
    chat = await store.get_group_chat(chat_id)
    if not chat:
        raise HTTPException(404, "Групповой чат не найден")

    characters = [await store.get_character(cid) for cid in chat["character_ids"]]
    characters = [c for c in characters if c]
    char_lookup = {c["id"]: c for c in characters}

    if payload.target_character_id and payload.target_character_id not in char_lookup:
        raise HTTPException(400, "Такого персонажа нет в этом чате")

    lock = _get_lock(chat_id)
    if lock.locked():
        raise HTTPException(429, "Разговор ещё отвечает на предыдущее сообщение — подожди пару секунд")
    await lock.acquire()

    try:
        # Мир берём у первого персонажа группы, у которого он указан — общий сеттинг для сцены.
        world = None
        for c in characters:
            if c.get("world_id"):
                world = await store.get_world(c["world_id"])
                if world:
                    break

        profile = await store.get_profile()
        await store.append_group_message(chat_id, "user", None, payload.content)
    except Exception:
        lock.release()
        raise

    # Кто отвечает: конкретный персонаж (@упоминание из UI) или все по очереди.
    responders = [char_lookup[payload.target_character_id]] if payload.target_character_id else characters

    async def event_stream():
        try:
            for speaker in responders:
                chat_now = await store.get_group_chat(chat_id)
                history = chat_now["chat_history"]
                others = [c for c in characters if c["id"] != speaker["id"]]
                system_prompt = build_group_system_prompt(speaker, others, world, profile, history, char_lookup)

                yield _sse("char_start", {"character_id": speaker["id"], "name": speaker["name"]})

                full_text = ""
                try:
                    async for chunk in stream_reply(system_prompt, speaker.get("generation_params")):
                        full_text += chunk
                        yield _sse("chunk", {"character_id": speaker["id"], "text": chunk})
                except asyncio.CancelledError:
                    # "Стоп" — сохраняем то, что успел сказать текущий говорящий, и не переходим к следующим.
                    if full_text.strip():
                        await store.append_group_message(chat_id, "character", speaker["id"], full_text.strip())
                    raise
                except Exception as e:
                    yield _sse("error", {"character_id": speaker["id"], "message": str(e)})
                    continue

                full_text = full_text.strip() or "…"
                await store.append_group_message(chat_id, "character", speaker["id"], full_text)
                yield _sse("char_done", {"character_id": speaker["id"], "text": full_text})

            yield _sse("done", {})
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
