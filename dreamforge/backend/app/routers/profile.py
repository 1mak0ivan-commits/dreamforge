from fastapi import APIRouter, Depends, HTTPException

from app.core.image_styles import IMAGE_STYLES
from app.core.telegram_auth import get_current_user
from app.schemas import ProfileIn, StyleIn
from app.services.store import store

router = APIRouter(prefix="/api/profile", tags=["profile"], dependencies=[Depends(get_current_user)])


@router.get("")
async def get_profile():
    return await store.get_profile()


@router.put("")
async def update_profile(payload: ProfileIn):
    return await store.update_profile(payload.name, payload.personality, payload.description)


style_router = APIRouter(prefix="/api/style", tags=["style"], dependencies=[Depends(get_current_user)])


@style_router.get("")
async def get_style():
    return {"current": await store.get_style(), "available": IMAGE_STYLES}


@style_router.put("")
async def set_style(payload: StyleIn):
    if payload.style not in IMAGE_STYLES:
        raise HTTPException(400, "Неизвестный стиль")
    await store.set_style(payload.style)
    return {"status": "ok"}
