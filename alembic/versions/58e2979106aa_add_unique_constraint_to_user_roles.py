"""add unique constraint to user_roles

Revision ID: 58e2979106aa
Revises: b1234567890a
Create Date: 2026-07-10 15:52:45.818871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '58e2979106aa'
down_revision: Union[str, Sequence[str], None] = 'b1234567890a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unique constraint on user_id to ensure one role per user
    op.create_unique_constraint(
        'uq_user_roles_user_id',
        'user_roles',
        ['user_id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unique constraint
    op.drop_constraint('uq_user_roles_user_id', 'user_roles', type_='unique')
