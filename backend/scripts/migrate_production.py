"""
Script to apply database migrations in production
Run this to update the production database schema
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
    print("🚀 Applying database migrations in production...")
    
    # Check if we're in production
    if not os.getenv('DATABASE_URL'):
        print("❌ DATABASE_URL not found. This script should be run in production.")
        sys.exit(1)
    
    # Apply migrations
    print("\n⬆️  Applying migrations...")
    if not run_command('alembic upgrade head'):
        print("❌ Failed to apply migrations")
        sys.exit(1)
    
    print("\n✅ Database migrations applied successfully!")
    print("\n📚 Database is now up to date with the latest schema.")


if __name__ == "__main__":
    main()
