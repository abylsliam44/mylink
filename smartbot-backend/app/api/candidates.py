from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID

from app.db.session import get_db
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.models.candidate import Candidate

router = APIRouter(prefix="/candidates", tags=["Candidates"])


@router.post("", response_model=CandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    candidate_data: CandidateCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new candidate profile"""
    new_candidate = Candidate(
        full_name=candidate_data.full_name,
        email=candidate_data.email,
        phone=candidate_data.phone,
        city=candidate_data.city,
        resume_text=candidate_data.resume_text
    )
    
    db.add(new_candidate)
    await db.flush()
    await db.refresh(new_candidate)
    
    return new_candidate


@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get candidate by ID"""
    result = await db.execute(
        select(Candidate).where(Candidate.id == candidate_id)
    )
    candidate = result.scalar_one_or_none()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found"
        )
    
    return candidate


@router.get("", response_model=List[CandidateResponse])
async def list_candidates(
    db: AsyncSession = Depends(get_db)
):
    """List all candidates"""
    result = await db.execute(
        select(Candidate).order_by(Candidate.created_at.desc())
    )
    candidates = result.scalars().all()
    
    return candidates

