"""
Base Autonomous Agent with LangGraph
Provides foundation for all autonomous agents
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient
import json
import logging

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    """Base state for all agents"""
    messages: List[BaseMessage]
    context: Dict[str, Any]
    memory: Dict[str, Any]
    tools_used: List[str]
    iteration: int
    max_iterations: int
    status: str  # "running", "completed", "failed", "waiting"

class BaseAgent(ABC):
    """Base class for autonomous agents"""
    
    def __init__(self, name: str, llm_model: str = "gpt-4o-mini"):
        self.name = name
        self.llm = ChatOpenAI(model=llm_model, temperature=0.2)
        self.qdrant_client = QdrantClient(host="qdrant", port=6333)
        self.vector_store = None
        self.graph = None
        self._setup_vector_store()
        self._build_graph()
    
    def _setup_vector_store(self):
        """Setup Qdrant vector store"""
        try:
            from langchain_openai import OpenAIEmbeddings
            embeddings = OpenAIEmbeddings()
            self.vector_store = Qdrant(
                client=self.qdrant_client,
                collection_name="smartbot_hr",
                embeddings=embeddings
            )
            logger.info(f"Vector store initialized for {self.name}")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            self.vector_store = None
    
    @abstractmethod
    def _build_graph(self):
        """Build the LangGraph workflow for this agent"""
        pass
    
    @abstractmethod
    def _define_tools(self) -> List[Any]:
        """Define tools available to this agent"""
        return []
    
    def _search_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """Search knowledge base using RAG"""
        if not self.vector_store:
            return []
        
        try:
            # This would use the vector store to search
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"Knowledge search failed: {e}")
            return []
    
    def _call_llm(self, messages: List[BaseMessage], **kwargs) -> str:
        """Call LLM with messages"""
        try:
            response = self.llm.invoke(messages, **kwargs)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return "Error: Failed to get response from LLM"
    
    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from LLM"""
        try:
            # Try to extract JSON from response
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
            else:
                json_str = response.strip()
            
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"JSON parsing failed: {e}")
            return {"error": "Failed to parse JSON response"}
    
    def run(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run the agent with initial state"""
        try:
            # Convert initial state to AgentState
            state = AgentState(
                messages=initial_state.get("messages", []),
                context=initial_state.get("context", {}),
                memory=initial_state.get("memory", {}),
                tools_used=[],
                iteration=0,
                max_iterations=initial_state.get("max_iterations", 10),
                status="running"
            )
            
            # Run the graph
            result = self.graph.invoke(state)
            
            logger.info(f"Agent {self.name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Agent {self.name} failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "context": initial_state.get("context", {})
            }
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end"""
        if state["iteration"] >= state["max_iterations"]:
            return "end"
        if state["status"] == "completed":
            return "end"
        if state["status"] == "failed":
            return "end"
        return "continue"
    
    def _increment_iteration(self, state: AgentState) -> AgentState:
        """Increment iteration counter"""
        state["iteration"] += 1
        return state
