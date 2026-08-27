from fastapi import APIRouter, Depends, HTTPException

from app.core.telegram_auth import get_current_user
from app.schemas import AvatarGenerateIn, CharacterIn, CharacterPatch
from app.services import imagegen, prompt_enhancer
from app.services.store import store

router = APIRouter(prefix="/api/characters", tags=["characters"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_characters():
    data = await store.get_all()
    return data["characters"]


@router.post("/generate-avatar")
async def generate_avatar(payload: AvatarGenerateIn):
    """
    Генерирует портрет персонажа по его описанию и заодно закрепляет
    'визуальную идентичность' (теги внешности) — её вернём фронту, чтобы
    он сохранил её вместе с персонажем и переиспользовал во всех сценах.
    """
    visual_identity = await prompt_enhancer.build_visual_identity(payload.name, payload.personality, payload.description)
    positive, negative = await prompt_enhancer.build_scene_prompt(
        visual_identity, "portrait, headshot, looking at viewer, neutral background"
    )
    style = await store.get_style()
    try:
        filename = await imagegen.generate_image(positive, style, negative)
    except imagegen.ImageGenError as e:
        raise HTTPException(502, str(e))
    return {"avatar_path": filename, "visual_identity": visual_identity}


@router.get("/{char_id}")
async def get_character(char_id: str):
    char = await store.get_character(char_id)
    if not char:
        raise HTTPException(404, "Персонаж не найден")
    return char


@router.post("")
async def create_character(payload: CharacterIn):
    return await store.create_character(payload.model_dump())


@router.patch("/{char_id}")
async def update_character(char_id: str, payload: CharacterPatch):
    patch = payload.model_dump(exclude_unset=True)
    char = await store.update_character(char_id, patch)
    if not char:
        raise HTTPException(404, "Персонаж не найден")
    return char


@router.delete("/{char_id}")
async def delete_character(char_id: str):
    await store.delete_character(char_id)
    return {"status": "ok"}


@router.post("/{char_id}/remove-from-world")
async def remove_from_world(char_id: str):
    await store.remove_character_from_world(char_id)
    return {"status": "ok"}


@router.post("/{char_id}/memory")
async def add_memory(char_id: str, fact: str):
    await store.append_memory(char_id, fact)
    return {"status": "ok"}
