"""add_difficulty_to_quiz

Revision ID: afbd40f1e68c
Revises: add_document_tables_railway
Create Date: 2026-01-02 15:06:14.230997

Adds difficulty column to quiz table for difficulty selection feature.
Difficulty can be 'easy', 'average', 'hard', or 'mixed'.
Default value is 'average' for backward compatibility.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'afbd40f1e68c'
down_revision: Union[str, Sequence[str], None] = 'add_document_tables_railway'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add difficulty column to quiz table."""
    conn = op.get_bind()
    
    # Check if column already exists (idempotent migration)
    # For PostgreSQL
    if conn.dialect.name == 'postgresql':
        col_exists = conn.execute(sa.text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='quiz' AND column_name='difficulty'
        """)).fetchone()
        
        if col_exists is None:
            # Add column with default value
            op.add_column('quiz', sa.Column('difficulty', sa.String(20), nullable=False, server_default='average'))
    else:
        # For SQLite
        try:
            col_exists = conn.execute(sa.text("""
                SELECT name FROM pragma_table_info('quiz') WHERE name='difficulty'
            """)).fetchone()
            
            if col_exists is None:
                # SQLite doesn't support adding NOT NULL columns with defaults easily
                # We'll add it as nullable first, then update existing rows, then make it NOT NULL
                op.add_column('quiz', sa.Column('difficulty', sa.String(20), nullable=True))
                # Update existing rows
                op.execute(sa.text("UPDATE quiz SET difficulty = 'average' WHERE difficulty IS NULL"))
                # Note: SQLite doesn't support altering column constraints, so we keep it nullable
                # The model will handle the default
        except Exception:
            # If table doesn't exist yet, it will be created by model
            pass


def downgrade() -> None:
    """Remove difficulty column from quiz table."""
    try:
        op.drop_column('quiz', 'difficulty')
    except Exception:
        # Column might not exist, ignore error
        pass
