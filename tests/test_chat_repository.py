from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.chat_repository import (
    ConversationNotFoundError,
    add_message,
    create_conversation,
    get_conversation,
    list_conversations,
    list_messages,
    list_recent_messages,
)


def make_user(session: Session, username: str) -> User:
    user = User(username=username, password_hash="hashed")
    session.add(user)
    session.flush()
    return user


def test_create_and_get_own_conversation(db_session: Session) -> None:
    alice = make_user(db_session, "alice")

    created = create_conversation(db_session, alice.id, title="첫 대화")
    found = get_conversation(db_session, alice.id, created.id)

    assert found is not None
    assert found.id == created.id
    assert found.title == "첫 대화"


def test_get_conversation_hides_other_users_conversation(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    alice_conversation = create_conversation(db_session, alice.id)

    assert get_conversation(db_session, bob.id, alice_conversation.id) is None


def test_get_conversation_returns_none_for_unknown_id(db_session: Session) -> None:
    alice = make_user(db_session, "alice")

    assert get_conversation(db_session, alice.id, 999_999) is None


def test_list_conversations_returns_only_own_newest_first(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    first = create_conversation(db_session, alice.id, title="first")
    second = create_conversation(db_session, alice.id, title="second")
    create_conversation(db_session, bob.id, title="bob's")

    conversations = list_conversations(db_session, alice.id)

    assert [c.id for c in conversations] == [second.id, first.id]


def test_list_conversations_supports_limit_and_offset(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    created = [create_conversation(db_session, alice.id) for _ in range(3)]

    page = list_conversations(db_session, alice.id, limit=1, offset=1)

    assert [c.id for c in page] == [created[1].id]


def test_list_conversations_is_empty_for_new_user(db_session: Session) -> None:
    alice = make_user(db_session, "alice")

    assert list_conversations(db_session, alice.id) == []


def test_add_and_list_messages_in_order(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    conversation = create_conversation(db_session, alice.id)

    add_message(db_session, alice.id, conversation.id, "user", "질문")
    add_message(
        db_session,
        alice.id,
        conversation.id,
        "assistant",
        "답변",
        ai_model="test-model",
        latency_ms=42,
    )
    messages = list_messages(db_session, alice.id, conversation.id)

    assert [(m.role, m.content) for m in messages] == [
        ("user", "질문"),
        ("assistant", "답변"),
    ]
    assert messages[1].ai_model == "test-model"
    assert messages[1].latency_ms == 42


def test_add_message_rejects_other_users_conversation(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    conversation = create_conversation(db_session, alice.id)

    with pytest.raises(ConversationNotFoundError):
        add_message(db_session, bob.id, conversation.id, "user", "침입")

    assert list_messages(db_session, alice.id, conversation.id) == []


def test_list_messages_hides_other_users_messages(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    conversation = create_conversation(db_session, alice.id)
    add_message(db_session, alice.id, conversation.id, "user", "비밀 질문")

    assert list_messages(db_session, bob.id, conversation.id) == []


def test_list_messages_is_scoped_to_one_conversation(db_session: Session) -> None:
    alice = make_user(db_session, "alice")
    first = create_conversation(db_session, alice.id)
    second = create_conversation(db_session, alice.id)
    add_message(db_session, alice.id, first.id, "user", "첫 대화")
    add_message(db_session, alice.id, second.id, "user", "둘째 대화")

    messages = list_messages(db_session, alice.id, first.id)

    assert [m.content for m in messages] == ["첫 대화"]


def test_message_added_to_own_conversation_is_visible_via_get(
    db_session: Session,
) -> None:
    alice = make_user(db_session, "alice")
    conversation = create_conversation(db_session, alice.id)
    add_message(db_session, alice.id, conversation.id, "user", "질문")
    db_session.refresh(conversation)

    found = get_conversation(db_session, alice.id, conversation.id)

    assert found is not None
    assert [m.content for m in found.messages] == ["질문"]


def test_list_recent_messages_returns_latest_conversations_in_chronological_order(
    db_session: Session,
) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    for index in range(1, 7):
        conversation = create_conversation(db_session, alice.id)
        add_message(db_session, alice.id, conversation.id, "user", f"q{index}")
        add_message(db_session, alice.id, conversation.id, "assistant", f"a{index}")
    bob_conversation = create_conversation(db_session, bob.id)
    add_message(db_session, bob.id, bob_conversation.id, "user", "bob question")
    add_message(db_session, bob.id, bob_conversation.id, "assistant", "bob answer")

    messages = list_recent_messages(db_session, alice.id, conversation_limit=5)

    assert [(message.role, message.content) for message in messages] == [
        ("user", "q2"),
        ("assistant", "a2"),
        ("user", "q3"),
        ("assistant", "a3"),
        ("user", "q4"),
        ("assistant", "a4"),
        ("user", "q5"),
        ("assistant", "a5"),
        ("user", "q6"),
        ("assistant", "a6"),
    ]
