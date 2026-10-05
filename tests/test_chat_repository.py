from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import User
from app.repositories.chat_repository import (
    create_conversation,
    get_conversation,
    list_conversations,
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
