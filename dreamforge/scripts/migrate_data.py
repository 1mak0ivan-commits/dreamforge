"""
Переносит data.json из старого проекта в новый формат.

Важно про аватары: в старой версии аватар персонажа хранился как
Telegram file_id (avatar_file_id) — картинка жила только на серверах Telegram.
Новая версия хранит аватары как локальные файлы в uploads/ (avatar_path).
Этот скрипт может докачать старые аватары через Bot API, если передать токен.

Использование:
    python migrate_data.py /путь/к/старому/data.json ./data.json --download-avatars

Без флага --download-avatars аватары просто останутся пустыми —
их можно будет перезалить вручную через форму редактирования персонажа в приложении.
"""
import argparse
import json
import sys
import uuid
from pathlib import Path

import requests


def migrate(old_data: dict, bot_token: str | None, upload_dir: Path) -> dict:
    new_data = {
        "worlds": [],
        "characters": [],
        "recent_chats": [],
        "user_profile": old_data.get("user_profile", {"name": "Пользователь", "personality": "", "description": ""}),
        "current_style": old_data.get("current_style", "realistic"),
    }

    for w in old_data.get("worlds", []):
        new_data["worlds"].append({"id": w["id"], "name": w["name"], "description": w.get("description", "")})

    for c in old_data.get("characters", []):
        avatar_path = c.get("avatar_path")  # если уже была новая версия — просто копируем
        file_id = c.get("avatar_file_id")

        if not avatar_path and file_id and bot_token:
            avatar_path = _download_telegram_file(bot_token, file_id, upload_dir)

        new_data["characters"].append(
            {
                "id": c["id"],
                "world_id": c.get("world_id"),
                "name": c["name"],
                "personality": c.get("personality", ""),
                "description": c.get("description", ""),
                "greeting": c.get("greeting", ""),
                "avatar_path": avatar_path,
                "memory": c.get("memory", []),
                "generation_params": c.get("generation_params", {"temperature": 0.7, "top_p": 0.9, "max_tokens": 512}),
                "message_count": 0,
                "chat_history": [],  # старая история хранилась только в памяти процесса и не переносится
            }
        )

    return new_data


def _download_telegram_file(bot_token: str, file_id: str, upload_dir: Path) -> str | None:
    try:
        info = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile", params={"file_id": file_id}, timeout=15).json()
        file_path = info["result"]["file_path"]
        content = requests.get(f"https://api.telegram.org/file/bot{bot_token}/{file_path}", timeout=30).content
        ext = Path(file_path).suffix or ".jpg"
        filename = f"{uuid.uuid4().hex}{ext}"
        upload_dir.mkdir(exist_ok=True)
        (upload_dir / filename).write_bytes(content)
        return filename
    except Exception as e:
        print(f"  ! Не удалось скачать аватар {file_id}: {e}", file=sys.stderr)
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("old_path")
    parser.add_argument("new_path")
    parser.add_argument("--bot-token", default=None, help="Токен бота, чтобы докачать старые аватары")
    parser.add_argument("--upload-dir", default="uploads")
    args = parser.parse_args()

    old_data = json.loads(Path(args.old_path).read_text(encoding="utf-8"))
    result = migrate(old_data, args.bot_token, Path(args.upload_dir))
    Path(args.new_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Готово: {len(result['worlds'])} миров, {len(result['characters'])} персонажей -> {args.new_path}")
