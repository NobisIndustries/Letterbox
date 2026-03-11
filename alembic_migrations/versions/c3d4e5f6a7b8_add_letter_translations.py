"""add letter_translations table

Revision ID: c3d4e5f6a7b8
Revises: b2a3c4d5e6f7
Create Date: 2026-03-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str]] = 'b2a3c4d5e6f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'letter_translations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('letter_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.Text(), nullable=False),
        sa.Column('translated_text', sa.Text(), nullable=True),
        sa.Column('translated_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['letter_id'], ['letters.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('letter_id', 'language', name='uq_letter_language'),
    )

    op.execute(
        "INSERT INTO settings (key, value) VALUES ('translation_languages', '[\"English\", \"German\", \"French\", \"Spanish\"]')"
    )


def downgrade() -> None:
    op.execute("DELETE FROM settings WHERE key = 'translation_languages'")
    op.drop_table('letter_translations')
