"""add aadhaar_number and pan_number to user_form_submissions

Revision ID: 8700acc8c510
Revises: c4f7a2e9d1b5
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8700acc8c510'
down_revision: Union[str, Sequence[str], None] = 'c4f7a2e9d1b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'aadhaar_number' not in columns:
        op.add_column('user_form_submissions', sa.Column('aadhaar_number', sa.String(), nullable=True))
    if 'pan_number' not in columns:
        op.add_column('user_form_submissions', sa.Column('pan_number', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'pan_number' in columns:
        op.drop_column('user_form_submissions', 'pan_number')
    if 'aadhaar_number' in columns:
        op.drop_column('user_form_submissions', 'aadhaar_number')
