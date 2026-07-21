"""add current_address and marital_status to user_form_submissions

Revision ID: 242cadd59de5
Revises: 6762c8994f46
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '242cadd59de5'
down_revision: Union[str, Sequence[str], None] = '6762c8994f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'current_address' not in columns:
        op.add_column('user_form_submissions', sa.Column('current_address', sa.Text(), nullable=True))
    if 'marital_status' not in columns:
        op.add_column('user_form_submissions', sa.Column('marital_status', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'marital_status' in columns:
        op.drop_column('user_form_submissions', 'marital_status')
    if 'current_address' in columns:
        op.drop_column('user_form_submissions', 'current_address')
