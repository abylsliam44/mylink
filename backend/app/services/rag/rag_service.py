"""
RAG Service - Main orchestrator for Retrieval-Augmented Generation
Combines vector search with LLM generation for enhanced responses
"""
from typing import List, Dict, Any, Optional
import logging
from .vector_store import vector_store
from .document_processor import document_processor
from app.services.ai.llm_client import llm_client

logger = logging.getLogger(__name__)

class RAGService:
    def __init__(self):
        self.vector_store = vector_store
        self.document_processor = document_processor
        self.llm_client = llm_client
    
    async def initialize(self):
        """Initialize RAG service"""
        await self.vector_store.initialize_collection()
        logger.info("RAG service initialized")
    
    async def add_job_description(self, job_data: Dict[str, Any]):
        """Add job description to knowledge base"""
        try:
            chunks = self.document_processor.process_job_description(job_data)
            await self.vector_store.add_documents(chunks)
            logger.info(f"Added job description: {job_data.get('title', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error adding job description: {e}")
            raise
    
    async def add_cv_text(self, cv_data: Dict[str, Any]):
        """Add CV text to knowledge base"""
        try:
            chunks = self.document_processor.process_cv_text(cv_data)
            await self.vector_store.add_documents(chunks)
            logger.info(f"Added CV: {cv_data.get('full_name', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error adding CV: {e}")
            raise
    
    async def add_hr_knowledge(self, knowledge_data: Dict[str, Any]):
        """Add HR knowledge to knowledge base"""
        try:
            chunks = self.document_processor.process_hr_knowledge(knowledge_data)
            await self.vector_store.add_documents(chunks)
            logger.info(f"Added HR knowledge: {knowledge_data.get('category', 'Unknown')}")
        except Exception as e:
            logger.error(f"Error adding HR knowledge: {e}")
            raise
    
    async def search_relevant_context(self, query: str, context_type: str = "all", limit: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant context based on query"""
        try:
            # Search in vector store
            results = await self.vector_store.search_similar(query, limit=limit)
            
            # Filter by context type if specified
            if context_type != "all":
                results = [r for r in results if r.get("type") == context_type]
            
            return results
        except Exception as e:
            logger.error(f"Error searching relevant context: {e}")
            return []
    
    async def generate_rag_response(self, query: str, context_type: str = "all", max_context: int = 3) -> str:
        """Generate response using RAG"""
        try:
            # Get relevant context
            context_docs = await self.search_relevant_context(query, context_type, max_context)
            
            # Build context string
            context_parts = []
            for doc in context_docs:
                context_parts.append(f"[{doc.get('source', 'Unknown')}]: {doc['text']}")
            
            context = "\n\n".join(context_parts)
            
            # Build prompt with context
            prompt = f"""
Контекст из базы знаний:
{context}

Запрос пользователя: {query}

Ответь на основе предоставленного контекста. Если в контексте нет нужной информации, скажи об этом честно.
"""
            
            # Generate response using LLM
            response = await self.llm_client.generate_response(prompt)
            return response
            
        except Exception as e:
            logger.error(f"Error generating RAG response: {e}")
            return "Извините, произошла ошибка при обработке запроса."
    
    async def enhance_mismatch_analysis(self, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance mismatch analysis using RAG"""
        try:
            # Search for similar job descriptions
            job_query = f"{job_data.get('title', '')} {job_data.get('description', '')}"
            similar_jobs = await self.search_relevant_context(job_query, "job", limit=3)
            
            # Search for similar CVs
            cv_query = f"{cv_data.get('resume_text', '')}"
            similar_cvs = await self.search_relevant_context(cv_query, "candidate", limit=3)
            
            # Build enhanced context
            context_parts = []
            
            if similar_jobs:
                context_parts.append("Похожие вакансии:")
                for job in similar_jobs:
                    context_parts.append(f"- {job['text']}")
            
            if similar_cvs:
                context_parts.append("Похожие резюме:")
                for cv in similar_cvs:
                    context_parts.append(f"- {cv['text']}")
            
            enhanced_context = "\n".join(context_parts)
            
            return {
                "enhanced_context": enhanced_context,
                "similar_jobs_count": len(similar_jobs),
                "similar_cvs_count": len(similar_cvs)
            }
            
        except Exception as e:
            logger.error(f"Error enhancing mismatch analysis: {e}")
            return {"enhanced_context": "", "similar_jobs_count": 0, "similar_cvs_count": 0}
    
    async def generate_enhanced_questions(self, job_data: Dict[str, Any], cv_data: Dict[str, Any]) -> List[str]:
        """Generate enhanced interview questions using RAG"""
        try:
            # Search for relevant HR knowledge
            hr_query = f"интервью вопросы {job_data.get('title', '')} {job_data.get('requirements', '')}"
            hr_knowledge = await self.search_relevant_context(hr_query, "knowledge", limit=5)
            
            # Build context
            context_parts = []
            for knowledge in hr_knowledge:
                context_parts.append(knowledge['text'])
            
            context = "\n".join(context_parts)
            
            # Generate questions
            prompt = f"""
Контекст HR знаний:
{context}

Вакансия: {job_data.get('title', '')}
Требования: {job_data.get('requirements', '')}
Резюме кандидата: {cv_data.get('resume_text', '')[:500]}...

Сгенерируй 3-5 уточняющих вопросов для интервью с кандидатом на основе контекста и анализа резюме.
Вопросы должны быть профессиональными и помогать оценить соответствие кандидата вакансии.
"""
            
            response = await self.llm_client.generate_response(prompt)
            
            # Parse questions from response
            questions = []
            lines = response.split('\n')
            for line in lines:
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.')):
                    # Clean up question
                    question = re.sub(r'^[-•\d\.\s]+', '', line).strip()
                    if question and question.endswith('?'):
                        questions.append(question)
            
            return questions[:5]  # Return max 5 questions
            
        except Exception as e:
            logger.error(f"Error generating enhanced questions: {e}")
            return []

# Global instance
rag_service = RAGService()
