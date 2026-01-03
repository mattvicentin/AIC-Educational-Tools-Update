"""add_flashcard_tables

Revision ID: cd2345678901
Revises: afbd40f1e68c
Create Date: 2026-01-02 17:00:00.000000

Creates flashcard_set and flashcard_session tables for Flashcards Tool.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'cd2345678901'
down_revision: Union[str, Sequence[str], None] = 'afbd40f1e68c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create flashcard_set and flashcard_session tables."""
    conn = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'
    
    # Create flashcard_set table
    op.create_table(
        'flashcard_set',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('context_mode', sa.String(20), nullable=False),
        sa.Column('library_doc_ids', postgresql.JSON() if is_postgres else sa.JSON(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('display_mode', sa.String(20), nullable=False),
        sa.Column('grid_size', sa.String(10), nullable=True),
        sa.Column('is_infinite', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('cards', postgresql.JSON() if is_postgres else sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['room.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_flashcard_set_chat_id', 'flashcard_set', ['chat_id'])
    op.create_index('ix_flashcard_set_room_id', 'flashcard_set', ['room_id'])
    op.create_index('ix_flashcard_set_created_by', 'flashcard_set', ['created_by'])
    
    # Create flashcard_session table
    op.create_table(
        'flashcard_session',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('flashcard_set_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.String(64), nullable=False),
        sa.Column('cursor_state', postgresql.JSON() if is_postgres else sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['flashcard_set_id'], ['flashcard_set.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    
    # Create indexes
    op.create_index('ix_flashcard_session_flashcard_set_id', 'flashcard_session', ['flashcard_set_id'])
    op.create_index('ix_flashcard_session_user_id', 'flashcard_session', ['user_id'])
    op.create_index('ix_flashcard_session_session_id', 'flashcard_session', ['session_id'])


def downgrade() -> None:
    """Drop flashcard_set and flashcard_session tables."""
    try:
        op.drop_index('ix_flashcard_session_session_id', table_name='flashcard_session')
        op.drop_index('ix_flashcard_session_user_id', table_name='flashcard_session')
        op.drop_index('ix_flashcard_session_flashcard_set_id', table_name='flashcard_session')
        op.drop_table('flashcard_session')
    except Exception:
        pass
    
    try:
        op.drop_index('ix_flashcard_set_created_by', table_name='flashcard_set')
        op.drop_index('ix_flashcard_set_room_id', table_name='flashcard_set')
        op.drop_index('ix_flashcard_set_chat_id', table_name='flashcard_set')
        op.drop_table('flashcard_set')
    except Exception:
        pass

