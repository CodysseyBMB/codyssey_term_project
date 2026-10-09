from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.integrations.ai_client import (
    AIProviderError,
    AITimeoutError,
    FakeAIClient,
)
from app.models import Conversation, Message, User
from app.repositories.chat_repository import add_message, create_conversation
from app.services import chat_service as chat_service_module
from app.services.chat_service import (
    ChatPersistenceError,
    ChatService,
    ChatTimeoutError,
    ChatUpstreamError,
)


def run(coro):
    return asyncio.run(coro)


def make_user(session: Session, username: str = "alice") -> User:
    user = User(username=username, password_hash="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def add_pair(session: Session, user_id: int, question: str, answer: str) -> None:
    conversation = create_conversation(session, user_id)
    add_message(session, user_id, conversation.id, "user", question)
    add_message(session, user_id, conversation.id, "assistant", answer)


def count_rows(session: Session, model: type[Conversation] | type[Message]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def test_ask_sends_only_current_question_without_history(db_session: Session) -> None:
    user = make_user(db_session)
    client = FakeAIClient(response="answer")
    service = ChatService(db_session, client, ai_model="test-model")

    result = run(service.ask(user.id, "current question"))

    assert client.received_messages == [
        {"role": "user", "content": "current question"}
    ]
    assert result.answer == "answer"


def test_ask_sends_latest_five_pairs_oldest_first_and_excludes_other_user(
    db_session: Session,
) -> None:
    alice = make_user(db_session, "alice")
    bob = make_user(db_session, "bob")
    for index in range(1, 7):
        add_pair(db_session, alice.id, f"q{index}", f"a{index}")
    add_pair(db_session, bob.id, "bob question", "bob answer")
    db_session.commit()
    client = FakeAIClient(response="new answer")
    service = ChatService(db_session, client, ai_model="test-model")

    run(service.ask(alice.id, "current"))

    assert client.received_messages == [
        {"role": "user", "content": "q2"},
        {"role": "assistant", "content": "a2"},
        {"role": "user", "content": "q3"},
        {"role": "assistant", "content": "a3"},
        {"role": "user", "content": "q4"},
        {"role": "assistant", "content": "a4"},
        {"role": "user", "content": "q5"},
        {"role": "assistant", "content": "a5"},
        {"role": "user", "content": "q6"},
        {"role": "assistant", "content": "a6"},
        {"role": "user", "content": "current"},
    ]


def test_ask_saves_question_and_answer_in_one_new_conversation(
    db_session: Session,
) -> None:
    user = make_user(db_session)
    client = FakeAIClient(response="saved answer")
    service = ChatService(db_session, client, ai_model="test-model")

    result = run(service.ask(user.id, "saved question"))

    conversation = db_session.get(Conversation, result.chat_id)
    assert conversation is not None
    messages = list(
        db_session.scalars(
            select(Message)
            .where(Message.conversation_id == result.chat_id)
            .order_by(Message.id)
        )
    )
    assert [(message.role, message.content) for message in messages] == [
        ("user", "saved question"),
        ("assistant", "saved answer"),
    ]
    assert messages[1].ai_model == "test-model"
    assert messages[1].latency_ms is not None
    assert result.created_at == messages[1].created_at


@pytest.mark.parametrize(
    ("error", "expected_error"),
    [
        (AITimeoutError("timeout"), ChatTimeoutError),
        (AIProviderError(503, "unavailable"), ChatUpstreamError),
    ],
)
def test_ai_failure_does_not_save_partial_conversation(
    db_session: Session,
    error: Exception,
    expected_error: type[Exception],
) -> None:
    user = make_user(db_session)
    client = FakeAIClient(error=error)
    service = ChatService(db_session, client, ai_model="test-model")

    with pytest.raises(expected_error):
        run(service.ask(user.id, "question"))

    assert count_rows(db_session, Conversation) == 0
    assert count_rows(db_session, Message) == 0


def test_second_message_failure_rolls_back_entire_conversation(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    user = make_user(db_session)
    client = FakeAIClient(response="answer")
    service = ChatService(db_session, client, ai_model="test-model")
    original_add_message = chat_service_module.add_message
    call_count = 0

    def fail_on_second_message(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise SQLAlchemyError("simulated write failure")
        return original_add_message(*args, **kwargs)

    monkeypatch.setattr(chat_service_module, "add_message", fail_on_second_message)

    with pytest.raises(ChatPersistenceError):
        run(service.ask(user.id, "question"))

    assert count_rows(db_session, Conversation) == 0
    assert count_rows(db_session, Message) == 0
