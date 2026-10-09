from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.security import hash_password
from tests.helpers import get_csrf_token, get_header_csrf_token


def create_user(db_session: Session, username: str = "whale01") -> User:
    user = User(
        username=username,
        password_hash=hash_password("sea-shanty-9"),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def login(client: TestClient, username: str = "whale01", password: str = "sea-shanty-9") -> None:
    csrf_token = get_csrf_token(client, "/auth/login")
    response = client.post(
        "/auth/login",
        data={"username": username, "password": password, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_chat_page_redirects_anonymous_user_to_login(client: TestClient) -> None:
    response = client.get("/chat", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_chat_page_renders_for_authenticated_user(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)
    login(client)

    response = client.get("/chat")

    assert response.status_code == 200
    assert "data-csrf-token" in response.text
    assert "chat-form" in response.text


def test_api_chat_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/chat", json={"question": "안녕"})

    assert response.status_code == 401


def test_api_chat_requires_csrf_header(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)
    login(client)

    response = client.post("/api/chat", json={"question": "안녕"})

    assert response.status_code == 403


def test_api_chat_rejects_blank_question(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)
    login(client)
    csrf_token = get_header_csrf_token(client, "/chat")

    response = client.post(
        "/api/chat",
        json={"question": "   "},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["request_id"]


def test_api_chat_rejects_question_over_length_limit(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)
    login(client)
    csrf_token = get_header_csrf_token(client, "/chat")

    response = client.post(
        "/api/chat",
        json={"question": "a" * 2001},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 422


def test_api_chat_returns_stub_answer_for_valid_question(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session)
    login(client)
    csrf_token = get_header_csrf_token(client, "/chat")

    response = client.post(
        "/api/chat",
        json={"question": "  FastAPI 세션이 뭐야?  "},
        headers={"X-CSRF-Token": csrf_token},
    )

    assert response.status_code == 200
    body = response.json()
    # 앞뒤 공백은 trim된 채로 응답에 반영된다 (서버가 trim된 값을 돌려받아 처리했다는 증거).
    assert "FastAPI 세션이 뭐야?" in body["answer"]
    assert body["request_id"]
    assert body["created_at"]
