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
    inspector = sa.inspect(op.get_bind())
    if 'bank_notifications' not in inspector.get_table_names():
        op.create_table(
            'bank_notifications',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('submission_id', sa.String(), nullable=False),
            sa.Column('bank_name', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(op.get_bind())
    indexes = {i['name'] for i in inspector.get_indexes('bank_notifications')}
    submission_index = op.f('ix_bank_notifications_submission_id')
    bank_index = op.f('ix_bank_notifications_bank_name')
    if submission_index not in indexes:
        op.create_index(submission_index, 'bank_notifications', ['submission_id'])
    if bank_index not in indexes:
        op.create_index(bank_index, 'bank_notifications', ['bank_name'])


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'bank_notifications' not in inspector.get_table_names():
        return
    indexes = {i['name'] for i in inspector.get_indexes('bank_notifications')}
    if op.f('ix_bank_notifications_bank_name') in indexes:
        op.drop_index(op.f('ix_bank_notifications_bank_name'), table_name='bank_notifications')
    if op.f('ix_bank_notifications_submission_id') in indexes:
        op.drop_index(op.f('ix_bank_notifications_submission_id'), table_name='bank_notifications')
    op.drop_table('bank_notifications')
