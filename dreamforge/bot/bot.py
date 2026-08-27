"""
Бот теперь "тонкий": вся логика (чат, создание персонажей и миров, профиль,
генерация картинок) происходит внутри мини-аппа через прямые запросы к бэкенду.
Бот только открывает мини-апп и может присылать уведомления.

Секреты берутся из .env — см. .env.example рядом.
"""
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ["BOT_TOKEN"]  # намеренно падаем, если токен не задан — не запускаемся без секрета
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://example.com")  # публичный URL фронтенда (ngrok/домен)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


def webapp_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✨ Открыть DreamForge", web_app=WebAppInfo(url=WEBAPP_URL))]]
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Добро пожаловать в DreamForge — твои миры и персонажи ждут внутри.\n\n"
        "Нажми кнопку ниже, чтобы открыть приложение.",
        reply_markup=webapp_keyboard(),
    )


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    await message.answer("Открыть DreamForge:", reply_markup=webapp_keyboard())


async def main():
    logging.info("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
