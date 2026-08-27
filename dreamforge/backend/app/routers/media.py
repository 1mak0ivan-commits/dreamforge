import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.telegram_auth import get_current_user
from app.services import imagegen
from app.services.store import store

router = APIRouter(prefix="/api", tags=["media"], dependencies=[Depends(get_current_user)])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD_BYTES = 8 * 1024 * 1024  # 8 МБ


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "Разрешены только jpg, png, webp")

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "Файл слишком большой (максимум 8 МБ)")

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    (upload_dir / filename).write_bytes(content)
    return {"filename": filename}


class GenerateImageIn(BaseModel):
    prompt: str


@router.post("/generate-image")
async def generate_image_endpoint(payload: GenerateImageIn):
    style = await store.get_style()
    try:
        filename = await imagegen.generate_image(payload.prompt, style)
    except imagegen.ImageGenError as e:
        raise HTTPException(502, str(e))
    return {"filename": filename}
