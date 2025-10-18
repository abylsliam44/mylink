"""
InterviewService - Orchestrates AI-powered candidate interview flow

This service integrates AI agents to:
1. Detect mismatches between vacancy and candidate resume
2. Generate clarifying questions dynamically
3. Process candidate answers and update findings
4. Recalculate relevance score after each answer
"""

from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from app.models.response import CandidateResponse, ResponseStatus
from app.models.vacancy import Vacancy
from app.models.candidate import Candidate
from app.services.ai.agents.mismatch_agent import MismatchDetectorAgent
from app.services.ai.agents.question_generator_agent import QuestionGeneratorAgent
from app.services.ai.agents.relevance_scorer_agent import RelevanceScorerAgent


class InterviewService:
    """Service for AI-powered candidate interview orchestration"""
    
    def __init__(self):
        self.mismatch_agent = MismatchDetectorAgent()
        self.question_agent = QuestionGeneratorAgent()
        self.scorer_agent = RelevanceScorerAgent()
    
    async def start_interview(
        self, 
        response_id: UUID, 
        db: AsyncSession,
        language: str = "ru"
    ) -> Dict[str, Any]:
        """
        Start interview by analyzing vacancy vs candidate and generating questions
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            language: Interview language (ru/kk/en)
            
        Returns:
            Dict with questions, metadata, and initial analysis
        """
        # Fetch response with related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Fetch vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        if not vacancy:
            raise ValueError(f"Vacancy {response.vacancy_id} not found")
        
        # Fetch candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not candidate:
            raise ValueError(f"Candidate {response.candidate_id} not found")
        
        # Step 1: Run mismatch detection
        mismatch_payload = self._build_mismatch_payload(vacancy, candidate)
        mismatch_analysis = self.mismatch_agent.run(mismatch_payload)
        
        # Step 2: Generate questions based on mismatches
        question_payload = self._build_question_payload(
            mismatch_analysis, 
            vacancy, 
            candidate,
            language
        )
        questions_result = self.question_agent.run(question_payload)
        
        # Step 3: Store analysis in database
        response.mismatch_analysis = mismatch_analysis
        response.language_preference = language
        response.dialog_findings = {
            "answers": [],
            "relocation_ready": False,
            "salary_flex": "",
            "lang_proofs": [],
            "other_clarifications": []
        }
        response.status = ResponseStatus.IN_CHAT
        
        await db.flush()
        await db.commit()
        
        return {
            "response_id": str(response_id),
            "questions": questions_result.get("questions", []),
            "closing_message": questions_result.get("closing_message", ""),
            "meta": questions_result.get("meta", {}),
            "total_questions": len(questions_result.get("questions", [])),
            "mismatch_summary": {
                "total_mismatches": len(mismatch_analysis.get("mismatches", [])),
                "missing_data": mismatch_analysis.get("missing_data", []),
                "coverage": mismatch_analysis.get("coverage_snapshot", {})
            }
        }
    
    async def process_answer(
        self,
        response_id: UUID,
        question_id: str,
        answer_text: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process candidate's answer and update findings
        
        Args:
            response_id: CandidateResponse ID
            question_id: Question identifier (e.g., "q1")
            answer_text: Candidate's answer
            db: Database session
            
        Returns:
            Dict with updated findings and next action
        """
        # Fetch response
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Get current findings
        findings = response.dialog_findings or {
            "answers": [],
            "relocation_ready": False,
            "salary_flex": "",
            "lang_proofs": [],
            "other_clarifications": []
        }
        
        # Store answer
        findings["answers"].append({
            "question_id": question_id,
            "answer": answer_text,
            "timestamp": None  # Will be set by DB
        })
        
        # Extract structured information from answer
        # This is a simplified version - you can enhance with NLP
        answer_lower = answer_text.lower().strip()
        
        # Check for relocation readiness
        if any(keyword in answer_lower for keyword in ["да", "готов", "yes", "иә"]):
            if "переезд" in answer_lower or "relocation" in answer_lower:
                findings["relocation_ready"] = True
        
        # Check for salary flexibility
        if any(keyword in answer_lower for keyword in ["обсуждаем", "negotiable", "гибко"]):
            findings["salary_flex"] = "negotiable"
        
        # Store updated findings
        response.dialog_findings = findings
        
        await db.flush()
        await db.commit()
        
        return {
            "response_id": str(response_id),
            "question_id": question_id,
            "answer_stored": True,
            "findings_updated": True
        }
    
    async def calculate_relevance(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Calculate updated relevance score based on current findings
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            
        Returns:
            Dict with relevance score and verdict
        """
        # Fetch response with related data
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        if not response:
            raise ValueError(f"CandidateResponse {response_id} not found")
        
        # Fetch vacancy
        vacancy_result = await db.execute(
            select(Vacancy).where(Vacancy.id == response.vacancy_id)
        )
        vacancy = vacancy_result.scalar_one_or_none()
        
        # Fetch candidate
        candidate_result = await db.execute(
            select(Candidate).where(Candidate.id == response.candidate_id)
        )
        candidate = candidate_result.scalar_one_or_none()
        
        if not vacancy or not candidate:
            raise ValueError("Vacancy or Candidate not found")
        
        # Build payload for scorer
        scorer_payload = {
            "ids": {
                "job_id": str(vacancy.id),
                "candidate_id": str(candidate.id),
                "application_id": str(response.id)
            },
            "job_struct": self._extract_job_struct(vacancy),
            "cv_struct": self._extract_cv_struct(candidate),
            "mismatches": response.mismatch_analysis.get("mismatches", []) if response.mismatch_analysis else [],
            "missing_data": response.mismatch_analysis.get("missing_data", []) if response.mismatch_analysis else [],
            "widget_payload": {
                "dialogFindings": response.dialog_findings or {}
            },
            "weights_mode": "auto",
            "must_have_skills": [],
            "verdict_thresholds": {"fit": 75, "borderline": 60}
        }
        
        # Run scorer agent
        score_result = self.scorer_agent.run(scorer_payload)
        
        # Update response with new score
        overall_score = score_result.get("overall_match_pct", 0)
        response.relevance_score = overall_score / 100.0  # Store as 0-1 float
        
        # Update status based on verdict
        verdict = score_result.get("verdict", "не подходит")
        if verdict == "подходит":
            response.status = ResponseStatus.APPROVED
            response.rejection_reasons = None
        elif verdict == "сомнительно":
            response.status = ResponseStatus.IN_CHAT  # Keep in chat for more questions
            response.rejection_reasons = {
                "verdict": verdict,
                "summary": score_result.get("summary", {})
            }
        else:
            response.status = ResponseStatus.REJECTED
            response.rejection_reasons = {
                "verdict": verdict,
                "summary": score_result.get("summary", {}),
                "risks": score_result.get("summary", {}).get("risks", [])
            }
        
        await db.flush()
        await db.commit()
        
        return {
            "response_id": str(response_id),
            "relevance_score": overall_score,
            "verdict": verdict,
            "status": response.status.value,
            "scores_breakdown": score_result.get("scores_pct", {}),
            "summary": score_result.get("summary", {})
        }
    
    async def finalize_interview(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Finalize interview and calculate final relevance score
        
        Args:
            response_id: CandidateResponse ID
            db: Database session
            
        Returns:
            Dict with final results
        """
        # Calculate final relevance
        relevance_result = await self.calculate_relevance(response_id, db)
        
        # Fetch updated response
        result = await db.execute(
            select(CandidateResponse)
            .where(CandidateResponse.id == response_id)
        )
        response = result.scalar_one_or_none()
        
        return {
            "response_id": str(response_id),
            "final_score": relevance_result["relevance_score"],
            "verdict": relevance_result["verdict"],
            "status": response.status.value,
            "total_answers": len(response.dialog_findings.get("answers", [])) if response.dialog_findings else 0,
            "summary": relevance_result.get("summary", {}),
            "interview_completed": True
        }
    
    # Helper methods for building payloads
    
    def _build_mismatch_payload(self, vacancy: Vacancy, candidate: Candidate) -> Dict[str, Any]:
        """Build payload for mismatch detection agent"""
        return {
            "jd_text": f"{vacancy.title}\n{vacancy.description}\nLocation: {vacancy.location}\nRequirements: {json.dumps(vacancy.requirements) if vacancy.requirements else 'N/A'}",
            "cv_text": f"{candidate.full_name}\nCity: {candidate.city}\nResume: {candidate.resume_text or 'N/A'}"
        }
    
    def _build_question_payload(
        self, 
        mismatch_analysis: Dict[str, Any], 
        vacancy: Vacancy, 
        candidate: Candidate,
        language: str
    ) -> Dict[str, Any]:
        """Build payload for question generator agent"""
        return {
            "job_struct": mismatch_analysis.get("job_struct", {}),
            "cv_struct": mismatch_analysis.get("cv_struct", {}),
            "mismatches": mismatch_analysis.get("mismatches", []),
            "missing_data": mismatch_analysis.get("missing_data", []),
            "coverage_snapshot": mismatch_analysis.get("coverage_snapshot", {}),
            "limits": {
                "max_questions": 3  # Can be increased if needed
            },
            "language": language
        }
    
    def _extract_job_struct(self, vacancy: Vacancy) -> Dict[str, Any]:
        """Extract job structure from vacancy model"""
        requirements = vacancy.requirements or {}
        
        return {
            "title": vacancy.title,
            "min_experience_years": requirements.get("min_experience_years", 0),
            "required_skills": requirements.get("required_skills", []),
            "nice_to_have": requirements.get("nice_to_have", []),
            "lang_requirement": requirements.get("lang_requirement", []),
            "education_min": requirements.get("education_min", "unknown"),
            "location_requirement": {
                "city": vacancy.location,
                "employment_type": requirements.get("employment_type", "unknown")
            },
            "salary_range": {
                "min": vacancy.salary_min or 0,
                "max": vacancy.salary_max or 0,
                "currency": "KZT"
            },
            "domain": requirements.get("domain", "")
        }
    
    def _extract_cv_struct(self, candidate: Candidate) -> Dict[str, Any]:
        """Extract CV structure from candidate model"""
        return {
            "name": candidate.full_name,
            "total_experience_years": 0,  # TODO: Extract from resume_text
            "skills": [],  # TODO: Extract from resume_text
            "langs": [],  # TODO: Extract from resume_text
            "education_level": "unknown",
            "location": {
                "city": candidate.city
            },
            "employment_type": "unknown",
            "relocation_ready": False,
            "salary_expectation": {
                "value": 0,
                "currency": "KZT",
                "unknown": True
            },
            "domain_tags": [],
            "notes": candidate.resume_text or ""
        }


# Singleton instance
interview_service = InterviewService()

