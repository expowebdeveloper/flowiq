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
    inspector = sa.inspect(op.get_bind())
    if 'loan_applications' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('loan_applications')}
    if 'date_of_birth' not in columns:
        op.add_column('loan_applications', sa.Column('date_of_birth', sa.String(), nullable=True))
    if 'gender' not in columns:
        op.add_column('loan_applications', sa.Column('gender', sa.String(), nullable=True))
    if 'address' not in columns:
        op.add_column('loan_applications', sa.Column('address', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'loan_applications' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('loan_applications')}
    if 'address' in columns:
        op.drop_column('loan_applications', 'address')
    if 'gender' in columns:
        op.drop_column('loan_applications', 'gender')
    if 'date_of_birth' in columns:
        op.drop_column('loan_applications', 'date_of_birth')
