from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Conversation, Message


class ConversationNotFoundError(LookupError):
    """대화가 없거나 요청한 사용자의 소유가 아닐 때 발생한다."""


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


def add_message(
    session: Session,
    user_id: int,
    conversation_id: int,
    role: str,
    content: str,
    ai_model: str | None = None,
    latency_ms: int | None = None,
) -> Message:
    """본인 대화에만 메시지를 추가한다. 소유자가 아니면 ConversationNotFoundError."""
    conversation = get_conversation(session, user_id, conversation_id)
    if conversation is None:
        raise ConversationNotFoundError(conversation_id)
    message = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        ai_model=ai_model,
        latency_ms=latency_ms,
    )
    session.add(message)
    session.flush()
    return message


def list_messages(
    session: Session, user_id: int, conversation_id: int
) -> list[Message]:
    """본인 대화의 메시지를 시간순으로 반환한다. 소유자가 아니면 빈 목록."""
    statement = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .where(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        )
        .order_by(Message.created_at, Message.id)
    )
    return list(session.scalars(statement))


def list_recent_messages(
    session: Session, user_id: int, conversation_limit: int = 5
) -> list[Message]:
    """사용자의 최근 대화 메시지를 선택한 뒤 오래된 순서로 반환한다."""
    recent_conversations = (
        select(Conversation.id)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(conversation_limit)
        .subquery()
    )
    statement = (
        select(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .join(
            recent_conversations,
            recent_conversations.c.id == Conversation.id,
        )
        .order_by(
            Conversation.created_at,
            Conversation.id,
            Message.created_at,
            Message.id,
        )
    )
    return list(session.scalars(statement))
