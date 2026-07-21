"""rename agent_commands.query to instruction, add attachment columns

Revision ID: 9763c4b79a5e
Revises: 2c52c627892b
Create Date: 2026-07-21 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9763c4b79a5e'
down_revision: Union[str, Sequence[str], None] = '2c52c627892b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column('agent_commands', 'query', new_column_name='instruction')
    op.add_column('agent_commands', sa.Column('attachment_filename', sa.String(), nullable=True))
    op.add_column('agent_commands', sa.Column('attachment_original_name', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('agent_commands', 'attachment_original_name')
    op.drop_column('agent_commands', 'attachment_filename')
    op.alter_column('agent_commands', 'instruction', new_column_name='query')
