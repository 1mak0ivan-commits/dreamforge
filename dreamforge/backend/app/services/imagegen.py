"""Генерация иллюстраций через локальный Stable Diffusion WebUI API."""
import asyncio
import base64
import uuid
from pathlib import Path

import aiohttp

from app.core.config import get_settings
from app.core.image_styles import IMAGE_STYLES


class ImageGenError(Exception):
    pass


async def generate_image(prompt: str, style: str, negative_prompt: str | None = None) -> str:
    """Генерирует изображение, сохраняет в uploads/, возвращает имя файла."""
    settings = get_settings()
    style_info = IMAGE_STYLES.get(style)
    checkpoint = style_info["checkpoint"] if style_info else None

    payload = {
        "prompt": prompt,
        "steps": 20,
        "width": 512,
        "height": 512,
        "cfg_scale": 7,
        "sampler_name": "Euler a",
        "negative_prompt": negative_prompt or "низкое качество, размыто, уродливо",
    }
    if checkpoint:
        payload["override_settings"] = {"sd_model_checkpoint": checkpoint}

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
            async with session.post(settings.image_api_url, json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise ImageGenError(f"SD WebUI вернул {resp.status}: {text[:200]}")
                result = await resp.json()
    except aiohttp.ClientConnectorError:
        raise ImageGenError("Не удалось подключиться к Stable Diffusion WebUI (localhost:7860)")
    except asyncio.TimeoutError:
        raise ImageGenError("Stable Diffusion WebUI не ответил за 300 секунд — похоже, генерация зависла")

    try:
        image_bytes = base64.b64decode(result["images"][0])
    except (KeyError, IndexError, TypeError, ValueError) as e:
        # SD WebUI ответил 200, но не тем, что мы ожидали (например, ошибка внутри самой
        # генерации, отданная в непредвиденном формате) — без этого перехвата такой ответ
        # ронял бы весь запрос необработанным исключением вместо понятной ошибки.
        raise ImageGenError(f"Неожиданный формат ответа от Stable Diffusion WebUI: {e}")

    filename = f"{uuid.uuid4().hex}.png"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(exist_ok=True)
    (upload_dir / filename).write_bytes(image_bytes)
    return filename
