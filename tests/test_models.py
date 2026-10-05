from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Conversation, Message, User


# db_session fixture와 테스트 시작 전 TRUNCATE(users CASCADE → 하위 테이블 포함)는
# conftest.py가 제공한다. 세션은 commit하지 않고 닫히므로 flush한 데이터는 롤백된다.


def make_user(username: str = "alice") -> User:
    return User(username=username, password_hash="hashed")


def test_conversation_is_saved_with_defaults(db_session: Session) -> None:
    user = make_user()
    conversation = Conversation(user=user)
    db_session.add(conversation)
    db_session.flush()
    db_session.refresh(conversation)

    assert conversation.id is not None
    assert conversation.user_id == user.id
    assert conversation.title is None
    assert conversation.created_at is not None
    assert conversation.messages == []


def test_message_is_saved_with_defaults(db_session: Session) -> None:
    conversation = Conversation(user=make_user(), title="첫 대화")
    message = Message(conversation=conversation, role="user", content="안녕?")
    db_session.add(message)
    db_session.flush()
    db_session.refresh(message)

    assert message.id is not None
    assert message.conversation_id == conversation.id
    assert message.created_at is not None
    assert message.ai_model is None
    assert message.latency_ms is None


def test_assistant_message_stores_tracking_fields(db_session: Session) -> None:
    conversation = Conversation(user=make_user())
    message = Message(
        conversation=conversation,
        role="assistant",
        content="안녕하세요!",
        ai_model="test-model",
        latency_ms=123,
    )
    db_session.add(message)
    db_session.flush()

    assert message.ai_model == "test-model"
    assert message.latency_ms == 123


def test_conversation_messages_follow_insert_order(db_session: Session) -> None:
    conversation = Conversation(user=make_user())
    conversation.messages.extend(
        [
            Message(role="user", content="질문"),
            Message(role="assistant", content="답변"),
        ]
    )
    db_session.add(conversation)
    db_session.flush()
    db_session.refresh(conversation)

    assert [m.role for m in conversation.messages] == ["user", "assistant"]
    assert conversation.messages[0].conversation is conversation


def test_message_role_must_be_user_or_assistant(db_session: Session) -> None:
    conversation = Conversation(user=make_user())
    db_session.add(Message(conversation=conversation, role="system", content="x"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_conversation_requires_existing_user(db_session: Session) -> None:
    db_session.add(Conversation(user_id=999_999))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_message_requires_content(db_session: Session) -> None:
    conversation = Conversation(user=make_user())
    db_session.add(Message(conversation=conversation, role="user"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_conversation_removes_its_messages(db_session: Session) -> None:
    conversation = Conversation(user=make_user())
    conversation.messages.append(Message(role="user", content="질문"))
    db_session.add(conversation)
    db_session.flush()

    db_session.delete(conversation)
    db_session.flush()

    assert db_session.scalars(select(Message)).all() == []
