#!/usr/bin/env python3
"""
Fix production database schema by adding missing columns for AI functionality.
This script adds the required columns that are missing in production.
"""

import asyncio
import os
import sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings

async def fix_production_schema():
    """Add missing columns to candidate_responses table"""
    
    # Create database engine
    engine = create_async_engine(settings.DATABASE_URL)
    
    try:
        async with engine.begin() as conn:
            print("🔧 Adding missing columns to candidate_responses table...")
            
            # Add mismatch_analysis column
            try:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS mismatch_analysis JSONB;
                """))
                print("✅ Added mismatch_analysis column")
            except Exception as e:
                print(f"⚠️  Error adding mismatch_analysis: {e}")
            
            # Add dialog_findings column
            try:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS dialog_findings JSONB;
                """))
                print("✅ Added dialog_findings column")
            except Exception as e:
                print(f"⚠️  Error adding dialog_findings: {e}")
            
            # Add language_preference column
            try:
                await conn.execute(text("""
                    ALTER TABLE candidate_responses 
                    ADD COLUMN IF NOT EXISTS language_preference VARCHAR(5) DEFAULT 'ru';
                """))
                print("✅ Added language_preference column")
            except Exception as e:
                print(f"⚠️  Error adding language_preference: {e}")
            
            # Verify columns exist
            result = await conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'candidate_responses' 
                AND column_name IN ('mismatch_analysis', 'dialog_findings', 'language_preference')
                ORDER BY column_name;
            """))
            
            columns = result.fetchall()
            print("\n📋 Current schema for candidate_responses:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]} (nullable: {col[2]}, default: {col[3]})")
            
            if len(columns) == 3:
                print("\n✅ All required columns are present!")
            else:
                print(f"\n⚠️  Expected 3 columns, found {len(columns)}")
                
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False
    finally:
        await engine.dispose()
    
    return True

if __name__ == "__main__":
    print("🚀 Fixing production database schema...")
    success = asyncio.run(fix_production_schema())
    if success:
        print("🎉 Database schema fixed successfully!")
    else:
        print("💥 Failed to fix database schema")
        sys.exit(1)
