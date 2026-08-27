import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.core.telegram_auth import get_current_user
from app.schemas import CreationMessageIn, CreationStartIn
from app.services import creation_extractor, creation_store, imagegen, prompt_enhancer
from app.services.llm import build_creation_system_prompt, stream_reply
from app.services.store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creation", tags=["creation"], dependencies=[Depends(get_current_user)])

OPENING_LINES = {
    "world": (
        "Привет! Давай вместе придумаем мир для твоих персонажей. Расскажи, какая атмосфера тебе "
        "интересна — фэнтези, киберпанк, что-то бытовое с необычным поворотом? Или у тебя уже есть "
        "зацепка, от которой можно оттолкнуться?"
    ),
    "character": (
        "Привет! Давай вместе придумаем персонажа. Кто это — герой, злодей, кто-то бытовой и "
        "обаятельный? Расскажи, что уже приходит в голову, а я подхвачу и предложу детали."
    ),
}

# Тот же паттерн, что и в chat.py/group_chats.py: один активный запрос на сессию создания,
# чтобы два сообщения подряд не генерировались параллельно.
_locks: dict[str, asyncio.Lock] = {}


def _get_lock(session_id: str) -> asyncio.Lock:
    if session_id not in _locks:
        _locks[session_id] = asyncio.Lock()
    return _locks[session_id]


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/start")
async def start_creation(payload: CreationStartIn):
    if payload.kind == "character" and payload.world_id and not await store.get_world(payload.world_id):
        raise HTTPException(404, "Мир не найден")

    session = creation_store.create_session(payload.kind, payload.world_id)
    creation_store.append_message(session["id"], "assistant", OPENING_LINES[payload.kind])
    return session


@router.get("/{session_id}")
async def get_creation(session_id: str):
    session = creation_store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Сессия создания не найдена или уже завершена")
    return session


@router.delete("/{session_id}")
async def cancel_creation(session_id: str):
    creation_store.delete_session(session_id)
    return {"status": "ok"}


@router.post("/{session_id}/message")
async def send_creation_message(session_id: str, payload: CreationMessageIn):
    session = creation_store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Сессия создания не найдена или уже завершена")

    lock = _get_lock(session_id)
    if lock.locked():
        raise HTTPException(429, "Помощник ещё отвечает на предыдущее сообщение — подожди пару секунд")
    await lock.acquire()

    try:
        creation_store.append_message(session_id, "user", payload.content)
        world_context = await store.get_world(session["world_id"]) if session.get("world_id") else None
        system_prompt = build_creation_system_prompt(session["kind"], world_context, session["history"])
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
                    creation_store.append_message(session_id, "assistant", full_text.strip())
                raise
            except Exception as e:
                yield _sse("error", {"message": str(e)})
                return

            full_text = full_text.strip() or "…"
            creation_store.append_message(session_id, "assistant", full_text)
            yield _sse("done", {"text": full_text})
        finally:
            lock.release()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/{session_id}/finalize")
async def finalize_creation(session_id: str):
    """
    Собирает всё обсуждение в готовую карточку и создаёт настоящего персонажа/мир.
    Для персонажа заодно генерирует портрет по итоговому описанию — так же, как
    ручная кнопка "Сгенерировать портрет" в форме персонажа, просто без ручного ввода.
    """
    session = creation_store.get_session(session_id)
    if not session:
        raise HTTPException(404, "Сессия создания не найдена или уже завершена")
    if not session["history"]:
        raise HTTPException(400, "Обсуждение пустое — не из чего собирать карточку")

    if session["kind"] == "world":
        try:
            data = await creation_extractor.extract_world(session["history"])
        except ValueError as e:
            raise HTTPException(422, str(e))
        created = await store.create_world(data["name"], data["description"])

        try:
            positive, negative = await prompt_enhancer.build_world_visual_prompt(data["name"], data["description"])
            style = await store.get_style()
            filename = await imagegen.generate_image(positive, style, negative)
            created = await store.update_world(created["id"], None, None, filename)
        except Exception:
            # Картинка — бонус к уже успешно созданному миру, а не условие успеха. Ловим широко,
            # а не только ImageGenError — иначе непредвиденный сбой на этом шаге срывал бы весь
            # ответ 500-й ошибкой, хотя мир на самом деле уже сохранён в данных.
            logger.exception("Не удалось сгенерировать изображение для мира %s из режима совместного создания", created["id"])

        creation_store.delete_session(session_id)
        return {"kind": "world", "entity": created}

    # kind == "character"
    world_context = await store.get_world(session["world_id"]) if session.get("world_id") else None
    try:
        data = await creation_extractor.extract_character(session["history"], world_context)
    except ValueError as e:
        raise HTTPException(422, str(e))

    created = await store.create_character(
        {
            "world_id": session.get("world_id"),
            "name": data["name"],
            "personality": data["personality"],
            "description": data["description"],
            "greeting": data["greeting"],
        }
    )

    try:
        visual_identity = await prompt_enhancer.build_visual_identity(data["name"], data["personality"], data["description"])
        positive, negative = await prompt_enhancer.build_scene_prompt(
            visual_identity, "portrait, headshot, looking at viewer, neutral background"
        )
        style = await store.get_style()
        filename = await imagegen.generate_image(positive, style, negative)
        created = await store.update_character(created["id"], {"avatar_path": filename, "visual_identity": visual_identity})
    except Exception:
        # Портрет не сгенерировался — не критично, персонаж уже создан и его можно
        # доработать вручную (в том числе перегенерировать портрет) в форме редактирования.
        # Ловим широко по той же причине, что и у мира выше.
        logger.exception("Не удалось сгенерировать портрет для персонажа %s из режима совместного создания", created["id"])

    creation_store.delete_session(session_id)
    return {"kind": "character", "entity": created}
