"""add message_send_events for a deletion-proof rate limit

Revision ID: b1c4e7a9d2f3
Revises: dfd0fcadf654
Create Date: 2026-10-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b1c4e7a9d2f3"
down_revision: Union[str, Sequence[str], None] = "dfd0fcadf654"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message_send_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sender_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    # The rate-limit window counts against this on every single send.
    op.create_index(
        "ix_message_send_events_sender_created",
        "message_send_events",
        ["sender_id", "created_at"],
    )

    # The old limit counted rows in `messages` filtered by sender and
    # timestamp, with no index to serve it.
    op.create_index(
        "ix_messages_sender_timestamp",
        "messages",
        ["sender_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_sender_timestamp", table_name="messages")
    op.drop_index("ix_message_send_events_sender_created", table_name="message_send_events")
    op.drop_table("message_send_events")
