from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.security import verify_password
from app.services.auth_service import (
    AuthService,
    InvalidCredentialFormatError,
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
    normalize_and_validate_credentials,
)
from app.validation import PASSWORD_POLICY_MESSAGE, USERNAME_POLICY_MESSAGE


def test_normalize_and_validate_credentials_trims_only_username() -> None:
    password = "  password  "

    username = normalize_and_validate_credentials("  whale01  ", password)

    assert username == "whale01"
    assert password == "  password  "


@pytest.mark.parametrize(
    ("username", "password"),
    [
        ("ab", "sea-shanty-9"),
        ("a" * 21, "sea-shanty-9"),
        ("고래 01", "sea-shanty-9"),
        ("whale01", "short"),
        ("whale01", "a" * 101),
    ],
)
def test_login_and_signup_share_credential_format_validation(
    db_session: Session, username: str, password: str
) -> None:
    service = AuthService(db_session)

    with pytest.raises(InvalidCredentialFormatError):
        service.authenticate(username, password)
    with pytest.raises(InvalidCredentialFormatError):
        service.register(username, password)


@pytest.mark.parametrize(
    ("username", "password", "message"),
    [
        ("고래 01", "sea-shanty-9", USERNAME_POLICY_MESSAGE),
        ("whale01", "short", PASSWORD_POLICY_MESSAGE),
    ],
)
def test_credential_validation_uses_specific_policy_message(
    username: str,
    password: str,
    message: str,
) -> None:
    with pytest.raises(InvalidCredentialFormatError, match=message):
        normalize_and_validate_credentials(username, password)


def test_register_normalizes_username_and_hashes_password(
    db_session: Session,
) -> None:
    service = AuthService(db_session)

    user = service.register("  whale01  ", "sea-shanty-9")

    assert user.username == "whale01"
    assert user.password_hash != "sea-shanty-9"
    assert verify_password("sea-shanty-9", user.password_hash)


def test_authenticate_returns_matching_user(db_session: Session) -> None:
    service = AuthService(db_session)
    registered = service.register("whale01", "sea-shanty-9")

    authenticated = service.authenticate("  whale01  ", "sea-shanty-9")

    assert authenticated.id == registered.id


@pytest.mark.parametrize(
    ("username", "password"),
    [("unknown", "sea-shanty-9"), ("whale01", "wrong-pass-9")],
)
def test_authenticate_rejects_unknown_user_and_wrong_password(
    db_session: Session, username: str, password: str
) -> None:
    service = AuthService(db_session)
    service.register("whale01", "sea-shanty-9")

    with pytest.raises(InvalidCredentialsError):
        service.authenticate(username, password)


def test_register_rolls_back_duplicate_username(db_session: Session) -> None:
    service = AuthService(db_session)
    service.register("whale01", "sea-shanty-9")

    with pytest.raises(UsernameAlreadyExistsError):
        service.register("whale01", "another-pass-9")

    service.register("whale02", "another-pass-9")
    user_count = db_session.scalar(select(func.count()).select_from(User))
    assert user_count == 2
