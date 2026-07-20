"""add aadhaar_verified to loan_applications

Revision ID: b2e4f8a1c6d3
Revises: 9c3d5e7f1a2b
Create Date: 2026-07-13 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2e4f8a1c6d3'
down_revision: Union[str, Sequence[str], None] = '9c3d5e7f1a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'loan_applications',
        sa.Column('aadhaar_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column('loan_applications', 'aadhaar_verified', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('loan_applications', 'aadhaar_verified')
