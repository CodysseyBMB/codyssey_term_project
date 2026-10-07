from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_missing_ai_api_key_fails_with_clear_error() -> None:
    # ai_api_key는 기본값이 없다 — 설정이 빠지면 "원인을 알 수 없는 런타임 에러"가 아니라
    # pydantic이 어떤 필드가 왜 문제인지 알려주는 명확한 검증 에러로 바로 실패해야 한다.
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            database_url="postgresql://x",
            session_secret="x" * 32,
        )

    assert "ai_api_key" in str(exc_info.value)
