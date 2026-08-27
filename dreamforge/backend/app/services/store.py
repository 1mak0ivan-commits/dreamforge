"""
Простое, но аккуратное хранилище поверх JSON-файла.
Оставлено намеренно (JSON вместо БД) по решению из этой итерации,
но с asyncio.Lock, чтобы параллельные запросы (чат + сохранение персонажа)
не портили файл гонкой записи, и с типобезопасным доступом через dataclass-подобные dict-хелперы.

Если проект вырастет — можно заменить только этот файл на SQLite-реализацию
с тем же публичным интерфейсом (load/save/get_*), не трогая роутеры.
"""
import json
import uuid
from asyncio import Lock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.image_styles import DEFAULT_STYLE

_lock = Lock()
_cache: dict[str, Any] | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

DEFAULT_DATA: dict[str, Any] = {
    "worlds": [],
    "characters": [],
    "recent_chats": [],
    "group_chats": [],
    "world_narratives": [],
    "user_profile": {"name": "Пользователь", "personality": "", "description": ""},
    "current_style": DEFAULT_STYLE,
}


def _data_path() -> Path:
    return Path(get_settings().data_file)


def _upload_path(filename: str) -> Path:
    return Path(get_settings().upload_dir) / filename


def _delete_upload_file(filename: str | None) -> None:
    """Тихо удаляет файл из uploads/, если он есть. Ошибка тут не должна ронять основную операцию с данными."""
    if not filename:
        return
    try:
        path = _upload_path(filename)
        if path.exists():
            path.unlink()
    except OSError:
        pass



def _read() -> dict[str, Any]:
    """
    Кэш в памяти процесса: без него КАЖДЫЙ вызов store (а их за одно сообщение в чате
    штук 5-8: получить персонажа, мир, профиль, дописать историю, проверить память,
    резюме, картинку...) заново читал бы и парсил весь JSON-файл с диска. С ростом
    истории (до 400 сообщений на персонажа) это реальные лишние миллисекунды на
    каждый чих. Кэш живёт, пока жив процесс, и обновляется при каждой записи —
    это безопасно ровно постольку, поскольку сервер запущен в один процесс
    (см. предупреждение про --workers в README). Если вручную поправить data.json
    прямо на диске, пока сервер работает, — правки будут не видны до перезапуска.
    """
    global _cache
    if _cache is None:
        path = _data_path()
        if not path.exists():
            _cache = json.loads(json.dumps(DEFAULT_DATA))
        else:
            with open(path, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            for key, value in DEFAULT_DATA.items():
                _cache.setdefault(key, value)
    return _cache


def _write(data: dict[str, Any]) -> None:
    global _cache
    _cache = data
    path = _data_path()
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(path)  # атомарная замена — не потеряем данные при падении на записи


class Store:
    """Каждый публичный метод сам берёт лок и читает/пишет файл — вызывающему думать не нужно."""

    async def get_all(self) -> dict[str, Any]:
        async with _lock:
            return _read()

    async def get_world(self, world_id: str) -> dict | None:
        data = await self.get_all()
        return next((w for w in data["worlds"] if w["id"] == world_id), None)

    async def get_character(self, char_id: str) -> dict | None:
        data = await self.get_all()
        return next((c for c in data["characters"] if c["id"] == char_id), None)

    async def create_world(self, name: str, description: str, image_path: str | None = None) -> dict:
        async with _lock:
            data = _read()
            world = {
                "id": f"world_{uuid.uuid4().hex[:10]}",
                "name": name,
                "description": description,
                "image_path": image_path,
                "created_at": _now_iso(),
            }
            data["worlds"].append(world)
            _write(data)
            return world

    async def update_world(
        self, world_id: str, name: str | None, description: str | None, image_path: str | None = None
    ) -> dict | None:
        async with _lock:
            data = _read()
            world = next((w for w in data["worlds"] if w["id"] == world_id), None)
            if not world:
                return None
            old_image = world.get("image_path")
            if name is not None:
                world["name"] = name
            if description is not None:
                world["description"] = description
            if image_path is not None:
                world["image_path"] = image_path
            _write(data)
            if image_path and old_image and old_image != image_path:
                _delete_upload_file(old_image)
            return world

    async def delete_world(self, world_id: str) -> None:
        async with _lock:
            data = _read()
            world = next((w for w in data["worlds"] if w["id"] == world_id), None)
            if world:
                _delete_upload_file(world.get("image_path"))
            data["worlds"] = [w for w in data["worlds"] if w["id"] != world_id]
            for c in data["characters"]:
                if c.get("world_id") == world_id:
                    c["world_id"] = None
            # Нарратив мира больше не на что ссылаться без самого мира — чистим в этом же
            # локе, а не отдельным вызовом (asyncio.Lock не реентерабельный, второй захват
            # изнутри уже захваченного лока — гарантированный deadlock).
            data["world_narratives"] = [n for n in data["world_narratives"] if n["world_id"] != world_id]
            _write(data)

    async def create_character(self, payload: dict) -> dict:
        async with _lock:
            data = _read()
            char = {
                "id": f"char_{uuid.uuid4().hex[:10]}",
                "world_id": payload.get("world_id"),
                "name": payload["name"],
                "personality": payload.get("personality", ""),
                "description": payload.get("description", ""),
                "greeting": payload.get("greeting", ""),
                "avatar_path": payload.get("avatar_path"),
                "visual_identity": payload.get("visual_identity"),
                "memory": [],
                "summary": "",
                "generation_params": {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512},
                "message_count": 0,
                "memory_counter": 0,
                "summary_counter": 0,
                "created_at": _now_iso(),
            }
            data["characters"].append(char)
            _write(data)
            return char

    async def update_character(self, char_id: str, patch: dict) -> dict | None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return None
            old_avatar = char.get("avatar_path")
            for key in ("world_id", "name", "personality", "description", "greeting", "avatar_path", "visual_identity"):
                if key in patch and patch[key] is not None:
                    char[key] = patch[key]
            if patch.get("generation_params"):
                char["generation_params"].update(patch["generation_params"])
            _write(data)
            # Старый портрет больше нигде не используется (у аватаров всегда уникальные имена файлов) —
            # без этого при каждой перегенерации аватара в uploads/ копился бы мусор навсегда.
            new_avatar = char.get("avatar_path")
            if old_avatar and old_avatar != new_avatar:
                _delete_upload_file(old_avatar)
            return char

    async def delete_character(self, char_id: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if char:
                # Портрет и все иллюстрации сцен этого персонажа больше никому не нужны — чистим диск,
                # иначе uploads/ будет расти бесконечно даже после удаления персонажей.
                _delete_upload_file(char.get("avatar_path"))
                for m in char.get("chat_history", []):
                    if m.get("image"):
                        _delete_upload_file(m["image"])
            data["characters"] = [c for c in data["characters"] if c["id"] != char_id]
            data["recent_chats"] = [r for r in data["recent_chats"] if r["char_id"] != char_id]
            _write(data)

    async def remove_character_from_world(self, char_id: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if char:
                char["world_id"] = None
                _write(data)

    async def append_memory(self, char_id: str, fact: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if char:
                char.setdefault("memory", []).append(fact)
                char["memory"] = char["memory"][-20:]
                _write(data)

    async def get_chat_history(self, char_id: str) -> list[dict]:
        data = await self.get_all()
        char = next((c for c in data["characters"] if c["id"] == char_id), None)
        return char.get("chat_history", []) if char else []

    async def append_chat_message(self, char_id: str, role: str, content: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return
            char.setdefault("chat_history", []).append({"role": role, "content": content, "timestamp": _now_iso()})
            # Храним щедрый запас истории для показа в интерфейсе (скролл назад) — это НЕ то же самое,
            # что попадает в промпт модели (там только хвост + summary, см. build_system_prompt).
            # Раньше тут стояла обрезка до 40 сообщений, из-за которой старая переписка удалялась навсегда.
            char["chat_history"] = char["chat_history"][-400:]
            char["message_count"] = char.get("message_count", 0) + (1 if role == "user" else 0)

            recent = data.setdefault("recent_chats", [])
            existing = next((r for r in recent if r["char_id"] == char_id), None)
            preview = content[:120]
            if existing:
                existing["last_message"] = preview
                recent.remove(existing)
            recent.insert(0, {"char_id": char_id, "last_message": preview})
            data["recent_chats"] = recent[:30]
            _write(data)

    async def remove_last_assistant_message(self, char_id: str) -> str | None:
        """Для 'Перегенерировать': убирает последний ответ персонажа. Возвращает текст, который убрали."""
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char or not char.get("chat_history"):
                return None
            if char["chat_history"][-1]["role"] != "assistant":
                return None
            removed = char["chat_history"].pop()
            _write(data)
            return removed["content"]

    async def edit_last_user_message(self, char_id: str, new_content: str) -> bool:
        """
        Для 'Редактировать': правит ПОСЛЕДНЕЕ сообщение пользователя и убирает ответ
        персонажа на него (если он уже был), чтобы затем сгенерировать новый ответ
        на исправленный текст. Редактировать можно только самое последнее сообщение —
        произвольные правки в середине истории не поддерживаются, это осознанное упрощение.
        """
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return False
            history = char.get("chat_history", [])
            if history and history[-1]["role"] == "assistant":
                history.pop()
            if not history or history[-1]["role"] != "user":
                return False
            history[-1]["content"] = new_content
            _write(data)
            return True

    async def clear_chat(self, char_id: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if char:
                # Иллюстрации сцен, сгенерированные за время этого разговора, теряют единственную
                # ссылку на себя вместе с историей — без явного удаления файлы останутся на диске навсегда.
                for m in char.get("chat_history", []):
                    if m.get("image"):
                        _delete_upload_file(m["image"])
                char["chat_history"] = []
                char["message_count"] = 0
                _write(data)

    async def bump_and_check_image_trigger(self, char_id: str) -> bool:
        """Возвращает True, если пора сгенерировать иллюстрацию сцены."""
        settings = get_settings()
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return False
            if char.get("message_count", 0) >= settings.image_generate_every:
                char["message_count"] = 0
                _write(data)
                return True
            return False

    async def bump_and_check_memory_trigger(self, char_id: str) -> bool:
        """Возвращает True, если пора попробовать выжать новый факт о пользователе в память."""
        settings = get_settings()
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return False
            char["memory_counter"] = char.get("memory_counter", 0) + 1
            if char["memory_counter"] >= settings.memory_extract_every:
                char["memory_counter"] = 0
                _write(data)
                return True
            _write(data)
            return False

    async def bump_and_check_summary_trigger(self, char_id: str) -> bool:
        """Возвращает True, если пора обновить скользящее резюме старой части разговора."""
        settings = get_settings()
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if not char:
                return False
            char["summary_counter"] = char.get("summary_counter", 0) + 1
            if char["summary_counter"] >= settings.summary_update_every:
                char["summary_counter"] = 0
                _write(data)
                return True
            _write(data)
            return False

    async def set_summary(self, char_id: str, summary: str) -> None:
        async with _lock:
            data = _read()
            char = next((c for c in data["characters"] if c["id"] == char_id), None)
            if char:
                char["summary"] = summary
                _write(data)

    async def get_profile(self) -> dict:
        data = await self.get_all()
        return data["user_profile"]

    async def update_profile(self, name: str, personality: str, description: str) -> dict:
        async with _lock:
            data = _read()
            data["user_profile"] = {"name": name, "personality": personality, "description": description}
            _write(data)
            return data["user_profile"]

    async def set_style(self, style: str) -> None:
        async with _lock:
            data = _read()
            data["current_style"] = style
            _write(data)

    async def get_style(self) -> str:
        data = await self.get_all()
        return data.get("current_style", DEFAULT_STYLE)

    # --- Групповые чаты ---

    async def list_group_chats(self) -> list[dict]:
        data = await self.get_all()
        return data["group_chats"]

    async def get_group_chat(self, chat_id: str) -> dict | None:
        data = await self.get_all()
        return next((g for g in data["group_chats"] if g["id"] == chat_id), None)

    async def create_group_chat(self, name: str, character_ids: list[str]) -> dict:
        async with _lock:
            data = _read()
            chat = {
                "id": f"group_{uuid.uuid4().hex[:10]}",
                "name": name,
                "character_ids": character_ids,
                "chat_history": [],
                "created_at": _now_iso(),
            }
            data["group_chats"].append(chat)
            _write(data)
            return chat

    async def delete_group_chat(self, chat_id: str) -> None:
        async with _lock:
            data = _read()
            data["group_chats"] = [g for g in data["group_chats"] if g["id"] != chat_id]
            _write(data)

    async def append_group_message(self, chat_id: str, role: str, character_id: str | None, content: str) -> None:
        async with _lock:
            data = _read()
            chat = next((g for g in data["group_chats"] if g["id"] == chat_id), None)
            if not chat:
                return
            chat.setdefault("chat_history", []).append(
                {"role": role, "character_id": character_id, "content": content, "timestamp": _now_iso()}
            )
            # Аналогично одиночным чатам — не обрезаем историю жёстко, только держим разумный запас.
            chat["chat_history"] = chat["chat_history"][-400:]
            _write(data)

    async def clear_group_chat(self, chat_id: str) -> None:
        async with _lock:
            data = _read()
            chat = next((g for g in data["group_chats"] if g["id"] == chat_id), None)
            if chat:
                chat["chat_history"] = []
                _write(data)

    # --- Нарратив мира ("Войти в мир" — свободное повествование без выбора конкретного
    # персонажа для разговора). Одна активная линия истории на мир — не отдельные "сохранения". ---

    async def get_world_narrative_by_world(self, world_id: str) -> dict | None:
        data = await self.get_all()
        return next((n for n in data["world_narratives"] if n["world_id"] == world_id), None)

    async def get_world_narrative(self, narrative_id: str) -> dict | None:
        data = await self.get_all()
        return next((n for n in data["world_narratives"] if n["id"] == narrative_id), None)

    async def create_world_narrative(self, world_id: str) -> dict:
        async with _lock:
            data = _read()
            narrative = {
                "id": f"narrative_{uuid.uuid4().hex[:10]}",
                "world_id": world_id,
                "chat_history": [],
                "created_at": _now_iso(),
            }
            data["world_narratives"].append(narrative)
            _write(data)
            return narrative

    async def append_narrative_message(self, narrative_id: str, role: str, content: str) -> None:
        async with _lock:
            data = _read()
            n = next((x for x in data["world_narratives"] if x["id"] == narrative_id), None)
            if not n:
                return
            n.setdefault("chat_history", []).append({"role": role, "content": content, "timestamp": _now_iso()})
            n["chat_history"] = n["chat_history"][-400:]
            _write(data)

    async def clear_world_narrative(self, narrative_id: str) -> None:
        async with _lock:
            data = _read()
            n = next((x for x in data["world_narratives"] if x["id"] == narrative_id), None)
            if n:
                n["chat_history"] = []
                _write(data)


store = Store()
