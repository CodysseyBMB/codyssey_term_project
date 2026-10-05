from __future__ import annotations

from collections.abc import Generator
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings
from app.main import create_app

from app.db import create_database_engine, create_session_factory


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_alembic_config(database_url: str) -> Config:
    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ["DATABASE_URL"]


@pytest.fixture
def migrated_database_url(database_url: str, monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("DATABASE_URL", database_url)
    command.upgrade(make_alembic_config(database_url), "head")
    return database_url


@pytest.fixture(autouse=True)
def _reset_tables(migrated_database_url: str) -> None:
    # 로컬 Postgres는 postgres_data 볼륨에 데이터가 계속 남아 있어서,
    # 테스트를 두 번 돌리면 이전 실행에서 만든 행(예: whale01)이 그대로 남아
    # "성공해야 할 가입"이 중복으로 걸려버린다. 그래서 매 테스트 시작 전에
    # 테이블을 비워서, pytest를 몇 번을 돌려도 항상 빈 DB에서 시작하게 만든다.
    engine = create_database_engine(migrated_database_url)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture
def settings(migrated_database_url: str) -> Settings:
    return Settings(
        _env_file=None,
        app_env="test",
        database_url=migrated_database_url,
    )


@pytest.fixture
def client(settings: Settings) -> Generator[TestClient, None, None]:
    with TestClient(create_app(settings)) as test_client:
        yield test_client

@pytest.fixture
def db_session(settings: Settings) -> Generator[Session, None, None]:
    # 테스트에서 "DB에 실제로 저장됐는지"를 직접 들여다보기 위한 세션.
    # client fixture와는 별개로, 검증용으로만 쓴다.
    engine = create_database_engine(settings.database_url)
    factory = create_session_factory(engine)
    with factory() as session:
        yield session
    engine.dispose()
