"""
Стили генерации изображений. Ключ — id стиля (используется во фронте и данных),
значение — имя чекпоинта в Stable Diffusion WebUI.
Отредактируй под свои реальные файлы моделей.
"""

IMAGE_STYLES: dict[str, dict] = {
    "realistic": {
        "label": "Реализм",
        "checkpoint": "sd\\cyberrealistic_final.safetensors",
    },
    "anime": {
        "label": "Аниме",
        "checkpoint": "sd\\itnsGreatestHits_v20.safetensors",
    },
}

DEFAULT_STYLE = "realistic"
