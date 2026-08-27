"""
Проверка подлинности данных, которые Telegram Mini App передаёт в заголовке
X-Telegram-Init-Data. Без этого любой человек с интернетом может дёргать
API напрямую (создавать/удалять персонажей, слать сообщения в LLM за твой счёт).

Алгоритм из официальной документации Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException, status

from app.core.config import get_settings


class TelegramUser:
    def __init__(self, user_id: int, first_name: str, username: str | None):
        self.id = user_id
        self.first_name = first_name
        self.username = username


def _validate_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> dict:
    parsed = dict(parse_qsl(init_data, strict_parsing=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("no hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("bad signature")

    auth_date = int(parsed.get("auth_date", "0"))
    if time.time() - auth_date > max_age_seconds:
        raise ValueError("expired")

    return parsed


async def get_current_user(
    x_telegram_init_data: str | None = Header(default=None),
) -> TelegramUser:
    settings = get_settings()

    if settings.dev_mode and not x_telegram_init_data:
        # Только для локальной разработки в обычном браузере, без Telegram.
        return TelegramUser(user_id=1, first_name="Dev", username="dev")

    if not x_telegram_init_data:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Telegram init data")

    try:
        parsed = _validate_init_data(x_telegram_init_data, settings.bot_token)
        user_json = json.loads(parsed.get("user", "{}"))
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Telegram init data")

    return TelegramUser(
        user_id=user_json.get("id"),
        first_name=user_json.get("first_name", "User"),
        username=user_json.get("username"),
    )
