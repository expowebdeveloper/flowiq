"""add short_code to user_form_submissions

Revision ID: b7d3f2a8c1e9
Revises: a3d8e1f4c7b9
Create Date: 2026-07-20 00:00:00.000000

"""
import secrets
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d3f2a8c1e9'
down_revision: Union[str, Sequence[str], None] = 'a3d8e1f4c7b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Same charset/length as loan_apply.agent.generate_short_code — kept in sync
# manually since migrations must not import application code (the app code
# is free to change later; this file has to keep working as a historical
# record of what ran).
_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_LENGTH = 8 


def _generate_short_code() -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(_LENGTH))


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    indexes = {i['name'] for i in inspector.get_indexes('user_form_submissions')}
    if 'short_code' not in columns:
        op.add_column('user_form_submissions', sa.Column('short_code', sa.String(length=8), nullable=True))
    if 'ix_user_form_submissions_short_code' not in indexes:
        op.create_index('ix_user_form_submissions_short_code', 'user_form_submissions', ['short_code'], unique=True)

    # Backfill existing rows so every submission has a short_code in
    # practice, not just newly-created ones — generated one at a time with a
    # uniqueness check against what's already been assigned this run, since
    # the column has no data to collide against yet.
    connection = op.get_bind()
    existing_ids = [
        row[0]
        for row in connection.execute(
            sa.text('SELECT id FROM user_form_submissions WHERE short_code IS NULL')
        ).fetchall()
    ]
    used_codes = {
        row[0]
        for row in connection.execute(
            sa.text('SELECT short_code FROM user_form_submissions WHERE short_code IS NOT NULL')
        ).fetchall()
    }
    for submission_id in existing_ids:
        code = _generate_short_code()
        while code in used_codes:
            code = _generate_short_code()
        used_codes.add(code)
        connection.execute(
            sa.text('UPDATE user_form_submissions SET short_code = :code WHERE id = :id'),
            {"code": code, "id": submission_id},
        )


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'user_form_submissions' not in inspector.get_table_names():
        return
    columns = {c['name'] for c in inspector.get_columns('user_form_submissions')}
    indexes = {i['name'] for i in inspector.get_indexes('user_form_submissions')}
    if 'ix_user_form_submissions_short_code' in indexes:
        op.drop_index('ix_user_form_submissions_short_code', table_name='user_form_submissions')
    if 'short_code' in columns:
        op.drop_column('user_form_submissions', 'short_code')
