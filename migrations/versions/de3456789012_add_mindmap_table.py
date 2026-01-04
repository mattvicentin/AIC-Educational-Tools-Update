"""add_mindmap_table

Revision ID: de3456789012
Revises: cd2345678901
Create Date: 2026-01-XX 17:00:00.000000

Creates mindmap table for Mind Map Tool.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'de3456789012'
down_revision: Union[str, Sequence[str], None] = 'cd2345678901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create mindmap table."""
    conn = op.get_bind()
    is_postgres = conn.dialect.name == 'postgresql'
    
    # Create mindmap table
    op.create_table(
        'mindmap',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('context_mode', sa.String(20), nullable=False),
        sa.Column('library_doc_ids', postgresql.JSON() if is_postgres else sa.JSON(), nullable=True),
        sa.Column('instructions', sa.Text(), nullable=True),
        sa.Column('size', sa.String(20), nullable=False),
        sa.Column('mind_map_data', postgresql.JSON() if is_postgres else sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['room_id'], ['room.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['user.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_mindmap_chat_id', 'mindmap', ['chat_id'])
    op.create_index('ix_mindmap_room_id', 'mindmap', ['room_id'])
    op.create_index('ix_mindmap_created_by', 'mindmap', ['created_by'])


def downgrade() -> None:
    """Drop mindmap table."""
    try:
        op.drop_index('ix_mindmap_created_by', table_name='mindmap')
        op.drop_index('ix_mindmap_room_id', table_name='mindmap')
        op.drop_index('ix_mindmap_chat_id', table_name='mindmap')
        op.drop_table('mindmap')
    except Exception:
        pass
