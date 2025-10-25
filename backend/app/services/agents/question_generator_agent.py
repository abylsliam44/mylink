"""
Autonomous Question Generator Agent
Uses LangGraph to autonomously generate contextual interview questions
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from .base_agent import BaseAgent, AgentState
import json
import logging

logger = logging.getLogger(__name__)

class QuestionGeneratorAgent(BaseAgent):
    """Autonomous agent for generating contextual interview questions"""
    
    def __init__(self):
        super().__init__("QuestionGenerator", "gpt-4o-mini")
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_context", self._analyze_context)
        workflow.add_node("search_question_templates", self._search_question_templates)
        workflow.add_node("generate_questions", self._generate_questions)
        workflow.add_node("validate_questions", self._validate_questions)
        workflow.add_node("prioritize_questions", self._prioritize_questions)
        workflow.add_node("finalize_questions", self._finalize_questions)
        
        # Add edges
        workflow.set_entry_point("analyze_context")
        workflow.add_edge("analyze_context", "search_question_templates")
        workflow.add_edge("search_question_templates", "generate_questions")
        workflow.add_edge("generate_questions", "validate_questions")
        workflow.add_edge("validate_questions", "prioritize_questions")
        workflow.add_edge("prioritize_questions", "finalize_questions")
        workflow.add_edge("finalize_questions", END)
        
        self.graph = workflow.compile()
    
    def _analyze_context(self, state: AgentState) -> AgentState:
        """Analyze the context to understand what questions are needed"""
        logger.info("QuestionGenerator: Analyzing context")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        mismatches = context.get("mismatches", [])
        missing_data = context.get("missing_data", [])
        
        analysis_prompt = f"""
        Analyze the context to determine what questions need to be asked:
        
        JOB STRUCTURE:
        {json.dumps(job_struct, indent=2, ensure_ascii=False)}
        
        CANDIDATE STRUCTURE:
        {json.dumps(cv_struct, indent=2, ensure_ascii=False)}
        
        MISMATCHES FOUND:
        {json.dumps(mismatches, indent=2, ensure_ascii=False)}
        
        MISSING DATA:
        {json.dumps(missing_data, indent=2, ensure_ascii=False)}
        
        Identify the most critical areas that need clarification:
        1. High-priority mismatches that need immediate clarification
        2. Missing critical information
        3. Ambiguous areas in the candidate's profile
        4. Skills/experience gaps that need validation
        
        Return as JSON with analysis of what questions are needed and why.
        """
        
        messages = [HumanMessage(content=analysis_prompt)]
        response = self._call_llm(messages)
        
        try:
            analysis = self._parse_json_response(response)
            state["context"]["question_analysis"] = analysis
            state["memory"]["context_analysis"] = analysis
        except Exception as e:
            logger.error(f"Context analysis failed: {e}")
            state["context"]["question_analysis"] = {"error": str(e)}
        
        return state
    
    def _search_question_templates(self, state: AgentState) -> AgentState:
        """Search for relevant question templates and best practices"""
        logger.info("QuestionGenerator: Searching question templates")
        
        context = state["context"]
        analysis = context.get("question_analysis", {})
        
        # Build search queries based on analysis
        queries = []
        if "critical_areas" in analysis:
            for area in analysis["critical_areas"]:
                queries.append(f"interview questions {area}")
        
        # Add general HR question queries
        queries.extend([
            "technical interview questions",
            "behavioral interview questions",
            "HR best practices questions"
        ])
        
        # Search knowledge base
        question_templates = []
        for query in queries:
            results = self._search_knowledge(query, limit=3)
            question_templates.extend(results)
        
        state["context"]["question_templates"] = question_templates
        state["memory"]["templates_found"] = len(question_templates)
        
        return state
    
    def _generate_questions(self, state: AgentState) -> AgentState:
        """Generate contextual questions based on analysis and templates"""
        logger.info("QuestionGenerator: Generating questions")
        
        context = state["context"]
        analysis = context.get("question_analysis", {})
        templates = context.get("question_templates", [])
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        
        generation_prompt = f"""
        Generate 3-5 high-quality interview questions based on the analysis and templates.
        
        CONTEXT ANALYSIS:
        {json.dumps(analysis, indent=2, ensure_ascii=False)}
        
        QUESTION TEMPLATES:
        {json.dumps(templates, indent=2, ensure_ascii=False)}
        
        JOB REQUIREMENTS:
        {json.dumps(job_struct, indent=2, ensure_ascii=False)}
        
        CANDIDATE PROFILE:
        {json.dumps(cv_struct, indent=2, ensure_ascii=False)}
        
        Generate questions that:
        1. Address the most critical mismatches
        2. Fill in missing information gaps
        3. Validate key skills and experience
        4. Are professional and respectful
        5. Have clear answer types and validation rules
        
        For each question, provide:
        - id: unique identifier
        - priority: 1-5 (1 = highest priority)
        - criterion: skills|experience|location|format|langs|compensation|education|domain
        - reason: why this question is important
        - question_text: the actual question (max 25 words)
        - answer_type: yes_no|level_select|years_number|free_text_short|option_select|salary_number|date_text
        - options: available options (if applicable)
        - validation: validation rules
        - examples: example answers
        - on_ambiguous_followup: follow-up for unclear answers
        
        Return as JSON following the exact schema from requirements.
        """
        
        messages = [HumanMessage(content=generation_prompt)]
        response = self._call_llm(messages)
        
        try:
            questions_data = self._parse_json_response(response)
            state["context"]["generated_questions"] = questions_data
            state["memory"]["questions_generated"] = len(questions_data.get("questions", []))
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            state["context"]["generated_questions"] = {"error": str(e)}
        
        return state
    
    def _validate_questions(self, state: AgentState) -> AgentState:
        """Validate generated questions for quality and completeness"""
        logger.info("QuestionGenerator: Validating questions")
        
        context = state["context"]
        questions_data = context.get("generated_questions", {})
        questions = questions_data.get("questions", [])
        
        validation_errors = []
        
        for i, question in enumerate(questions):
            # Check required fields
            required_fields = ["id", "priority", "criterion", "question_text", "answer_type"]
            for field in required_fields:
                if field not in question:
                    validation_errors.append(f"Question {i}: Missing {field}")
            
            # Check question length
            if "question_text" in question and len(question["question_text"]) > 25:
                validation_errors.append(f"Question {i}: Text too long")
            
            # Check answer type validity
            valid_types = ["yes_no", "level_select", "years_number", "free_text_short", 
                          "option_select", "salary_number", "date_text"]
            if question.get("answer_type") not in valid_types:
                validation_errors.append(f"Question {i}: Invalid answer_type")
        
        if validation_errors:
            logger.warning(f"Question validation errors: {validation_errors}")
            state["context"]["validation_errors"] = validation_errors
        else:
            state["context"]["validation_passed"] = True
        
        return state
    
    def _prioritize_questions(self, state: AgentState) -> AgentState:
        """Prioritize questions based on importance and impact"""
        logger.info("QuestionGenerator: Prioritizing questions")
        
        context = state["context"]
        questions = context.get("generated_questions", {}).get("questions", [])
        
        # Sort by priority (1 = highest)
        sorted_questions = sorted(questions, key=lambda x: x.get("priority", 5))
        
        # Limit to max 3 questions as per requirements
        prioritized_questions = sorted_questions[:3]
        
        state["context"]["prioritized_questions"] = prioritized_questions
        state["memory"]["questions_prioritized"] = len(prioritized_questions)
        
        return state
    
    def _finalize_questions(self, state: AgentState) -> AgentState:
        """Finalize questions and prepare output"""
        logger.info("QuestionGenerator: Finalizing questions")
        
        context = state["context"]
        questions = context.get("prioritized_questions", [])
        
        # Prepare final output
        final_output = {
            "questions": questions,
            "closing_message": "Спасибо за ответы! Мы рассмотрим вашу кандидатуру и свяжемся с вами в ближайшее время.",
            "meta": {
                "max_questions": 3,
                "tone": "профессиональный, вежливый",
                "language": "ru",
                "agent_name": self.name,
                "iteration": state["iteration"],
                "validation_passed": context.get("validation_passed", False)
            }
        }
        
        state["context"]["final_output"] = final_output
        state["status"] = "completed"
        
        logger.info(f"QuestionGenerator completed with {len(questions)} questions generated")
        
        return state
    
    def _define_tools(self) -> List[Any]:
        """Define tools available to this agent"""
        return [
            # Question template search tool
            # Question validation tool
            # Priority scoring tool
        ]

# Global instance
question_generator_agent = QuestionGeneratorAgent()
