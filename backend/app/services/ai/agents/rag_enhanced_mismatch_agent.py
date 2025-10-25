"""
RAG-Enhanced Mismatch Detection Agent
Uses vector search to improve mismatch analysis accuracy
"""
import json
import logging
from typing import Dict, Any, List
from app.services.ai.agents.mismatch_agent import MismatchAgent
from app.services.rag.rag_service import rag_service

logger = logging.getLogger(__name__)

class RAGEnhancedMismatchAgent(MismatchAgent):
    """
    Enhanced Mismatch Agent with RAG capabilities
    Uses vector search to find similar job descriptions and CVs for better analysis
    """
    
    def __init__(self):
        super().__init__()
        self.rag_service = rag_service
    
    async def analyze_with_rag(self, job_text: str, cv_text: str, hints: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhanced mismatch analysis using RAG
        """
        try:
            # Get basic analysis from parent class
            basic_analysis = await self.analyze(job_text, cv_text, hints)
            
            # Enhance with RAG
            job_data = {
                "title": basic_analysis.get("job_struct", {}).get("title", ""),
                "description": job_text,
                "requirements": basic_analysis.get("job_struct", {}).get("required_skills", []),
                "location": basic_analysis.get("job_struct", {}).get("location_requirement", {}).get("city", ""),
                "salary_min": basic_analysis.get("job_struct", {}).get("salary_range", {}).get("min", 0),
                "salary_max": basic_analysis.get("job_struct", {}).get("salary_range", {}).get("max", 0)
            }
            
            cv_data = {
                "full_name": basic_analysis.get("cv_struct", {}).get("name", ""),
                "resume_text": cv_text,
                "city": basic_analysis.get("cv_struct", {}).get("location", {}).get("city", "")
            }
            
            # Get RAG enhancement
            rag_enhancement = await self.rag_service.enhance_mismatch_analysis(job_data, cv_data)
            
            # Add RAG insights to analysis
            enhanced_analysis = basic_analysis.copy()
            enhanced_analysis["rag_insights"] = {
                "similar_jobs_found": rag_enhancement.get("similar_jobs_count", 0),
                "similar_cvs_found": rag_enhancement.get("similar_cvs_count", 0),
                "enhanced_context": rag_enhancement.get("enhanced_context", ""),
                "rag_confidence": self._calculate_rag_confidence(rag_enhancement)
            }
            
            # Enhance mismatches with RAG insights
            enhanced_analysis["mismatches"] = self._enhance_mismatches_with_rag(
                basic_analysis.get("mismatches", []),
                rag_enhancement
            )
            
            return enhanced_analysis
            
        except Exception as e:
            logger.error(f"Error in RAG-enhanced analysis: {e}")
            # Fallback to basic analysis
            return await self.analyze(job_text, cv_text, hints)
    
    def _calculate_rag_confidence(self, rag_enhancement: Dict[str, Any]) -> float:
        """Calculate confidence score based on RAG results"""
        similar_jobs = rag_enhancement.get("similar_jobs_count", 0)
        similar_cvs = rag_enhancement.get("similar_cvs_count", 0)
        
        # Higher confidence with more similar documents
        confidence = min(1.0, (similar_jobs + similar_cvs) / 10.0)
        return round(confidence, 2)
    
    def _enhance_mismatches_with_rag(self, mismatches: List[Dict[str, Any]], rag_enhancement: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance mismatch details with RAG insights"""
        enhanced_context = rag_enhancement.get("enhanced_context", "")
        
        for mismatch in mismatches:
            # Add RAG context to mismatch details
            if enhanced_context:
                mismatch["rag_context"] = enhanced_context[:200] + "..." if len(enhanced_context) > 200 else enhanced_context
            
            # Adjust severity based on RAG insights
            if rag_enhancement.get("similar_jobs_count", 0) > 0:
                # If we found similar jobs, this might be a common requirement
                if mismatch.get("severity") == "high":
                    mismatch["severity"] = "medium"
                    mismatch["rag_note"] = "Similar jobs found - this might be a common requirement"
        
        return mismatches
    
    async def add_job_to_knowledge_base(self, job_data: Dict[str, Any]):
        """Add job description to knowledge base for future RAG queries"""
        try:
            await self.rag_service.add_job_description(job_data)
            logger.info(f"Added job to knowledge base: {job_data.get('title', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error adding job to knowledge base: {e}")
    
    async def add_cv_to_knowledge_base(self, cv_data: Dict[str, Any]):
        """Add CV to knowledge base for future RAG queries"""
        try:
            await self.rag_service.add_cv_text(cv_data)
            logger.info(f"Added CV to knowledge base: {cv_data.get('full_name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error adding CV to knowledge base: {e}")

# Global instance
rag_enhanced_mismatch_agent = RAGEnhancedMismatchAgent()
