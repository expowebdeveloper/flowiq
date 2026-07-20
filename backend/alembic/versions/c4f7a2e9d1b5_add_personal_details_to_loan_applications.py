"""add personal details to loan_applications

Revision ID: c4f7a2e9d1b5
Revises: b2e4f8a1c6d3
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4f7a2e9d1b5'
down_revision: Union[str, Sequence[str], None] = 'b2e4f8a1c6d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('loan_applications', sa.Column('date_of_birth', sa.String(), nullable=True))
    op.add_column('loan_applications', sa.Column('gender', sa.String(), nullable=True))
    op.add_column('loan_applications', sa.Column('address', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loan_applications', 'address')
    op.drop_column('loan_applications', 'gender')
    op.drop_column('loan_applications', 'date_of_birth')
