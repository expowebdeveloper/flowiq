"""add thread_id and mailbox_email to user_form_submissions

Revision ID: 8f373ba885f3
Revises: d69905ababd2
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f373ba885f3'
down_revision: Union[str, Sequence[str], None] = 'd69905ababd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_form_submissions', sa.Column('thread_id', sa.String(), nullable=True))
    op.add_column('user_form_submissions', sa.Column('mailbox_email', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_form_submissions', 'mailbox_email')
    op.drop_column('user_form_submissions', 'thread_id')
