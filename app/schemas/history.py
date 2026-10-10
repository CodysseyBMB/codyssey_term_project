from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ChatHistoryItem(BaseModel):
    chat_id: int
    question: str
    answer: str
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    items: list[ChatHistoryItem]
    limit: int
    offset: int
    has_more: bool
