"""add portal_url, portal_username, portal_password to banks

Revision ID: 2c52c627892b
Revises: 3902750cf60f
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c52c627892b'
down_revision: Union[str, Sequence[str], None] = '3902750cf60f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('banks', sa.Column('portal_url', sa.String(), nullable=True))
    op.add_column('banks', sa.Column('portal_username', sa.String(), nullable=True))
    op.add_column('banks', sa.Column('portal_password', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('banks', 'portal_password')
    op.drop_column('banks', 'portal_username')
    op.drop_column('banks', 'portal_url')
