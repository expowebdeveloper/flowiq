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
    inspector = sa.inspect(op.get_bind())
    if 'banks' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('banks')}

    if 'portal_url' not in columns:
        op.add_column('banks', sa.Column('portal_url', sa.String(), nullable=True))
    if 'portal_username' not in columns:
        op.add_column('banks', sa.Column('portal_username', sa.String(), nullable=True))
    if 'portal_password' not in columns:
        op.add_column('banks', sa.Column('portal_password', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'banks' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('banks')}

    if 'portal_password' in columns:
        op.drop_column('banks', 'portal_password')
    if 'portal_username' in columns:
        op.drop_column('banks', 'portal_username')
    if 'portal_url' in columns:
        op.drop_column('banks', 'portal_url')
