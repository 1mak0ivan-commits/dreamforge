"""Общий хелпер для мест, где от LLM ждут структурированный JSON-ответ, а не свободный текст."""
import json
import re


def extract_json(text: str) -> dict | None:
    """Модель иногда оборачивает JSON в ```json ... ``` или добавляет пояснения — вытаскиваем сам объект."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
