"""
Integration with existing services
Bridges autonomous agents with existing business logic
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..autonomous_agents import autonomous_agent_orchestrator
from ..autonomous_agents.agent_state import EventType
from ..interview_service import InterviewService
from ..chat_service import ChatService
from ...models.vacancy import Vacancy
from ...models.candidate import Candidate
from ...models.response import CandidateResponse, ResponseStatus

logger = logging.getLogger(__name__)


class AutonomousAgentIntegration:
    """Integration layer between autonomous agents and existing services"""
    
    def __init__(self):
        self.interview_service = InterviewService()
        self.chat_service = ChatService()
        self.orchestrator = autonomous_agent_orchestrator
    
    async def integrate_candidate_application(
        self,
        response_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Integrate candidate application with autonomous agents"""
        try:
            # Get response with related data
            result = await db.execute(
                select(CandidateResponse)
                .where(CandidateResponse.id == response_id)
            )
            response = result.scalar_one_or_none()
            
            if not response:
                return {"error": "Response not found"}
            
            # Get vacancy and candidate data
            vacancy_result = await db.execute(
                select(Vacancy).where(Vacancy.id == response.vacancy_id)
            )
            vacancy = vacancy_result.scalar_one_or_none()
            
            candidate_result = await db.execute(
                select(Candidate).where(Candidate.id == response.candidate_id)
            )
            candidate = candidate_result.scalar_one_or_none()
            
            if not vacancy or not candidate:
                return {"error": "Vacancy or candidate not found"}
            
            # Convert to dictionaries for autonomous agents
            vacancy_data = {
                "id": str(vacancy.id),
                "title": vacancy.title,
                "description": vacancy.description,
                "requirements": vacancy.requirements,
                "location": vacancy.location,
                "salary_min": vacancy.salary_min,
                "salary_max": vacancy.salary_max,
                "company": vacancy.company,
                "required_skills": vacancy.required_skills or [],
                "language_requirement": vacancy.language_requirement or "",
                "domain": vacancy.domain or ""
            }
            
            candidate_data = {
                "id": str(candidate.id),
                "full_name": candidate.full_name,
                "resume_text": candidate.resume_text or "",
                "email": candidate.email,
                "phone": candidate.phone
            }
            
            # Process through autonomous agents
            result = await self.orchestrator.process_candidate_application(
                vacancy_id=str(vacancy.id),
                candidate_id=str(candidate.id),
                response_id=str(response_id),
                vacancy_data=vacancy_data,
                candidate_data=candidate_data,
                language=response.language_preference or "ru"
            )
            
            if result.get("success"):
                # Update response status
                response.status = ResponseStatus.IN_CHAT
                await db.commit()
                
                logger.info(f"Integrated candidate application {response_id} with autonomous agents")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to integrate candidate application: {e}")
            return {"error": str(e)}
    
    async def integrate_candidate_response(
        self,
        response_id: UUID,
        question_index: int,
        answer: str,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Integrate candidate response with autonomous agents"""
        try:
            # Get response data
            result = await db.execute(
                select(CandidateResponse)
                .where(CandidateResponse.id == response_id)
            )
            response = result.scalar_one_or_none()
            
            if not response:
                return {"error": "Response not found"}
            
            # Process through autonomous agents
            result = await self.orchestrator.process_employer_request(
                employer_id="system",
                request_type="candidate_responded",
                data={
                    "response_id": str(response_id),
                    "question_index": question_index,
                    "answer": answer,
                    "candidate_id": str(response.candidate_id),
                    "vacancy_id": str(response.vacancy_id)
                }
            )
            
            if result.get("success"):
                # Update conversation history in response
                if not response.dialog_findings:
                    response.dialog_findings = {
                        "answers": [],
                        "relocation_ready": False,
                        "salary_flex": "",
                        "lang_proofs": [],
                        "other_clarifications": []
                    }
                
                # Add answer to dialog findings
                response.dialog_findings["answers"].append({
                    "question_index": question_index,
                    "answer": answer,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
                await db.commit()
                
                logger.info(f"Integrated candidate response {response_id} with autonomous agents")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to integrate candidate response: {e}")
            return {"error": str(e)}
    
    async def integrate_employer_view(
        self,
        employer_id: str,
        candidate_id: UUID,
        vacancy_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Integrate employer viewing candidate with autonomous agents"""
        try:
            # Get vacancy and candidate data
            vacancy_result = await db.execute(
                select(Vacancy).where(Vacancy.id == vacancy_id)
            )
            vacancy = vacancy_result.scalar_one_or_none()
            
            candidate_result = await db.execute(
                select(Candidate).where(Candidate.id == candidate_id)
            )
            candidate = candidate_result.scalar_one_or_none()
            
            if not vacancy or not candidate:
                return {"error": "Vacancy or candidate not found"}
            
            # Convert to dictionaries
            vacancy_data = {
                "id": str(vacancy.id),
                "title": vacancy.title,
                "description": vacancy.description,
                "requirements": vacancy.requirements,
                "location": vacancy.location,
                "salary_min": vacancy.salary_min,
                "salary_max": vacancy.salary_max,
                "company": vacancy.company,
                "required_skills": vacancy.required_skills or [],
                "language_requirement": vacancy.language_requirement or "",
                "domain": vacancy.domain or ""
            }
            
            candidate_data = {
                "id": str(candidate.id),
                "full_name": candidate.full_name,
                "resume_text": candidate.resume_text or "",
                "email": candidate.email,
                "phone": candidate.phone
            }
            
            # Process through autonomous agents
            result = await self.orchestrator.process_employer_request(
                employer_id=employer_id,
                request_type="view_candidate",
                data={
                    "candidate": candidate_data,
                    "vacancy": vacancy_data,
                    "candidate_id": str(candidate_id),
                    "vacancy_id": str(vacancy_id)
                }
            )
            
            if result.get("success"):
                logger.info(f"Integrated employer view for candidate {candidate_id} with autonomous agents")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to integrate employer view: {e}")
            return {"error": str(e)}
    
    async def get_enhanced_analysis(
        self,
        response_id: UUID,
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get enhanced analysis from autonomous agents"""
        try:
            # Get analysis from autonomous agents
            result = await self.orchestrator.get_candidate_analysis(
                candidate_id="",  # Will be extracted from response
                vacancy_id="",    # Will be extracted from response
                response_id=str(response_id)
            )
            
            if not result.get("success"):
                return {"error": result.get("error", "Analysis not available")}
            
            return {
                "success": True,
                "analysis": result.get("analysis"),
                "analysis_type": analysis_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get enhanced analysis: {e}")
            return {"error": str(e)}
    
    async def get_employer_insights(
        self,
        employer_id: str,
        vacancy_id: UUID,
        insights_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """Get employer insights from autonomous agents"""
        try:
            # Get insights from autonomous agents
            result = await self.orchestrator.get_employer_insights(
                employer_id=employer_id,
                vacancy_id=str(vacancy_id)
            )
            
            if not result.get("success"):
                return {"error": result.get("error", "Insights not available")}
            
            return {
                "success": True,
                "insights": result.get("insights"),
                "insights_type": insights_type,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get employer insights: {e}")
            return {"error": str(e)}
    
    async def add_hr_knowledge(
        self,
        knowledge_data: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Add HR knowledge to RAG system"""
        try:
            result = await self.orchestrator.add_rag_documents(
                documents=knowledge_data,
                document_type="hr_knowledge"
            )
            
            if result.get("success"):
                logger.info(f"Added {len(knowledge_data)} HR knowledge documents")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to add HR knowledge: {e}")
            return {"error": str(e)}
    
    async def search_hr_knowledge(
        self,
        query: str,
        context_type: str = "hr_knowledge",
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search HR knowledge base"""
        try:
            result = await self.orchestrator.search_knowledge_base(
                query=query,
                context_type=context_type,
                limit=limit
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to search HR knowledge: {e}")
            return {"error": str(e)}
    
    async def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics including autonomous agents"""
        try:
            # Get autonomous agents metrics
            autonomous_metrics = self.orchestrator.get_system_metrics()
            
            # Get existing service metrics (if any)
            existing_metrics = {
                "interview_service": {
                    "status": "active",
                    "cache_ttl": self.interview_service.CACHE_TTL
                },
                "chat_service": {
                    "status": "active"
                }
            }
            
            return {
                "autonomous_agents": autonomous_metrics,
                "existing_services": existing_metrics,
                "integration_status": "active",
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {"error": str(e)}


# Global integration instance
autonomous_agent_integration = AutonomousAgentIntegration()
