"""
Разовая уборка uploads/ для тех, кто уже пользовался приложением до того, как
удаление персонажа/очистка истории стали сами подчищать за собой файлы.
Новые утечки эта версия больше не создаёт — скрипт нужен только чтобы прибраться
за прошлым.

Использование:
    cd backend
    python ../scripts/cleanup_uploads.py data.json uploads

Без флага --apply только покажет, что было бы удалено, ничего не трогая.
"""
import argparse
import json
from pathlib import Path


def collect_referenced_files(data: dict) -> set[str]:
    referenced = set()
    for char in data.get("characters", []):
        if char.get("avatar_path"):
            referenced.add(char["avatar_path"])
        for m in char.get("chat_history", []):
            if m.get("image"):
                referenced.add(m["image"])
    # Групповые чаты сейчас картинок не генерируют, но на будущее — если появятся, тоже учитываем.
    for chat in data.get("group_chats", []):
        for m in chat.get("chat_history", []):
            if m.get("image"):
                referenced.add(m["image"])
    return referenced


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data_path")
    parser.add_argument("upload_dir")
    parser.add_argument("--apply", action="store_true", help="Реально удалить файлы (по умолчанию — только показать)")
    args = parser.parse_args()

    data = json.loads(Path(args.data_path).read_text(encoding="utf-8"))
    referenced = collect_referenced_files(data)

    upload_dir = Path(args.upload_dir)
    orphans = [p for p in upload_dir.iterdir() if p.is_file() and p.name not in referenced and p.name != ".gitkeep"]

    total_size = sum(p.stat().st_size for p in orphans)
    print(f"Найдено {len(orphans)} неиспользуемых файлов ({total_size / 1024 / 1024:.1f} МБ)")

    if not args.apply:
        for p in orphans[:20]:
            print(f"  would delete: {p.name}")
        if len(orphans) > 20:
            print(f"  ...и ещё {len(orphans) - 20}")
        print("\nЭто был предпросмотр (dry-run). Добавь --apply, чтобы реально удалить.")
    else:
        for p in orphans:
            p.unlink()
        print(f"Удалено {len(orphans)} файлов, освобождено {total_size / 1024 / 1024:.1f} МБ")
