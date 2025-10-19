"""
Script to fix production database migration state
This script marks the current database state as applied without running migrations
"""
import subprocess
import sys
import os


def run_command(command):
    """Run a shell command"""
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return False
    print(result.stdout)
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
    
    # Mark the initial migration as applied (since tables already exist)
    print("\n🏷️  Marking initial migration as applied...")
    if not run_command('alembic stamp 5ece2ad0c9fb'):
        print("❌ Failed to stamp initial migration")
        sys.exit(1)
    
    # Check if max_questions column already exists
    print("\n🔍 Checking if max_questions column exists...")
    check_column_cmd = '''
    python3 -c "
    import sys
    sys.path.append('/app')
    from app.db.session import get_db
    from sqlalchemy import text
    import asyncio

    async def check_column():
        async for db in get_db():
            result = await db.execute(text('SELECT column_name FROM information_schema.columns WHERE table_name = \\'vacancies\\' AND column_name = \\'max_questions\\''))
            exists = result.fetchone() is not None
            print('max_questions exists:', exists)
            return exists

    asyncio.run(check_column())
    "
    '''
    
    result = subprocess.run(check_column_cmd, shell=True, capture_output=True, text=True)
    column_exists = 'max_questions exists: True' in result.stdout
    
    if column_exists:
        print("✅ max_questions column already exists, marking migration as applied...")
        if not run_command('alembic stamp head'):
            print("❌ Failed to stamp head migration")
            sys.exit(1)
    else:
        print("⬆️  Applying new migration (adding max_questions column)...")
        if not run_command('alembic upgrade head'):
            print("❌ Failed to apply new migration")
            sys.exit(1)
    
    print("\n✅ Database migration state fixed successfully!")
    print("\n📚 Database is now up to date with the latest schema.")


if __name__ == "__main__":
    main()
