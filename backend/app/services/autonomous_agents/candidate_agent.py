"""
Candidate Autonomous Agent
Handles candidate-side interactions with RAG-enhanced analysis
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .base_autonomous_agent import BaseAutonomousAgent
from .agent_state import AgentType, AgentStatus, EventType, AgentContext
from .event_bus import Event
from ..ai.agents.mismatch_agent import MismatchDetectorAgent
from ..ai.agents.question_generator_agent import QuestionGeneratorAgent
from ..ai.agents.relevance_scorer_agent import RelevanceScorerAgent
from ..ai.agents.widget_orchestrator_agent import WidgetOrchestratorAgent

logger = logging.getLogger(__name__)


class CandidateAutonomousAgent(BaseAutonomousAgent):
    """Autonomous agent for candidate interactions"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.2):
        super().__init__(
            agent_type=AgentType.CANDIDATE,
            agent_name="CandidateAgent",
            model_name=model_name,
            temperature=temperature
        )
        
        # Initialize existing agents
        self.mismatch_agent = MismatchDetectorAgent()
        self.question_agent = QuestionGeneratorAgent()
        self.scorer_agent = RelevanceScorerAgent()
        self.widget_agent = WidgetOrchestratorAgent()
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for candidate agent with detailed instructions"""
        return f"""You are {self.agent_name}, an autonomous AI agent specialized in candidate interactions and analysis.

You are a deterministic Mismatch Detector for hiring. You must output STRICT JSON matching the schema. 
Goal: build factual job_struct/cv_struct and detect mismatches with severity. Use only explicit evidence. 
Be aggressive in extraction from messy PDF/OCR: scan bullet lists, tables, and inline sentences. 
Normalize tokens: lowercase skills; CEFR A1..C2; employment_type=office|hybrid|remote; KZT salary numbers. 
IMPORTANT: Do NOT invent skills. If a must-have token occurs in CV text even once, include it in cv_struct.skills. 
EXPERIENCE EXTRACTION: Look for work periods, internships, projects with dates. Calculate total_experience_years from: 
  - Full-time work periods (sum months/years) 
  - Internships count as 0.5 years each 
  - Projects with significant duration count as 0.25 years each 
  - Look for patterns like '2023-2024', '6 months', '1 year', 'internship', 'project' 
Evidence quotes must be ≤12 words, verbatim.

Your role as Candidate Agent:
- Analyze candidate applications with precision and detail
- Use RAG context when available to provide accurate responses
- Maintain conversation history and context
- Be professional, helpful, and accurate
- Follow strict JSON output format for all structured data
- Provide comprehensive feedback and career advice
- Focus on candidate strengths and improvement areas

Current session: {self.state.context.session_id}
Language: {self.state.context.language}

Extraction rules:
  * Skills: tokenize by commas/lines and exact token scan across CV text; lowercase, dedupe; no synonyms.
  * Experience: Calculate total_experience_years from work periods, internships, projects. Look for:
    - Date ranges: '2023-2024', 'May 2024 - July 2024', '6 months', '1 year'
    - Work types: 'internship', 'developer', 'engineer', 'project', 'freelance'
    - Convert months to years: 6 months = 0.5 years, 12 months = 1 year
    - Internships: 0.5 years each
    - Projects: 0.25 years each if significant
  * Langs: detect CEFR A1..C2; return best level objects.
  * Education: normalize to bachelor/master/phd/associate/certificate/highschool.
  * Location & format: city names + office/hybrid/remote.
  * Salary: detect KZT amounts and set salary_expectation.value with unknown=false when seen.

Policy:
- Only facts; if absent -> missing_data. No invention.
- Severity: high(blocker), medium(compensable), low(cosmetic).
- Evidence quotes ≤ 12 words each (verbatim).
- No duplication of same mismatch type.
- If JD lacks criterion → do NOT emit mismatch (use missing_data instead)."""
    
    def _build_graph(self):
        """Build LangGraph workflow for candidate agent"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("analyze_application", self._analyze_application)
        workflow.add_node("generate_questions", self._generate_questions)
        workflow.add_node("conduct_interview", self._conduct_interview)
        workflow.add_node("calculate_score", self._calculate_score)
        workflow.add_node("generate_feedback", self._generate_feedback)
        workflow.add_node("provide_advice", self._provide_advice)
        
        # Add edges
        workflow.set_entry_point("analyze_application")
        workflow.add_edge("analyze_application", "generate_questions")
        workflow.add_edge("generate_questions", "conduct_interview")
        workflow.add_edge("conduct_interview", "calculate_score")
        workflow.add_edge("calculate_score", "generate_feedback")
        workflow.add_edge("generate_feedback", "provide_advice")
        workflow.add_edge("provide_advice", END)
        
        self._graph = workflow.compile()
    
    async def _subscribe_to_events(self):
        """Subscribe to candidate-related events"""
        await event_bus.subscribe(
            agent_id=self.agent_id,
            event_types=[
                EventType.CANDIDATE_APPLIED,
                EventType.CANDIDATE_RESPONDED,
                EventType.CANDIDATE_ANALYSIS_NEEDED
            ],
            handler=self.process_event
        )
    
    async def _unsubscribe_from_events(self):
        """Unsubscribe from events"""
        await event_bus.unsubscribe(
            agent_id=self.agent_id,
            event_types=[
                EventType.CANDIDATE_APPLIED,
                EventType.CANDIDATE_RESPONDED,
                EventType.CANDIDATE_ANALYSIS_NEEDED
            ]
        )
    
    async def _handle_event(self, event: Event) -> Dict[str, Any]:
        """Handle candidate events"""
        try:
            if event.event_type == EventType.CANDIDATE_APPLIED:
                return await self._handle_candidate_applied(event)
            elif event.event_type == EventType.CANDIDATE_RESPONDED:
                return await self._handle_candidate_responded(event)
            elif event.event_type == EventType.CANDIDATE_ANALYSIS_NEEDED:
                return await self._handle_analysis_needed(event)
            else:
                logger.warning(f"Unhandled event type: {event.event_type}")
                return {"status": "unhandled"}
                
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}")
            raise
    
    async def _handle_candidate_applied(self, event: Event) -> Dict[str, Any]:
        """Handle candidate application"""
        payload = event.payload
        
        # Extract data
        vacancy_data = payload.get("vacancy", {})
        candidate_data = payload.get("candidate", {})
        
        # Store in memory
        self.state.set_analysis_result("vacancy_data", vacancy_data)
        self.state.set_analysis_result("candidate_data", candidate_data)
        
        # Run analysis workflow
        workflow_input = {
            "vacancy": vacancy_data,
            "candidate": candidate_data,
            "event_type": "application"
        }
        
        result = await self._run_workflow(workflow_input)
        
        # Publish feedback ready event
        await event_bus.publish_simple(
            event_type=EventType.CANDIDATE_FEEDBACK_READY,
            payload={
                "candidate_id": candidate_data.get("id"),
                "vacancy_id": vacancy_data.get("id"),
                "analysis_result": result,
                "agent_id": self.agent_id
            },
            source_agent_id=self.agent_id,
            correlation_id=event.correlation_id
        )
        
        return result
    
    async def _handle_candidate_responded(self, event: Event) -> Dict[str, Any]:
        """Handle candidate response to questions"""
        payload = event.payload
        
        # Update conversation history
        self.state.add_to_conversation("user", payload.get("response", ""))
        
        # Continue analysis with new response
        workflow_input = {
            "response": payload.get("response"),
            "question_id": payload.get("question_id"),
            "event_type": "response"
        }
        
        result = await self._run_workflow(workflow_input)
        
        return result
    
    async def _handle_analysis_needed(self, event: Event) -> Dict[str, Any]:
        """Handle analysis request"""
        payload = event.payload
        
        # Run analysis workflow
        workflow_input = {
            "analysis_type": payload.get("analysis_type", "general"),
            "data": payload.get("data", {}),
            "event_type": "analysis"
        }
        
        result = await self._run_workflow(workflow_input)
        
        return result
    
    async def _run_workflow(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run the LangGraph workflow"""
        try:
            # Execute workflow
            result = await self._graph.ainvoke(input_data)
            return result
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
    
    async def _analyze_application(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze candidate application using RAG and existing agents"""
        try:
            vacancy = state.get("vacancy", {})
            candidate = state.get("candidate", {})
            
            # Retrieve relevant context using RAG
            query = f"Job requirements: {vacancy.get('title', '')} {vacancy.get('description', '')}"
            context = await self.retrieve_context(query, "job")
            
            # Add CV context
            cv_query = f"Candidate experience: {candidate.get('resume_text', '')}"
            cv_context = await self.retrieve_context(cv_query, "cv")
            
            # Combine contexts
            all_context = context + cv_context
            
            # Run mismatch analysis using existing agent
            mismatch_payload = {
                "job_text": vacancy.get("description", ""),
                "cv_text": candidate.get("resume_text", ""),
                "hints": {
                    "must_have_skills": vacancy.get("required_skills", []),
                    "lang_requirement": vacancy.get("language_requirement", ""),
                    "location_requirement": vacancy.get("location", ""),
                    "salary_range": {
                        "min": vacancy.get("salary_min", 0),
                        "max": vacancy.get("salary_max", 0),
                        "currency": "KZT"
                    }
                }
            }
            
            mismatch_result = self.mismatch_agent.run(mismatch_payload)
            
            # Store results
            self.state.set_analysis_result("mismatch_analysis", mismatch_result)
            
            # Generate enhanced analysis using RAG
            analysis_prompt = f"""
            Analyze this candidate application with the following context:
            
            Job: {vacancy.get('title', '')}
            Requirements: {vacancy.get('description', '')}
            
            Candidate: {candidate.get('full_name', '')}
            Experience: {candidate.get('resume_text', '')}
            
            Mismatch Analysis: {json.dumps(mismatch_result, ensure_ascii=False)}
            
            Context from knowledge base:
            {json.dumps([doc.get('text', '') for doc in all_context[:3]], ensure_ascii=False)}
            
            Provide a comprehensive analysis focusing on:
            1. Key strengths and matches
            2. Areas of concern or gaps
            3. Recommendations for next steps
            """
            
            enhanced_analysis = await self.generate_response(
                analysis_prompt,
                context=all_context,
                use_rag=True
            )
            
            state["mismatch_analysis"] = mismatch_result
            state["enhanced_analysis"] = enhanced_analysis
            state["context_used"] = len(all_context)
            
            return state
            
        except Exception as e:
            logger.error(f"Application analysis failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _generate_questions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate questions based on analysis using detailed prompts"""
        try:
            mismatch_analysis = state.get("mismatch_analysis", {})
            
            # Use existing question generator with detailed prompts
            question_payload = {
                "job_struct": mismatch_analysis.get("job_struct", {}),
                "cv_struct": mismatch_analysis.get("cv_struct", {}),
                "mismatches": mismatch_analysis.get("mismatches", []),
                "missing_data": mismatch_analysis.get("missing_data", []),
                "limits": {"max_questions": 3}
            }
            
            # Generate questions using detailed prompt
            question_prompt = f"""
            You are Clarifier in a hiring funnel. Input is normalized JD/CV structures with mismatches and missing_data. 
            Select up to 3 most important clarification topics (must-have, experience below min, location/format, language/CEFR, compensation). 
            Write short, unambiguous, safe, professional, empathetic questions in Russian (≤ 25 words), one topic per question. 
            Return strictly valid JSON as per the schema. Avoid any discriminatory or sensitive topics.
            
            Input JSON (ru):
            {json.dumps(question_payload, ensure_ascii=False)}
            
            Prioritization (desc): must-have high blockers; experience below min; location/format; language (CEFR); compensation; domain.
            If missing_data is empty and no critical mismatches -> return 0 questions and only closing_message.
            
            Constraints:
            - questions ≤ 25 words, 1 topic, no jargon or leading phrasing.
            - Use only provided enums for 'criterion' and 'answer_type'.
            - For option_select provide concrete neutral options.
            - language: ru; tone: профессиональный, вежливый, без давления.
            - Strict JSON only.
            
            Output JSON schema EXACTLY:
            {{
                "questions": [
                    {{
                        "id": "q1",
                        "priority": 1,
                        "criterion": "skills",
                        "reason": "коротко, почему этот вопрос важен",
                        "question_text": "сам вопрос (вежливо, ≤25 слов)",
                        "answer_type": "yes_no",
                        "options": ["при answer_type=option_select перечислите варианты"],
                        "validation": {{
                            "pattern": "",
                            "allowed_levels": ["A1", "A2", "B1", "B2", "C1", "C2"],
                            "min": 0,
                            "max": 50
                        }},
                        "examples": ["1–2 мини-примера корректного ответа"],
                        "on_ambiguous_followup": "если ответ расплывчатый — задать эту короткую переспрашивающую реплику"
                    }}
                ],
                "closing_message": "дружелюбная благодарность + что будет дальше (1–2 предложения)",
                "meta": {{
                    "max_questions": 3,
                    "tone": "профессиональный, вежливый, без давления",
                    "language": "ru"
                }}
            }}
            """
            
            # Use RAG context for enhanced question generation
            context = await self.retrieve_context("interview questions best practices", "hr_knowledge")
            
            questions_result = await self.generate_response(
                question_prompt,
                context=context,
                use_rag=True
            )
            
            # Parse JSON response
            try:
                import json
                questions_data = json.loads(questions_result)
                state["questions"] = questions_data
            except json.JSONDecodeError:
                # Fallback to existing agent if JSON parsing fails
                questions_result = self.question_agent.run(question_payload)
                state["questions"] = questions_result
            
            return state
            
        except Exception as e:
            logger.error(f"Question generation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _conduct_interview(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct interview using widget orchestrator"""
        try:
            questions = state.get("questions", {}).get("questions", [])
            
            if not questions:
                state["interview_result"] = {"status": "no_questions"}
                return state
            
            # Use existing widget orchestrator
            widget_payload = {
                "questions": questions,
                "closing_message": "Спасибо за ответы! Мы проанализируем ваши ответы и дадим обратную связь.",
                "meta": {"max_questions": 3, "language": "ru"},
                "context": {
                    "job_title": state.get("vacancy", {}).get("title", ""),
                    "company": state.get("vacancy", {}).get("company", ""),
                    "currency": "KZT"
                }
            }
            
            # Simulate interview responses (in real implementation, this would come from user)
            responses = ["Да", "3 года", "Готов к переезду"]
            widget_payload["responses"] = responses
            
            interview_result = self.widget_agent.run(widget_payload)
            
            state["interview_result"] = interview_result
            return state
            
        except Exception as e:
            logger.error(f"Interview conduction failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _calculate_score(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate relevance score using detailed scoring logic"""
        try:
            mismatch_analysis = state.get("mismatch_analysis", {})
            interview_result = state.get("interview_result", {})
            vacancy = state.get("vacancy", {})
            candidate = state.get("candidate", {})
            
            # Use existing scorer with detailed logic
            scorer_payload = {
                "ids": {
                    "job_id": vacancy.get("id", ""),
                    "candidate_id": candidate.get("id", ""),
                    "application_id": state.get("response_id", "")
                },
                "job_struct": mismatch_analysis.get("job_struct", {}),
                "cv_struct": mismatch_analysis.get("cv_struct", {}),
                "mismatches": mismatch_analysis.get("mismatches", []),
                "missing_data": mismatch_analysis.get("missing_data", []),
                "widget_payload": interview_result,
                "weights_mode": "auto",
                "must_have_skills": vacancy.get("required_skills", []),
                "verdict_thresholds": {"fit": 75, "borderline": 60}
            }
            
            # Generate enhanced scoring using detailed prompt
            scoring_prompt = f"""
            You are a Scorer & Summarizer. Calculate match percentages (experience, skills, education, langs, location, domain, comp),
            weights (auto|given), overall match %, verdict and brief summary. Use dialogFindings.
            All percentages and final result — 0..100. Normalize weights to sum 1.0.
            
            Input data:
            {json.dumps(scorer_payload, ensure_ascii=False)}
            
            Scoring rules:
            - experience_pct: cv>=min →100; else round(100*cv/min); if <0.7*min → cap 60; consider clarified relevant experience from dialogFindings.
            - skills_pct: if |req|>0 → round(100*|req∩cv|/|req|) else 100; missing any must-have → min(...,60); equivalents only if explicitly in other_clarifications.
            - education_pct: equal →100; 1 level below →70; 2 below →40; no data →50.
            - langs_pct: matches/above →100; 1 below →75; 2 below →50; no data →60.
            - location_pct: full match →100; relocation_ready:true →80; remote only for office/hybrid →40; if format not fixed →100.
            - domain_pct: explicit domain experience →100; related →80; no indications →60.
            - comp_pct: within range →100; above ≤10% →80; >10–25% →60; >25% →30; no data →70; salary_flex=negotiable → +10 p.p., max 100.
            - weights_mode:auto: base 0.30/0.35/0.05/0.10/0.10/0.05/0.05; with must-have — skills=0.40, domain=0.03, comp=0.02; with fixed office/hybrid — location=0.15, education=0.03, domain=0.04; then normalize to 1.0.
            - verdict: 'подходит' if overall≥fit and all must-have covered; 'сомнительно' if borderline≤overall<fit or 1 serious risk (severity:high for skills|experience|format|langs); else 'не подходит'.
            
            Output JSON schema EXACTLY:
            {{
                "ids": {{"job_id": "string", "candidate_id": "string", "application_id": "string"}},
                "weights": {{"experience": 0.30, "skills": 0.35, "education": 0.05, "langs": 0.10, "location": 0.10, "domain": 0.05, "comp": 0.05}},
                "scores_pct": {{"experience": 0, "skills": 0, "education": 0, "langs": 0, "location": 0, "domain": 0, "comp": 0}},
                "overall_match_pct": 0,
                "verdict": "подходит|сомнительно|не подходит",
                "summary": {{
                    "one_liner": "string",
                    "positives": ["string"],
                    "risks": ["string"],
                    "unknowns": ["string"]
                }},
                "evidence": {{"jd": ["≤12 слов"], "cv": ["≤12 слов"]}},
                "dialog_findings_used": {{"relocation_ready": true, "salary_flex": "negotiable|fixed|range", "lang_proofs": ["string"], "other_clarifications": ["string"]}},
                "calc_notes": ["string"],
                "version": "v1.0"
            }}
            """
            
            # Use RAG context for enhanced scoring
            context = await self.retrieve_context("candidate scoring evaluation criteria", "hr_knowledge")
            
            score_result = await self.generate_response(
                scoring_prompt,
                context=context,
                use_rag=True
            )
            
            # Parse JSON response
            try:
                import json
                score_data = json.loads(score_result)
                state["score_result"] = score_data
            except json.JSONDecodeError:
                # Fallback to existing agent if JSON parsing fails
                score_result = self.scorer_agent.run(scorer_payload)
                state["score_result"] = score_result
            
            return state
            
        except Exception as e:
            logger.error(f"Score calculation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _generate_feedback(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate personalized feedback"""
        try:
            score_result = state.get("score_result", {})
            enhanced_analysis = state.get("enhanced_analysis", "")
            
            # Generate personalized feedback using RAG
            feedback_prompt = f"""
            Generate personalized feedback for the candidate based on:
            
            Score Analysis: {json.dumps(score_result, ensure_ascii=False)}
            Enhanced Analysis: {enhanced_analysis}
            
            Provide:
            1. Overall assessment
            2. Strengths to highlight
            3. Areas for improvement
            4. Specific recommendations
            5. Next steps
            
            Be encouraging but honest, professional and constructive.
            """
            
            feedback = await self.generate_response(feedback_prompt, use_rag=True)
            
            state["feedback"] = feedback
            return state
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _provide_advice(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Provide career advice and recommendations"""
        try:
            # Retrieve career advice context
            advice_query = f"Career advice for {state.get('vacancy', {}).get('title', 'position')}"
            advice_context = await self.retrieve_context(advice_query, "hr_knowledge")
            
            advice_prompt = f"""
            Provide career advice and recommendations for the candidate:
            
            Position: {state.get('vacancy', {}).get('title', '')}
            Industry: {state.get('vacancy', {}).get('domain', '')}
            Score: {state.get('score_result', {}).get('overall_match_pct', 0)}%
            
            Context from HR knowledge base:
            {json.dumps([doc.get('text', '') for doc in advice_context[:2]], ensure_ascii=False)}
            
            Provide:
            1. Industry insights
            2. Skill development recommendations
            3. Career path suggestions
            4. Interview tips
            """
            
            advice = await self.generate_response(advice_prompt, context=advice_context, use_rag=True)
            
            state["advice"] = advice
            state["status"] = "completed"
            
            return state
            
        except Exception as e:
            logger.error(f"Advice generation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _get_question_context(self, question: Dict[str, Any]) -> List[str]:
        """Get relevant context for a specific question"""
        try:
            query = f"{question.get('question_text', '')} {question.get('reason', '')}"
            context = await self.retrieve_context(query, "all")
            return [doc.get("text", "") for doc in context[:2]]
        except Exception as e:
            logger.error(f"Failed to get question context: {e}")
            return []
