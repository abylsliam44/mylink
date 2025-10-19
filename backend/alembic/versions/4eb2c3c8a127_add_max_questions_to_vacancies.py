"""add_max_questions_to_vacancies

Revision ID: 4eb2c3c8a127
Revises: 5ece2ad0c9fb
Create Date: 2025-10-19 07:25:54.953177

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4eb2c3c8a127'
down_revision = '5ece2ad0c9fb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add max_questions column to vacancies table
    op.add_column('vacancies', sa.Column('max_questions', sa.Integer(), nullable=False, server_default='3', comment='Maximum interview questions (3-8)'))


def downgrade() -> None:
    # Remove max_questions column from vacancies table
    op.drop_column('vacancies', 'max_questions')

