"""add reminder tracking to user_form_submissions

Revision ID: c9a1e4f6b3d7
Revises: b7d3f2a8c1e9
Create Date: 2026-07-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9a1e4f6b3d7'
down_revision: Union[str, Sequence[str], None] = 'b7d3f2a8c1e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'reminder_count' not in columns:
        op.add_column(
            'user_form_submissions',
            sa.Column('reminder_count', sa.Integer(), nullable=False, server_default='0'),
        )
    if 'last_reminder_sent_at' not in columns:
        op.add_column(
            'user_form_submissions',
            sa.Column('last_reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    if 'last_reminder_sent_at' in columns:
        op.drop_column('user_form_submissions', 'last_reminder_sent_at')
    if 'reminder_count' in columns:
        op.drop_column('user_form_submissions', 'reminder_count')
