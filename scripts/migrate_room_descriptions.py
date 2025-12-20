#!/usr/bin/env python3
"""
Migrate existing room descriptions to use the new smart description logic.
Updates rooms that have the generic template description with better descriptions based on their goals.

SECURITY: This script uses Flask app context to access the database.
It reads credentials from environment variables via app.config, NOT hardcoded values.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import create_app, db
from src.models.room import Room
from src.utils.room_descriptions import generate_room_short_description


# Pattern to detect the old generic template
GENERIC_PATTERN = "A collaborative learning space focused on"


def is_generic_description(description: str) -> bool:
    """Check if a description uses the old generic template."""
    if not description:
        return False
    return GENERIC_PATTERN in description and "Designed to help you achieve your learning goals" in description


def migrate_room_descriptions(dry_run: bool = True, limit: int = None):
    """
    Migrate room descriptions to use the new smart logic.
    
    Args:
        dry_run: If True, show what would change without saving
        limit: Optional limit on number of rooms to process
    """
    app = create_app()
    
    with app.app_context():
        # Find rooms with generic descriptions
        query = Room.query.filter(Room.is_active == True)
        
        if limit:
            query = query.limit(limit)
        
        rooms = query.all()
        
        print(f"🔍 Checking {len(rooms)} active rooms...\n")
        
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        for room in rooms:
            try:
                # Check if room has generic description
                if not is_generic_description(room.short_description):
                    skipped_count += 1
                    continue
                
                # Generate new description
                new_description = generate_room_short_description(
                    template_type="general",
                    room_name=room.name,
                    group_size=room.group_size or "",
                    goals=room.goals or ""
                )
                
                # Check if it actually changed
                if new_description == room.short_description:
                    print(f"⏭️  Room {room.id} ({room.name}): No change needed")
                    skipped_count += 1
                    continue
                
                # Show the change
                print(f"\n{'='*80}")
                print(f"📝 Room {room.id}: {room.name}")
                print(f"{'='*80}")
                print(f"OLD: {room.short_description}")
                print(f"NEW: {new_description}")
                print(f"{'='*80}\n")
                
                if not dry_run:
                    # Save the new description
                    room.short_description = new_description
                    db.session.add(room)
                    updated_count += 1
                else:
                    updated_count += 1
                
            except Exception as e:
                print(f"❌ Error processing room {room.id}: {e}")
                error_count += 1
        
        # Commit changes if not dry run
        if not dry_run and updated_count > 0:
            try:
                db.session.commit()
                print(f"\n✅ Successfully updated {updated_count} rooms")
            except Exception as e:
                db.session.rollback()
                print(f"\n❌ Error committing changes: {e}")
                return
        
        # Summary
        print(f"\n{'='*80}")
        print(f"📊 SUMMARY")
        print(f"{'='*80}")
        print(f"Total rooms checked: {len(rooms)}")
        print(f"Would update: {updated_count}")
        print(f"Skipped (no change needed): {skipped_count}")
        print(f"Errors: {error_count}")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN - No changes were saved")
            print(f"Run with --execute to apply these changes")
        else:
            print(f"\n✅ Changes committed to database")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Migrate room descriptions to use improved logic')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually apply changes (default is dry-run)')
    parser.add_argument('--limit', type=int, 
                       help='Limit number of rooms to process')
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        print("🔍 DRY RUN MODE - showing what would change without saving\n")
    else:
        print("⚠️  EXECUTE MODE - changes will be saved to database\n")
        confirm = input("Are you sure you want to update room descriptions? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
    
    migrate_room_descriptions(dry_run=dry_run, limit=args.limit)

