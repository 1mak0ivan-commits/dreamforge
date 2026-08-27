"""
Два фоновых процесса, которые держат долгий диалог "живым", не раздувая промпт:

1. Память: раз в несколько сообщений модель сама решает, есть ли в последнем обмене
   репликами что-то устойчивое и достойное запомнить о пользователе (имя, предпочтение,
   деталь биографии) — и если да, добавляет один факт в память персонажа.
2. Резюме: раз в N сообщений вся история (кроме недавнего хвоста) сжимается в 2-4
   предложения, которые держатся в промпте постоянно — так персонаж не "забывает"
   начало долгого разговора, даже если сырые сообщения из промпта уже выпали.

Обе функции немые к сбоям Ollama — если модель недоступна, просто ничего не делаем,
не роняя основной чат.
"""
from app.services.llm import generate_once

MAX_MEMORY_FACTS = 20


async def extract_memory_fact(user_message: str, assistant_reply: str, existing_memory: list[str]) -> str | None:
    existing_text = "\n".join(f"- {m}" for m in existing_memory) if existing_memory else "(пока пусто)"
    prompt = (
        "Ты помогаешь ролевому ИИ-персонажу вести долговременную память о пользователе.\n"
        "Посмотри на последний обмен репликами и реши, есть ли там КОНКРЕТНЫЙ устойчивый факт "
        "о пользователе, достойный запоминания надолго (имя, черта характера, предпочтение, "
        "событие из жизни, отношение к чему-либо). Мимолётные детали текущей сцены не считаются.\n"
        "Если такой факт есть — выведи ОДНО короткое предложение на русском с этим фактом.\n"
        "Если ничего нового и существенного нет — выведи ровно: NONE\n\n"
        f"Уже есть в памяти:\n{existing_text}\n\n"
        f"Пользователь написал: {user_message}\n"
        f"Персонаж ответил: {assistant_reply}\n\n"
        "Факт (или NONE):"
    )
    try:
        text = await generate_once(prompt, temperature=0.3, num_predict=80)
    except RuntimeError:
        return None
    text = text.strip().strip('"')
    if not text or text.upper().startswith("NONE"):
        return None
    return text


async def update_summary(existing_summary: str, older_messages: list[dict], char_name: str) -> str | None:
    if not older_messages:
        return None
    lines = [f"{'Пользователь' if m['role'] == 'user' else char_name}: {m['content']}" for m in older_messages]
    history_text = "\n".join(lines)
    prompt = (
        f"Ты сжимаешь предысторию ролевого разговора с персонажем по имени {char_name} в короткое резюме.\n"
        "Резюме нужно персонажу как краткая память о том, что уже происходило, до недавних сообщений.\n"
        "Пиши 2-4 предложения на русском, только ключевые события и развитие отношений, без диалогов дословно.\n\n"
        f"Предыдущее резюме (если было): {existing_summary or '(пусто)'}\n\n"
        f"Новые сообщения для добавления в резюме:\n{history_text}\n\n"
        "Обновлённое резюме:"
    )
    try:
        text = await generate_once(prompt, temperature=0.3, num_predict=220)
    except RuntimeError:
        return None
    return text.strip() or None
