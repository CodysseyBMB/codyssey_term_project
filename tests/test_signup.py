from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.security import verify_password


def test_signup_success_hashes_password(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/auth/signup",
        data={"username": "whale01", "password": "sea-shanty-9"},
        follow_redirects=False,  # 리다이렉트를 따라가지 않고 303 자체를 확인
    )

    assert response.status_code == 303

    # DB에 직접 들어가서 저장된 값을 확인 — 완료 조건 1번 검증
    user = db_session.scalar(select(User).where(User.username == "whale01"))
    assert user is not None
    assert user.password_hash != "sea-shanty-9"  # 평문 그대로면 안 된다
    assert verify_password("sea-shanty-9", user.password_hash)


def test_signup_rejects_duplicate_username(client: TestClient) -> None:
    # 완료 조건 2번 검증: 같은 아이디로 두 번 가입하면 두 번째는 거부
    payload = {"username": "whale02", "password": "sea-shanty-9"}
    client.post("/auth/signup", data=payload)

    response = client.post("/auth/signup", data=payload)

    assert response.status_code == 409


def test_signup_rejects_short_password(client: TestClient) -> None:
    # 입력 검증 요구사항: 최소 1개 이상의 검증 로직이 있어야 한다
    response = client.post(
        "/auth/signup",
        data={"username": "whale03", "password": "short"},
    )

    assert response.status_code == 422