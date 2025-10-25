"""
Autonomous Agent Orchestrator
Coordinates autonomous agents and manages the overall system
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .agent_registry import autonomous_agent_registry
from .event_bus import event_bus, Event, EventType
from .agent_state import AgentType, AgentStatus
from .candidate_agent import CandidateAutonomousAgent
from .employer_agent import EmployerAutonomousAgent

logger = logging.getLogger(__name__)


class AutonomousAgentOrchestrator:
    """Orchestrator for autonomous agents system"""
    
    def __init__(self):
        self.registry = autonomous_agent_registry
        self.event_bus = event_bus
        self._is_running = False
        self._startup_task: Optional[asyncio.Task] = None
        self._metrics = {
            "total_events_processed": 0,
            "candidate_events_processed": 0,
            "employer_events_processed": 0,
            "system_events_processed": 0,
            "errors": 0,
            "start_time": None
        }
    
    async def start(self):
        """Start the orchestrator and all agents"""
        if self._is_running:
            return
        
        try:
            self._is_running = True
            self._metrics["start_time"] = datetime.utcnow().isoformat()
            
            # Start event bus
            await self.event_bus.start()
            
            # Start registry
            await self.registry.start()
            
            # Register default agents
            await self._register_default_agents()
            
            # Start monitoring
            self._startup_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("Autonomous agent orchestrator started")
            
        except Exception as e:
            logger.error(f"Failed to start orchestrator: {e}")
            self._is_running = False
            raise
    
    async def stop(self):
        """Stop the orchestrator and all agents"""
        if not self._is_running:
            return
        
        try:
            self._is_running = False
            
            # Stop monitoring
            if self._startup_task:
                self._startup_task.cancel()
                try:
                    await self._startup_task
                except asyncio.CancelledError:
                    pass
            
            # Stop registry (this will stop all agents)
            await self.registry.stop()
            
            # Stop event bus
            await self.event_bus.stop()
            
            logger.info("Autonomous agent orchestrator stopped")
            
        except Exception as e:
            logger.error(f"Error stopping orchestrator: {e}")
    
    async def _register_default_agents(self):
        """Register default autonomous agents"""
        try:
            # Register candidate agent
            candidate_agent = CandidateAutonomousAgent()
            await self.registry.register_agent(candidate_agent)
            logger.info("Registered candidate autonomous agent")
            
            # Register employer agent
            employer_agent = EmployerAutonomousAgent()
            await self.registry.register_agent(employer_agent)
            logger.info("Registered employer autonomous agent")
            
        except Exception as e:
            logger.error(f"Failed to register default agents: {e}")
            raise
    
    async def _monitoring_loop(self):
        """Monitoring loop for system health"""
        while self._is_running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
    
    async def _perform_health_checks(self):
        """Perform health checks on all agents"""
        try:
            # Check agent health
            health_status = await self.registry.health_check_all()
            unhealthy_agents = [agent_id for agent_id, healthy in health_status.items() if not healthy]
            
            if unhealthy_agents:
                logger.warning(f"Unhealthy agents detected: {unhealthy_agents}")
                # Attempt to restart unhealthy agents
                restarted_count = await self.registry.restart_unhealthy_agents()
                if restarted_count > 0:
                    logger.info(f"Restarted {restarted_count} unhealthy agents")
            
            # Log metrics
            metrics = self.get_system_metrics()
            logger.debug(f"System metrics: {metrics}")
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    async def process_candidate_application(
        self,
        vacancy_id: str,
        candidate_id: str,
        response_id: str,
        vacancy_data: Dict[str, Any],
        candidate_data: Dict[str, Any],
        language: str = "ru"
    ) -> Dict[str, Any]:
        """Process candidate application through autonomous agents"""
        try:
            # Publish candidate applied event
            await self.event_bus.publish_simple(
                event_type=EventType.CANDIDATE_APPLIED,
                payload={
                    "vacancy_id": vacancy_id,
                    "candidate_id": candidate_id,
                    "response_id": response_id,
                    "vacancy": vacancy_data,
                    "candidate": candidate_data,
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=5  # High priority
            )
            
            self._metrics["candidate_events_processed"] += 1
            self._metrics["total_events_processed"] += 1
            
            return {
                "success": True,
                "message": "Candidate application processing initiated",
                "response_id": response_id
            }
            
        except Exception as e:
            logger.error(f"Failed to process candidate application: {e}")
            self._metrics["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def process_employer_request(
        self,
        employer_id: str,
        request_type: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process employer request through autonomous agents"""
        try:
            # Determine event type based on request
            if request_type == "view_candidate":
                event_type = EventType.EMPLOYER_VIEWED_CANDIDATE
            elif request_type == "request_analysis":
                event_type = EventType.EMPLOYER_REQUESTED_ANALYSIS
            elif request_type == "chat_request":
                event_type = EventType.EMPLOYER_CHAT_REQUESTED
            else:
                raise ValueError(f"Unknown request type: {request_type}")
            
            # Publish employer event
            await self.event_bus.publish_simple(
                event_type=event_type,
                payload={
                    "employer_id": employer_id,
                    "request_type": request_type,
                    "data": data,
                    "timestamp": datetime.utcnow().isoformat()
                },
                priority=3  # Medium priority
            )
            
            self._metrics["employer_events_processed"] += 1
            self._metrics["total_events_processed"] += 1
            
            return {
                "success": True,
                "message": f"Employer {request_type} processing initiated"
            }
            
        except Exception as e:
            logger.error(f"Failed to process employer request: {e}")
            self._metrics["errors"] += 1
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_candidate_analysis(
        self,
        candidate_id: str,
        vacancy_id: str,
        response_id: str
    ) -> Dict[str, Any]:
        """Get analysis results for a candidate"""
        try:
            # Get candidate agent
            candidate_agents = self.registry.get_agents_by_type(AgentType.CANDIDATE)
            if not candidate_agents:
                return {"error": "No candidate agents available"}
            
            # Get the first candidate agent's analysis
            agent = candidate_agents[0]
            analysis_result = agent.state.get_analysis_result(f"analysis_{response_id}")
            
            if not analysis_result:
                return {"error": "Analysis not found"}
            
            return {
                "success": True,
                "analysis": analysis_result
            }
            
        except Exception as e:
            logger.error(f"Failed to get candidate analysis: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_employer_insights(
        self,
        employer_id: str,
        vacancy_id: str
    ) -> Dict[str, Any]:
        """Get insights for employer"""
        try:
            # Get employer agent
            employer_agents = self.registry.get_agents_by_type(AgentType.EMPLOYER)
            if not employer_agents:
                return {"error": "No employer agents available"}
            
            # Get the first employer agent's insights
            agent = employer_agents[0]
            insights = agent.state.get_analysis_result(f"insights_{vacancy_id}")
            
            if not insights:
                return {"error": "Insights not found"}
            
            return {
                "success": True,
                "insights": insights
            }
            
        except Exception as e:
            logger.error(f"Failed to get employer insights: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        registry_metrics = self.registry.get_registry_metrics()
        event_bus_metrics = self.event_bus.get_metrics()
        
        return {
            "orchestrator": {
                "is_running": self._is_running,
                "uptime": self._get_uptime(),
                **self._metrics
            },
            "registry": registry_metrics,
            "event_bus": event_bus_metrics
        }
    
    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get metrics for specific agent"""
        return self.registry.get_agent_metrics(agent_id)
    
    def get_all_agent_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all agents"""
        return self.registry.get_all_agent_metrics()
    
    def _get_uptime(self) -> Optional[str]:
        """Get system uptime"""
        if not self._metrics["start_time"]:
            return None
        
        start_time = datetime.fromisoformat(self._metrics["start_time"])
        uptime = datetime.utcnow() - start_time
        return str(uptime)
    
    async def add_rag_documents(
        self,
        documents: List[Dict[str, Any]],
        document_type: str = "general"
    ) -> Dict[str, Any]:
        """Add documents to RAG knowledge base"""
        try:
            # Get any agent to access RAG service
            all_agents = self.registry.get_all_agents()
            if not all_agents:
                return {"error": "No agents available"}
            
            agent = all_agents[0]
            rag_service = agent.rag_service
            
            # Add documents based on type
            if document_type == "job":
                for doc in documents:
                    await rag_service.add_job_description(doc)
            elif document_type == "cv":
                for doc in documents:
                    await rag_service.add_cv_text(doc)
            elif document_type == "hr_knowledge":
                for doc in documents:
                    await rag_service.add_hr_knowledge(doc)
            else:
                return {"error": f"Unknown document type: {document_type}"}
            
            return {
                "success": True,
                "message": f"Added {len(documents)} {document_type} documents"
            }
            
        except Exception as e:
            logger.error(f"Failed to add RAG documents: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_knowledge_base(
        self,
        query: str,
        context_type: str = "all",
        limit: int = 5
    ) -> Dict[str, Any]:
        """Search the knowledge base"""
        try:
            # Get any agent to access RAG service
            all_agents = self.registry.get_all_agents()
            if not all_agents:
                return {"error": "No agents available"}
            
            agent = all_agents[0]
            rag_service = agent.rag_service
            
            # Search for relevant documents
            results = await rag_service.search_relevant_context(
                query=query,
                context_type=context_type,
                limit=limit
            )
            
            return {
                "success": True,
                "results": results,
                "query": query,
                "context_type": context_type
            }
            
        except Exception as e:
            logger.error(f"Failed to search knowledge base: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Global orchestrator instance
autonomous_agent_orchestrator = AutonomousAgentOrchestrator()
