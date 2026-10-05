from __future__ import annotations

from alembic import command
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
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

    # 마이그레이션이 하나도 없던 스켈레톤 시절엔 head가 항상 None이었지만,
    # 이제 users 테이블 리비전이 생겼으니 "현재 DB 리비전 == 스크립트상의 head"로 비교한다.
    head_revision = ScriptDirectory.from_config(config).get_current_head()
    assert current_revision(database_url) == head_revision
