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
    # agent_commands can already have this migration's target shape: if
    # create_all() created the table fresh (see 3902750cf60f), it was built
    # from whatever AgentCommand model was current at the time, which may
    # already have `instruction` and the attachment columns.
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('agent_commands')}

    if 'query' in columns and 'instruction' not in columns:
        op.alter_column('agent_commands', 'query', new_column_name='instruction')
    if 'attachment_filename' not in columns:
        op.add_column('agent_commands', sa.Column('attachment_filename', sa.String(), nullable=True))
    if 'attachment_original_name' not in columns:
        op.add_column('agent_commands', sa.Column('attachment_original_name', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    columns = {c['name'] for c in sa.inspect(bind).get_columns('agent_commands')}

    if 'attachment_original_name' in columns:
        op.drop_column('agent_commands', 'attachment_original_name')
    if 'attachment_filename' in columns:
        op.drop_column('agent_commands', 'attachment_filename')
    if 'instruction' in columns and 'query' not in columns:
        op.alter_column('agent_commands', 'instruction', new_column_name='query')
