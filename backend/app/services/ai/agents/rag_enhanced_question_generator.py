"""
RAG-Enhanced Question Generator Agent
Uses vector search to generate more relevant and contextual interview questions
"""
import json
import logging
from typing import Dict, Any, List
from app.services.ai.agents.question_generator_agent import QuestionGeneratorAgent
from app.services.rag import rag_service

logger = logging.getLogger(__name__)

class RAGEnhancedQuestionGeneratorAgent(QuestionGeneratorAgent):
    """
    Enhanced Question Generator with RAG capabilities
    Uses vector search to find relevant HR knowledge and similar cases
    """
    
    def __init__(self):
        super().__init__()
        self.rag_service = rag_service
    
    async def generate_questions_with_rag(
        self, 
        job_struct: Dict[str, Any], 
        cv_struct: Dict[str, Any], 
        mismatches: List[Dict[str, Any]], 
        missing_data: List[str],
        limits: Dict[str, int] = None
    ) -> Dict[str, Any]:
        """
        Generate enhanced questions using RAG
        """
        try:
            # Get basic questions from parent class
            basic_questions = await self.generate_questions(job_struct, cv_struct, mismatches, missing_data, limits)
            
            # Enhance with RAG-generated questions
            rag_questions = await self._generate_rag_questions(job_struct, cv_struct, mismatches)
            
            # Combine and prioritize questions
            enhanced_questions = self._combine_questions(basic_questions, rag_questions)
            
            return enhanced_questions
            
        except Exception as e:
            logger.error(f"Error in RAG-enhanced question generation: {e}")
            # Fallback to basic questions
            return await self.generate_questions(job_struct, cv_struct, mismatches, missing_data, limits)
    
    async def _generate_rag_questions(
        self, 
        job_struct: Dict[str, Any], 
        cv_struct: Dict[str, Any], 
        mismatches: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate questions using RAG knowledge base"""
        try:
            # Build context for RAG query
            job_title = job_struct.get("title", "")
            job_requirements = job_struct.get("required_skills", [])
            cv_skills = cv_struct.get("skills", [])
            cv_experience = cv_struct.get("total_experience_years", 0)
            
            # Create RAG query
            rag_query = f"""
            Генерация вопросов для интервью:
            Должность: {job_title}
            Требования: {', '.join(job_requirements)}
            Навыки кандидата: {', '.join(cv_skills)}
            Опыт кандидата: {cv_experience} лет
            """
            
            # Search for relevant HR knowledge
            hr_knowledge = await self.rag_service.search_relevant_context(
                rag_query, 
                context_type="knowledge", 
                limit=5
            )
            
            # Generate questions using RAG context
            if hr_knowledge:
                context_text = "\n".join([doc["text"] for doc in hr_knowledge])
                
                # Use LLM to generate questions based on RAG context
                prompt = f"""
                На основе HR знаний и контекста сгенерируй 3-5 профессиональных вопросов для интервью:
                
                Контекст HR знаний:
                {context_text}
                
                Должность: {job_title}
                Требования: {', '.join(job_requirements)}
                Навыки кандидата: {', '.join(cv_skills)}
                Опыт: {cv_experience} лет
                
                Несоответствия:
                {json.dumps(mismatches, ensure_ascii=False, indent=2)}
                
                Сгенерируй вопросы в формате JSON:
                {{
                    "questions": [
                        {{
                            "id": "q1",
                            "priority": 1,
                            "criterion": "skills|experience|location|format|langs|compensation|education|domain",
                            "reason": "string",
                            "question_text": "string",
                            "answer_type": "yes_no|level_select|years_number|free_text_short|option_select|salary_number|date_text",
                            "options": ["string"],
                            "validation": {{"pattern": "regex", "allowed_levels": ["A1","A2","B1","B2","C1","C2"], "min": 0, "max": 50}},
                            "examples": ["string"],
                            "on_ambiguous_followup": "string"
                        }}
                    ]
                }}
                """
                
                response = await self.rag_service.llm_client.generate_response(prompt)
                
                try:
                    # Parse JSON response
                    rag_data = json.loads(response)
                    return rag_data.get("questions", [])
                except json.JSONDecodeError:
                    # If JSON parsing fails, extract questions manually
                    return self._extract_questions_from_text(response)
            
            return []
            
        except Exception as e:
            logger.error(f"Error generating RAG questions: {e}")
            return []
    
    def _extract_questions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Extract questions from text response"""
        questions = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line and (line.startswith('-') or line.startswith('•') or line.startswith(f'{i+1}.')):
                # Clean up question
                question_text = line
                for prefix in ['-', '•', f'{i+1}.']:
                    if question_text.startswith(prefix):
                        question_text = question_text[len(prefix):].strip()
                
                if question_text and question_text.endswith('?'):
                    questions.append({
                        "id": f"rag_q{i+1}",
                        "priority": i + 1,
                        "criterion": "skills",
                        "reason": "RAG-generated question",
                        "question_text": question_text,
                        "answer_type": "free_text_short",
                        "options": [],
                        "validation": {"pattern": ".*", "min": 0, "max": 200},
                        "examples": [],
                        "on_ambiguous_followup": "Уточните, пожалуйста"
                    })
        
        return questions[:5]  # Return max 5 questions
    
    def _combine_questions(self, basic_questions: Dict[str, Any], rag_questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine basic and RAG questions, prioritizing by relevance"""
        try:
            basic_q_list = basic_questions.get("questions", [])
            
            # Add RAG questions with adjusted priorities
            for i, rag_q in enumerate(rag_questions):
                rag_q["priority"] = len(basic_q_list) + i + 1
                basic_q_list.append(rag_q)
            
            # Sort by priority
            basic_q_list.sort(key=lambda x: x.get("priority", 999))
            
            # Limit to max questions
            max_questions = basic_questions.get("meta", {}).get("max_questions", 3)
            basic_q_list = basic_q_list[:max_questions]
            
            # Update response
            enhanced_questions = basic_questions.copy()
            enhanced_questions["questions"] = basic_q_list
            enhanced_questions["meta"]["rag_enhanced"] = True
            enhanced_questions["meta"]["rag_questions_count"] = len(rag_questions)
            
            return enhanced_questions
            
        except Exception as e:
            logger.error(f"Error combining questions: {e}")
            return basic_questions

# Global instance
rag_enhanced_question_generator = RAGEnhancedQuestionGeneratorAgent()
