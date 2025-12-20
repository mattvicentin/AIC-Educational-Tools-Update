"""Add group_size field to Room model

Revision ID: 55f5aa3fe9e7
Revises: 
Create Date: 2025-08-18 12:31:50.175942

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '55f5aa3fe9e7'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add group_size column to room table (only if it doesn't exist)
    conn = op.get_bind()
    
    # Check if column already exists
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='room' AND column_name='group_size'
    """))
    
    if result.fetchone() is None:
        # Column doesn't exist, add it
        op.add_column('room', sa.Column('group_size', sa.String(20), nullable=True))
    # else: column already exists, skip


def downgrade() -> None:
    """Downgrade schema."""
    # Remove group_size column from room table
    op.drop_column('room', 'group_size')
