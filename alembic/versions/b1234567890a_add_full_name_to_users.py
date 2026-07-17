"""add full_name to users

Revision ID: b1234567890a
Revises: 88589b4d6a7f
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b1234567890a'
down_revision: Union[str, Sequence[str], None] = '88589b4d6a7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('full_name', sa.String(length=225), nullable=True))

    # Update existing users with a default full_name (using email prefix)
    op.execute("UPDATE users SET full_name = split_part(email, '@', 1) WHERE full_name IS NULL")

    # Make full_name non-nullable after setting defaults
    op.alter_column('users', 'full_name', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'full_name')
