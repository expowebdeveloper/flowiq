"""add dispatched_messages table

Revision ID: 9c3d5e7f1a2b
Revises: 7a1f2c9b3e4d
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c3d5e7f1a2b'
down_revision: Union[str, Sequence[str], None] = '7a1f2c9b3e4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'dispatched_messages' not in inspector.get_table_names():
        op.create_table(
            'dispatched_messages',
            sa.Column('message_id', sa.String(), nullable=False),
            sa.Column('email', sa.String(), nullable=False),
            sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('message_id'),
        )


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'dispatched_messages' in inspector.get_table_names():
        op.drop_table('dispatched_messages')
