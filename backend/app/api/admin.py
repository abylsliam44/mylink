"""
Admin endpoints for production fixes
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.employer import Employer
from app.utils.auth import get_current_employer

router = APIRouter(tags=["Admin"])

@router.post("/fix-database-schema")
async def fix_database_schema(
    db: AsyncSession = Depends(get_db),
    current_employer: Employer = Depends(get_current_employer)
):
    """
    Fix production database schema by adding missing AI columns.
    This endpoint can be called to fix the schema issue.
    """
    try:
        # Add missing columns
        await db.execute(text("""
            ALTER TABLE candidate_responses 
            ADD COLUMN IF NOT EXISTS mismatch_analysis JSONB;
        """))
        
        await db.execute(text("""
            ALTER TABLE candidate_responses 
            ADD COLUMN IF NOT EXISTS dialog_findings JSONB;
        """))
        
        await db.execute(text("""
            ALTER TABLE candidate_responses 
            ADD COLUMN IF NOT EXISTS language_preference VARCHAR(5) DEFAULT 'ru';
        """))
        
        await db.commit()
        
        # Verify columns exist
        result = await db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'candidate_responses' 
            AND column_name IN ('mismatch_analysis', 'dialog_findings', 'language_preference');
        """))
        
        columns = [row[0] for row in result.fetchall()]
        
        return {
            "success": True,
            "message": "Database schema fixed successfully",
            "added_columns": columns,
            "total_columns": len(columns)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fix database schema: {str(e)}"
        )

@router.get("/check-database-schema")
async def check_database_schema(
    db: AsyncSession = Depends(get_db),
    current_employer: Employer = Depends(get_current_employer)
):
    """
    Check if database schema has all required columns.
    """
    try:
        result = await db.execute(text("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'candidate_responses' 
            AND column_name IN ('mismatch_analysis', 'dialog_findings', 'language_preference')
            ORDER BY column_name;
        """))
        
        columns = result.fetchall()
        
        required_columns = ['mismatch_analysis', 'dialog_findings', 'language_preference']
        found_columns = [col[0] for col in columns]
        missing_columns = [col for col in required_columns if col not in found_columns]
        
        return {
            "schema_ok": len(missing_columns) == 0,
            "found_columns": found_columns,
            "missing_columns": missing_columns,
            "total_required": len(required_columns),
            "total_found": len(found_columns)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check database schema: {str(e)}"
        )
