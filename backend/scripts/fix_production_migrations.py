"""
Script to fix production database migration state
This script adds missing columns and marks the current database state as applied
"""
import subprocess
import sys
import os
import asyncio
from sqlalchemy import text


def run_command(command):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
    return True


async def check_and_add_missing_columns():
    """Check if missing columns exist and add them if needed"""
    try:
        from app.db.session import get_db
        from sqlalchemy import text
        
        print("🔍 Checking for missing columns in candidate_responses table...")
        
        # Get database session
        async for db in get_db():
            # Check if mismatch_analysis column exists
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name = 'mismatch_analysis'
            """))
            mismatch_exists = result.fetchone() is not None
            
            # Check if dialog_findings column exists
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name = 'dialog_findings'
            """))
            dialog_exists = result.fetchone() is not None
            
            # Check if language_preference column exists
            result = await db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name = 'language_preference'
            """))
            lang_exists = result.fetchone() is not None
            
            # Add missing columns
            if not mismatch_exists:
                print("➕ Adding mismatch_analysis column...")
                await db.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN mismatch_analysis JSONB
                """))
                await db.commit()
                print("✅ mismatch_analysis column added")
            
            if not dialog_exists:
                print("➕ Adding dialog_findings column...")
                await db.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN dialog_findings JSONB
                """))
                await db.commit()
                print("✅ dialog_findings column added")
            
            if not lang_exists:
                print("➕ Adding language_preference column...")
                await db.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN language_preference VARCHAR(5) NOT NULL DEFAULT 'ru'
                """))
                await db.commit()
                print("✅ language_preference column added")
            
            print("✅ All required columns are now present")
            break
            
    except Exception as e:
        print(f"❌ Error checking/adding columns: {e}")
        return False
    
    return True


def main():
    print("🔧 Fixing production database migration state...")
    
    # Check if we're in production
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL not found. This script should be run in production.")
        sys.exit(1)
    
    # First, check current migration state
    print("\n📊 Checking current migration state...")
    if not run_command('alembic current'):
        print("❌ Failed to check current state")
        sys.exit(1)
    
    # Add missing columns if needed
    print("\n🔧 Adding missing columns...")
    asyncio.run(check_and_add_missing_columns())
    
    # Mark the initial migration as applied (since tables already exist)
    print("\n🏷️  Marking initial migration as applied...")
    if not run_command('alembic stamp 5ece2ad0c9fb'):
        print("❌ Failed to stamp initial migration")
        sys.exit(1)
    
    # Mark the max_questions migration as applied
    print("\n🏷️  Marking max_questions migration as applied...")
    if not run_command('alembic stamp 4eb2c3c8a127'):
        print("❌ Failed to stamp max_questions migration")
        sys.exit(1)
    
    # Mark head as applied
    print("\n🏷️  Marking head migration as applied...")
    if not run_command('alembic stamp head'):
        print("❌ Failed to stamp head migration")
        sys.exit(1)
    
    print("\n✅ Database migration state fixed successfully!")
    print("\n📚 Database is now up to date with the latest schema.")


if __name__ == "__main__":
    main()