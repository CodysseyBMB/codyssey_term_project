from __future__ import annotations

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.user_repository import create_user, get_user_by_username
from app.security import hash_password, verify_password
from app.validation import (
    PASSWORD_POLICY_MESSAGE,
    USERNAME_POLICY_MESSAGE,
    is_valid_password,
    is_valid_username,
)


class AuthServiceError(Exception):
    """인증 서비스에서 예상 가능한 실패의 공통 예외."""


class InvalidCredentialFormatError(AuthServiceError):
    def __init__(self, message: str, username: str) -> None:
        super().__init__(message)
        self.username = username


class InvalidCredentialsError(AuthServiceError):
    def __init__(self, username: str) -> None:
        super().__init__("invalid credentials")
        self.username = username


class UsernameAlreadyExistsError(AuthServiceError):
    """이미 등록된 아이디로 회원가입을 시도한 경우."""


def normalize_and_validate_credentials(username: str, password: str) -> str:
    normalized_username = username.strip()
    if not is_valid_username(normalized_username):
        raise InvalidCredentialFormatError(
            USERNAME_POLICY_MESSAGE,
            normalized_username,
        )
    if not is_valid_password(password):
        raise InvalidCredentialFormatError(
            PASSWORD_POLICY_MESSAGE,
            normalized_username,
        )
    return normalized_username


class AuthService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def authenticate(self, username: str, password: str) -> User:
        normalized_username = normalize_and_validate_credentials(username, password)
        user = get_user_by_username(self._session, normalized_username)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError(normalized_username)
        return user

    def register(self, username: str, password: str) -> User:
        normalized_username = normalize_and_validate_credentials(username, password)
        try:
            user = create_user(
                self._session,
                username=normalized_username,
                password_hash=hash_password(password),
            )
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            raise UsernameAlreadyExistsError from exc
        except SQLAlchemyError:
            self._session.rollback()
            raise
        return user
