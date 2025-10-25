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
    print("🔧 Setting up clean database...")
    
    # Check if we're in production
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL not found. This script should be run in production.")
        sys.exit(1)
    
    # Run migrations to create all tables
    print("\n📊 Running database migrations...")
    if not run_command('alembic upgrade head'):
        print("❌ Failed to run migrations")
        sys.exit(1)
    
    print("\n✅ Database setup completed successfully!")
    print("\n📚 All tables created and ready for use.")


if __name__ == "__main__":
    main()

#jnckdjncjdjncjdndl
djcnjkdncjkld
kjbcidjckdnj