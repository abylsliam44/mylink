#!/usr/bin/env python3
"""
Quick fix for production database - add missing AI columns.
This script can be run directly on production to fix the schema issue.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def fix_production():
    """Quick fix for production database"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    print(f"🔗 Connecting to database...")
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            print("🔧 Adding missing AI columns...")
            
            # Add columns one by one with error handling
            columns_to_add = [
                ("mismatch_analysis", "JSONB"),
                ("dialog_findings", "JSONB"), 
                ("language_preference", "VARCHAR(5) DEFAULT 'ru'")
            ]
            
            for col_name, col_type in columns_to_add:
                try:
                    await conn.execute(text(f"""
                        ALTER TABLE candidate_responses 
                        ADD COLUMN IF NOT EXISTS {col_name} {col_type};
                    """))
                    print(f"✅ Added {col_name}")
                except Exception as e:
                    print(f"⚠️  Error adding {col_name}: {e}")
            
            # Verify the fix
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name IN ('mismatch_analysis', 'dialog_findings', 'language_preference');
            """))
            
            columns = [row[0] for row in result.fetchall()]
            print(f"\n📋 Found columns: {columns}")
            
            if len(columns) >= 3:
                print("✅ Database schema fixed successfully!")
                return True
            else:
                print("⚠️  Some columns might be missing")
                return False
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("🚀 Quick fix for production database...")
    success = asyncio.run(fix_production())
    if success:
        print("🎉 Production database fixed!")
    else:
        print("💥 Failed to fix production database")
        sys.exit(1)
