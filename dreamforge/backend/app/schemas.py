from typing import Literal

from pydantic import BaseModel, Field


class WorldIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=4000)
    image_path: str | None = None


class WorldPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    image_path: str | None = None


class WorldImageGenerateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=4000)


class GenerationParams(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None


class CharacterIn(BaseModel):
    world_id: str | None = None
    name: str = Field(min_length=1, max_length=60)
    personality: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=4000)
    greeting: str = Field(default="", max_length=1000)
    avatar_path: str | None = None
    visual_identity: str | None = None


class CharacterPatch(BaseModel):
    world_id: str | None = None
    name: str | None = None
    personality: str | None = None
    description: str | None = None
    greeting: str | None = None
    avatar_path: str | None = None
    visual_identity: str | None = None
    generation_params: GenerationParams | None = None


class AvatarGenerateIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    personality: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=4000)


class ProfileIn(BaseModel):
    name: str = Field(default="Пользователь", max_length=60)
    personality: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=1000)


class ChatMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class StyleIn(BaseModel):
    style: str


class GroupChatIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    character_ids: list[str] = Field(min_length=2, max_length=6)


class GroupMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    # None/"all" — отвечают все персонажи по очереди; конкретный id — отвечает только он.
    target_character_id: str | None = None


class CreationStartIn(BaseModel):
    kind: Literal["world", "character"]
    world_id: str | None = None  # только для character — необязательно привязать к существующему миру


class CreationMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)


class NarrativeMessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
