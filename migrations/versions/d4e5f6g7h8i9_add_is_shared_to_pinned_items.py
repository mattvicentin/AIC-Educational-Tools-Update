"""add is_shared to pinned_items

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-12-04

Adds is_shared boolean column to pinned_items table for collaborative pins.
Shared pins are visible to all room/chat members.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6g7h8i9'
down_revision = 'c3d4e5f6g7h8'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    
    # Add is_shared column with default False (idempotent)
    col_exists = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='pinned_items' AND column_name='is_shared'
    """)).fetchone()
    
    if col_exists is None:
        op.add_column('pinned_items', sa.Column('is_shared', sa.Boolean(), nullable=False, server_default='false'))
    
    # Add indexes for efficient shared pin queries (idempotent)
    indexes = conn.execute(sa.text("""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = 'pinned_items'
    """)).fetchall()
    index_names = {row[0] for row in indexes}
    
    if 'ix_pinned_items_chat_shared' not in index_names:
        op.create_index('ix_pinned_items_chat_shared', 'pinned_items', ['chat_id', 'is_shared'], unique=False)
    if 'ix_pinned_items_room_shared' not in index_names:
        op.create_index('ix_pinned_items_room_shared', 'pinned_items', ['room_id', 'is_shared'], unique=False)


def downgrade():
    # Remove indexes
    op.drop_index('ix_pinned_items_room_shared', table_name='pinned_items')
    op.drop_index('ix_pinned_items_chat_shared', table_name='pinned_items')
    
    # Remove column
    op.drop_column('pinned_items', 'is_shared')
