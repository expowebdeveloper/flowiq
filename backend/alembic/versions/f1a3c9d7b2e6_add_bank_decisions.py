"""add bank_decisions

Revision ID: f1a3c9d7b2e6
Revises: 9406624c09a4
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a3c9d7b2e6'
down_revision: Union[str, Sequence[str], None] = '9406624c09a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'bank_decisions' not in inspector.get_table_names():
        op.create_table(
            'bank_decisions',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('submission_id', sa.String(), nullable=False),
            sa.Column('bank_name', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('remarks', sa.Text(), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('agent_notified_at', sa.DateTime(timezone=True), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(op.get_bind())
    indexes = {i['name'] for i in inspector.get_indexes('bank_decisions')}
    submission_index = op.f('ix_bank_decisions_submission_id')
    bank_index = op.f('ix_bank_decisions_bank_name')
    if submission_index not in indexes:
        op.create_index(submission_index, 'bank_decisions', ['submission_id'])
    if bank_index not in indexes:
        op.create_index(bank_index, 'bank_decisions', ['bank_name'])


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'bank_decisions' not in inspector.get_table_names():
        return
    indexes = {i['name'] for i in inspector.get_indexes('bank_decisions')}
    if op.f('ix_bank_decisions_bank_name') in indexes:
        op.drop_index(op.f('ix_bank_decisions_bank_name'), table_name='bank_decisions')
    if op.f('ix_bank_decisions_submission_id') in indexes:
        op.drop_index(op.f('ix_bank_decisions_submission_id'), table_name='bank_decisions')
    op.drop_table('bank_decisions')
