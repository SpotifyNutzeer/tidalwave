"""track durations

Adds listens.duration_sec and the track_durations cache table so "time
listened" can be aggregated from per-track lengths resolved via Last.fm.

Revision ID: a1d2e3f40510
Revises: c01b5b802766
Create Date: 2026-06-18 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1d2e3f40510'
down_revision: Union[str, Sequence[str], None] = 'c01b5b802766'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('listens', sa.Column('duration_sec', sa.Integer(), nullable=True))
    op.create_table(
        'track_durations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('artist', sa.Text(), nullable=False),
        sa.Column('track_title', sa.Text(), nullable=False),
        sa.Column('duration_sec', sa.Integer(), nullable=True),
        sa.Column('fetched_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('artist', 'track_title', name='uq_track_duration'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('track_durations')
    op.drop_column('listens', 'duration_sec')
