from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    username: str


class UserResponse(BaseModel):
    user_id: UUID
    username: str


class TaskResponse(BaseModel):
    task_id: UUID
    status: str


class TaskStatusResponse(BaseModel):
    task_id: UUID
    status: str
    audio_text: str | None = None
    extracted_products: list[str] | None = None
    error: str | None = None


class ListItemCreate(BaseModel):
    product_name: str


class ListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_name: str
    added_at: datetime
    source: str


class ShoppingListResponse(BaseModel):
    list_id: int
    items: list[ListItemResponse]
