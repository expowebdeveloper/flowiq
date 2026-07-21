"""add required_documents to bank_loan_rates

Revision ID: de82eb8d06af
Revises: 1dc8f7efd6d5
Create Date: 2026-07-03 12:20:46.616658

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de82eb8d06af'
down_revision: Union[str, Sequence[str], None] = '1dc8f7efd6d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'bank_loan_rates' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('bank_loan_rates')}
    if 'required_documents' not in columns:
        op.add_column('bank_loan_rates', sa.Column('required_documents', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'bank_loan_rates' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('bank_loan_rates')}
    if 'required_documents' in columns:
        op.drop_column('bank_loan_rates', 'required_documents')
