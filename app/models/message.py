from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.conversation import Conversation

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
MESSAGE_ROLES = (ROLE_USER, ROLE_ASSISTANT)


class Message(Base):
    """대화에 속한 메시지 한 건. role은 사용자 질문(user) 또는 AI 답변(assistant)이다."""

    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_messages_role",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    # AI 답변(assistant)에만 채워지는 장애 추적용 정보
    ai_model: Mapped[str | None] = mapped_column(String(100))
    latency_ms: Mapped[int | None]

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
