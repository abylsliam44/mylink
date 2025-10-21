#!/usr/bin/env python3
"""
Auto-fix database schema on startup
This script runs automatically when the app starts to fix missing columns
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

async def auto_fix_schema():
    """Automatically fix database schema on startup"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("⚠️  DATABASE_URL not found, skipping schema fix")
        return False
    
    print("🔧 Auto-fixing database schema on startup...")
    engine = create_async_engine(database_url)
    
    try:
        async with engine.begin() as conn:
            # Check if columns already exist
            result = await conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name IN ('mismatch_analysis', 'dialog_findings', 'language_preference');
            """))
            
            existing_columns = [row[0] for row in result.fetchall()]
            required_columns = ['mismatch_analysis', 'dialog_findings', 'language_preference']
            missing_columns = [col for col in required_columns if col not in existing_columns]
            
            if not missing_columns:
                print("✅ All required columns already exist")
                return True
            
            print(f"🔧 Adding missing columns: {missing_columns}")
            
            # Add missing columns
            if 'mismatch_analysis' in missing_columns:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS mismatch_analysis JSONB;
                """))
                print("✅ Added mismatch_analysis")
            
            if 'dialog_findings' in missing_columns:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS dialog_findings JSONB;
                """))
                print("✅ Added dialog_findings")
            
            if 'language_preference' in missing_columns:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS language_preference VARCHAR(5) DEFAULT 'ru';
                """))
                print("✅ Added language_preference")
            
            print("🎉 Database schema auto-fixed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Auto-fix failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(auto_fix_schema())
    sys.exit(0 if success else 1)
