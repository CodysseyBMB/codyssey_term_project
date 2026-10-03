from __future__ import annotations

from alembic import command
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

from tests.conftest import make_alembic_config


def current_revision(database_url: str) -> str | None:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()


def test_upgrade_head_is_idempotent(database_url: str, monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", database_url)
    config = make_alembic_config(database_url)

    command.upgrade(config, "head")
    command.upgrade(config, "head")

    assert current_revision(database_url) is None
