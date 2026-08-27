"""
Превращает диалог из режима совместного создания в готовую структурированную карточку
мира или персонажа. Вызывается один раз — когда пользователь жмёт "Готово, создать".
"""
from app.services.json_utils import extract_json
from app.services.llm import generate_once


def _format_discussion(history: list[dict]) -> str:
    return "\n".join(f"{'Пользователь' if h['role'] == 'user' else 'Помощник'}: {h['content']}" for h in history)


async def extract_world(history: list[dict]) -> dict:
    discussion = _format_discussion(history)
    prompt = (
        "На основе всего обсуждения ниже сформулируй итоговую карточку мира для приложения "
        "ролевых чатов с ИИ-персонажами.\n"
        'Ответь СТРОГО в формате JSON, без пояснений и markdown: {"name": "...", "description": "..."}\n'
        "name — короткое название мира (несколько слов).\n"
        "description — подробное, атмосферное описание на русском (абзац-два), которое объединяет "
        "все идеи из обсуждения в цельный связный текст, а не просто пересказывает реплики по порядку.\n\n"
        f"Обсуждение:\n{discussion}\n\nJSON:"
    )
    try:
        text = await generate_once(prompt, temperature=0.4, num_predict=700)
    except RuntimeError as e:
        # generate_once бросает RuntimeError, если модель недоступна/не ответила за таймаут —
        # без этого перехвата исключение улетало необработанным и роутер отдавал голый 500
        # вместо понятного сообщения пользователю.
        raise ValueError(f"Не удалось связаться с моделью, чтобы собрать карточку мира: {e}")
    parsed = extract_json(text)
    if not parsed or not parsed.get("name") or not parsed.get("description"):
        raise ValueError("Не удалось собрать итоговую карточку мира из обсуждения — попробуй обсудить чуть подробнее")
    return {"name": parsed["name"], "description": parsed["description"]}


async def extract_character(history: list[dict], world_context: dict | None) -> dict:
    discussion = _format_discussion(history)
    world_hint = f"Мир, в котором существует персонаж: {world_context['name']} — {world_context['description']}\n\n" if world_context else ""
    prompt = (
        "На основе всего обсуждения ниже сформулируй итоговую карточку персонажа для приложения "
        "ролевых чатов с ИИ-персонажами.\n"
        f"{world_hint}"
        "Ответь СТРОГО в формате JSON, без пояснений и markdown:\n"
        '{"name": "...", "personality": "...", "description": "...", "greeting": "..."}\n'
        "name — имя персонажа.\n"
        "personality — краткая характеристика характера (несколько слов-фраз через запятую).\n"
        "description — подробное описание внешности, истории, манеры речи на русском (абзац-два), "
        "объединяющее все идеи из обсуждения в цельный связный текст.\n"
        "greeting — первая реплика персонажа при начале разговора с пользователем, в его характере "
        "и манере речи, 1-2 предложения.\n\n"
        f"Обсуждение:\n{discussion}\n\nJSON:"
    )
    try:
        text = await generate_once(prompt, temperature=0.4, num_predict=700)
    except RuntimeError as e:
        raise ValueError(f"Не удалось связаться с моделью, чтобы собрать карточку персонажа: {e}")
    parsed = extract_json(text)
    required = ("name", "personality", "description", "greeting")
    if not parsed or not all(parsed.get(k) for k in required):
        raise ValueError("Не удалось собрать итоговую карточку персонажа из обсуждения — попробуй обсудить чуть подробнее")
    return {k: parsed[k] for k in required}
