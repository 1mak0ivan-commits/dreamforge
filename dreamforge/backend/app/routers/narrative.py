import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.telegram_auth import get_current_user
from app.schemas import NarrativeMessageIn
from app.services.llm import build_narrative_system_prompt, stream_reply
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["narrative"], dependencies=[Depends(get_current_user)])

# Тот же паттерн, что и в chat.py/group_chats.py/creation.py: один активный запрос
# на нарратив, чтобы два действия подряд не генерировались параллельно.
_locks: dict[str, asyncio.Lock] = {}


def _get_lock(key: str) -> asyncio.Lock:
    if key not in _locks:
        _locks[key] = asyncio.Lock()
    return _locks[key]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _characters_for_world(world_id: str) -> list[dict]:
    data = await store.get_all()
    return [c for c in data["characters"] if c.get("world_id") == world_id]


@router.post("/worlds/{world_id}/narrative/start")
async def start_narrative(world_id: str):
    """
    Заходит в мир: если нарратив для этого мира уже есть — просто возвращает его.
    Если это первый вход — генерирует атмосферное начало истории (один блокирующий
    вызов модели, без стрима — вход в новый мир и так ощущается как отдельный "экран
    загрузки", а не как обычное сообщение в чате).
    """
    world = await store.get_world(world_id)
    if not world:
        raise HTTPException(404, "Мир не найден")

    narrative = await store.get_world_narrative_by_world(world_id)
    if not narrative:
        narrative = await store.create_world_narrative(world_id)

    if not narrative["chat_history"]:
        lock = _get_lock(narrative["id"])
        if lock.locked():
            raise HTTPException(429, "Мир ещё готовит начало истории — подожди пару секунд")
        await lock.acquire()
        try:
            characters = await _characters_for_world(world_id)
            system_prompt = build_narrative_system_prompt(world, characters, [])
            full_text = ""
            async for chunk in stream_reply(system_prompt, None):
                full_text += chunk
            opening = full_text.strip() or "…"
            await store.append_narrative_message(narrative["id"], "narrator", opening)
            narrative = await store.get_world_narrative(narrative["id"])
        finally:
            lock.release()

    return narrative


@router.get("/narratives/{narrative_id}")
async def get_narrative(narrative_id: str):
    narrative = await store.get_world_narrative(narrative_id)
    if not narrative:
        raise HTTPException(404, "История не найдена")
    return narrative


@router.post("/narratives/{narrative_id}/clear")
async def clear_narrative(narrative_id: str):
    narrative = await store.get_world_narrative(narrative_id)
    if not narrative:
        raise HTTPException(404, "История не найдена")
    await store.clear_world_narrative(narrative_id)
    return {"status": "ok"}


@router.post("/narratives/{narrative_id}/message")
async def send_narrative_message(narrative_id: str, payload: NarrativeMessageIn):
    narrative = await store.get_world_narrative(narrative_id)
    if not narrative:
        raise HTTPException(404, "История не найдена")

    lock = _get_lock(narrative_id)
    if lock.locked():
        raise HTTPException(429, "Мир ещё обрабатывает предыдущее действие — подожди пару секунд")
    await lock.acquire()

    try:
        world = await store.get_world(narrative["world_id"])
        if not world:
            raise HTTPException(404, "Мир не найден")
        characters = await _characters_for_world(narrative["world_id"])
        await store.append_narrative_message(narrative_id, "user", payload.content)
        narrative = await store.get_world_narrative(narrative_id)
        system_prompt = build_narrative_system_prompt(world, characters, narrative["chat_history"])
    except Exception:
        lock.release()
        raise

    async def event_stream():
        full_text = ""
        try:
            try:
                async for chunk in stream_reply(system_prompt, None):
                    full_text += chunk
                    yield _sse("chunk", {"text": chunk})
            except asyncio.CancelledError:
                if full_text.strip():
                    await store.append_narrative_message(narrative_id, "narrator", full_text.strip())
                raise
            except Exception as e:
                yield _sse("error", {"message": str(e)})
                return

            full_text = full_text.strip() or "…"
            await store.append_narrative_message(narrative_id, "narrator", full_text)
            yield _sse("done", {"text": full_text})
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
