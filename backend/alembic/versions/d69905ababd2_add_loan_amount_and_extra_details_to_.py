"""add loan_amount and extra_loan_details to user_form_submissions

Revision ID: d69905ababd2
Revises: 8700acc8c510
Create Date: 2026-07-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd69905ababd2'
down_revision: Union[str, Sequence[str], None] = '8700acc8c510'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_form_submissions', sa.Column('loan_amount', sa.Float(), nullable=True))
    op.add_column('user_form_submissions', sa.Column('extra_loan_details', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_form_submissions', 'extra_loan_details')
    op.drop_column('user_form_submissions', 'loan_amount')
