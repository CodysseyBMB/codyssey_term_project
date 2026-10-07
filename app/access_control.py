from __future__ import annotations

import secrets

from fastapi import Depends, Form, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User


CSRF_SESSION_KEY = "csrf_token"


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    """Return the current database user without trusting the cookie alone."""
    user_id = request.session.get("user_id")
    if user_id is None:
        return None

    if type(user_id) is not int:
        request.session.clear()
        return None

    user = db.get(User, user_id)
    if user is None:
        request.session.clear()
        return None
    return user


def require_user(current_user: User | None = Depends(get_current_user)) -> User:
    """Require authentication for a JSON API."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
        )
    return current_user


def require_page_user(current_user: User | None = Depends(get_current_user)) -> User:
    """Require authentication for an HTML page or form action."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"},
        )
    return current_user


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)
    if not isinstance(token, str) or not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token
    return token


def _validate_csrf_token(request: Request, submitted_token: str | None) -> None:
    expected_token = request.session.get(CSRF_SESSION_KEY)
    if (
        not isinstance(expected_token, str)
        or not isinstance(submitted_token, str)
        or not secrets.compare_digest(expected_token, submitted_token)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="유효하지 않은 CSRF 토큰입니다.",
        )


def require_form_csrf(
    request: Request,
    csrf_token: str | None = Form(default=None),
) -> None:
    _validate_csrf_token(request, csrf_token)


def require_header_csrf(
    request: Request,
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
) -> None:
    _validate_csrf_token(request, csrf_token)
