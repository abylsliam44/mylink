"""
Autonomous Widget Orchestrator Agent
Uses LangGraph to autonomously manage the interview widget conversation
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from .base_agent import BaseAgent, AgentState
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WidgetOrchestratorAgent(BaseAgent):
    """Autonomous agent for managing widget interview conversations"""
    
    def __init__(self):
        super().__init__("WidgetOrchestrator", "gpt-4o-mini")
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("initialize_session", self._initialize_session)
        workflow.add_node("process_question", self._process_question)
        workflow.add_node("validate_answer", self._validate_answer)
        workflow.add_node("handle_skip_stop", self._handle_skip_stop)
        workflow.add_node("generate_next_question", self._generate_next_question)
        workflow.add_node("finalize_session", self._finalize_session)
        
        # Add conditional edges
        workflow.set_entry_point("initialize_session")
        workflow.add_edge("initialize_session", "process_question")
        workflow.add_conditional_edges(
            "process_question",
            self._should_validate,
            {
                "validate": "validate_answer",
                "skip": "handle_skip_stop",
                "stop": "finalize_session",
                "continue": "generate_next_question"
            }
        )
        workflow.add_conditional_edges(
            "validate_answer",
            self._should_continue_after_validation,
            {
                "next_question": "generate_next_question",
                "reask": "process_question",
                "finalize": "finalize_session"
            }
        )
        workflow.add_edge("handle_skip_stop", "generate_next_question")
        workflow.add_conditional_edges(
            "generate_next_question",
            self._should_finalize,
            {
                "continue": "process_question",
                "finalize": "finalize_session"
            }
        )
        workflow.add_edge("finalize_session", END)
        
        self.graph = workflow.compile()
    
    def _initialize_session(self, state: AgentState) -> AgentState:
        """Initialize the interview session"""
        logger.info("WidgetOrchestrator: Initializing session")
        
        context = state["context"]
        questions = context.get("questions", [])
        
        # Initialize session data
        session_data = {
            "session_id": context.get("session_id", "unknown"),
            "started_at": datetime.now().isoformat(),
            "questions": questions,
            "current_question_index": 0,
            "answers": [],
            "transcript": [],
            "skipped_count": 0,
            "asked_count": 0,
            "answered_count": 0,
            "status": "active"
        }
        
        state["context"]["session_data"] = session_data
        state["memory"]["session_initialized"] = True
        
        # Add welcome message to transcript
        welcome_message = {
            "role": "assistant",
            "text": "Добро пожаловать! Давайте пройдем мини-собеседование. Я задам вам несколько вопросов для лучшего понимания вашей квалификации.",
            "timestamp": datetime.now().isoformat()
        }
        session_data["transcript"].append(welcome_message)
        
        return state
    
    def _process_question(self, state: AgentState) -> AgentState:
        """Process the current question"""
        logger.info("WidgetOrchestrator: Processing question")
        
        context = state["context"]
        session_data = context.get("session_data", {})
        questions = session_data.get("questions", [])
        current_index = session_data.get("current_question_index", 0)
        
        if current_index >= len(questions):
            state["status"] = "completed"
            return state
        
        current_question = questions[current_index]
        session_data["asked_count"] += 1
        
        # Add question to transcript
        question_message = {
            "role": "assistant",
            "text": current_question.get("question_text", ""),
            "timestamp": datetime.now().isoformat(),
            "question_id": current_question.get("id", ""),
            "question_meta": {
                "answer_type": current_question.get("answer_type", ""),
                "options": current_question.get("options", []),
                "validation": current_question.get("validation", {})
            }
        }
        session_data["transcript"].append(question_message)
        
        state["context"]["session_data"] = session_data
        state["context"]["current_question"] = current_question
        
        return state
    
    def _validate_answer(self, state: AgentState) -> AgentState:
        """Validate the user's answer"""
        logger.info("WidgetOrchestrator: Validating answer")
        
        context = state["context"]
        current_question = context.get("current_question", {})
        user_answer = context.get("user_answer", "")
        answer_type = current_question.get("answer_type", "free_text_short")
        
        validation_result = self._validate_answer_by_type(user_answer, answer_type, current_question)
        
        if validation_result["valid"]:
            # Answer is valid, process it
            self._process_valid_answer(state, current_question, user_answer, validation_result)
            state["context"]["validation_status"] = "valid"
        else:
            # Answer is invalid, prepare re-ask
            state["context"]["validation_status"] = "invalid"
            state["context"]["validation_error"] = validation_result["error"]
        
        return state
    
    def _validate_answer_by_type(self, answer: str, answer_type: str, question: Dict[str, Any]) -> Dict[str, Any]:
        """Validate answer based on its type"""
        answer = answer.strip().lower()
        
        if answer_type == "yes_no":
            if answer in ["да", "нет", "yes", "no", "ok", "ок"]:
                return {"valid": True, "normalized": answer in ["да", "yes", "ok", "ок"]}
            return {"valid": False, "error": "Пожалуйста, ответьте 'да' или 'нет'"}
        
        elif answer_type == "level_select":
            allowed_levels = question.get("validation", {}).get("allowed_levels", ["A1", "A2", "B1", "B2", "C1", "C2"])
            if answer.upper() in [level.upper() for level in allowed_levels]:
                return {"valid": True, "normalized": answer.upper()}
            return {"valid": False, "error": f"Пожалуйста, выберите уровень: {', '.join(allowed_levels)}"}
        
        elif answer_type == "years_number":
            try:
                years = int(answer)
                min_val = question.get("validation", {}).get("min", 0)
                max_val = question.get("validation", {}).get("max", 50)
                if min_val <= years <= max_val:
                    return {"valid": True, "normalized": years}
                return {"valid": False, "error": f"Пожалуйста, введите число от {min_val} до {max_val}"}
            except ValueError:
                return {"valid": False, "error": "Пожалуйста, введите число лет опыта"}
        
        elif answer_type == "salary_number":
            try:
                salary = int(answer)
                min_val = question.get("validation", {}).get("min", 0)
                max_val = question.get("validation", {}).get("max", 10000000)
                if min_val <= salary <= max_val:
                    return {"valid": True, "normalized": salary}
                return {"valid": False, "error": f"Пожалуйста, введите зарплату от {min_val} до {max_val}"}
            except ValueError:
                return {"valid": False, "error": "Пожалуйста, введите числовое значение зарплаты"}
        
        elif answer_type == "option_select":
            options = question.get("options", [])
            if answer in [opt.lower() for opt in options]:
                return {"valid": True, "normalized": answer}
            return {"valid": False, "error": f"Пожалуйста, выберите один из вариантов: {', '.join(options)}"}
        
        elif answer_type == "free_text_short":
            max_length = question.get("validation", {}).get("max", 200)
            if len(answer) <= max_length:
                return {"valid": True, "normalized": answer}
            return {"valid": False, "error": f"Пожалуйста, сократите ответ до {max_length} символов"}
        
        else:
            return {"valid": True, "normalized": answer}
    
    def _process_valid_answer(self, state: AgentState, question: Dict[str, Any], answer: str, validation: Dict[str, Any]) -> None:
        """Process a valid answer"""
        session_data = state["context"]["session_data"]
        
        # Add answer to answers list
        answer_data = {
            "id": question.get("id", ""),
            "criterion": question.get("criterion", ""),
            "question_text": question.get("question_text", ""),
            "raw_answer": answer,
            "normalized": {
                "value": validation["normalized"],
                "units": self._get_units_for_type(question.get("answer_type", "")),
                "valid": True,
                "unknown": False,
                "skipped": False
            },
            "validation_notes": "Validated successfully"
        }
        
        session_data["answers"].append(answer_data)
        session_data["answered_count"] += 1
        
        # Add answer to transcript
        answer_message = {
            "role": "user",
            "text": answer,
            "timestamp": datetime.now().isoformat()
        }
        session_data["transcript"].append(answer_message)
        
        # Move to next question
        session_data["current_question_index"] += 1
    
    def _get_units_for_type(self, answer_type: str) -> str:
        """Get units for answer type"""
        units_map = {
            "years_number": "years",
            "salary_number": "currency",
            "level_select": "cefr",
            "yes_no": "boolean",
            "date_text": "date",
            "free_text_short": "text",
            "option_select": "option"
        }
        return units_map.get(answer_type, "text")
    
    def _handle_skip_stop(self, state: AgentState) -> AgentState:
        """Handle skip or stop commands"""
        logger.info("WidgetOrchestrator: Handling skip/stop")
        
        context = state["context"]
        user_input = context.get("user_answer", "").strip().lower()
        session_data = context.get("session_data", {})
        
        if user_input in ["пропустить", "skip", "пропустить вопрос"]:
            session_data["skipped_count"] += 1
            session_data["current_question_index"] += 1
            
            # Add skip to transcript
            skip_message = {
                "role": "user",
                "text": "Пропустить",
                "timestamp": datetime.now().isoformat()
            }
            session_data["transcript"].append(skip_message)
            
        elif user_input in ["стоп", "stop", "завершить", "закончить"]:
            session_data["status"] = "stopped_by_user"
            state["status"] = "completed"
        
        state["context"]["session_data"] = session_data
        return state
    
    def _generate_next_question(self, state: AgentState) -> AgentState:
        """Generate or prepare next question"""
        logger.info("WidgetOrchestrator: Generating next question")
        
        context = state["context"]
        session_data = context.get("session_data", {})
        current_index = session_data.get("current_question_index", 0)
        questions = session_data.get("questions", [])
        
        if current_index >= len(questions):
            # No more questions
            state["status"] = "completed"
        else:
            # Prepare next question
            state["context"]["ready_for_next"] = True
        
        return state
    
    def _finalize_session(self, state: AgentState) -> AgentState:
        """Finalize the interview session"""
        logger.info("WidgetOrchestrator: Finalizing session")
        
        context = state["context"]
        session_data = context.get("session_data", {})
        
        # Update session status
        session_data["ended_at"] = datetime.now().isoformat()
        session_data["status"] = "completed"
        
        # Prepare final output
        final_output = {
            "answers": session_data.get("answers", []),
            "transcript": session_data.get("transcript", []),
            "session": {
                "completed": True,
                "stopped_by_user": session_data.get("status") == "stopped_by_user",
                "skipped_count": session_data.get("skipped_count", 0),
                "asked": session_data.get("asked_count", 0),
                "answered": session_data.get("answered_count", 0),
                "language": "ru"
            },
            "for_scorer_payload": {
                "dialogFindings": {
                    "relocation_ready": self._extract_relocation_ready(session_data),
                    "lang_proofs": self._extract_lang_proofs(session_data),
                    "salary_flex": self._extract_salary_flex(session_data),
                    "other_clarifications": self._extract_other_clarifications(session_data)
                }
            },
            "agent_metadata": {
                "agent_name": self.name,
                "iteration": state["iteration"],
                "session_duration": self._calculate_session_duration(session_data)
            }
        }
        
        state["context"]["final_output"] = final_output
        state["status"] = "completed"
        
        logger.info(f"WidgetOrchestrator completed session with {len(session_data.get('answers', []))} answers")
        
        return state
    
    def _should_validate(self, state: AgentState) -> str:
        """Determine if answer should be validated"""
        context = state["context"]
        user_input = context.get("user_answer", "").strip().lower()
        
        if user_input in ["пропустить", "skip", "стоп", "stop"]:
            return "skip"
        elif user_input:
            return "validate"
        else:
            return "continue"
    
    def _should_continue_after_validation(self, state: AgentState) -> str:
        """Determine next step after validation"""
        validation_status = state["context"].get("validation_status", "valid")
        
        if validation_status == "valid":
            return "next_question"
        elif validation_status == "invalid":
            return "reask"
        else:
            return "finalize"
    
    def _should_finalize(self, state: AgentState) -> str:
        """Determine if session should be finalized"""
        if state["status"] == "completed":
            return "finalize"
        else:
            return "continue"
    
    def _extract_relocation_ready(self, session_data: Dict[str, Any]) -> bool:
        """Extract relocation readiness from answers"""
        answers = session_data.get("answers", [])
        for answer in answers:
            if answer.get("criterion") == "location" and "готов" in answer.get("raw_answer", "").lower():
                return True
        return False
    
    def _extract_lang_proofs(self, session_data: Dict[str, Any]) -> List[str]:
        """Extract language proofs from answers"""
        answers = session_data.get("answers", [])
        lang_proofs = []
        for answer in answers:
            if answer.get("criterion") == "langs":
                lang_proofs.append(answer.get("raw_answer", ""))
        return lang_proofs
    
    def _extract_salary_flex(self, session_data: Dict[str, Any]) -> str:
        """Extract salary flexibility from answers"""
        answers = session_data.get("answers", [])
        for answer in answers:
            if answer.get("criterion") == "compensation":
                raw_answer = answer.get("raw_answer", "").lower()
                if "переговоры" in raw_answer or "гибко" in raw_answer:
                    return "negotiable"
                elif "фиксированная" in raw_answer:
                    return "fixed"
                else:
                    return "range"
        return "negotiable"
    
    def _extract_other_clarifications(self, session_data: Dict[str, Any]) -> List[str]:
        """Extract other clarifications from answers"""
        answers = session_data.get("answers", [])
        clarifications = []
        for answer in answers:
            if answer.get("criterion") not in ["location", "langs", "compensation"]:
                clarifications.append(answer.get("raw_answer", ""))
        return clarifications
    
    def _calculate_session_duration(self, session_data: Dict[str, Any]) -> str:
        """Calculate session duration"""
        try:
            started = datetime.fromisoformat(session_data.get("started_at", ""))
            ended = datetime.fromisoformat(session_data.get("ended_at", ""))
            duration = ended - started
            return str(duration)
        except:
            return "unknown"
    
    def _define_tools(self) -> List[Any]:
        """Define tools available to this agent"""
        return [
            # Answer validation tool
            # Session management tool
            # Transcript analysis tool
        ]

# Global instance
widget_orchestrator_agent = WidgetOrchestratorAgent()

