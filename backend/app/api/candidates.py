from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID

from app.db.session import get_db
from app.schemas.candidate import CandidateCreate, CandidateResponse
from app.models.candidate import Candidate
from app.models.response import CandidateResponse as RespModel
from app.models.response import ResponseStatus
from app.models.vacancy import Vacancy

from pypdf import PdfReader

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


@router.post("/upload_pdf", response_model=CandidateResponse)
async def upload_candidate_pdf(
    file: UploadFile = File(...),
    full_name: str = Form(...),
    email: str = Form(...),
    city: str = Form(""),
    phone: Optional[str] = Form(None),
    vacancy_id: Optional[UUID] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload PDF resume, extract text, create candidate, and optional response."""
    if file.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=400, detail="Поддерживается только PDF")
    content = await file.read()
    try:
        reader = PdfReader(bytes(content))
        pages = [p.extract_text() or "" for p in reader.pages]
        text = "\n".join(pages).strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка чтения PDF: {e}")

    cand = Candidate(full_name=full_name, email=email, phone=phone, city=city or "", resume_text=text[:20000])
    db.add(cand)
    await db.flush()
    await db.refresh(cand)

    if vacancy_id:
        # ensure vacancy exists
        v = await db.execute(select(Vacancy).where(Vacancy.id == vacancy_id))
        if v.scalar_one_or_none():
            r = RespModel(vacancy_id=vacancy_id, candidate_id=cand.id, status=ResponseStatus.NEW)
            db.add(r)
            await db.flush()
    return cand


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

