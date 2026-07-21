"""add phone_number to user_form_submissions

Revision ID: e6454433d711
Revises: c4c6cbed394f
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6454433d711'
down_revision: Union[str, Sequence[str], None] = 'c4c6cbed394f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'phone_number' not in columns:
        op.add_column('user_form_submissions', sa.Column('phone_number', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'phone_number' in columns:
        op.drop_column('user_form_submissions', 'phone_number')
