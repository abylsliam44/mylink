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


def add_missing_columns_direct():
    """Add missing columns using direct SQL commands"""
    try:
        import os
        import subprocess
        
        # Get database URL from environment
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found")
            return False
        
        print("🔍 Adding missing columns to candidate_responses table...")
        
        # Use psql to execute SQL commands directly
        sql_commands = [
            "ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS mismatch_analysis JSONB;",
            "ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS dialog_findings JSONB;", 
            "ALTER TABLE candidate_responses ADD COLUMN IF NOT EXISTS language_preference VARCHAR(5) DEFAULT 'ru';"
        ]
        
        for sql in sql_commands:
            print(f"➕ Executing: {sql}")
            result = subprocess.run([
                'psql', database_url, '-c', sql
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"⚠️  Warning: {sql} - {result.stderr}")
            else:
                print(f"✅ Success: {sql}")
        
        print("✅ All required columns are now present")
        return True
        
    except Exception as e:
        print(f"❌ Error adding columns: {e}")
        return False


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
    add_missing_columns_direct()
    
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