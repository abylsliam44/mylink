"""add_ai_columns_to_responses

Revision ID: add_ai_columns_to_responses
Revises: 4eb2c3c8a127
Create Date: 2025-10-21 16:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_ai_columns_to_responses'
down_revision = '4eb2c3c8a127'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add AI interview columns to candidate_responses table
    op.add_column('candidate_responses', sa.Column('mismatch_analysis', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Initial mismatch detection results from AI'))
    op.add_column('candidate_responses', sa.Column('dialog_findings', postgresql.JSON(astext_type=sa.Text()), nullable=True, comment='Collected answers and findings during interview'))
    op.add_column('candidate_responses', sa.Column('language_preference', sa.String(length=5), nullable=True, server_default='ru', comment='Interview language: ru, kk, en'))


def downgrade() -> None:
    # Remove AI interview columns
    op.drop_column('candidate_responses', 'language_preference')
    op.drop_column('candidate_responses', 'dialog_findings')
    op.drop_column('candidate_responses', 'mismatch_analysis')
