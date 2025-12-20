#!/usr/bin/env python3
"""
main.py
Purpose: Main Flask application entry point for AI Collab Online
Status: [ACTIVE]
Created: 2025-01-27
Author: writeian

Main application entry point with health checks and production migrations
"""

import os
from datetime import datetime, timedelta
from flask import Flask, render_template, redirect, url_for

# Import the application factory
from src.app import create_app, db

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✓ Loaded environment variables from .env file")
except ImportError:
    print(
        "⚠️ python-dotenv not installed - environment variables may not be loaded from .env"
    )
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")


def run_production_migrations(app):
    """Run Alembic migrations in production environment.
    
    Uses PostgreSQL advisory locks to prevent race conditions when multiple
    Gunicorn workers start simultaneously. Only one worker will run migrations;
    others will wait and then skip if migrations are already complete.
    """
    # Only run migrations if explicitly enabled (prevents per-worker runs)
    run_migrations = os.getenv("RUN_DB_MIGRATIONS_ON_STARTUP", "true").lower() == "true"
    if not run_migrations:
        print("⚠️ Migrations disabled via RUN_DB_MIGRATIONS_ON_STARTUP=false")
        return
    
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("FLASK_ENV") == "production":
        try:
            from alembic.config import Config
            from alembic import command
            from alembic.runtime.migration import MigrationContext
            from alembic.script import ScriptDirectory
            import time

            print("🔒 Acquiring migration lock...")
            alembic_cfg = Config("alembic.ini")
            
            # Use PostgreSQL advisory lock to prevent concurrent migration runs
            # Lock ID: 1234567890 (arbitrary but consistent)
            LOCK_ID = 1234567890
            lock_acquired = False
            
            with app.app_context():
                from src.app import db
                conn = db.engine.connect()
                
                # Try to acquire advisory lock (non-blocking)
                # If another worker is running migrations, this will return False
                try:
                    lock_result = conn.execute(
                        db.text("SELECT pg_try_advisory_lock(:lock_id)").bindparams(lock_id=LOCK_ID)
                    ).scalar()
                    lock_acquired = lock_result
                except Exception as lock_error:
                    # If advisory locks aren't available (e.g., SQLite), fall back to old behavior
                    print(f"⚠️ Advisory lock not available ({lock_error}), proceeding without lock")
                    lock_acquired = True  # Proceed anyway
                
                if not lock_acquired:
                    print("⏳ Another worker is running migrations. Waiting 5 seconds...")
                    time.sleep(5)
                    # Check if migrations are already complete
                    try:
                        context = MigrationContext.configure(conn)
                        current_rev = context.get_current_revision()
                        script = ScriptDirectory.from_config(alembic_cfg)
                        head_rev = script.get_current_head()
                        
                        if current_rev == head_rev:
                            print(f"✅ Migrations already complete ({head_rev}). Skipping.")
                            app.config["MIGRATION_STATUS"] = "applied"
                            conn.close()
                            return
                        else:
                            print(f"⚠️ Migrations still in progress. Skipping this worker.")
                            conn.close()
                            return
                    except Exception:
                        # alembic_version table might not exist yet, let the other worker handle it
                        print("⚠️ Migrations in progress by another worker. Skipping.")
                        conn.close()
                        return
                
                # We have the lock - proceed with migration checks
                print("✅ Migration lock acquired. Checking current revision...")
                
                try:
                    context = MigrationContext.configure(conn)
                    current_rev = context.get_current_revision()
                    
                    # Get head revision
                    script = ScriptDirectory.from_config(alembic_cfg)
                    head_rev = script.get_current_head()
                    
                    if current_rev == head_rev:
                        print(f"✅ Database already at head revision ({head_rev}). Skipping migrations.")
                        app.config["MIGRATION_STATUS"] = "applied"
                        # Release lock before returning
                        try:
                            conn.execute(db.text("SELECT pg_advisory_unlock(:lock_id)").bindparams(lock_id=LOCK_ID))
                        except:
                            pass
                        conn.close()
                        return
                except Exception as check_error:
                    # alembic_version table might not exist - that's okay, we'll create it
                    print(f"ℹ️  Checking revision status: {check_error}")
                    print("   (This is normal if alembic_version table doesn't exist yet)")
                
                # Keep connection open to maintain lock during migrations
                # We'll close it after migrations complete
                migration_conn = conn
            
            # Run migrations with error handling
            # Note: The advisory lock is still held by migration_conn
            try:
                print("🚀 Running Alembic migrations...")
                command.upgrade(alembic_cfg, "head")
                print("✅ Alembic migrations complete.")
                app.config["MIGRATION_STATUS"] = "applied"
                # Clear any previous migration errors
                if "MIGRATION_ERROR" in app.config:
                    del app.config["MIGRATION_ERROR"]
            except Exception as e:
                error_msg = str(e)
                # Check if it's a race condition error we can safely ignore
                if "duplicate key value violates unique constraint" in error_msg and "pg_type_typname_nsp_index" in error_msg:
                    print(f"⚠️ Race condition detected (another worker created alembic_version). Checking status...")
                    # Check if migrations actually completed despite the error
                    with app.app_context():
                        from src.app import db
                        check_conn = db.engine.connect()
                        try:
                            context = MigrationContext.configure(check_conn)
                            current_rev = context.get_current_revision()
                            script = ScriptDirectory.from_config(alembic_cfg)
                            head_rev = script.get_current_head()
                            if current_rev == head_rev:
                                print(f"✅ Migrations completed successfully by another worker ({head_rev})")
                                app.config["MIGRATION_STATUS"] = "applied"
                                check_conn.close()
                                # Release lock and close connection
                                try:
                                    migration_conn.execute(db.text("SELECT pg_advisory_unlock(:lock_id)").bindparams(lock_id=LOCK_ID))
                                except:
                                    pass
                                migration_conn.close()
                                return
                        except:
                            pass
                        check_conn.close()
                
                print(f"⚠️ Alembic migration warning: {error_msg}")
                print("Continuing with app startup...")
                app.config["MIGRATION_ERROR"] = error_msg
            finally:
                # Always release lock and close connection
                if 'migration_conn' in locals():
                    try:
                        migration_conn.execute(db.text("SELECT pg_advisory_unlock(:lock_id)").bindparams(lock_id=LOCK_ID))
                    except:
                        pass
                    migration_conn.close()
        except Exception as e:
            print(f"❌ Alembic migration failed: {e}")
            app.config["MIGRATION_ERROR"] = str(e)
            # Don't crash - let app continue
            print("Continuing with app startup...")
        
        # Ensure basic tables exist using the created app context
        try:
            print("Ensuring basic tables exist...")
            from src.app import db
            with app.app_context():
                db.create_all()
                print("✓ Basic tables ensured")
                
                # CRITICAL: Manually create chat_notes table (migration system broken)
                try:
                    from src.models import ChatNotes
                    ChatNotes.query.first()  # Test if table exists
                    print("✓ chat_notes table exists")
                except Exception:
                    print("⚠️ chat_notes table missing, creating manually...")
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(db.text("""
                                CREATE TABLE IF NOT EXISTS chat_notes (
                                    id SERIAL PRIMARY KEY,
                                    chat_id INTEGER NOT NULL UNIQUE REFERENCES chat(id),
                                    room_id INTEGER NOT NULL REFERENCES room(id),
                                    notes_content TEXT NOT NULL,
                                    generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    message_count INTEGER NOT NULL
                                )
                            """))
                            conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_chat_notes_room_id ON chat_notes(room_id)"))
                            conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_chat_notes_generated_at ON chat_notes(generated_at)"))
                            conn.commit()
                        print("✓ chat_notes table created manually")
                    except Exception as create_error:
                        print(f"❌ Failed to create chat_notes table: {create_error}")
                
                # CRITICAL: Manually create pinned_items table (migration system broken)
                try:
                    from src.models import PinnedItem
                    PinnedItem.query.first()  # Test if table exists
                    print("✓ pinned_items table exists")
                except Exception:
                    print("⚠️ pinned_items table missing, creating manually...")
                    try:
                        # Detect if PostgreSQL or SQLite
                        is_postgres = 'postgresql' in str(db.engine.url)
                        
                        with db.engine.connect() as conn:
                            if is_postgres:
                                # PostgreSQL-specific SQL (includes is_shared column)
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS pinned_items (
                                        id SERIAL PRIMARY KEY,
                                        user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                                        room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                        chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
                                        message_id INTEGER REFERENCES message(id) ON DELETE CASCADE,
                                        comment_id INTEGER REFERENCES comment(id) ON DELETE CASCADE,
                                        role VARCHAR(20),
                                        content TEXT NOT NULL,
                                        is_shared BOOLEAN NOT NULL DEFAULT FALSE,
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        CONSTRAINT check_exactly_one_item CHECK (
                                            (message_id IS NOT NULL AND comment_id IS NULL) OR
                                            (message_id IS NULL AND comment_id IS NOT NULL)
                                        )
                                    )
                                """))
                                conn.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS unique_user_message_pin ON pinned_items(user_id, message_id) WHERE message_id IS NOT NULL"))
                                conn.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS unique_user_comment_pin ON pinned_items(user_id, comment_id) WHERE comment_id IS NOT NULL"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_user_id ON pinned_items(user_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_room_id ON pinned_items(room_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_id ON pinned_items(chat_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pins_user_chat ON pinned_items(user_id, chat_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_shared ON pinned_items(chat_id, is_shared)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_room_shared ON pinned_items(room_id, is_shared)"))
                            else:
                                # SQLite-compatible SQL (includes is_shared column)
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS pinned_items (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user_id INTEGER NOT NULL REFERENCES user(id) ON DELETE CASCADE,
                                        room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                        chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
                                        message_id INTEGER REFERENCES message(id) ON DELETE CASCADE,
                                        comment_id INTEGER REFERENCES comment(id) ON DELETE CASCADE,
                                        role VARCHAR(20),
                                        content TEXT NOT NULL,
                                        is_shared INTEGER NOT NULL DEFAULT 0,
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        CHECK (
                                            (message_id IS NOT NULL AND comment_id IS NULL) OR
                                            (message_id IS NULL AND comment_id IS NOT NULL)
                                        )
                                    )
                                """))
                                conn.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS unique_user_message_pin ON pinned_items(user_id, message_id)"))
                                conn.execute(db.text("CREATE UNIQUE INDEX IF NOT EXISTS unique_user_comment_pin ON pinned_items(user_id, comment_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_user_id ON pinned_items(user_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_room_id ON pinned_items(room_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_id ON pinned_items(chat_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pins_user_chat ON pinned_items(user_id, chat_id)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_shared ON pinned_items(chat_id, is_shared)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pinned_items_room_shared ON pinned_items(room_id, is_shared)"))
                            conn.commit()
                        print("✓ pinned_items table created manually")
                    except Exception as create_error:
                        print(f"❌ Failed to create pinned_items table: {create_error}")
                
                # PHASE B: Add is_shared column to pinned_items for shared pins feature
                try:
                    with db.engine.connect() as conn:
                        result = conn.execute(db.text("SELECT is_shared FROM pinned_items LIMIT 1"))
                        result.close()
                    print("✓ is_shared column exists")
                except Exception as check_error:
                    print(f"⚠️ is_shared column missing ({check_error}), adding...")
                    try:
                        is_postgres = 'postgresql' in str(db.engine.url)
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text("""
                                    ALTER TABLE pinned_items 
                                    ADD COLUMN IF NOT EXISTS is_shared BOOLEAN NOT NULL DEFAULT FALSE
                                """))
                                conn.execute(db.text("""
                                    CREATE INDEX IF NOT EXISTS ix_pinned_items_chat_shared 
                                        ON pinned_items(chat_id, is_shared)
                                """))
                                conn.execute(db.text("""
                                    CREATE INDEX IF NOT EXISTS ix_pinned_items_room_shared 
                                        ON pinned_items(room_id, is_shared)
                                """))
                            else:
                                # SQLite: BOOLEAN stored as INTEGER
                                conn.execute(db.text("""
                                    ALTER TABLE pinned_items 
                                    ADD COLUMN is_shared INTEGER NOT NULL DEFAULT 0
                                """))
                                try:
                                    conn.execute(db.text("""
                                        CREATE INDEX ix_pinned_items_chat_shared 
                                            ON pinned_items(chat_id, is_shared)
                                    """))
                                    conn.execute(db.text("""
                                        CREATE INDEX ix_pinned_items_room_shared 
                                            ON pinned_items(room_id, is_shared)
                                    """))
                                except Exception:
                                    pass  # Indexes may already exist
                            conn.commit()
                        print("✓ is_shared column added")
                    except Exception as alter_error:
                        print(f"❌ Failed to add is_shared column: {alter_error}")
                
                # PHASE D: Manually create pin_chat_metadata table for pin-seeded chats
                try:
                    from src.models import PinChatMetadata
                    PinChatMetadata.query.first()  # Test if table exists
                    print("✓ pin_chat_metadata table exists")
                except Exception:
                    print("⚠️ pin_chat_metadata table missing, creating manually...")
                    try:
                        is_postgres = 'postgresql' in str(db.engine.url)
                        
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS pin_chat_metadata (
                                        id SERIAL PRIMARY KEY,
                                        chat_id INTEGER NOT NULL UNIQUE REFERENCES chat(id) ON DELETE CASCADE,
                                        option VARCHAR(32) NOT NULL,
                                        pin_snapshot TEXT NOT NULL,
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    )
                                """))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pin_chat_metadata_chat_id ON pin_chat_metadata(chat_id)"))
                            else:
                                # SQLite-compatible SQL
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS pin_chat_metadata (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        chat_id INTEGER NOT NULL UNIQUE REFERENCES chat(id) ON DELETE CASCADE,
                                        option VARCHAR(32) NOT NULL,
                                        pin_snapshot TEXT NOT NULL,
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    )
                                """))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_pin_chat_metadata_chat_id ON pin_chat_metadata(chat_id)"))
                            conn.commit()
                        print("✓ pin_chat_metadata table created manually")
                    except Exception as create_error:
                        print(f"❌ Failed to create pin_chat_metadata table: {create_error}")
                
                # PHASE E: Manually create card_comment table for Card View comments
                try:
                    from src.models import CardComment
                    CardComment.query.first()  # Test if table exists
                    print("✓ card_comment table exists")
                    
                    # Check if content_type column exists, add if missing
                    try:
                        is_postgres = 'postgresql' in str(db.engine.url)
                        with db.engine.connect() as conn:
                            if is_postgres:
                                result = conn.execute(db.text(
                                    "SELECT column_name FROM information_schema.columns "
                                    "WHERE table_name='card_comment' AND column_name='content_type'"
                                ))
                            else:
                                result = conn.execute(db.text("PRAGMA table_info(card_comment)"))
                                cols = [row[1] for row in result.fetchall()]
                                has_content_type = 'content_type' in cols
                                if not has_content_type:
                                    conn.execute(db.text(
                                        "ALTER TABLE card_comment ADD COLUMN content_type VARCHAR(10) NOT NULL DEFAULT 'user'"
                                    ))
                                    conn.commit()
                                    print("✓ Added content_type column to card_comment")
                                result = None  # Prevent further processing
                            
                            if result is not None:  # PostgreSQL path
                                if not result.fetchone():
                                    conn.execute(db.text(
                                        "ALTER TABLE card_comment ADD COLUMN content_type VARCHAR(10) NOT NULL DEFAULT 'user'"
                                    ))
                                    conn.commit()
                                    print("✓ Added content_type column to card_comment")
                    except Exception as alter_error:
                        print(f"⚠️ Could not check/add content_type column: {alter_error}")
                        
                except Exception:
                    print("⚠️ card_comment table missing, creating manually...")
                    try:
                        is_postgres = 'postgresql' in str(db.engine.url)
                        
                        with db.engine.connect() as conn:
                            if is_postgres:
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS card_comment (
                                        id SERIAL PRIMARY KEY,
                                        chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
                                        room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                        message_id INTEGER NOT NULL REFERENCES message(id) ON DELETE CASCADE,
                                        user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                                        card_key VARCHAR(40) NOT NULL,
                                        segment_index INTEGER NOT NULL,
                                        segment_body_hash VARCHAR(16),
                                        content TEXT NOT NULL,
                                        content_type VARCHAR(10) NOT NULL DEFAULT 'user',
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        deleted_at TIMESTAMP
                                    )
                                """))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_card_key ON card_comment(card_key)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_chat_card_created ON card_comment(chat_id, card_key, created_at)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_user_created ON card_comment(user_id, created_at)"))
                            else:
                                # SQLite-compatible SQL
                                conn.execute(db.text("""
                                    CREATE TABLE IF NOT EXISTS card_comment (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        chat_id INTEGER NOT NULL REFERENCES chat(id) ON DELETE CASCADE,
                                        room_id INTEGER NOT NULL REFERENCES room(id) ON DELETE CASCADE,
                                        message_id INTEGER NOT NULL REFERENCES message(id) ON DELETE CASCADE,
                                        user_id INTEGER REFERENCES user(id) ON DELETE SET NULL,
                                        card_key VARCHAR(40) NOT NULL,
                                        segment_index INTEGER NOT NULL,
                                        segment_body_hash VARCHAR(16),
                                        content TEXT NOT NULL,
                                        content_type VARCHAR(10) NOT NULL DEFAULT 'user',
                                        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                        deleted_at TIMESTAMP
                                    )
                                """))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_card_key ON card_comment(card_key)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_chat_card_created ON card_comment(chat_id, card_key, created_at)"))
                                conn.execute(db.text("CREATE INDEX IF NOT EXISTS ix_card_comment_user_created ON card_comment(user_id, created_at)"))
                            conn.commit()
                        print("✓ card_comment table created manually")
                    except Exception as create_error:
                        print(f"❌ Failed to create card_comment table: {create_error}")
        except Exception as e:
            print(f"Table creation warning: {e}")
            print("Continuing with app startup...")


# Create the Flask application
print("🚀 CREATING FLASK APP WITH DEBUG LOGGING 🚀")
try:
    app = create_app()
    print("🚀 FLASK APP CREATED - ADDING REQUEST LOGGING 🚀")
except Exception as e:
    print(f"❌ CRITICAL: Failed to create Flask app: {e}")
    import traceback
    traceback.print_exc()
    # Create minimal app for health checks
    app = Flask(__name__)
    app.config['ERROR_STATUS'] = str(e)

# Liveness check - Is the process alive? (Register early for healthchecks)
@app.route("/health")
def health():
    """
    Liveness probe: Returns 200 as long as the process is running.
    Does NOT check database - use /ready for that.
    """
    try:
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
        }, 200
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }, 200  # Still return 200 so Railway knows process is alive

# Automatically run Alembic migrations in production (e.g., on Railway)
# Do this AFTER health endpoint is registered so healthchecks can pass
try:
    run_production_migrations(app)
except Exception as e:
    print(f"⚠️ Migration error (non-critical): {e}")
    # Don't crash - app can still serve health checks


# Readiness check - Is the app ready to serve traffic?
@app.route("/ready")
def ready():
    """
    Readiness probe: Returns 200 only when database is connected and migrations applied.
    Used by load balancers to determine if traffic should be routed here.
    """
    from time import time as current_time
    
    checks = {}
    overall_status = 200
    
    # Database connection check (with timeout)
    db_start = current_time()
    try:
        # Short timeout (2s) to fail fast if DB is unreachable
        with db.engine.connect().execution_options(timeout=2.0) as conn:
            conn.execute(db.text("SELECT 1"))
        
        latency_ms = int((current_time() - db_start) * 1000)
        checks["database"] = {
            "status": "connected",
            "latency_ms": latency_ms
        }
    except Exception as e:
        checks["database"] = {
            "status": "error",
            "message": str(e)[:200]  # Truncate long error messages
        }
        overall_status = 503
    
    # Check for DB initialization errors
    if app.config.get("DB_INIT_ERROR"):
        checks["db_init"] = {
            "status": "error",
            "message": app.config["DB_INIT_ERROR"][:200]
        }
        overall_status = 503
    
    # Check for migration errors
    if app.config.get("MIGRATION_ERROR"):
        checks["migrations"] = {
            "status": "error", 
            "message": app.config["MIGRATION_ERROR"][:200]
        }
        overall_status = 503
    elif app.config.get("MIGRATION_STATUS") == "applied":
        checks["migrations"] = {"status": "applied"}
    
    return {
        "status": "ready" if overall_status == 200 else "not_ready",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
        "version": "3.1.0"
    }, overall_status


# Test endpoint to list all routes
@app.route("/routes")
def list_routes():
    """List all registered routes for debugging."""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append(
            {
                "endpoint": rule.endpoint,
                "methods": list(rule.methods),
                "rule": str(rule),
            }
        )
    return {"routes": routes}



# Debug: Check deployed code version
@app.route("/version")
def version_check():
    """Check which commit/version is deployed."""
    import subprocess
    try:
        commit = subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()
    except:
        commit = 'unknown'
    
    return {
        "commit": commit,
        "has_pin_logging": True,  # This line added in commit aff3088
        "has_nested_transaction": True,  # This line added in commit acbec7a
        "timestamp": datetime.utcnow().isoformat()
    }, 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
# Force deployment Sun Sep 14 21:41:37 PDT 2025
