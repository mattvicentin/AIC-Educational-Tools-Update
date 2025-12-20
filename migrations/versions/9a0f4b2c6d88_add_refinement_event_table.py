"""Add refinement_event table

Revision ID: 9a0f4b2c6d88
Revises: 8c2d1a7f3b21
Create Date: 2025-09-11 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a0f4b2c6d88'
down_revision: Union[str, Sequence[str], None] = '8c2d1a7f3b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='refinement_event'
    """))
    
    if result.fetchone() is None:
        # Table doesn't exist, create it
        op.create_table(
            'refinement_event',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('room_id', sa.Integer(), nullable=True),
            sa.Column('event_type', sa.String(length=32), nullable=False),
            sa.Column('preference', sa.Text(), nullable=True),
            sa.Column('added', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('removed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('changed', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['room_id'], ['room.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_ref_event_user_id', 'refinement_event', ['user_id'])
        op.create_index('ix_ref_event_room_id', 'refinement_event', ['room_id'])
        op.create_index('ix_ref_event_created_at', 'refinement_event', ['created_at'])
    # else: table already exists, skip


def downgrade() -> None:
    op.drop_index('ix_ref_event_created_at', table_name='refinement_event')
    op.drop_index('ix_ref_event_room_id', table_name='refinement_event')
    op.drop_index('ix_ref_event_user_id', table_name='refinement_event')
    op.drop_table('refinement_event')


