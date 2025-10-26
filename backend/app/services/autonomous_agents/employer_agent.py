"""
Employer Autonomous Agent
Handles employer-side interactions with RAG-enhanced analysis
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
from ..ai.agents.relevance_scorer_agent import RelevanceScorerAgent

logger = logging.getLogger(__name__)


class EmployerAutonomousAgent(BaseAutonomousAgent):
    """Autonomous agent for employer interactions"""
    
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.2):
        super().__init__(
            agent_type=AgentType.EMPLOYER,
            agent_name="EmployerAgent",
            model_name=model_name,
            temperature=temperature
        )
        
        # Initialize existing agents
        self.mismatch_agent = MismatchDetectorAgent()
        self.scorer_agent = RelevanceScorerAgent()
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for employer agent with detailed instructions"""
        return f"""You are {self.agent_name}, an autonomous AI agent specialized in employer interactions and candidate analysis.

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

Your role as Employer Agent:
- Analyze candidates from employer perspective with precision and detail
- Use RAG context when available to provide accurate responses
- Maintain conversation history and context
- Be professional, helpful, and accurate
- Follow strict JSON output format for all structured data
- Provide comprehensive hiring insights and recommendations
- Focus on candidate fit, risks, and hiring decisions
- Compare multiple candidates objectively
- Provide market insights and salary benchmarking

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
- If JD lacks criterion → do NOT emit mismatch (use missing_data instead).
- Provide actionable hiring recommendations.
- Consider both technical fit and cultural fit.
- Highlight both strengths and potential risks."""
    
    def _build_graph(self):
        """Build LangGraph workflow for employer agent"""
        workflow = StateGraph(dict)
        
        # Add nodes
        workflow.add_node("analyze_candidate", self._analyze_candidate)
        workflow.add_node("compare_candidates", self._compare_candidates)
        workflow.add_node("generate_insights", self._generate_insights)
        workflow.add_node("provide_recommendations", self._provide_recommendations)
        workflow.add_node("assist_with_questions", self._assist_with_questions)
        
        # Add edges
        workflow.set_entry_point("analyze_candidate")
        workflow.add_edge("analyze_candidate", "compare_candidates")
        workflow.add_edge("compare_candidates", "generate_insights")
        workflow.add_edge("generate_insights", "provide_recommendations")
        workflow.add_edge("provide_recommendations", "assist_with_questions")
        workflow.add_edge("assist_with_questions", END)
        
        self._graph = workflow.compile()
    
    async def _subscribe_to_events(self):
        """Subscribe to employer-related events"""
        # subscribe is synchronous in EventBus
        self.event_bus.subscribe(
            agent_id=self.agent_id,
            event_types=[
                EventType.EMPLOYER_VIEWED_CANDIDATE,
                EventType.EMPLOYER_REQUESTED_ANALYSIS,
                EventType.EMPLOYER_CHAT_REQUESTED
            ],
            handler=self.process_event
        )
    
    async def _unsubscribe_from_events(self):
        """Unsubscribe from events"""
        # unsubscribe is synchronous in EventBus
        self.event_bus.unsubscribe(
            agent_id=self.agent_id,
            event_types=[
                EventType.EMPLOYER_VIEWED_CANDIDATE,
                EventType.EMPLOYER_REQUESTED_ANALYSIS,
                EventType.EMPLOYER_CHAT_REQUESTED
            ]
        )
    
    async def _handle_event(self, event: Event) -> Dict[str, Any]:
        """Handle employer events"""
        try:
            if event.event_type == EventType.EMPLOYER_VIEWED_CANDIDATE:
                return await self._handle_candidate_viewed(event)
            elif event.event_type == EventType.EMPLOYER_REQUESTED_ANALYSIS:
                return await self._handle_analysis_requested(event)
            elif event.event_type == EventType.EMPLOYER_CHAT_REQUESTED:
                return await self._handle_chat_requested(event)
            else:
                logger.warning(f"Unhandled event type: {event.event_type}")
                return {"status": "unhandled"}
                
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}")
            raise
    
    async def _handle_candidate_viewed(self, event: Event) -> Dict[str, Any]:
        """Handle employer viewing a candidate"""
        payload = event.payload
        
        # Extract data
        candidate_data = payload.get("candidate", {})
        vacancy_data = payload.get("vacancy", {})
        employer_id = payload.get("employer_id")
        
        # Store in memory
        self.state.set_analysis_result("current_candidate", candidate_data)
        self.state.set_analysis_result("current_vacancy", vacancy_data)
        self.state.context.user_id = employer_id
        
        # Run analysis workflow
        workflow_input = {
            "candidate": candidate_data,
            "vacancy": vacancy_data,
            "employer_id": employer_id,
            "event_type": "candidate_viewed"
        }
        
        result = await self._run_workflow(workflow_input)
        
        # Publish analysis ready event
        await event_bus.publish_simple(
            event_type=EventType.EMPLOYER_ANALYSIS_READY,
            payload={
                "employer_id": employer_id,
                "candidate_id": candidate_data.get("id"),
                "vacancy_id": vacancy_data.get("id"),
                "analysis_result": result,
                "agent_id": self.agent_id
            },
            source_agent_id=self.agent_id,
            correlation_id=event.correlation_id
        )
        
        return result
    
    async def _handle_analysis_requested(self, event: Event) -> Dict[str, Any]:
        """Handle analysis request from employer"""
        payload = event.payload
        
        # Run analysis workflow
        workflow_input = {
            "analysis_type": payload.get("analysis_type", "comprehensive"),
            "candidates": payload.get("candidates", []),
            "vacancy": payload.get("vacancy", {}),
            "employer_id": payload.get("employer_id"),
            "event_type": "analysis_requested"
        }
        
        result = await self._run_workflow(workflow_input)
        
        return result
    
    async def _handle_chat_requested(self, event: Event) -> Dict[str, Any]:
        """Handle chat assistance request from employer"""
        payload = event.payload
        
        # Store chat context
        self.state.add_to_conversation("user", payload.get("message", ""))
        
        # Run chat assistance workflow
        workflow_input = {
            "message": payload.get("message"),
            "context": payload.get("context", {}),
            "employer_id": payload.get("employer_id"),
            "event_type": "chat_requested"
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
    
    async def _analyze_candidate(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze candidate for employer"""
        try:
            candidate = state.get("candidate", {})
            vacancy = state.get("vacancy", {})
            
            # Retrieve relevant context using RAG
            query = f"Job requirements: {vacancy.get('title', '')} {vacancy.get('description', '')}"
            job_context = await self.retrieve_context(query, "job")
            
            # Add candidate context
            cv_query = f"Candidate profile: {candidate.get('full_name', '')} {candidate.get('resume_text', '')}"
            candidate_context = await self.retrieve_context(cv_query, "cv")
            
            # Add HR knowledge context
            hr_query = f"Hiring best practices for {vacancy.get('title', 'position')}"
            hr_context = await self.retrieve_context(hr_query, "hr_knowledge")
            
            # Combine all contexts
            all_context = job_context + candidate_context + hr_context
            
            # Run mismatch analysis
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
            
            # Calculate relevance score
            scorer_payload = {
                "ids": {
                    "job_id": vacancy.get("id", ""),
                    "candidate_id": candidate.get("id", ""),
                    "application_id": state.get("response_id", "")
                },
                "job_struct": mismatch_result.get("job_struct", {}),
                "cv_struct": mismatch_result.get("cv_struct", {}),
                "mismatches": mismatch_result.get("mismatches", []),
                "missing_data": mismatch_result.get("missing_data", []),
                "widget_payload": {},
                "weights_mode": "auto",
                "must_have_skills": vacancy.get("required_skills", []),
                "verdict_thresholds": {"fit": 75, "borderline": 60}
            }
            
            score_result = self.scorer_agent.run(scorer_payload)
            
            # Generate enhanced analysis
            analysis_prompt = f"""
            Provide a comprehensive candidate analysis for the employer:
            
            Position: {vacancy.get('title', '')}
            Company: {vacancy.get('company', '')}
            
            Candidate: {candidate.get('full_name', '')}
            Experience: {candidate.get('resume_text', '')}
            
            Mismatch Analysis: {json.dumps(mismatch_result, ensure_ascii=False)}
            Score Result: {json.dumps(score_result, ensure_ascii=False)}
            
            HR Knowledge Context:
            {json.dumps([doc.get('text', '') for doc in hr_context[:3]], ensure_ascii=False)}
            
            Provide:
            1. Executive summary
            2. Key strengths and concerns
            3. Interview focus areas
            4. Hiring recommendation
            5. Risk assessment
            """
            
            enhanced_analysis = await self.generate_response(
                analysis_prompt,
                context=all_context,
                use_rag=True
            )
            
            state["mismatch_analysis"] = mismatch_result
            state["score_result"] = score_result
            state["enhanced_analysis"] = enhanced_analysis
            state["context_used"] = len(all_context)
            
            return state
            
        except Exception as e:
            logger.error(f"Candidate analysis failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _compare_candidates(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Compare multiple candidates"""
        try:
            candidates = state.get("candidates", [])
            vacancy = state.get("vacancy", {})
            
            if len(candidates) < 2:
                state["comparison"] = {"status": "insufficient_candidates"}
                return state
            
            # Analyze each candidate
            candidate_analyses = []
            for candidate in candidates:
                # Run quick analysis for comparison
                analysis = await self._quick_candidate_analysis(candidate, vacancy)
                candidate_analyses.append({
                    "candidate": candidate,
                    "analysis": analysis
                })
            
            # Generate comparison
            comparison_prompt = f"""
            Compare these candidates for the position {vacancy.get('title', '')}:
            
            {json.dumps(candidate_analyses, ensure_ascii=False)}
            
            Provide:
            1. Ranking with rationale
            2. Strengths comparison
            3. Risk comparison
            4. Interview priority
            5. Final recommendation
            """
            
            comparison = await self.generate_response(comparison_prompt, use_rag=True)
            
            state["candidate_analyses"] = candidate_analyses
            state["comparison"] = comparison
            
            return state
            
        except Exception as e:
            logger.error(f"Candidate comparison failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _generate_insights(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate hiring insights and trends"""
        try:
            vacancy = state.get("vacancy", {})
            candidates = state.get("candidates", [])
            
            # Retrieve market insights
            market_query = f"Market trends for {vacancy.get('title', 'position')} hiring"
            market_context = await self.retrieve_context(market_query, "hr_knowledge")
            
            insights_prompt = f"""
            Generate hiring insights for the employer:
            
            Position: {vacancy.get('title', '')}
            Industry: {vacancy.get('domain', '')}
            Number of candidates: {len(candidates)}
            
            Market Context:
            {json.dumps([doc.get('text', '') for doc in market_context[:3]], ensure_ascii=False)}
            
            Provide:
            1. Market insights for this role
            2. Salary benchmarking
            3. Skill demand trends
            4. Hiring challenges
            5. Best practices
            """
            
            insights = await self.generate_response(insights_prompt, context=market_context, use_rag=True)
            
            state["insights"] = insights
            
            return state
            
        except Exception as e:
            logger.error(f"Insights generation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _provide_recommendations(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Provide hiring recommendations"""
        try:
            analysis = state.get("enhanced_analysis", "")
            comparison = state.get("comparison", "")
            insights = state.get("insights", "")
            
            recommendations_prompt = f"""
            Provide actionable hiring recommendations:
            
            Candidate Analysis: {analysis}
            Comparison: {comparison}
            Market Insights: {insights}
            
            Provide:
            1. Immediate actions
            2. Interview strategy
            3. Decision timeline
            4. Risk mitigation
            5. Next steps
            """
            
            recommendations = await self.generate_response(recommendations_prompt, use_rag=True)
            
            state["recommendations"] = recommendations
            
            return state
            
        except Exception as e:
            logger.error(f"Recommendations generation failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _assist_with_questions(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Assist employer with questions and chat"""
        try:
            message = state.get("message", "")
            context = state.get("context", {})
            
            # Retrieve relevant context for the question
            query = f"HR question: {message}"
            hr_context = await self.retrieve_context(query, "hr_knowledge")
            
            chat_prompt = f"""
            Assist the employer with their question:
            
            Question: {message}
            Context: {json.dumps(context, ensure_ascii=False)}
            
            HR Knowledge:
            {json.dumps([doc.get('text', '') for doc in hr_context[:3]], ensure_ascii=False)}
            
            Provide helpful, professional assistance.
            """
            
            response = await self.generate_response(chat_prompt, context=hr_context, use_rag=True)
            
            # Add to conversation
            self.state.add_to_conversation("assistant", response)
            
            state["chat_response"] = response
            state["status"] = "completed"
            
            return state
            
        except Exception as e:
            logger.error(f"Chat assistance failed: {e}")
            state["error"] = str(e)
            return state
    
    async def _quick_candidate_analysis(self, candidate: Dict[str, Any], vacancy: Dict[str, Any]) -> Dict[str, Any]:
        """Quick analysis for candidate comparison"""
        try:
            # Run mismatch analysis
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
            
            # Calculate score
            scorer_payload = {
                "ids": {
                    "job_id": vacancy.get("id", ""),
                    "candidate_id": candidate.get("id", ""),
                    "application_id": ""
                },
                "job_struct": mismatch_result.get("job_struct", {}),
                "cv_struct": mismatch_result.get("cv_struct", {}),
                "mismatches": mismatch_result.get("mismatches", []),
                "missing_data": mismatch_result.get("missing_data", []),
                "widget_payload": {},
                "weights_mode": "auto",
                "must_have_skills": vacancy.get("required_skills", []),
                "verdict_thresholds": {"fit": 75, "borderline": 60}
            }
            
            score_result = self.scorer_agent.run(scorer_payload)
            
            return {
                "mismatch_analysis": mismatch_result,
                "score_result": score_result
            }
            
        except Exception as e:
            logger.error(f"Quick analysis failed for candidate {candidate.get('id', 'unknown')}: {e}")
            return {"error": str(e)}
