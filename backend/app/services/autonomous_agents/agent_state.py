"""
Agent State Management for Autonomous Agents
Defines state structures and context management
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid


class AgentType(Enum):
    CANDIDATE = "candidate"
    EMPLOYER = "employer"


class AgentStatus(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    WAITING_FOR_INPUT = "waiting_for_input"
    ERROR = "error"
    COMPLETED = "completed"


class EventType(Enum):
    # Candidate events
    CANDIDATE_APPLIED = "candidate_applied"
    CANDIDATE_RESPONDED = "candidate_responded"
    CANDIDATE_ANALYSIS_NEEDED = "candidate_analysis_needed"
    CANDIDATE_FEEDBACK_READY = "candidate_feedback_ready"
    
    # Employer events
    EMPLOYER_VIEWED_CANDIDATE = "employer_viewed_candidate"
    EMPLOYER_REQUESTED_ANALYSIS = "employer_requested_analysis"
    EMPLOYER_ANALYSIS_READY = "employer_analysis_ready"
    EMPLOYER_CHAT_REQUESTED = "employer_chat_requested"
    
    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    AGENT_HEALTH_CHECK = "agent_health_check"


@dataclass
class AgentContext:
    """Context for agent operations"""
    session_id: str
    agent_type: AgentType
    user_id: Optional[str] = None
    vacancy_id: Optional[str] = None
    candidate_id: Optional[str] = None
    response_id: Optional[str] = None
    language: str = "ru"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RAGContext:
    """RAG-specific context"""
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    query: str = ""
    context_type: str = "all"  # all, job, cv, hr_knowledge
    similarity_threshold: float = 0.7
    max_documents: int = 5
    search_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentMemory:
    """Agent memory and conversation history"""
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    analysis_results: Dict[str, Any] = field(default_factory=dict)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    session_metrics: Dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AgentState:
    """Main agent state"""
    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: AgentStatus = AgentStatus.IDLE
    context: AgentContext = field(default_factory=lambda: AgentContext(
        session_id=str(uuid.uuid4()),
        agent_type=AgentType.CANDIDATE
    ))
    rag_context: RAGContext = field(default_factory=RAGContext)
    memory: AgentMemory = field(default_factory=AgentMemory)
    current_task: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "context": {
                "session_id": self.context.session_id,
                "agent_type": self.context.agent_type.value,
                "user_id": self.context.user_id,
                "vacancy_id": self.context.vacancy_id,
                "candidate_id": self.context.candidate_id,
                "response_id": self.context.response_id,
                "language": self.context.language,
                "metadata": self.context.metadata,
                "created_at": self.context.created_at.isoformat(),
                "updated_at": self.context.updated_at.isoformat()
            },
            "rag_context": {
                "retrieved_documents": self.rag_context.retrieved_documents,
                "query": self.rag_context.query,
                "context_type": self.rag_context.context_type,
                "similarity_threshold": self.rag_context.similarity_threshold,
                "max_documents": self.rag_context.max_documents,
                "search_filters": self.rag_context.search_filters
            },
            "memory": {
                "conversation_history": self.memory.conversation_history,
                "analysis_results": self.memory.analysis_results,
                "user_preferences": self.memory.user_preferences,
                "session_metrics": self.memory.session_metrics,
                "last_activity": self.memory.last_activity.isoformat()
            },
            "current_task": self.current_task,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create state from dictionary"""
        state = cls()
        state.agent_id = data.get("agent_id", str(uuid.uuid4()))
        state.status = AgentStatus(data.get("status", "idle"))
        state.current_task = data.get("current_task")
        state.error_message = data.get("error_message")
        state.retry_count = data.get("retry_count", 0)
        state.max_retries = data.get("max_retries", 3)
        
        # Context
        context_data = data.get("context", {})
        state.context = AgentContext(
            session_id=context_data.get("session_id", str(uuid.uuid4())),
            agent_type=AgentType(context_data.get("agent_type", "candidate")),
            user_id=context_data.get("user_id"),
            vacancy_id=context_data.get("vacancy_id"),
            candidate_id=context_data.get("candidate_id"),
            response_id=context_data.get("response_id"),
            language=context_data.get("language", "ru"),
            metadata=context_data.get("metadata", {}),
            created_at=datetime.fromisoformat(context_data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(context_data.get("updated_at", datetime.utcnow().isoformat()))
        )
        
        # RAG Context
        rag_data = data.get("rag_context", {})
        state.rag_context = RAGContext(
            retrieved_documents=rag_data.get("retrieved_documents", []),
            query=rag_data.get("query", ""),
            context_type=rag_data.get("context_type", "all"),
            similarity_threshold=rag_data.get("similarity_threshold", 0.7),
            max_documents=rag_data.get("max_documents", 5),
            search_filters=rag_data.get("search_filters", {})
        )
        
        # Memory
        memory_data = data.get("memory", {})
        state.memory = AgentMemory(
            conversation_history=memory_data.get("conversation_history", []),
            analysis_results=memory_data.get("analysis_results", {}),
            user_preferences=memory_data.get("user_preferences", {}),
            session_metrics=memory_data.get("session_metrics", {}),
            last_activity=datetime.fromisoformat(memory_data.get("last_activity", datetime.utcnow().isoformat()))
        )
        
        # Timestamps
        state.created_at = datetime.fromisoformat(data.get("created_at", datetime.utcnow().isoformat()))
        state.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.utcnow().isoformat()))
        
        return state
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.memory.last_activity = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def add_to_conversation(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """Add message to conversation history"""
        self.memory.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        })
        self.update_activity()
    
    def set_analysis_result(self, key: str, result: Any):
        """Store analysis result"""
        self.memory.analysis_results[key] = result
        self.update_activity()
    
    def get_analysis_result(self, key: str, default: Any = None) -> Any:
        """Get analysis result"""
        return self.memory.analysis_results.get(key, default)
    
    def increment_metric(self, metric_name: str, value: float = 1.0):
        """Increment session metric"""
        current = self.memory.session_metrics.get(metric_name, 0)
        self.memory.session_metrics[metric_name] = current + value
        self.update_activity()
    
    def set_error(self, error_message: str):
        """Set error state"""
        self.status = AgentStatus.ERROR
        self.error_message = error_message
        self.retry_count += 1
        self.update_activity()
    
    def reset_error(self):
        """Reset error state"""
        self.status = AgentStatus.IDLE
        self.error_message = None
        self.retry_count = 0
        self.update_activity()
    
    def can_retry(self) -> bool:
        """Check if agent can retry after error"""
        return self.retry_count < self.max_retries
