from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation


def create_conversation(
    session: Session, user_id: int, title: str | None = None
) -> Conversation:
    conversation = Conversation(user_id=user_id, title=title)
    session.add(conversation)
    session.flush()
    return conversation


def get_conversation(
    session: Session, user_id: int, conversation_id: int
) -> Conversation | None:
    """본인 소유의 대화만 반환한다. 다른 사용자의 대화는 존재하지 않는 것처럼 None."""
    statement = select(Conversation).where(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id,
    )
    return session.scalars(statement).one_or_none()


def list_conversations(
    session: Session, user_id: int, limit: int = 20, offset: int = 0
) -> list[Conversation]:
    """본인 대화를 최신순으로 반환한다."""
    statement = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(session.scalars(statement))
