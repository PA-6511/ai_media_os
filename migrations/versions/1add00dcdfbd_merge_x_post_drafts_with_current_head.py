"""merge x post drafts with current head

Revision ID: 1add00dcdfbd
Revises: b7e2c4d9f1a6, e7c3a9d4f1b2
Create Date: 2026-09-28 22:41:07.587008

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1add00dcdfbd'
down_revision: Union[str, Sequence[str], None] = ('b7e2c4d9f1a6', 'e7c3a9d4f1b2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
