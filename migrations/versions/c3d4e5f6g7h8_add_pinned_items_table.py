"""Add pinned_items table for message/comment pinning

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6a7
Create Date: 2025-12-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c3d4e5f6g7h8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    # Create pinned_items table (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='pinned_items'
    """))
    
    if result.fetchone() is None:
        op.create_table('pinned_items',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('chat_id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=True),
            sa.Column('comment_id', sa.Integer(), nullable=True),
            sa.Column('role', sa.String(length=20), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            
            # Foreign keys with CASCADE delete
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['room_id'], ['room.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['message_id'], ['message.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['comment_id'], ['comment.id'], ondelete='CASCADE'),
            
            # Primary key
            sa.PrimaryKeyConstraint('id'),
            
            # Check constraint: exactly one of message_id or comment_id must be set
            sa.CheckConstraint(
                '(message_id IS NOT NULL AND comment_id IS NULL) OR '
                '(message_id IS NULL AND comment_id IS NOT NULL)',
                name='check_exactly_one_item'
            ),
            
            # Unique constraints to prevent duplicate pins
            sa.UniqueConstraint('user_id', 'message_id', name='unique_user_message_pin'),
            sa.UniqueConstraint('user_id', 'comment_id', name='unique_user_comment_pin'),
        )
        
        # Create indexes for performance
        op.create_index('ix_pinned_items_user_id', 'pinned_items', ['user_id'])
        op.create_index('ix_pinned_items_room_id', 'pinned_items', ['room_id'])
        op.create_index('ix_pinned_items_chat_id', 'pinned_items', ['chat_id'])
        # Compound index for fast user+chat lookups
        op.create_index('ix_pins_user_chat', 'pinned_items', ['user_id', 'chat_id'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_pins_user_chat', table_name='pinned_items')
    op.drop_index('ix_pinned_items_chat_id', table_name='pinned_items')
    op.drop_index('ix_pinned_items_room_id', table_name='pinned_items')
    op.drop_index('ix_pinned_items_user_id', table_name='pinned_items')
    
    # Drop table
    op.drop_table('pinned_items')
