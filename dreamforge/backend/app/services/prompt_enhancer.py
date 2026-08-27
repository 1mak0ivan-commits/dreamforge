"""
Превращает человеческое описание персонажа/сцены в грамотный промпт для Stable Diffusion.

Два уровня:
1. "Визуальная идентичность" персонажа — стабильный набор тегов внешности
   (причёска, глаза, одежда, телосложение), сгенерированный один раз из description
   и сохранённый у персонажа. Используется как якорь в КАЖДОЙ последующей картинке,
   чтобы персонаж выглядел одинаково от сцены к сцене, а не рисовался заново каждый раз.
2. "Промпт сцены" — для конкретной иллюстрации: visual_identity персонажа + что
   происходит в сцене + позитивные/негативные теги качества.

Модель просят отвечать JSON-строкой — компактно и легко парсить, без лишней болтовни.
"""
from app.services.json_utils import extract_json
from app.services.llm import generate_once

DEFAULT_NEGATIVE = (
    "low quality, worst quality, blurry, deformed, disfigured, bad anatomy, "
    "extra limbs, extra fingers, mutated hands, watermark, text, signature, "
    "jpeg artifacts, cropped, out of frame"
)

QUALITY_BOOST = "masterpiece, best quality, highly detailed, sharp focus"


async def build_visual_identity(name: str, personality: str, description: str) -> str:
    """Из свободного текстового описания персонажа делает устойчивый список тегов внешности на английском."""
    prompt = (
        "You are a prompt engineer preparing a character sheet for Stable Diffusion image generation.\n"
        "Read the character description below (it may be in Russian or any language) and extract ONLY "
        "the character's fixed PHYSICAL APPEARANCE as a comma-separated list of concise English tags: "
        "hair color/style, eye color, face, body build, skin tone, typical clothing, distinguishing features. "
        "Do NOT include personality, backstory, actions, or scene details. "
        "Output ONLY the comma-separated tag list, nothing else, 12-25 tags.\n\n"
        f"Character name: {name}\n"
        f"Personality: {personality}\n"
        f"Description: {description}\n\n"
        "Appearance tags:"
    )
    try:
        text = await generate_once(prompt, temperature=0.3, num_predict=200)
    except RuntimeError:
        # Ollama недоступна — откатываемся на грубый вариант, лучше кривой промпт, чем падение.
        return description[:300]
    cleaned = text.strip().strip("`").replace("\n", ", ")
    return cleaned or description[:300]


async def build_scene_prompt(visual_identity: str, scene_context: str) -> tuple[str, str]:
    """Собирает позитивный и негативный промпт для конкретной сцены на основе идентичности персонажа."""
    prompt = (
        "You are a prompt engineer for Stable Diffusion. Combine a character's fixed appearance tags "
        "with a scene description (from a roleplay chat, any language) into an image generation prompt.\n"
        'Respond with STRICT JSON only, no commentary, in this exact shape: '
        '{"positive": "tag, tag, tag", "negative": "tag, tag, tag"}\n'
        "positive: the character's appearance tags first, then scene/pose/setting/lighting tags in English, "
        "then quality tags at the end.\n"
        "negative: standard image-quality negatives, plus anything specifically wrong to avoid for this scene.\n\n"
        f"Character appearance tags: {visual_identity}\n"
        f"Scene context: {scene_context[:300]}\n\n"
        "JSON:"
    )
    try:
        text = await generate_once(prompt, temperature=0.4, num_predict=350)
    except RuntimeError:
        return f"{visual_identity}, {scene_context[:150]}, {QUALITY_BOOST}", DEFAULT_NEGATIVE

    parsed = extract_json(text)
    if not parsed or "positive" not in parsed:
        # Модель не вернула валидный JSON — собираем промпт сами, не проваливаем генерацию.
        return f"{visual_identity}, {scene_context[:150]}, {QUALITY_BOOST}", DEFAULT_NEGATIVE

    positive = f"{parsed['positive']}, {QUALITY_BOOST}"
    negative = parsed.get("negative") or DEFAULT_NEGATIVE
    return positive, negative


async def build_world_visual_prompt(name: str, description: str) -> tuple[str, str]:
    """
    В отличие от портрета персонажа — тут широкий план ОКРУЖЕНИЯ: пейзаж, архитектура,
    атмосфера, свет. Явно просим модель не фокусироваться на персонаже/существе в кадре.
    """
    prompt = (
        "You are a prompt engineer for Stable Diffusion. Based on a fictional world's description below "
        "(it may be in Russian or any language), produce an image generation prompt for an atmospheric "
        "ESTABLISHING SHOT of the world's environment and setting — landscape, architecture, mood, lighting, "
        "art style. Do NOT focus on a specific character or creature as the subject; this is a place, not a portrait.\n"
        'Respond with STRICT JSON only, no commentary: {"positive": "tag, tag, tag", "negative": "tag, tag, tag"}\n'
        "positive: English tags describing scenery, architecture, atmosphere, lighting, art style, "
        "then quality tags at the end.\n"
        "negative: standard image-quality negatives, plus anything that would wrongly put a character portrait "
        "front and center.\n\n"
        f"World name: {name}\n"
        f"Description: {description[:800]}\n\n"
        "JSON:"
    )
    fallback_positive = f"{name}, {description[:200]}, wide establishing shot, atmospheric, {QUALITY_BOOST}"
    try:
        text = await generate_once(prompt, temperature=0.4, num_predict=350)
    except RuntimeError:
        return fallback_positive, DEFAULT_NEGATIVE

    parsed = extract_json(text)
    if not parsed or "positive" not in parsed:
        return fallback_positive, DEFAULT_NEGATIVE

    positive = f"{parsed['positive']}, {QUALITY_BOOST}"
    negative = parsed.get("negative") or DEFAULT_NEGATIVE
    return positive, negative
