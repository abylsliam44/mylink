"""
Base Autonomous Agent
Foundation for all autonomous agents using LangGraph
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import uuid

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI

from .agent_state import AgentState, AgentStatus, AgentType, EventType, AgentContext
from .event_bus import Event
from app.services.rag import RAGService
from ..ai.llm_client import get_llm

logger = logging.getLogger(__name__)


class BaseAutonomousAgent(ABC):
    """Base class for autonomous agents"""
    
    def __init__(
        self,
        agent_type: AgentType,
        agent_name: str,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2
    ):
        from .event_bus import event_bus
        self.event_bus = event_bus
        self.agent_type = agent_type
        self.agent_name = agent_name
        self.model_name = model_name
        self.temperature = temperature
        self.agent_id = str(uuid.uuid4())
        self.state = AgentState(
            agent_id=self.agent_id,
            context=AgentContext(
                session_id=str(uuid.uuid4()),
                agent_type=agent_type
            )
        )
        self.rag_service = RAGService()
        self.llm = get_llm(model=model_name, temperature=temperature)
        self._graph: Optional[StateGraph] = None
        self._is_running = False
        self._health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """Initialize agent"""
        try:
            # Initialize RAG service
            await self.rag_service.initialize()
            
            # Build LangGraph workflow
            self._build_graph()
            
            # Subscribe to events
            await self._subscribe_to_events()
            
            # Start health check
            self._start_health_check()
            
            self.state.status = AgentStatus.IDLE
            logger.info(f"Agent {self.agent_name} ({self.agent_id}) initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize agent {self.agent_name}: {e}")
            self.state.set_error(str(e))
            raise
    
    async def shutdown(self):
        """Shutdown agent"""
        self._is_running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # Unsubscribe from events
        await self._unsubscribe_from_events()
        
        self.state.status = AgentStatus.IDLE
        logger.info(f"Agent {self.agent_name} ({self.agent_id}) shutdown")
    
    @abstractmethod
    def _build_graph(self):
        """Build LangGraph workflow - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _subscribe_to_events(self):
        """Subscribe to relevant events - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _unsubscribe_from_events(self):
        """Unsubscribe from events - must be implemented by subclasses"""
        pass
    
    @abstractmethod
    async def _handle_event(self, event: Event) -> Any:
        """Handle incoming event - must be implemented by subclasses"""
        pass
    
    async def process_event(self, event: Event) -> Dict[str, Any]:
        """Process event through agent workflow"""
        try:
            self.state.status = AgentStatus.PROCESSING
            self.state.current_task = f"Processing {event.event_type.value}"
            self.state.update_activity()
            
            # Update context from event
            self._update_context_from_event(event)
            
            # Handle event with subclass implementation
            result = await self._handle_event(event)
            
            # Update state
            self.state.status = AgentStatus.IDLE
            self.state.current_task = None
            self.state.reset_error()
            
            # Log metrics
            self.state.increment_metric("events_processed")
            
            return {
                "success": True,
                "agent_id": self.agent_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error processing event in {self.agent_name}: {e}")
            self.state.set_error(str(e))
            self.state.increment_metric("errors")
            
            return {
                "success": False,
                "agent_id": self.agent_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _update_context_from_event(self, event: Event):
        """Update agent context from event payload"""
        payload = event.payload
        
        # Update basic context
        if "session_id" in payload:
            self.state.context.session_id = payload["session_id"]
        if "user_id" in payload:
            self.state.context.user_id = payload["user_id"]
        if "vacancy_id" in payload:
            self.state.context.vacancy_id = payload["vacancy_id"]
        if "candidate_id" in payload:
            self.state.context.candidate_id = payload["candidate_id"]
        if "response_id" in payload:
            self.state.context.response_id = payload["response_id"]
        if "language" in payload:
            self.state.context.language = payload["language"]
        
        # Update metadata
        if "metadata" in payload:
            self.state.context.metadata.update(payload["metadata"])
        
        self.state.update_activity()
    
    async def retrieve_context(self, query: str, context_type: str = "all") -> List[Dict[str, Any]]:
        """Retrieve relevant context using RAG"""
        try:
            # Update RAG context
            self.state.rag_context.query = query
            self.state.rag_context.context_type = context_type
            
            # Search for relevant documents
            documents = await self.rag_service.search_relevant_context(
                query=query,
                context_type=context_type,
                limit=self.state.rag_context.max_documents
            )
            
            # Update state
            self.state.rag_context.retrieved_documents = documents
            self.state.increment_metric("rag_queries")
            
            return documents
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            self.state.increment_metric("rag_errors")
            return []
    
    async def generate_response(
        self, 
        prompt: str, 
        context: Optional[List[Dict[str, Any]]] = None,
        use_rag: bool = True
    ) -> str:
        """Generate response using LLM with optional RAG context"""
        try:
            if use_rag and context:
                # Use RAG service for enhanced generation
                response = await self.rag_service.generate_rag_response(
                    query=prompt,
                    context_type=self.state.rag_context.context_type,
                    max_context=len(context)
                )
            else:
                # Direct LLM generation
                messages = [
                    SystemMessage(content=self._get_system_prompt()),
                    HumanMessage(content=prompt)
                ]
                
                if context:
                    context_text = "\n\n".join([doc.get("text", "") for doc in context])
                    messages.insert(-1, HumanMessage(content=f"Context:\n{context_text}"))
                
                response = self.llm.invoke(messages).content
            
            # Add to conversation history
            self.state.add_to_conversation("assistant", response)
            self.state.increment_metric("responses_generated")
            
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            self.state.increment_metric("generation_errors")
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for agent - to be overridden by subclasses"""
        return f"""You are {self.agent_name}, an autonomous AI agent specialized in {self.agent_type.value} interactions.

Your role:
- Analyze and respond to {self.agent_type.value} requests
- Use RAG context when available to provide accurate responses
- Maintain conversation history and context
- Be professional, helpful, and accurate

Current session: {self.state.context.session_id}
Language: {self.state.context.language}"""
    
    def _start_health_check(self):
        """Start health check task"""
        self._is_running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
    
    async def _health_check_loop(self):
        """Health check loop"""
        while self._is_running:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._perform_health_check()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check failed for {self.agent_name}: {e}")
    
    async def _perform_health_check(self):
        """Perform health check"""
        try:
            # Check if agent is responsive
            if self.state.status == AgentStatus.ERROR and not self.state.can_retry():
                logger.warning(f"Agent {self.agent_name} is in error state and cannot retry")
                return
            
            # Publish health check event
            await self.event_bus.publish_simple(
                event_type=EventType.AGENT_HEALTH_CHECK,
                payload={
                    "agent_id": self.agent_id,
                    "agent_name": self.agent_name,
                    "status": self.state.status.value,
                    "metrics": self.state.memory.session_metrics
                },
                source_agent_id=self.agent_id
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def get_state(self) -> Dict[str, Any]:
        """Get current agent state"""
        return self.state.to_dict()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent metrics"""
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type.value,
            "status": self.state.status.value,
            "session_metrics": self.state.memory.session_metrics,
            "conversation_length": len(self.state.memory.conversation_history),
            "last_activity": self.state.memory.last_activity.isoformat(),
            "error_count": self.state.retry_count
        }
    
    def is_healthy(self) -> bool:
        """Check if agent is healthy"""
        return (
            self.state.status != AgentStatus.ERROR or 
            self.state.can_retry()
        )
