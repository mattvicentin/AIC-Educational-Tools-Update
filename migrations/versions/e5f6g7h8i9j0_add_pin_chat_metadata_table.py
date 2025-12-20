"""Add pin_chat_metadata table for pin-seeded chats

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-12-04

Stores metadata for pin-seeded chats including the option selected
and a snapshot of pins used to create the chat.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade():
    # Create pin_chat_metadata table (idempotent)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='pin_chat_metadata'
    """))
    
    if result.fetchone() is None:
        op.create_table('pin_chat_metadata',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('chat_id', sa.Integer(), nullable=False),
            sa.Column('option', sa.String(length=32), nullable=False),
            sa.Column('pin_snapshot', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            
            # Foreign key with CASCADE delete
            sa.ForeignKeyConstraint(['chat_id'], ['chat.id'], ondelete='CASCADE'),
            
            # Primary key
            sa.PrimaryKeyConstraint('id'),
            
            # Unique constraint: one metadata per chat
            sa.UniqueConstraint('chat_id', name='uq_pin_chat_metadata_chat_id'),
        )
        
        # Create index for chat_id lookups
        op.create_index('ix_pin_chat_metadata_chat_id', 'pin_chat_metadata', ['chat_id'])


def downgrade():
    # Drop index
    op.drop_index('ix_pin_chat_metadata_chat_id', table_name='pin_chat_metadata')
    
    # Drop table
    op.drop_table('pin_chat_metadata')
