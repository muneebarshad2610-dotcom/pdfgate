"""Initial schema: sessions, players, leaderboard

Revision ID: 001
Revises:
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("host_id", sa.BigInteger(), nullable=False),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("game_type", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="lobby"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "players",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("eliminated", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("eliminated_at_round", sa.Integer(), nullable=True),
        sa.Column("joined_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "leaderboard",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("discord_id", sa.BigInteger(), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("campaign_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("session_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("leaderboard")
    op.drop_table("players")
    op.drop_table("sessions")
