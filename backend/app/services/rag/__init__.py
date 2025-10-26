"""
RAG Service Package
Handles RAG dependencies with graceful fallback
"""
import logging

logger = logging.getLogger(__name__)

# Try to import RAG dependencies
try:
    from .rag_service import RAGService
    RAG_AVAILABLE = True
    logger.info("RAG dependencies available")
except ImportError as e:
    logger.warning(f"RAG dependencies not available: {e}")
    RAG_AVAILABLE = False
    
    # Create dummy RAG service
    class RAGService:
        """Dummy RAG service when dependencies are not available"""
        
        async def initialize(self):
            logger.info("RAG service initialized (dummy mode - no vector store)")
            pass
        
        async def add_job_description(self, job_data):
            logger.debug("RAG disabled - skipping job description indexing")
            pass
        
        async def add_cv_text(self, cv_data):
            logger.debug("RAG disabled - skipping CV indexing")
            pass
        
        async def add_hr_knowledge(self, knowledge_data):
            logger.debug("RAG disabled - skipping HR knowledge indexing")
            pass
        
        async def search_relevant_context(self, query: str, context_type: str = "all", limit: int = 5):
            logger.debug("RAG disabled - returning empty context")
            return []
        
        async def generate_rag_response(self, query: str, context_type: str = "all", max_context: int = 3):
            logger.debug("RAG disabled - returning simple response")
            return "RAG service is not available in this deployment."

# Create singleton instance
rag_service = RAGService()

__all__ = ["RAGService", "rag_service", "RAG_AVAILABLE"]
