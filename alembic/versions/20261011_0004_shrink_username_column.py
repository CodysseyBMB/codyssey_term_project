"""shrink users.username to match unified policy (max 20 chars)

Revision ID: 20261011_0004
Revises: 20261005_0003
Create Date: 2026-10-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20261011_0004"
down_revision: Union[str, None] = "20261005_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # HTML(login/signup)·서버 검증(app/validation.py)·DB 컬럼 길이가 각각
    # 50/20/50으로 제각각이던 것을 20자로 통일한다 (이슈 #14).
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=50),
        type_=sa.String(length=20),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=20),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
