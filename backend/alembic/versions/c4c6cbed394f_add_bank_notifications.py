"""add bank_notifications

Revision ID: c4c6cbed394f
Revises: 8f373ba885f3
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4c6cbed394f'
down_revision: Union[str, Sequence[str], None] = '8f373ba885f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'bank_notifications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('submission_id', sa.String(), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_bank_notifications_submission_id'), 'bank_notifications', ['submission_id'])
    op.create_index(op.f('ix_bank_notifications_bank_name'), 'bank_notifications', ['bank_name'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_bank_notifications_bank_name'), table_name='bank_notifications')
    op.drop_index(op.f('ix_bank_notifications_submission_id'), table_name='bank_notifications')
    op.drop_table('bank_notifications')
