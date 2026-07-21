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
    inspector = sa.inspect(op.get_bind())
    if 'loan_applications' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('loan_applications')}
    indexes = {i['name'] for i in inspector.get_indexes('loan_applications')}
    if 'kyc_token' not in columns:
        op.add_column('loan_applications', sa.Column('kyc_token', sa.String(), nullable=True))
    if 'credit_score' not in columns:
        op.add_column('loan_applications', sa.Column('credit_score', sa.String(), nullable=True))
    if 'kyc_submitted_at' not in columns:
        op.add_column('loan_applications', sa.Column('kyc_submitted_at', sa.DateTime(timezone=True), nullable=True))
    if op.f('ix_loan_applications_kyc_token') not in indexes:
        op.create_index(op.f('ix_loan_applications_kyc_token'), 'loan_applications', ['kyc_token'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'loan_applications' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('loan_applications')}
    indexes = {i['name'] for i in inspector.get_indexes('loan_applications')}
    if op.f('ix_loan_applications_kyc_token') in indexes:
        op.drop_index(op.f('ix_loan_applications_kyc_token'), table_name='loan_applications')
    if 'kyc_submitted_at' in columns:
        op.drop_column('loan_applications', 'kyc_submitted_at')
    if 'credit_score' in columns:
        op.drop_column('loan_applications', 'credit_score')
    if 'kyc_token' in columns:
        op.drop_column('loan_applications', 'kyc_token')
