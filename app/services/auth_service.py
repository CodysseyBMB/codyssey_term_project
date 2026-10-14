from __future__ import annotations

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import User
from app.repositories.auth_repository import create_user, get_user_by_username
from app.security import hash_password, verify_password


CREDENTIAL_FORMAT_MESSAGE = (
    "아이디는 3~20자, 비밀번호는 8~100자 사이로 입력해주세요."
)


class AuthServiceError(Exception):
    """인증 서비스에서 예상 가능한 실패의 공통 예외."""


class InvalidCredentialFormatError(AuthServiceError):
    def __init__(self, username: str) -> None:
        super().__init__(CREDENTIAL_FORMAT_MESSAGE)
        self.username = username


class InvalidCredentialsError(AuthServiceError):
    def __init__(self, username: str) -> None:
        super().__init__("invalid credentials")
        self.username = username


class UsernameAlreadyExistsError(AuthServiceError):
    """이미 등록된 아이디로 회원가입을 시도한 경우."""


def normalize_and_validate_credentials(username: str, password: str) -> str:
    normalized_username = username.strip()
    if not (3 <= len(normalized_username) <= 20) or not (
        8 <= len(password) <= 100
    ):
        raise InvalidCredentialFormatError(normalized_username)
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
