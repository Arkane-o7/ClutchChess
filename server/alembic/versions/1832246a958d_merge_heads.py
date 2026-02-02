"""merge heads

Revision ID: 1832246a958d
Revises: 006_add_legacy_replay_tables, 007_update_leaderboard_indexes
Create Date: 2026-02-01 16:27:19.218750

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1832246a958d'
down_revision: Union[str, None] = ('006_add_legacy_replay_tables', '007_update_leaderboard_indexes')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
