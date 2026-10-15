from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
)


def test_create_and_find_user(db_session: Session) -> None:
    user = create_user(db_session, "whale01", "hashed-password")

    assert get_user_by_id(db_session, user.id) is user
    assert get_user_by_username(db_session, "whale01") is user


def test_get_user_by_username_returns_none_for_unknown_user(
    db_session: Session,
) -> None:
    assert get_user_by_username(db_session, "unknown") is None


def test_create_user_stores_supplied_password_hash(db_session: Session) -> None:
    create_user(db_session, "whale01", "already-hashed")
    db_session.commit()

    db_session.expire_all()
    stored = get_user_by_username(db_session, "whale01")
    assert stored is not None
    assert stored.password_hash == "already-hashed"
