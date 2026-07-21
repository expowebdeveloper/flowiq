"""repair missing banks columns after stamped revision

Revision ID: 5f6b1a2c3d4e
Revises: 9763c4b79a5e
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5f6b1a2c3d4e'
down_revision: Union[str, Sequence[str], None] = '9763c4b79a5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'banks' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('banks')}
    indexes = {i['name'] for i in inspector.get_indexes('banks')}

    if 'contact_email' not in columns:
        op.add_column('banks', sa.Column('contact_email', sa.String(), nullable=True))
    if 'portal_url' not in columns:
        op.add_column('banks', sa.Column('portal_url', sa.String(), nullable=True))
    if 'portal_username' not in columns:
        op.add_column('banks', sa.Column('portal_username', sa.String(), nullable=True))
    if 'portal_password' not in columns:
        op.add_column('banks', sa.Column('portal_password', sa.String(), nullable=True))
    if 'ix_banks_contact_email' not in indexes:
        op.create_index('ix_banks_contact_email', 'banks', ['contact_email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'banks' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('banks')}
    indexes = {i['name'] for i in inspector.get_indexes('banks')}

    if 'ix_banks_contact_email' in indexes:
        op.drop_index('ix_banks_contact_email', table_name='banks')
    if 'portal_password' in columns:
        op.drop_column('banks', 'portal_password')
    if 'portal_username' in columns:
        op.drop_column('banks', 'portal_username')
    if 'portal_url' in columns:
        op.drop_column('banks', 'portal_url')
    if 'contact_email' in columns:
        op.drop_column('banks', 'contact_email')
