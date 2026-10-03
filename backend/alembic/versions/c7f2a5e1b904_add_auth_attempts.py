"""add auth_attempts to throttle login guessing

Revision ID: c7f2a5e1b904
Revises: b1c4e7a9d2f3
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7f2a5e1b904"
down_revision: Union[str, Sequence[str], None] = "b1c4e7a9d2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        # No foreign key: the rows that matter most name accounts that do not
        # exist, which is what a sweep across guessed usernames looks like.
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Both counts run on every login attempt, so neither may scan.
    op.create_index(
        "ix_auth_attempts_identity",
        "auth_attempts",
        ["username", "client_ip", "created_at"],
    )
    op.create_index(
        "ix_auth_attempts_ip",
        "auth_attempts",
        ["client_ip", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_auth_attempts_ip", table_name="auth_attempts")
    op.drop_index("ix_auth_attempts_identity", table_name="auth_attempts")
    op.drop_table("auth_attempts")
