from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers import (
    characters,
    chat,
    creation,
    group_chats,
    media,
    narrative,
    profile,
    worlds,
)

settings = get_settings()

app = FastAPI(title="DreamForge API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(worlds.router)
app.include_router(characters.router)
app.include_router(chat.router)
app.include_router(group_chats.router)
app.include_router(creation.router)
app.include_router(narrative.router)
app.include_router(profile.router)
app.include_router(profile.style_router)
app.include_router(media.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
