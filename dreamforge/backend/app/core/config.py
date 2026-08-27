"""
Центральная конфигурация. Все секреты и адреса берутся из переменных окружения (.env),
а не хранятся в коде — см. backend/.env.example.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", protected_namespaces=("settings_",)
    )

    # --- Telegram ---
    bot_token: str = ""
    # Разрешить запуск без проверки initData (только для локальной разработки в браузере!)
    dev_mode: bool = True

    # --- LLM (Ollama) ---
    ollama_url: str = "http://localhost:11434/api/generate"
    model_name: str = "llama3.1:8b-instruct-q4_K_M"
    max_history_messages: int = 20
    memory_extract_every: int = 4
    summary_update_every: int = 20
    # Размер контекстного окна модели. Если системный промпт (персонаж + мир + память +
    # резюме + история) не помещается сюда, модель начинает "терять нить": повторяться,
    # путать, кто что сказал, зацикливаться. Подними, если видишь такое поведение и
    # железо/модель позволяют — но учти, что больше окно = больше видеопамяти и медленнее.
    ollama_num_ctx: int = 4096
    # Штраф за повторение уже сказанных слов/фраз. 1.0 = выключено. Без него локальные
    # модели (особенно небольшие/квантованные) склонны залипать в одних и тех же
    # формулировках — это самая частая причина ощущения "повторяется и несёт чушь".
    ollama_repeat_penalty: float = 1.15
    # Таймауты на запросы к Ollama — без них зависшая модель держит блокировку персонажа
    # вечно (пока не перезапустишь сервер). Чат может честно занимать минуты на слабом железе,
    # служебные вызовы (память/резюме/промпт для картинок) должны быть куда быстрее.
    ollama_chat_timeout_seconds: int = 180
    ollama_utility_timeout_seconds: int = 180

    # --- OpenRouter (необязательно) ---
    # Если задан ключ — реплики персонажей (не служебные вызовы вроде памяти/резюме/
    # промптов для картинок, они остаются на Ollama) идут через OpenRouter вместо
    # локальной модели. Пусто = поведение как раньше, только Ollama.
    # Актуальный слаг модели смотри на openrouter.ai/models — они периодически меняются,
    # дефолт ниже может устареть.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat"

    # --- Генерация изображений (Stable Diffusion WebUI API) ---
    image_api_url: str = "http://127.0.0.1:7860/sdapi/v1/txt2img"
    image_generate_every: int = 10

    # --- Пути ---
    data_file: str = "data.json"
    upload_dir: str = "uploads"

    # --- CORS ---
    cors_origins: list[str] = ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
