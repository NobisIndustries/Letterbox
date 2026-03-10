"""add tags column, settings table, rebuild FTS5 with tags

Revision ID: b2a3c4d5e6f7
Revises: 97fdc4ef4986
Create Date: 2026-03-09 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2a3c4d5e6f7'
down_revision: Union[str, Sequence[str]] = '97fdc4ef4986'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tags column to letters
    op.add_column('letters', sa.Column('tags', sa.Text(), nullable=True))

    # Create settings table
    op.create_table('settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.Text(), nullable=False),
        sa.Column('value', sa.Text(), server_default='[]', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )

    # Seed default settings
    op.execute("INSERT INTO settings (key, value) VALUES ('recipients', '[]')")
    op.execute("""INSERT INTO settings (key, value) VALUES ('tags', '["invoice","bill","banking","insurance","tax","refund","order","shipping","coupon","marketing","government","legal","contract","health","subscription"]')""")

    # Drop old FTS triggers and table, rebuild with tags column
    op.execute("DROP TRIGGER IF EXISTS letters_au")
    op.execute("DROP TRIGGER IF EXISTS letters_ad")
    op.execute("DROP TRIGGER IF EXISTS letters_ai")
    op.execute("DROP TABLE IF EXISTS letters_fts")

    op.execute("""
        CREATE VIRTUAL TABLE letters_fts USING fts5(
            title, summary, sender, receiver, keywords, tags, full_text,
            content='letters', content_rowid='id'
        )
    """)
    op.execute("""
        CREATE TRIGGER letters_ai AFTER INSERT ON letters BEGIN
            INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, tags, full_text)
            VALUES (new.id, new.title, new.summary, new.sender, new.receiver, new.keywords, new.tags, new.full_text);
        END
    """)
    op.execute("""
        CREATE TRIGGER letters_ad AFTER DELETE ON letters BEGIN
            INSERT INTO letters_fts(letters_fts, rowid, title, summary, sender, receiver, keywords, tags, full_text)
            VALUES ('delete', old.id, old.title, old.summary, old.sender, old.receiver, old.keywords, old.tags, old.full_text);
        END
    """)
    op.execute("""
        CREATE TRIGGER letters_au AFTER UPDATE ON letters BEGIN
            INSERT INTO letters_fts(letters_fts, rowid, title, summary, sender, receiver, keywords, tags, full_text)
            VALUES ('delete', old.id, old.title, old.summary, old.sender, old.receiver, old.keywords, old.tags, old.full_text);
            INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, tags, full_text)
            VALUES (new.id, new.title, new.summary, new.sender, new.receiver, new.keywords, new.tags, new.full_text);
        END
    """)

    # Rebuild FTS index from existing data
    op.execute("""
        INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, tags, full_text)
        SELECT id, title, summary, sender, receiver, keywords, tags, full_text FROM letters
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS letters_au")
    op.execute("DROP TRIGGER IF EXISTS letters_ad")
    op.execute("DROP TRIGGER IF EXISTS letters_ai")
    op.execute("DROP TABLE IF EXISTS letters_fts")

    # Recreate old FTS without tags
    op.execute("""
        CREATE VIRTUAL TABLE letters_fts USING fts5(
            title, summary, sender, receiver, keywords, full_text,
            content='letters', content_rowid='id'
        )
    """)
    op.execute("""
        CREATE TRIGGER letters_ai AFTER INSERT ON letters BEGIN
            INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, full_text)
            VALUES (new.id, new.title, new.summary, new.sender, new.receiver, new.keywords, new.full_text);
        END
    """)
    op.execute("""
        CREATE TRIGGER letters_ad AFTER DELETE ON letters BEGIN
            INSERT INTO letters_fts(letters_fts, rowid, title, summary, sender, receiver, keywords, full_text)
            VALUES ('delete', old.id, old.title, old.summary, old.sender, old.receiver, old.keywords, old.full_text);
        END
    """)
    op.execute("""
        CREATE TRIGGER letters_au AFTER UPDATE ON letters BEGIN
            INSERT INTO letters_fts(letters_fts, rowid, title, summary, sender, receiver, keywords, full_text)
            VALUES ('delete', old.id, old.title, old.summary, old.sender, old.receiver, old.keywords, old.full_text);
            INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, full_text)
            VALUES (new.id, new.title, new.summary, new.sender, new.receiver, new.keywords, new.full_text);
        END
    """)

    # Rebuild FTS index
    op.execute("""
        INSERT INTO letters_fts(rowid, title, summary, sender, receiver, keywords, full_text)
        SELECT id, title, summary, sender, receiver, keywords, full_text FROM letters
    """)

    op.drop_table('settings')
    op.drop_column('letters', 'tags')
