from fastapi import APIRouter, Depends, HTTPException

from app.core.telegram_auth import get_current_user
from app.schemas import WorldImageGenerateIn, WorldIn, WorldPatch
from app.services import imagegen, prompt_enhancer
from app.services.store import store

router = APIRouter(prefix="/api/worlds", tags=["worlds"], dependencies=[Depends(get_current_user)])


@router.get("")
async def list_worlds():
    data = await store.get_all()
    return data["worlds"]


@router.post("/generate-image")
async def generate_world_image(payload: WorldImageGenerateIn):
    """Генерирует атмосферное изображение окружения мира по названию и описанию."""
    positive, negative = await prompt_enhancer.build_world_visual_prompt(payload.name, payload.description)
    style = await store.get_style()
    try:
        filename = await imagegen.generate_image(positive, style, negative)
    except imagegen.ImageGenError as e:
        raise HTTPException(502, str(e))
    return {"image_path": filename}


@router.get("/{world_id}")
async def get_world(world_id: str):
    world = await store.get_world(world_id)
    if not world:
        raise HTTPException(404, "Мир не найден")
    data = await store.get_all()
    characters = [c for c in data["characters"] if c.get("world_id") == world_id]
    return {**world, "characters": characters}


@router.post("")
async def create_world(payload: WorldIn):
    return await store.create_world(payload.name, payload.description, payload.image_path)


@router.patch("/{world_id}")
async def update_world(world_id: str, payload: WorldPatch):
    world = await store.update_world(world_id, payload.name, payload.description, payload.image_path)
    if not world:
        raise HTTPException(404, "Мир не найден")
    return world


@router.delete("/{world_id}")
async def delete_world(world_id: str):
    await store.delete_world(world_id)
    return {"status": "ok"}
