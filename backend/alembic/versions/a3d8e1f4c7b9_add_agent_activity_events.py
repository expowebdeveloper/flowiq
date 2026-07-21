"""add agent_activity_events

Revision ID: a3d8e1f4c7b9
Revises: f1a3c9d7b2e6
Create Date: 2026-07-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3d8e1f4c7b9'
down_revision: Union[str, Sequence[str], None] = 'f1a3c9d7b2e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'agent_activity_events' not in inspector.get_table_names():
        op.create_table(
            'agent_activity_events',
            sa.Column('id', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('status', sa.String(), nullable=False),
            sa.Column('message', sa.Text(), nullable=False),
            sa.Column('submission_id', sa.String(), nullable=True),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        inspector = sa.inspect(op.get_bind())
    indexes = {i['name'] for i in inspector.get_indexes('agent_activity_events')}
    created_index = op.f('ix_agent_activity_events_created_at')
    submission_index = op.f('ix_agent_activity_events_submission_id')
    if created_index not in indexes:
        op.create_index(created_index, 'agent_activity_events', ['created_at'])
    if submission_index not in indexes:
        op.create_index(submission_index, 'agent_activity_events', ['submission_id'])


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'agent_activity_events' not in inspector.get_table_names():
        return
    indexes = {i['name'] for i in inspector.get_indexes('agent_activity_events')}
    if op.f('ix_agent_activity_events_submission_id') in indexes:
        op.drop_index(op.f('ix_agent_activity_events_submission_id'), table_name='agent_activity_events')
    if op.f('ix_agent_activity_events_created_at') in indexes:
        op.drop_index(op.f('ix_agent_activity_events_created_at'), table_name='agent_activity_events')
    op.drop_table('agent_activity_events')
