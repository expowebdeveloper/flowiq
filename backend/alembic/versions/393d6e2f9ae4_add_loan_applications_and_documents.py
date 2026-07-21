"""add loan applications and documents

Revision ID: 393d6e2f9ae4
Revises: de82eb8d06af
Create Date: 2026-07-03 20:51:48.531880

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '393d6e2f9ae4'
down_revision: Union[str, Sequence[str], None] = 'de82eb8d06af'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    inspector = sa.inspect(op.get_bind())

    if 'loan_application_documents' not in inspector.get_table_names():
        op.create_table('loan_application_documents',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('saved_path', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        inspector = sa.inspect(op.get_bind())
    doc_indexes = {i['name'] for i in inspector.get_indexes('loan_application_documents')}
    doc_index = op.f('ix_loan_application_documents_application_id')
    if doc_index not in doc_indexes:
        op.create_index(doc_index, 'loan_application_documents', ['application_id'], unique=False)

    if 'loan_applications' not in inspector.get_table_names():
        op.create_table('loan_applications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('broker_id', sa.String(), nullable=False),
        sa.Column('bank_loan_rate_id', sa.String(), nullable=False),
        sa.Column('bank_name', sa.String(), nullable=False),
        sa.Column('loan_type', sa.String(), nullable=False),
        sa.Column('applicant_name', sa.String(), nullable=False),
        sa.Column('applicant_phone', sa.String(), nullable=False),
        sa.Column('applicant_email', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        inspector = sa.inspect(op.get_bind())
    app_indexes = {i['name'] for i in inspector.get_indexes('loan_applications')}
    rate_index = op.f('ix_loan_applications_bank_loan_rate_id')
    broker_index = op.f('ix_loan_applications_broker_id')
    if rate_index not in app_indexes:
        op.create_index(rate_index, 'loan_applications', ['bank_loan_rate_id'], unique=False)
    if broker_index not in app_indexes:
        op.create_index(broker_index, 'loan_applications', ['broker_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    inspector = sa.inspect(op.get_bind())
    if 'loan_applications' in inspector.get_table_names():
        app_indexes = {i['name'] for i in inspector.get_indexes('loan_applications')}
        if op.f('ix_loan_applications_broker_id') in app_indexes:
            op.drop_index(op.f('ix_loan_applications_broker_id'), table_name='loan_applications')
        if op.f('ix_loan_applications_bank_loan_rate_id') in app_indexes:
            op.drop_index(op.f('ix_loan_applications_bank_loan_rate_id'), table_name='loan_applications')
        op.drop_table('loan_applications')
    if 'loan_application_documents' in inspector.get_table_names():
        doc_indexes = {i['name'] for i in inspector.get_indexes('loan_application_documents')}
        if op.f('ix_loan_application_documents_application_id') in doc_indexes:
            op.drop_index(op.f('ix_loan_application_documents_application_id'), table_name='loan_application_documents')
        op.drop_table('loan_application_documents')
