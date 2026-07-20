"""add current_address and marital_status to user_form_submissions

Revision ID: 242cadd59de5
Revises: 6762c8994f46
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '242cadd59de5'
down_revision: Union[str, Sequence[str], None] = '6762c8994f46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_form_submissions', sa.Column('current_address', sa.Text(), nullable=True))
    op.add_column('user_form_submissions', sa.Column('marital_status', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_form_submissions', 'marital_status')
    op.drop_column('user_form_submissions', 'current_address')
