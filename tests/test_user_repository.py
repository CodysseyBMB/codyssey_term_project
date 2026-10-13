from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.user_repository import (
    create_user,
    get_user_by_id,
    get_user_by_username,
)


def test_create_and_find_user(db_session: Session) -> None:
    user = create_user(db_session, "whale01", "hashed-password")
    db_session.commit()

    assert get_user_by_id(db_session, user.id) is user
    assert get_user_by_username(db_session, "whale01") is user
    assert get_user_by_username(db_session, "unknown") is None
