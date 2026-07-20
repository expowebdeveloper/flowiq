"""add date_of_birth and ssn to user_form_submissions

Revision ID: 6762c8994f46
Revises: e6454433d711
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6762c8994f46'
down_revision: Union[str, Sequence[str], None] = 'e6454433d711'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_form_submissions', sa.Column('date_of_birth', sa.String(), nullable=True))
    op.add_column('user_form_submissions', sa.Column('ssn', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_form_submissions', 'ssn')
    op.drop_column('user_form_submissions', 'date_of_birth')
