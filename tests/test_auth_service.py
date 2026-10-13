from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.security import verify_password
from app.services.auth_service import (
    AuthValidationError,
    DuplicateUsernameError,
    InvalidCredentialsError,
    authenticate_user,
    register_user,
)


def test_register_user_normalizes_username_and_hashes_password(
    db_session: Session,
) -> None:
    user = register_user(db_session, "  whale01  ", "sea-shanty-9")

    assert user.username == "whale01"
    assert user.password_hash != "sea-shanty-9"
    assert verify_password("sea-shanty-9", user.password_hash)


def test_register_user_rejects_duplicate_username(db_session: Session) -> None:
    register_user(db_session, "whale01", "sea-shanty-9")

    with pytest.raises(DuplicateUsernameError):
        register_user(db_session, "whale01", "another-pass-9")


def test_authenticate_user_returns_matching_user(db_session: Session) -> None:
    registered = register_user(db_session, "whale01", "sea-shanty-9")

    authenticated = authenticate_user(db_session, "  whale01  ", "sea-shanty-9")

    assert authenticated.id == registered.id


@pytest.mark.parametrize(
    ("username", "password"),
    [("ab", "sea-shanty-9"), ("whale01", "short")],
)
def test_auth_service_rejects_invalid_input(
    db_session: Session, username: str, password: str
) -> None:
    with pytest.raises(AuthValidationError):
        authenticate_user(db_session, username, password)


def test_authenticate_user_rejects_wrong_credentials(db_session: Session) -> None:
    register_user(db_session, "whale01", "sea-shanty-9")

    with pytest.raises(InvalidCredentialsError):
        authenticate_user(db_session, "whale01", "wrong-pass-9")
