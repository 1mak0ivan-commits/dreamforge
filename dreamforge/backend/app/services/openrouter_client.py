"""
Клиент для OpenRouter — агрегатор, дающий доступ к DeepSeek и другим моделям через
один OpenAI-совместимый REST API. Используется как альтернатива локальной Ollama
для реплик персонажей — если задан OPENROUTER_API_KEY, отвечает он.

Служебные вызовы (память, резюме, промпты для картинок) через generate_once
намеренно ВСЕГДА идут в Ollama, а не сюда — экономит платный/лимитированный
токен-бюджет OpenRouter на не самое важное для качества ответов.
"""
import asyncio
import json
from collections.abc import AsyncGenerator

import aiohttp

from app.core.config import get_settings


async def stream_reply(system_prompt: str, char_params: dict | None) -> AsyncGenerator[str, None]:
    settings = get_settings()
    payload = {
        "model": settings.openrouter_model,
        # Промпт в проекте собирается как один цельный текстовый блок (см. llm.build_system_prompt),
        # а не как раздельные системные/пользовательские сообщения — поэтому передаём его одним
        # сообщением, ровно как раньше уходило в Ollama через поле "prompt".
        "messages": [{"role": "user", "content": f"{system_prompt}\n\nТвоя реплика:"}],
        "stream": True,
        "temperature": (char_params or {}).get("temperature", 0.7),
        "top_p": (char_params or {}).get("top_p", 0.9),
        "max_tokens": (char_params or {}).get("max_tokens", 512),
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        # Необязательные, но рекомендуемые OpenRouter заголовки — попадают в их публичный
        # рейтинг приложений, на работу API не влияют, если не заданы.
        "HTTP-Referer": "https://github.com/",
        "X-Title": "DreamForge",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=settings.ollama_chat_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(f"{settings.openrouter_base_url}/chat/completions", json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    yield f"[Ошибка OpenRouter API: HTTP {resp.status}. {text[:200]}]"
                    return
                async for raw_line in resp.content:
                    if not raw_line:
                        continue
                    line = raw_line.decode("utf-8").strip()
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    piece = choices[0].get("delta", {}).get("content")
                    if piece:
                        yield piece
    except aiohttp.ClientConnectorError:
        yield "[Не удалось подключиться к OpenRouter API. Проверь интернет-соединение.]"
    except asyncio.TimeoutError:
        yield f"[OpenRouter не ответил за {settings.ollama_chat_timeout_seconds} секунд.]"
