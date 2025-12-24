from datetime import datetime, timezone
from typing import Annotated
from pydantic import BaseModel, Field, ConfigDict
from pydantic.functional_validators import BeforeValidator

# Handle MongoDB ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_deleted: bool = False


class DocumentMetadata(BaseModel):
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_deleted: bool = False


class ChatSession(BaseModel):
    id: PyObjectId | None = Field(alias="_id", default=None)
    title: str | None = "New Chat"
    messages: list[ChatMessage] = []
    documents: list[DocumentMetadata] = []
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    is_deleted: bool = False

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
