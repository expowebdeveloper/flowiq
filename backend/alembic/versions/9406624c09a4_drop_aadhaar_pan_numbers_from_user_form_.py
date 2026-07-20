"""drop aadhaar_number and pan_number from user_form_submissions

Revision ID: 9406624c09a4
Revises: 242cadd59de5
Create Date: 2026-07-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9406624c09a4'
down_revision: Union[str, Sequence[str], None] = '242cadd59de5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column('user_form_submissions', 'pan_number')
    op.drop_column('user_form_submissions', 'aadhaar_number')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('user_form_submissions', sa.Column('aadhaar_number', sa.String(), nullable=True))
    op.add_column('user_form_submissions', sa.Column('pan_number', sa.String(), nullable=True))
