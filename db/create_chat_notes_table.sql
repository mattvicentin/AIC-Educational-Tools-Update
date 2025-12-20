-- Create chat_notes table for learning progression system
-- This creates the table directly if migrations aren't working

CREATE TABLE IF NOT EXISTS chat_notes (
    id SERIAL PRIMARY KEY,
    chat_id INTEGER NOT NULL UNIQUE REFERENCES chat(id),
    room_id INTEGER NOT NULL REFERENCES room(id),
    notes_content TEXT NOT NULL,
    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_count INTEGER NOT NULL
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS ix_chat_notes_room_id ON chat_notes(room_id);
CREATE INDEX IF NOT EXISTS ix_chat_notes_generated_at ON chat_notes(generated_at);

-- Verify table was created
SELECT 'chat_notes table created successfully' as status;
