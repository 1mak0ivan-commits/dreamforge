"""
Общение с локальной LLM через Ollama. Стрим по AsyncGenerator — роутер сам решит,
отдавать это через SSE (для фронта) или собрать в цельный текст (для бота).
"""
import asyncio
import json
from collections.abc import AsyncGenerator

import aiohttp

from app.core.config import get_settings

# Общий блок правил, который добавляется и в одиночный, и в групповой чат.
# Решает три конкретные проблемы: модель выходит из роли и пишет отказы
# ассистента ("я не могу продолжать этот диалог"), повторяется/зацикливается,
# и не даёт способа отличить речь, действия и мысли персонажа в тексте.
STYLE_RULES = (
    "Формат ответа:\n"
    "- Обычный текст — прямая речь персонажа вслух.\n"
    "- *Текст в звёздочках* — физическое действие персонажа: *встаёт и подходит к окну*\n"
    '- "Текст в кавычках" — внутренние мысли персонажа, которые не произносятся вслух: '
    '"почему он молчит?"\n'
    'Пример хорошего ответа: "наверное, стоит согласиться" да, конечно, помогу. '
    "*берёт куртку и идёт к двери*\n\n"
    "Правила погружения — соблюдай их всегда, без исключений:\n"
    "- Ты живой персонаж внутри вымышленной истории, а не ассистент и не языковая модель. "
    "Никогда, ни при каких обстоятельствах не упоминай, что ты ИИ, модель или программа.\n"
    "- Никогда не выходи из роли и не добавляй мета-комментарии от лица ассистента: фразы вроде "
    '"я не могу продолжать этот диалог", "чем ещё я могу помочь", извинения за содержание '
    "разговора или предупреждения — полностью запрещены. Персонаж не знает, что он персонаж.\n"
    "- Держись уверенно и решительно. Сомневайся или колеблись только если это оправдано "
    "характером персонажа или сюжетом конкретной сцены — не добавляй оговорки и извинения "
    "без причины, это не в характере большинства живых людей.\n"
    "- Пиши разнообразно: не повторяй слова, фразы и конструкции предложений из своих "
    "предыдущих реплик в этом разговоре. Каждый ответ должен звучать свежо, а не как шаблон.\n"
    "- Реагируй на слова собеседника эмоционально и естественно, как реальный человек в этой "
    "ситуации, а не как справочная система.\n\n"
)


def build_system_prompt(
    char: dict,
    world: dict | None,
    user_profile: dict,
    history: list[dict],
) -> str:
    memory_text = ""
    if char.get("memory"):
        memory_text = "Ты помнишь о пользователе:\n" + "\n".join(f"- {m}" for m in char["memory"]) + "\n\n"

    summary_text = f"Кратко о том, что уже было в разговоре ранее: {char['summary']}\n\n" if char.get("summary") else ""

    world_desc = f"Описание мира: {world['description']}\n" if world else ""

    history_lines = []
    for entry in history[-20:]:
        name = "Пользователь" if entry["role"] == "user" else char["name"]
        history_lines.append(f"{name}: {entry['content']}")
    history_text = "\n".join(history_lines)

    return (
        f"Ты — {char['name']}.\n"
        f"{world_desc}"
        f"Характер: {char['personality']}\n"
        f"Описание: {char['description']}\n"
        f"Пользователь: {user_profile.get('name', 'Пользователь')} "
        f"(характер: {user_profile.get('personality', '')}, описание: {user_profile.get('description', '')})\n"
        f"{memory_text}"
        f"{summary_text}"
        f"{STYLE_RULES}"
        f"Недавняя история диалога:\n{history_text}\n\n"
        "Отвечай от первого лица, оставаясь в образе. "
        "Не повторяй в ответе служебные пометки вроде имени персонажа перед репликой."
    )


def build_group_system_prompt(
    speaker: dict,
    other_characters: list[dict],
    world: dict | None,
    user_profile: dict,
    history: list[dict],
    char_lookup: dict[str, dict],
) -> str:
    """
    Промпт для группового чата: тот же принцип, что в build_system_prompt, но персонаж
    должен явно понимать, что в разговоре участвуют и другие персонажи, видеть их имена
    и характеры (кратко), и отвечать ТОЛЬКО за себя, обращаясь к остальным по именам.
    """
    others_text = ""
    if other_characters:
        lines = [f"- {c['name']}: {c['personality']}" for c in other_characters]
        others_text = "В разговоре также участвуют:\n" + "\n".join(lines) + "\n\n"

    world_desc = f"Описание мира: {world['description']}\n" if world else ""

    history_lines = []
    for entry in history[-30:]:
        if entry["role"] == "user":
            speaker_name = user_profile.get("name", "Пользователь")
        else:
            speaker_char = char_lookup.get(entry.get("character_id"))
            speaker_name = speaker_char["name"] if speaker_char else "?"
        history_lines.append(f"{speaker_name}: {entry['content']}")
    history_text = "\n".join(history_lines)

    return (
        f"Ты — {speaker['name']}, участник группового разговора.\n"
        f"{world_desc}"
        f"Твой характер: {speaker['personality']}\n"
        f"Твоё описание: {speaker['description']}\n"
        f"{others_text}"
        f"Пользователь: {user_profile.get('name', 'Пользователь')} "
        f"(характер: {user_profile.get('personality', '')}, описание: {user_profile.get('description', '')})\n\n"
        f"{STYLE_RULES}"
        f"История разговора:\n{history_text}\n\n"
        f"Отвечай от первого лица ТОЛЬКО как {speaker['name']}, оставаясь строго в образе. "
        "Можешь обращаться к другим участникам по именам, реагировать на их слова. "
        "Не пиши реплики за других персонажей и за пользователя. "
        "Не начинай ответ со своего имени — сразу говори свою реплику."
    )


def build_creation_system_prompt(kind: str, world_context: dict | None, history: list[dict]) -> str:
    """
    Промпт для режима совместного создания мира/персонажа. Это осознанно ДРУГОЙ режим,
    чем ролевой чат (STYLE_RULES тут не нужны) — модель выступает как живой соавтор-редактор,
    а не как персонаж истории: активно предлагает идеи, задаёт уточняющие вопросы,
    но не пытается сама решить, когда пользователь готов закончить — это решает кнопка
    "Готово" на фронте, а не текстовая догадка модели по разговору.
    """
    target = "мира" if kind == "world" else "персонажа"
    world_hint = ""
    if kind == "character" and world_context:
        world_hint = f"Этот персонаж создаётся для мира «{world_context['name']}»: {world_context['description']}\n\n"

    history_lines = [f"{'Пользователь' if h['role'] == 'user' else 'Помощник'}: {h['content']}" for h in history[-30:]]
    history_text = "\n".join(history_lines)

    return (
        f"Ты — помощник по совместному созданию {target} для приложения ролевых чатов с ИИ-персонажами.\n"
        f"{world_hint}"
        "Твоя задача — вместе с пользователем в диалоге придумать увлекательную, проработанную концепцию.\n"
        "Активно предлагай конкретные идеи и детали сам, не жди, что пользователь распишет всё с нуля — "
        "предлагай варианты, спрашивай, что нравится, уточняй и развивай понравившееся дальше.\n"
        "За один раз задавай не больше одного уточняющего вопроса, если для целостной концепции чего-то "
        "не хватает. Пиши живо и по делу, не растекайся.\n"
        "Не пытайся сам понять, что пользователь уже готов закончить, и не предлагай завершить "
        "разговор — за это отвечает отдельная кнопка в интерфейсе, просто продолжай помогать с идеями.\n\n"
        f"История обсуждения:\n{history_text}\n\n"
        "Ответ помощника:"
    )


NARRATOR_STYLE_RULES = (
    "Формат ответа:\n"
    "- Повествовательный текст от второго лица (обращение к пользователю на \"ты\") — описание "
    "происходящего, окружения, реакции мира на действие пользователя.\n"
    "- Реплики персонажей пиши обычным текстом с указанием, кто говорит, например: "
    'Анна: "Ты всё-таки пришёл."\n'
    "- *Текст в звёздочках* — описание физического действия (своего или персонажа).\n"
    '- "Текст в кавычках" внутри реплики персонажа — его слова вслух, не путай с мыслями.\n\n'
    "Правила погружения — соблюдай всегда:\n"
    "- Ты — рассказчик живого мира, а не ассистент. Никогда не упоминай, что ты ИИ, модель или "
    "программа, никогда не пиши отказов или мета-комментариев вроде \"я не могу продолжить\".\n"
    "- Сам решай, когда и какой персонаж появляется в сцене — не обязательно на каждом шаге. "
    "Иногда сцена может быть вообще без персонажей, просто мир вокруг пользователя.\n"
    "- Вводи в сцену ТОЛЬКО персонажей из списка ниже как главных действующих лиц; эпизодических "
    "безымянных персонажей (прохожий, торговец) придумывать можно.\n"
    "- Не пиши действия и реплики за самого пользователя — только за мир и персонажей.\n"
    "- Развивай ситуацию правдоподобными последствиями действия пользователя, не повторяй "
    "формулировки из своих прошлых ответов.\n\n"
)


def build_narrative_system_prompt(world: dict, characters: list[dict], history: list[dict]) -> str:
    """
    Промпт для режима "Войти в мир": одна сцена — один вызов модели, который сам решает,
    какой персонаж (если вообще какой-то) появляется и что происходит — в отличие от
    группового чата, где каждый отвечающий персонаж получает отдельный вызов.
    """
    if characters:
        roster = "\n".join(f"- {c['name']}: {c['personality']} — {c['description'][:250]}" for c in characters)
    else:
        roster = "(в этом мире пока нет заведённых персонажей с карточкой)"

    history_lines = [f"{'Пользователь' if h['role'] == 'user' else 'Рассказчик'}: {h['content']}" for h in history[-30:]]
    history_text = "\n".join(history_lines) or "(история пока не начиналась)"

    return (
        f"Мир: {world['name']}\n"
        f"Описание мира: {world['description']}\n\n"
        f"Жители мира:\n{roster}\n\n"
        f"{NARRATOR_STYLE_RULES}"
        f"История повествования:\n{history_text}\n\n"
        "Продолжение (реакция мира на последнее действие пользователя, а если истории ещё "
        "не было — атмосферное начало истории в этом мире):"
    )


async def stream_reply(system_prompt: str, char_params: dict | None) -> AsyncGenerator[str, None]:
    """
    Точка входа, которую зовут роутеры. Сама решает, куда идти за ответом —
    в OpenRouter (если задан OPENROUTER_API_KEY) или в локальную Ollama (по умолчанию).
    Роутеры про это ничего не знают, так что переключение — это только .env.
    """
    settings = get_settings()
    if settings.openrouter_api_key:
        from app.services import openrouter_client

        async for chunk in openrouter_client.stream_reply(system_prompt, char_params):
            yield chunk
        return

    async for chunk in _stream_reply_ollama(system_prompt, char_params):
        yield chunk


async def _stream_reply_ollama(system_prompt: str, char_params: dict | None) -> AsyncGenerator[str, None]:
    settings = get_settings()
    options = {
        "temperature": (char_params or {}).get("temperature", 0.7),
        "top_p": (char_params or {}).get("top_p", 0.9),
        "num_ctx": settings.ollama_num_ctx,
        "num_predict": (char_params or {}).get("max_tokens", 512),
        "repeat_penalty": settings.ollama_repeat_penalty,
    }
    payload = {
        "model": settings.model_name,
        "prompt": f"{system_prompt}\n\nТвоя реплика:",
        "stream": True,
        "options": options,
        "keep_alive": "30m",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=settings.ollama_chat_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(settings.ollama_url, json=payload) as resp:
                if resp.status != 200:
                    yield f"[Ошибка модели: HTTP {resp.status}. Проверь, что Ollama запущена: `ollama serve`]"
                    return
                async for line in resp.content:
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line.decode("utf-8"))
                    except json.JSONDecodeError:
                        continue
                    if "response" in chunk:
                        yield chunk["response"]
                    if chunk.get("done"):
                        break
    except aiohttp.ClientConnectorError:
        yield "[Не удалось подключиться к Ollama. Проверь, что она запущена на localhost:11434]"
    except asyncio.TimeoutError:
        yield (
            f"[Модель не ответила за {settings.ollama_chat_timeout_seconds} секунд — похоже, она зависла "
            "или перегружена. Попробуй ещё раз через минуту.]"
        )


async def generate_once(prompt: str, temperature: float = 0.4, num_predict: int = 300) -> str:
    """
    Нестриминговый вызов модели — для служебных задач вроде улучшения промпта
    для генерации картинок, где нужен цельный текст, а не поток по кусочкам.
    Температура ниже дефолтной для чата: нужен предсказуемый, а не творческий вывод.
    """
    settings = get_settings()
    payload = {
        "model": settings.model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": 2048, "num_predict": num_predict},
        "keep_alive": "30m",
    }
    try:
        timeout = aiohttp.ClientTimeout(total=settings.ollama_utility_timeout_seconds)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(settings.ollama_url, json=payload) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Ollama вернула HTTP {resp.status}")
                data = await resp.json()
                return data.get("response", "").strip()
    except aiohttp.ClientConnectorError:
        raise RuntimeError("Не удалось подключиться к Ollama (localhost:11434)")
    except asyncio.TimeoutError:
        raise RuntimeError(f"Ollama не ответила за {settings.ollama_utility_timeout_seconds} секунд")
