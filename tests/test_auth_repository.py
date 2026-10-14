from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.auth_repository import create_user, get_user_by_username


def test_get_user_by_username_returns_matching_user(db_session: Session) -> None:
    created = create_user(db_session, "whale01", "hashed-password")

    found = get_user_by_username(db_session, "whale01")

    assert found is created


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
