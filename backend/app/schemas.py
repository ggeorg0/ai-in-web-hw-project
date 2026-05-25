from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=255,
        description="Username for registration/login",
        examples=["alice"],
    )


class UserResponse(BaseModel):
    user_id: UUID = Field(description="Unique user identifier")
    username: str = Field(description="Registered username")


class TaskResponse(BaseModel):
    task_id: UUID = Field(description="Task identifier for status polling")
    status: str = Field(description="Initial task status", examples=["pending"])


class TaskStatusResponse(BaseModel):
    task_id: UUID = Field(description="Task identifier")
    status: str = Field(description="Current task status", examples=["processing", "completed", "failed"])
    audio_text: str | None = Field(None, description="Transcribed audio text")
    extracted_products: list[str] | None = Field(None, description="Lemmatized product names")
    error: str | None = Field(None, description="Error message if task failed")


class ListItemCreate(BaseModel):
    product_name: str = Field(
        min_length=1,
        max_length=255,
        description="Lemmatized product name to add to the list",
        examples=["огурец", "помидор"],
    )


class ListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Item identifier")
    product_name: str = Field(description="Lemmatized product name")
    added_at: datetime = Field(description="Timestamp when item was added")
    source: str = Field(description="How item was added", examples=["voice", "manual"])


class ShoppingListResponse(BaseModel):
    list_id: int = Field(description="Shopping list identifier")
    items: list[ListItemResponse] = Field(description="Items in the shopping list")


class HealthResponse(BaseModel):
    status: str = Field(description="Overall health status", examples=["healthy", "degraded"])
    db: str = Field(description="Database connectivity status", examples=["ok", "error"])
    redis: str = Field(description="Redis connectivity status", examples=["ok", "error"])
    triton: str = Field(description="Triton ASR model readiness", examples=["ok", "error", "not_configured"])
    vllm: str = Field(description="vLLM model readiness", examples=["ok", "error", "not_configured"])
