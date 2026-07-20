"""add kyc fields to loan_applications

Revision ID: 7a1f2c9b3e4d
Revises: 393d6e2f9ae4
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a1f2c9b3e4d'
down_revision: Union[str, Sequence[str], None] = '393d6e2f9ae4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('loan_applications', sa.Column('kyc_token', sa.String(), nullable=True))
    op.add_column('loan_applications', sa.Column('credit_score', sa.String(), nullable=True))
    op.add_column('loan_applications', sa.Column('kyc_submitted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_loan_applications_kyc_token'), 'loan_applications', ['kyc_token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_loan_applications_kyc_token'), table_name='loan_applications')
    op.drop_column('loan_applications', 'kyc_submitted_at')
    op.drop_column('loan_applications', 'credit_score')
    op.drop_column('loan_applications', 'kyc_token')
