from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Annotated
from datetime import datetime, timezone
from pydantic.functional_validators import BeforeValidator


# Handle MongoDB ObjectId as string
PyObjectId = Annotated[str, BeforeValidator(str)]


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant" or "system"
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))


class DocumentMetadata(BaseModel):
    filename: str
    content_type: str
    size: int
    uploaded_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))


class ChatSession(BaseModel):
    id: Optional[PyObjectId] = Field(alias="_id", default=None)
    title: Optional[str] = "New Chat"
    messages: List[ChatMessage] = []
    documents: List[DocumentMetadata] = []
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )
