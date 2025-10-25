"""
RAG API Endpoints
Provides endpoints for vector search and RAG functionality
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from uuid import UUID

from app.db.session import get_db
from app.services.rag.rag_service import rag_service
from app.services.rag.knowledge_base import get_hr_knowledge, get_it_skills_taxonomy, get_interview_questions
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from sqlalchemy import select

router = APIRouter(prefix="/rag", tags=["RAG"])

@router.post("/initialize")
async def initialize_rag():
    """Initialize RAG service and populate knowledge base"""
    try:
        await rag_service.initialize()
        
        # Populate knowledge base
        hr_knowledge = get_hr_knowledge()
        for knowledge in hr_knowledge:
            await rag_service.add_hr_knowledge(knowledge)
        
        return {"message": "RAG service initialized successfully", "knowledge_items": len(hr_knowledge)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize RAG: {str(e)}")

@router.post("/search")
async def search_knowledge(
    query: str,
    context_type: str = "all",
    limit: int = 5
):
    """Search knowledge base"""
    try:
        results = await rag_service.search_relevant_context(query, context_type, limit)
        return {"query": query, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.post("/generate-response")
async def generate_rag_response(
    query: str,
    context_type: str = "all",
    max_context: int = 3
):
    """Generate response using RAG"""
    try:
        response = await rag_service.generate_rag_response(query, context_type, max_context)
        return {"query": query, "response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Response generation failed: {str(e)}")

@router.post("/add-job/{job_id}")
async def add_job_to_knowledge(
    job_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Add job description to knowledge base"""
    try:
        # Get job from database
        result = await db.execute(select(Vacancy).where(Vacancy.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Convert to dict
        job_data = {
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "location": job.location,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "employer_id": str(job.employer_id)
        }
        
        await rag_service.add_job_description(job_data)
        return {"message": f"Job {job.title} added to knowledge base"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add job: {str(e)}")

@router.post("/add-candidate/{candidate_id}")
async def add_candidate_to_knowledge(
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Add candidate CV to knowledge base"""
    try:
        # Get candidate from database
        result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Convert to dict
        candidate_data = {
            "id": str(candidate.id),
            "full_name": candidate.full_name,
            "email": candidate.email,
            "city": candidate.city,
            "resume_text": candidate.resume_text
        }
        
        await rag_service.add_cv_text(candidate_data)
        return {"message": f"Candidate {candidate.full_name} added to knowledge base"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add candidate: {str(e)}")

@router.post("/enhance-mismatch-analysis")
async def enhance_mismatch_analysis(
    job_id: UUID,
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Enhance mismatch analysis using RAG"""
    try:
        # Get job and candidate
        job_result = await db.execute(select(Vacancy).where(Vacancy.id == job_id))
        job = job_result.scalar_one_or_none()
        
        candidate_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = candidate_result.scalar_one_or_none()
        
        if not job or not candidate:
            raise HTTPException(status_code=404, detail="Job or candidate not found")
        
        # Convert to dicts
        job_data = {
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "location": job.location
        }
        
        candidate_data = {
            "id": str(candidate.id),
            "full_name": candidate.full_name,
            "resume_text": candidate.resume_text
        }
        
        # Enhance analysis
        enhancement = await rag_service.enhance_mismatch_analysis(job_data, candidate_data)
        return enhancement
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enhancement failed: {str(e)}")

@router.post("/generate-questions")
async def generate_enhanced_questions(
    job_id: UUID,
    candidate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Generate enhanced interview questions using RAG"""
    try:
        # Get job and candidate
        job_result = await db.execute(select(Vacancy).where(Vacancy.id == job_id))
        job = job_result.scalar_one_or_none()
        
        candidate_result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
        candidate = candidate_result.scalar_one_or_none()
        
        if not job or not candidate:
            raise HTTPException(status_code=404, detail="Job or candidate not found")
        
        # Convert to dicts
        job_data = {
            "id": str(job.id),
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements
        }
        
        candidate_data = {
            "id": str(candidate.id),
            "full_name": candidate.full_name,
            "resume_text": candidate.resume_text
        }
        
        # Generate questions
        questions = await rag_service.generate_enhanced_questions(job_data, candidate_data)
        return {"questions": questions}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Question generation failed: {str(e)}")

@router.get("/knowledge/skills")
async def get_skills_taxonomy():
    """Get IT skills taxonomy"""
    return {"skills": get_it_skills_taxonomy()}

@router.get("/knowledge/questions")
async def get_interview_questions_db():
    """Get interview questions database"""
    return {"questions": get_interview_questions()}

@router.get("/health")
async def rag_health_check():
    """Health check for RAG service"""
    try:
        # Test vector store connection
        await rag_service.vector_store.initialize_collection()
        return {"status": "healthy", "service": "RAG"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
