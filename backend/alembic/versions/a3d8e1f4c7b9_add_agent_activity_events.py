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
    op.create_index(op.f('ix_agent_activity_events_created_at'), 'agent_activity_events', ['created_at'])
    op.create_index(op.f('ix_agent_activity_events_submission_id'), 'agent_activity_events', ['submission_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_agent_activity_events_submission_id'), table_name='agent_activity_events')
    op.drop_index(op.f('ix_agent_activity_events_created_at'), table_name='agent_activity_events')
    op.drop_table('agent_activity_events')
