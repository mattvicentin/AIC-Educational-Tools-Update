"""add document tables railway

Revision ID: add_document_tables_railway
Revises: f6g7h8i9j0k1
Create Date: 2024-11-06 12:00:00.000000

Creates document and document_chunk tables for Library Tool (Railway PostgreSQL).

⚠️⚠️⚠️ MIGRATION DEPENDENCY ⚠️⚠️⚠️
This migration depends on: f6g7h8i9j0k1_add_card_comment_table.py

Before running this migration:
1. Verify parent migration is applied: alembic current
2. If f6g7h8i9j0k1 is NOT applied, run: alembic upgrade f6g7h8i9j0k1 first
3. Then run: alembic upgrade head

Migration creates:
- document table (metadata, full text, room scoping)
- document_chunk table (chunked text with FTS search_vector)
- pg_trgm extension (PostgreSQL full-text search)
- GIN index on search_vector for fast text search

Note: This migration uses PostgreSQL-specific features (pg_trgm extension).
For SQLite testing, the pg_trgm line will fail - modify migration or use PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_document_tables_railway'
down_revision = 'f6g7h8i9j0k1'  # Updated: card_comment table migration
branch_labels = None
depends_on = None


def upgrade():
    # Enable pg_trgm extension for full-text search (if not already enabled)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    
    conn = op.get_bind()
    
    # Check if document table already exists (idempotent migration)
    doc_table_exists = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='document'
    """)).fetchone()
    
    if doc_table_exists is None:
        # Create document table
        op.create_table(
            'document',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('file_id', sa.String(length=255), nullable=False),
            sa.Column('name', sa.String(length=500), nullable=False),
            sa.Column('full_text', sa.Text(), nullable=True),
            sa.Column('file_size', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('uploaded_by', sa.Integer(), nullable=True),
            sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column('summary', sa.Text(), nullable=True),
            sa.ForeignKeyConstraint(['room_id'], ['room.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['uploaded_by'], ['user.id'], ondelete='SET NULL'),
            sa.PrimaryKeyConstraint('id')
        )
        
        # Create indexes on document table
        op.create_index(op.f('ix_document_file_id'), 'document', ['file_id'], unique=False)
        op.create_index(op.f('ix_document_room_id'), 'document', ['room_id'], unique=False)
        op.create_index(op.f('ix_document_uploaded_by'), 'document', ['uploaded_by'], unique=False)
        op.create_index(op.f('ix_document_uploaded_at'), 'document', ['uploaded_at'], unique=False)
        
        # Create composite unique constraint: (room_id, file_id)
        # This allows same file_id in different rooms, but prevents duplicates within a room
        op.create_index(
            'ix_document_room_file_unique',
            'document',
            ['room_id', 'file_id'],
            unique=True
        )
    
    # Check if document_chunk table already exists (idempotent migration)
    chunk_table_exists = conn.execute(sa.text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema='public' AND table_name='document_chunk'
    """)).fetchone()
    
    if chunk_table_exists is None:
        # Create document_chunk table with TSVECTOR type
        op.create_table(
            'document_chunk',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('document_id', sa.Integer(), nullable=False),
            sa.Column('chunk_index', sa.Integer(), nullable=False),
            sa.Column('chunk_text', sa.Text(), nullable=False),
            sa.Column('start_char', sa.Integer(), nullable=True),
            sa.Column('end_char', sa.Integer(), nullable=True),
            sa.Column('token_count', sa.Integer(), nullable=True),
            sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),  # Proper TSVECTOR type
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['document_id'], ['document.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('document_id', 'chunk_index', name='uq_document_chunk_doc_idx')  # Uniqueness constraint
        )
        
        # Create indexes on document_chunk table
        op.create_index(op.f('ix_document_chunk_document_id'), 'document_chunk', ['document_id'], unique=False)
        
        # Create GIN index directly on search_vector column (not computed)
        op.execute("""
            CREATE INDEX idx_chunk_search_vector 
            ON document_chunk 
            USING gin (search_vector);
        """)
        
        # Create composite index for housekeeping queries (document_id, created_at)
        op.create_index(
            'ix_document_chunk_doc_created_at',
            'document_chunk',
            ['document_id', 'created_at'],
            unique=False
        )
        
        # Create trigger function to update search_vector automatically
        op.execute("""
            CREATE OR REPLACE FUNCTION update_document_chunk_search_vector()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.search_vector := to_tsvector('english', NEW.chunk_text);
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Create trigger to auto-update search_vector on insert/update
        op.execute("""
            CREATE TRIGGER document_chunk_search_vector_update
            BEFORE INSERT OR UPDATE ON document_chunk
            FOR EACH ROW
            EXECUTE FUNCTION update_document_chunk_search_vector();
        """)
    
    # Create function to get room storage usage (idempotent - CREATE OR REPLACE)
    op.execute("""
        CREATE OR REPLACE FUNCTION get_room_storage_usage(target_room_id INTEGER)
        RETURNS TABLE(
            total_bytes BIGINT,
            file_count BIGINT,
            limit_bytes BIGINT,
            remaining_bytes BIGINT,
            percent_used NUMERIC
        ) AS $$
        DECLARE
            storage_limit BIGINT := 10485760; -- 10MB
        BEGIN
            RETURN QUERY
            SELECT
                COALESCE(SUM(d.file_size), 0)::BIGINT as total_bytes,
                COUNT(d.id)::BIGINT as file_count,
                storage_limit as limit_bytes,
                GREATEST(0, storage_limit - COALESCE(SUM(d.file_size), 0))::BIGINT as remaining_bytes,
                ROUND((COALESCE(SUM(d.file_size), 0)::NUMERIC / storage_limit * 100), 2) as percent_used
            FROM document d
            WHERE d.room_id = target_room_id;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    # Drop function
    op.execute("DROP FUNCTION IF EXISTS get_room_storage_usage(INTEGER);")
    
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS document_chunk_search_vector_update ON document_chunk;")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_document_chunk_search_vector();")
    
    # Drop indexes
    op.drop_index('ix_document_chunk_doc_created_at', table_name='document_chunk')
    op.drop_index('idx_chunk_search_vector', table_name='document_chunk')
    op.drop_index(op.f('ix_document_chunk_document_id'), table_name='document_chunk')
    
    # Drop unique constraint
    op.drop_constraint('uq_document_chunk_doc_idx', 'document_chunk', type_='unique')
    
    # Drop tables (chunks first due to foreign key)
    op.drop_table('document_chunk')
    
    # Drop document indexes
    op.drop_index('ix_document_room_file_unique', table_name='document')
    op.drop_index(op.f('ix_document_uploaded_at'), table_name='document')
    op.drop_index(op.f('ix_document_uploaded_by'), table_name='document')
    op.drop_index(op.f('ix_document_room_id'), table_name='document')
    op.drop_index(op.f('ix_document_file_id'), table_name='document')
    
    # Drop document table
    op.drop_table('document')
    
    # Note: We don't drop pg_trgm extension as it might be used elsewhere

