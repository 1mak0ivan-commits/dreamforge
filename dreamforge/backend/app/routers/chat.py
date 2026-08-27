import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.telegram_auth import TelegramUser, get_current_user
from app.schemas import ChatMessageIn
from app.services import imagegen, memory, prompt_enhancer
from app.services.llm import build_system_prompt, stream_reply
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(get_current_user)])

# По одному активному запросу на персонажа — не даём двум сообщениям генерироваться
# параллельно и путать историю чата гонкой записи (см. README про этот же паттерн в group_chats.py).
_char_locks: dict[str, asyncio.Lock] = {}


def _get_lock(char_id: str) -> asyncio.Lock:
    if char_id not in _char_locks:
        _char_locks[char_id] = asyncio.Lock()
    return _char_locks[char_id]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/{char_id}/history")
async def get_history(char_id: str):
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")
    history = char.get("chat_history", [])
    if not history and char.get("greeting"):
        # Первое открытие чата — приветствие персонажа, но пока не сохраняем его,
        # чтобы не плодить дубликаты при повторных GET.
        return [{"role": "assistant", "content": char["greeting"], "is_greeting": True}]
    return history


@router.post("/{char_id}/clear")
async def clear_chat(char_id: str):
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")
    await store.clear_chat(char_id)
    return {"status": "ok"}


async def _trigger_scene_image_if_due(char_id: str, char: dict, last_user_message: str):
    should_generate = await store.bump_and_check_image_trigger(char_id)
    if not should_generate:
        return None
    style = await store.get_style()

    # Идентичность внешности персонажа переиспользуется из карточки — если её ещё нет
    # (персонаж создан без генерации аватара), собираем на лету из сырого описания.
    visual_identity = char.get("visual_identity") or await prompt_enhancer.build_visual_identity(
        char["name"], char.get("personality", ""), char.get("description", "")
    )
    positive, negative = await prompt_enhancer.build_scene_prompt(visual_identity, last_user_message)
    try:
        filename = await imagegen.generate_image(positive, style, negative)
        return filename
    except imagegen.ImageGenError:
        return None


async def _maybe_extract_memory(char_id: str, char: dict, user_message: str, assistant_reply: str):
    should_try = await store.bump_and_check_memory_trigger(char_id)
    if not should_try:
        return
    fact = await memory.extract_memory_fact(user_message, assistant_reply, char.get("memory", []))
    if fact:
        await store.append_memory(char_id, fact)


async def _maybe_update_summary(char_id: str, char: dict):
    should_try = await store.bump_and_check_summary_trigger(char_id)
    if not should_try:
        return
    history = char.get("chat_history", [])
    older = history[:-20]  # то, что уже выпало из "недавнего хвоста" в промпте
    if not older:
        return
    new_summary = await memory.update_summary(char.get("summary", ""), older, char["name"])
    if new_summary:
        await store.set_summary(char_id, new_summary)


async def _generate_and_store_reply(char_id: str, char: dict, world, profile, last_user_message: str):
    """Общая часть для обычной отправки и регенерации: строит промпт, стримит, сохраняет побочные эффекты."""
    history = char.get("chat_history", [])
    system_prompt = build_system_prompt(char, world, profile, history)

    full_text = ""
    try:
        async for chunk in stream_reply(system_prompt, char.get("generation_params")):
            full_text += chunk
            yield _sse("chunk", {"text": chunk})
    except asyncio.CancelledError:
        # Пользователь нажал "Стоп" — клиент отключился, поэтому дальше yield уже никто не увидит,
        # но то, что персонаж успел "сказать" до остановки, всё равно сохраняем, а не теряем целиком.
        if full_text.strip():
            await store.append_chat_message(char_id, "assistant", full_text.strip())
        raise
    except Exception as e:  # не даём стриму молча оборваться на фронте
        yield _sse("error", {"message": str(e)})
        return

    full_text = full_text.strip() or "…"
    await store.append_chat_message(char_id, "assistant", full_text)

    # Побочные фоновые процессы — не должны ронять ответ, если что-то пойдёт не так,
    # но сбой стоит хотя бы залогировать, а не проглатывать молча.
    try:
        await _maybe_extract_memory(char_id, char, last_user_message, full_text)
    except Exception:
        logger.exception("Не удалось извлечь память для персонажа %s", char_id)
    char_fresh = await store.get_character(char_id)
    try:
        await _maybe_update_summary(char_id, char_fresh)
    except Exception:
        logger.exception("Не удалось обновить резюме для персонажа %s", char_id)

    image_filename = await _trigger_scene_image_if_due(char_id, char, last_user_message)
    yield _sse("done", {"text": full_text, "image": image_filename})


@router.post("/{char_id}/message")
async def send_message(char_id: str, payload: ChatMessageIn, user: TelegramUser = Depends(get_current_user)):
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")

    lock = _get_lock(char_id)
    if lock.locked():
        raise HTTPException(429, "Персонаж ещё отвечает на предыдущее сообщение — подожди пару секунд")
    await lock.acquire()

    try:
        world = await store.get_world(char["world_id"]) if char.get("world_id") else None
        profile = await store.get_profile()

        # Если приветствие ещё не сохранено в историю — сохраняем его первым сообщением от лица персонажа.
        history = char.get("chat_history", [])
        if not history and char.get("greeting"):
            await store.append_chat_message(char_id, "assistant", char["greeting"])

        await store.append_chat_message(char_id, "user", payload.content)
        char = await store.get_character(char_id)
    except Exception:
        # Если что-то упало ДО того, как стрим начался — лок нужно отпустить прямо тут,
        # иначе персонаж "зависнет" с вечным 429 до перезапуска сервера.
        lock.release()
        raise

    async def event_stream():
        try:
            async for event in _generate_and_store_reply(char_id, char, world, profile, payload.content):
                yield event
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{char_id}/regenerate")
async def regenerate_message(char_id: str):
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")

    history = char.get("chat_history", [])
    if not history or history[-1]["role"] != "assistant":
        raise HTTPException(400, "Нечего перегенерировать")

    lock = _get_lock(char_id)
    if lock.locked():
        raise HTTPException(429, "Персонаж ещё отвечает на предыдущее сообщение — подожди пару секунд")
    await lock.acquire()

    try:
        await store.remove_last_assistant_message(char_id)
        char = await store.get_character(char_id)
        history = char.get("chat_history", [])
        last_user_message = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")

        world = await store.get_world(char["world_id"]) if char.get("world_id") else None
        profile = await store.get_profile()
    except Exception:
        lock.release()
        raise

    async def event_stream():
        try:
            async for event in _generate_and_store_reply(char_id, char, world, profile, last_user_message):
                yield event
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{char_id}/edit-message")
async def edit_last_message(char_id: str, payload: ChatMessageIn):
    """Правит последнее отправленное сообщение пользователя и генерирует новый ответ на него."""
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")

    lock = _get_lock(char_id)
    if lock.locked():
        raise HTTPException(429, "Персонаж ещё отвечает на предыдущее сообщение — подожди пару секунд")
    await lock.acquire()

    ok = await store.edit_last_user_message(char_id, payload.content)
    if not ok:
        lock.release()
        raise HTTPException(400, "Нет отправленного сообщения для редактирования")

    try:
        char = await store.get_character(char_id)
        world = await store.get_world(char["world_id"]) if char.get("world_id") else None
        profile = await store.get_profile()
    except Exception:
        lock.release()
        raise

    async def event_stream():
        try:
            async for event in _generate_and_store_reply(char_id, char, world, profile, payload.content):
                yield event
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
