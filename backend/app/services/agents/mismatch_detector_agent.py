"""
Autonomous Mismatch Detector Agent
Uses LangGraph to autonomously analyze job-candidate mismatches
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from .base_agent import BaseAgent, AgentState
import json
import logging

logger = logging.getLogger(__name__)

class MismatchDetectorAgent(BaseAgent):
    """Autonomous agent for detecting mismatches between job descriptions and CVs"""
    
    def __init__(self):
        super().__init__("MismatchDetector", "gpt-4o-mini")
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_input", self._analyze_input)
        workflow.add_node("search_knowledge", self._search_knowledge)
        workflow.add_node("detect_mismatches", self._detect_mismatches)
        workflow.add_node("validate_results", self._validate_results)
        workflow.add_node("finalize_analysis", self._finalize_analysis)
        
        # Add edges
        workflow.set_entry_point("analyze_input")
        workflow.add_edge("analyze_input", "search_knowledge")
        workflow.add_edge("search_knowledge", "detect_mismatches")
        workflow.add_edge("detect_mismatches", "validate_results")
        workflow.add_edge("validate_results", "finalize_analysis")
        workflow.add_edge("finalize_analysis", END)
        
        self.graph = workflow.compile()
    
    def _analyze_input(self, state: AgentState) -> AgentState:
        """Analyze input data and extract key information"""
        logger.info("MismatchDetector: Analyzing input data")
        
        context = state["context"]
        job_text = context.get("job_text", "")
        cv_text = context.get("cv_text", "")
        
        # Extract key information
        analysis_prompt = f"""
        Analyze the following job description and CV to extract key information:
        
        JOB DESCRIPTION:
        {job_text}
        
        CV TEXT:
        {cv_text}
        
        Extract and structure the following information:
        1. Job requirements (skills, experience, education, location)
        2. Candidate qualifications (skills, experience, education, location)
        3. Key differences and potential mismatches
        4. Missing information that needs clarification
        
        Return as JSON with structured data.
        """
        
        messages = [HumanMessage(content=analysis_prompt)]
        response = self._call_llm(messages)
        
        try:
            analysis = self._parse_json_response(response)
            state["context"]["analysis"] = analysis
            state["memory"]["input_analysis"] = analysis
        except Exception as e:
            logger.error(f"Input analysis failed: {e}")
            state["context"]["analysis"] = {"error": str(e)}
        
        return state
    
    def _search_knowledge(self, state: AgentState) -> AgentState:
        """Search knowledge base for similar cases and best practices"""
        logger.info("MismatchDetector: Searching knowledge base")
        
        context = state["context"]
        analysis = context.get("analysis", {})
        
        # Build search queries
        queries = []
        if "job_requirements" in analysis:
            queries.append(f"job requirements {analysis['job_requirements']}")
        if "candidate_skills" in analysis:
            queries.append(f"candidate skills {analysis['candidate_skills']}")
        
        # Search knowledge base
        knowledge_results = []
        for query in queries:
            results = self._search_knowledge(query)
            knowledge_results.extend(results)
        
        state["context"]["knowledge_results"] = knowledge_results
        state["memory"]["knowledge_search"] = knowledge_results
        
        return state
    
    def _detect_mismatches(self, state: AgentState) -> AgentState:
        """Detect specific mismatches using AI analysis"""
        logger.info("MismatchDetector: Detecting mismatches")
        
        context = state["context"]
        analysis = context.get("analysis", {})
        knowledge = context.get("knowledge_results", [])
        
        mismatch_prompt = f"""
        You are an expert HR analyst. Analyze the job-candidate match and identify specific mismatches.
        
        JOB ANALYSIS:
        {json.dumps(analysis.get('job_requirements', {}), indent=2)}
        
        CANDIDATE ANALYSIS:
        {json.dumps(analysis.get('candidate_qualifications', {}), indent=2)}
        
        KNOWLEDGE BASE CONTEXT:
        {json.dumps(knowledge, indent=2)}
        
        Identify mismatches in these categories:
        1. Experience level (too high/low)
        2. Required skills (missing/present)
        3. Education level (insufficient/overqualified)
        4. Location (mismatch/remote preference)
        5. Language requirements
        6. Salary expectations
        7. Domain expertise
        
        For each mismatch, provide:
        - Type: experience|skills|education|location|language|salary|domain
        - Severity: high|medium|low
        - Description: detailed explanation
        - Evidence: specific quotes from job/CV (max 12 words each)
        - Recommendation: how to address this mismatch
        
        Return as JSON following the exact schema from the original requirements.
        """
        
        messages = [HumanMessage(content=mismatch_prompt)]
        response = self._call_llm(messages)
        
        try:
            mismatches = self._parse_json_response(response)
            state["context"]["mismatches"] = mismatches
            state["memory"]["mismatch_analysis"] = mismatches
        except Exception as e:
            logger.error(f"Mismatch detection failed: {e}")
            state["context"]["mismatches"] = {"error": str(e)}
        
        return state
    
    def _validate_results(self, state: AgentState) -> AgentState:
        """Validate the analysis results"""
        logger.info("MismatchDetector: Validating results")
        
        context = state["context"]
        mismatches = context.get("mismatches", {})
        
        # Validate JSON structure
        required_fields = ["job_struct", "cv_struct", "mismatches", "missing_data"]
        validation_errors = []
        
        for field in required_fields:
            if field not in mismatches:
                validation_errors.append(f"Missing required field: {field}")
        
        if validation_errors:
            logger.warning(f"Validation errors: {validation_errors}")
            state["context"]["validation_errors"] = validation_errors
        else:
            state["context"]["validation_passed"] = True
        
        return state
    
    def _finalize_analysis(self, state: AgentState) -> AgentState:
        """Finalize the analysis and prepare output"""
        logger.info("MismatchDetector: Finalizing analysis")
        
        context = state["context"]
        
        # Prepare final output
        final_output = {
            "job_struct": context.get("analysis", {}).get("job_requirements", {}),
            "cv_struct": context.get("analysis", {}).get("candidate_qualifications", {}),
            "mismatches": context.get("mismatches", {}).get("mismatches", []),
            "missing_data": context.get("mismatches", {}).get("missing_data", []),
            "coverage_snapshot": {
                "must_have_covered": [],
                "must_have_missing": [],
                "skills_overlap": []
            },
            "agent_metadata": {
                "agent_name": self.name,
                "iteration": state["iteration"],
                "tools_used": state["tools_used"],
                "knowledge_sources": len(context.get("knowledge_results", [])),
                "validation_passed": context.get("validation_passed", False)
            }
        }
        
        state["context"]["final_output"] = final_output
        state["status"] = "completed"
        
        logger.info(f"MismatchDetector completed analysis with {len(final_output['mismatches'])} mismatches found")
        
        return state
    
    def _define_tools(self) -> List[Any]:
        """Define tools available to this agent"""
        return [
            # Knowledge search tool
            # Mismatch analysis tool
            # Validation tool
        ]

# Global instance
mismatch_detector_agent = MismatchDetectorAgent()
