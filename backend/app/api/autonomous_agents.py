"""
Autonomous Agents API
REST API endpoints for autonomous agents system
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_db
from ..services.autonomous_agents import autonomous_agent_orchestrator
from ..services.autonomous_agents.agent_state import AgentType, EventType
from ..models.vacancy import Vacancy
from ..models.candidate import Candidate
from ..models.response import CandidateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autonomous-agents", tags=["autonomous-agents"])


# Pydantic models
class CandidateApplicationRequest(BaseModel):
    vacancy_id: str
    candidate_id: str
    response_id: str
    language: str = "ru"


class EmployerRequestRequest(BaseModel):
    employer_id: str
    request_type: str = Field(..., description="view_candidate, request_analysis, chat_request")
    data: Dict[str, Any]


class RAGDocumentRequest(BaseModel):
    documents: List[Dict[str, Any]]
    document_type: str = Field(..., description="job, cv, hr_knowledge")


class KnowledgeSearchRequest(BaseModel):
    query: str
    context_type: str = "all"
    limit: int = 5


class AgentMetricsResponse(BaseModel):
    success: bool
    metrics: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Startup and shutdown events
@router.on_event("startup")
async def startup_autonomous_agents():
    """Start autonomous agents system on startup"""
    try:
        await autonomous_agent_orchestrator.start()
        logger.info("Autonomous agents system started")
    except Exception as e:
        logger.error(f"Failed to start autonomous agents: {e}")


@router.on_event("shutdown")
async def shutdown_autonomous_agents():
    """Stop autonomous agents system on shutdown"""
    try:
        await autonomous_agent_orchestrator.stop()
        logger.info("Autonomous agents system stopped")
    except Exception as e:
        logger.error(f"Failed to stop autonomous agents: {e}")


# Health check
@router.get("/health")
async def health_check():
    """Health check for autonomous agents system"""
    try:
        metrics = autonomous_agent_orchestrator.get_system_metrics()
        is_healthy = metrics["orchestrator"]["is_running"]
        
        if not is_healthy:
            raise HTTPException(status_code=503, detail="Autonomous agents system not running")
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Health check failed: {e}")


# System metrics
@router.get("/metrics", response_model=AgentMetricsResponse)
async def get_system_metrics():
    """Get system metrics"""
    try:
        metrics = autonomous_agent_orchestrator.get_system_metrics()
        return AgentMetricsResponse(success=True, metrics=metrics)
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        return AgentMetricsResponse(success=False, error=str(e))


# Agent-specific metrics
@router.get("/agents/metrics")
async def get_all_agent_metrics():
    """Get metrics for all agents"""
    try:
        metrics = autonomous_agent_orchestrator.get_all_agent_metrics()
        return {"success": True, "metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get agent metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{agent_id}/metrics")
async def get_agent_metrics(agent_id: str):
    """Get metrics for specific agent"""
    try:
        metrics = autonomous_agent_orchestrator.get_agent_metrics(agent_id)
        if not metrics:
            raise HTTPException(status_code=404, detail="Agent not found")
        return {"success": True, "metrics": metrics}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Candidate endpoints
@router.post("/candidates/process-application")
async def process_candidate_application(
    request: CandidateApplicationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Process candidate application through autonomous agents"""
    try:
        # Get vacancy and candidate data from database
        vacancy_result = await db.execute(
            Vacancy.__table__.select().where(Vacancy.id == request.vacancy_id)
        )
        vacancy_row = vacancy_result.fetchone()
        if not vacancy_row:
            raise HTTPException(status_code=404, detail="Vacancy not found")
        
        candidate_result = await db.execute(
            Candidate.__table__.select().where(Candidate.id == request.candidate_id)
        )
        candidate_row = candidate_result.fetchone()
        if not candidate_row:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Convert to dictionaries
        vacancy_data = dict(vacancy_row._mapping)
        candidate_data = dict(candidate_row._mapping)
        
        # Process through autonomous agents
        result = await autonomous_agent_orchestrator.process_candidate_application(
            vacancy_id=request.vacancy_id,
            candidate_id=request.candidate_id,
            response_id=request.response_id,
            vacancy_data=vacancy_data,
            candidate_data=candidate_data,
            language=request.language
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process candidate application: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/candidates/{candidate_id}/analysis")
async def get_candidate_analysis(
    candidate_id: str,
    vacancy_id: str,
    response_id: str
):
    """Get analysis results for a candidate"""
    try:
        result = await autonomous_agent_orchestrator.get_candidate_analysis(
            candidate_id=candidate_id,
            vacancy_id=vacancy_id,
            response_id=response_id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Analysis not found"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get candidate analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Employer endpoints
@router.post("/employers/request")
async def process_employer_request(request: EmployerRequestRequest):
    """Process employer request through autonomous agents"""
    try:
        result = await autonomous_agent_orchestrator.process_employer_request(
            employer_id=request.employer_id,
            request_type=request.request_type,
            data=request.data
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Request failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process employer request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/employers/{employer_id}/insights")
async def get_employer_insights(
    employer_id: str,
    vacancy_id: str
):
    """Get insights for employer"""
    try:
        result = await autonomous_agent_orchestrator.get_employer_insights(
            employer_id=employer_id,
            vacancy_id=vacancy_id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error", "Insights not found"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get employer insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# RAG endpoints
@router.post("/rag/documents")
async def add_rag_documents(request: RAGDocumentRequest):
    """Add documents to RAG knowledge base"""
    try:
        result = await autonomous_agent_orchestrator.add_rag_documents(
            documents=request.documents,
            document_type=request.document_type
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to add documents"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add RAG documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/search")
async def search_knowledge_base(request: KnowledgeSearchRequest):
    """Search the knowledge base"""
    try:
        result = await autonomous_agent_orchestrator.search_knowledge_base(
            query=request.query,
            context_type=request.context_type,
            limit=request.limit
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search knowledge base: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Event bus endpoints
@router.get("/events/metrics")
async def get_event_metrics():
    """Get event bus metrics"""
    try:
        metrics = autonomous_agent_orchestrator.event_bus.get_metrics()
        return {"success": True, "metrics": metrics}
    except Exception as e:
        logger.error(f"Failed to get event metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events/dlq")
async def get_dead_letter_queue():
    """Get dead letter queue events"""
    try:
        dlq_events = autonomous_agent_orchestrator.event_bus.get_dead_letter_queue()
        return {"success": True, "events": dlq_events}
    except Exception as e:
        logger.error(f"Failed to get DLQ events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/events/dlq")
async def clear_dead_letter_queue():
    """Clear dead letter queue"""
    try:
        autonomous_agent_orchestrator.event_bus.clear_dead_letter_queue()
        return {"success": True, "message": "Dead letter queue cleared"}
    except Exception as e:
        logger.error(f"Failed to clear DLQ: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Agent management endpoints
@router.get("/agents")
async def list_agents():
    """List all registered agents"""
    try:
        all_agents = autonomous_agent_orchestrator.registry.get_all_agents()
        agents_info = []
        
        for agent in all_agents:
            agents_info.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_type": agent.agent_type.value,
                "status": agent.state.status.value,
                "is_healthy": agent.is_healthy(),
                "metrics": agent.get_metrics()
            })
        
        return {"success": True, "agents": agents_info}
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agents/{agent_id}/restart")
async def restart_agent(agent_id: str):
    """Restart a specific agent"""
    try:
        agent = autonomous_agent_orchestrator.registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Shutdown and reinitialize
        await agent.shutdown()
        await agent.initialize()
        
        return {"success": True, "message": f"Agent {agent_id} restarted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restart agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Integration with existing endpoints
@router.post("/integrate/candidate-response")
async def integrate_candidate_response(
    response_id: str,
    question_index: int,
    answer: str,
    db: AsyncSession = Depends(get_db)
):
    """Integrate with existing candidate response processing"""
    try:
        # Get response from database
        response_result = await db.execute(
            CandidateResponse.__table__.select().where(CandidateResponse.id == response_id)
        )
        response_row = response_result.fetchone()
        if not response_row:
            raise HTTPException(status_code=404, detail="Response not found")
        
        response_data = dict(response_row._mapping)
        
        # Process through autonomous agents
        result = await autonomous_agent_orchestrator.process_employer_request(
            employer_id="system",
            request_type="candidate_responded",
            data={
                "response_id": response_id,
                "question_index": question_index,
                "answer": answer,
                "response_data": response_data
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to integrate candidate response: {e}")
        raise HTTPException(status_code=500, detail=str(e))