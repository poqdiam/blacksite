"""baseline_existing_schema

Baseline migration — no operations.

The BLACKSITE database schema was built through 39 development phases using
a hand-rolled _migrate_db() function in app/models.py.  This revision marks
the existing schema as the starting point for Alembic-managed migrations.

All existing databases should be stamped with this revision:
  BLACKSITE_DB_KEY=<key> alembic stamp 76c7030ec0c1

Future schema changes should be made by editing app/models.py and running:
  BLACKSITE_DB_KEY=<key> alembic revision --autogenerate -m "describe change"
  BLACKSITE_DB_KEY=<key> alembic upgrade head

Revision ID: 76c7030ec0c1
Revises:
Create Date: 2026-03-10 19:02:09.394626

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76c7030ec0c1'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
