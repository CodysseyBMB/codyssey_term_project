from __future__ import annotations

from datetime import datetime, timezone

# DateTime, String은 sqlalchemy의 컬럼 타입

# Mapped[...]
# python의 타입힌트 문법

# mapped_column(...)
# 실제로 이게 DB 컬럼임을 정의하는 부분
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )