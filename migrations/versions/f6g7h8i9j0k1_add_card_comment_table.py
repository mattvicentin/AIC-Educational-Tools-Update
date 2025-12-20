"""Add card_comment table for Card View comments

Revision ID: f6g7h8i9j0k1
Revises: e5f6g7h8i9j0
Create Date: 2025-12-08

Card comments allow users to discuss individual cards (segments) in Card View.
Cards are ephemeral but card_key provides a stable reference.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6g7h8i9j0k1'
down_revision = 'e5f6g7h8i9j0'
branch_labels = None
depends_on = None


def upgrade():
    # Create card_comment table (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='card_comment'
    """))
    
    if result.fetchone() is None:
        op.create_table(
            'card_comment',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('chat_id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('message_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('card_key', sa.String(40), nullable=False),
            sa.Column('segment_index', sa.Integer(), nullable=False),
            sa.Column('segment_body_hash', sa.String(16), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['room_id'], ['room.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['message_id'], ['message.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes for efficient queries
        op.create_index('ix_card_comment_card_key', 'card_comment', ['card_key'])
        op.create_index('ix_card_comment_chat_card_created', 'card_comment', ['chat_id', 'card_key', 'created_at'])
        op.create_index('ix_card_comment_user_created', 'card_comment', ['user_id', 'created_at'])


def downgrade():
    # Drop indexes first
    op.drop_index('ix_card_comment_user_created', table_name='card_comment')
    op.drop_index('ix_card_comment_chat_card_created', table_name='card_comment')
    op.drop_index('ix_card_comment_card_key', table_name='card_comment')
    
    # Drop table
    op.drop_table('card_comment')

