"""Add room_refinement_history table

Revision ID: 8c2d1a7f3b21
Revises: 55f5aa3fe9e7
Create Date: 2025-09-11 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c2d1a7f3b21'
down_revision: Union[str, Sequence[str], None] = '55f5aa3fe9e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if table already exists (idempotent migration)
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='room_refinement_history'
    """))
    
    if result.fetchone() is None:
        # Table doesn't exist, create it
        op.create_table(
            'room_refinement_history',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=True),
            sa.Column('preference', sa.Text(), nullable=True),
            sa.Column('old_modes_json', sa.Text(), nullable=True),
            sa.Column('new_modes_json', sa.Text(), nullable=True),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(['room_id'], ['room.id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_room_ref_hist_room_id', 'room_refinement_history', ['room_id'])
        op.create_index('ix_room_ref_hist_user_id', 'room_refinement_history', ['user_id'])
        op.create_index('ix_room_ref_hist_created_at', 'room_refinement_history', ['created_at'])
    # else: table already exists, skip


def downgrade() -> None:
    op.drop_index('ix_room_ref_hist_created_at', table_name='room_refinement_history')
    op.drop_index('ix_room_ref_hist_user_id', table_name='room_refinement_history')
    op.drop_index('ix_room_ref_hist_room_id', table_name='room_refinement_history')
    op.drop_table('room_refinement_history')


