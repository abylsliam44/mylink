"""
Autonomous Scorer & Summarizer Agent
Uses LangGraph to autonomously calculate relevance scores and generate summaries
"""
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage
from .base_agent import BaseAgent, AgentState
import json
import logging

logger = logging.getLogger(__name__)

class ScorerAgent(BaseAgent):
    """Autonomous agent for scoring and summarizing candidate-job matches"""
    
    def __init__(self):
        super().__init__("Scorer", "gpt-4o-mini")
    
    def _build_graph(self):
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_data", self._analyze_data)
        workflow.add_node("calculate_weights", self._calculate_weights)
        workflow.add_node("score_experience", self._score_experience)
        workflow.add_node("score_skills", self._score_skills)
        workflow.add_node("score_education", self._score_education)
        workflow.add_node("score_languages", self._score_languages)
        workflow.add_node("score_location", self._score_location)
        workflow.add_node("score_domain", self._score_domain)
        workflow.add_node("score_compensation", self._score_compensation)
        workflow.add_node("calculate_overall", self._calculate_overall)
        workflow.add_node("generate_verdict", self._generate_verdict)
        workflow.add_node("generate_summary", self._generate_summary)
        workflow.add_node("finalize_scoring", self._finalize_scoring)
        
        # Add edges
        workflow.set_entry_point("analyze_data")
        workflow.add_edge("analyze_data", "calculate_weights")
        workflow.add_edge("calculate_weights", "score_experience")
        workflow.add_edge("score_experience", "score_skills")
        workflow.add_edge("score_skills", "score_education")
        workflow.add_edge("score_education", "score_languages")
        workflow.add_edge("score_languages", "score_location")
        workflow.add_edge("score_location", "score_domain")
        workflow.add_edge("score_domain", "score_compensation")
        workflow.add_edge("score_compensation", "calculate_overall")
        workflow.add_edge("calculate_overall", "generate_verdict")
        workflow.add_edge("generate_verdict", "generate_summary")
        workflow.add_edge("generate_summary", "finalize_scoring")
        workflow.add_edge("finalize_scoring", END)
        
        self.graph = workflow.compile()
    
    def _analyze_data(self, state: AgentState) -> AgentState:
        """Analyze input data for scoring"""
        logger.info("Scorer: Analyzing data")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        mismatches = context.get("mismatches", [])
        dialog_findings = context.get("dialog_findings", {})
        
        analysis_prompt = f"""
        Analyze the following data for scoring:
        
        JOB STRUCTURE:
        {json.dumps(job_struct, indent=2, ensure_ascii=False)}
        
        CANDIDATE STRUCTURE:
        {json.dumps(cv_struct, indent=2, ensure_ascii=False)}
        
        MISMATCHES:
        {json.dumps(mismatches, indent=2, ensure_ascii=False)}
        
        DIALOG FINDINGS:
        {json.dumps(dialog_findings, indent=2, ensure_ascii=False)}
        
        Extract key scoring factors:
        1. Experience levels and relevance
        2. Skills match and gaps
        3. Education requirements
        4. Language proficiency
        5. Location compatibility
        6. Domain expertise
        7. Compensation alignment
        
        Return structured analysis for scoring.
        """
        
        messages = [HumanMessage(content=analysis_prompt)]
        response = self._call_llm(messages)
        
        try:
            analysis = self._parse_json_response(response)
            state["context"]["scoring_analysis"] = analysis
            state["memory"]["data_analysis"] = analysis
        except Exception as e:
            logger.error(f"Data analysis failed: {e}")
            state["context"]["scoring_analysis"] = {"error": str(e)}
        
        return state
    
    def _calculate_weights(self, state: AgentState) -> AgentState:
        """Calculate scoring weights based on job requirements"""
        logger.info("Scorer: Calculating weights")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        analysis = context.get("scoring_analysis", {})
        weights_mode = context.get("weights_mode", "auto")
        
        # Default weights
        weights = {
            "experience": 0.30,
            "skills": 0.35,
            "education": 0.05,
            "langs": 0.10,
            "location": 0.10,
            "domain": 0.05,
            "comp": 0.05
        }
        
        if weights_mode == "auto":
            # Adjust weights based on job requirements
            must_have_skills = job_struct.get("required_skills", [])
            if must_have_skills:
                weights["skills"] = 0.40
                weights["domain"] = 0.03
                weights["comp"] = 0.02
            
            # Check for office/hybrid requirements
            location_req = job_struct.get("location_requirement", {})
            if location_req.get("employment_type") in ["office", "hybrid"]:
                weights["location"] = 0.15
                weights["education"] = 0.03
                weights["domain"] = 0.04
            
            # Normalize weights to sum to 1.0
            total = sum(weights.values())
            weights = {k: v/total for k, v in weights.items()}
        
        state["context"]["weights"] = weights
        state["memory"]["weights_calculated"] = weights
        
        return state
    
    def _score_experience(self, state: AgentState) -> AgentState:
        """Score experience match"""
        logger.info("Scorer: Scoring experience")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        dialog_findings = context.get("dialog_findings", {})
        
        min_experience = job_struct.get("min_experience_years", 0)
        cv_experience = cv_struct.get("total_experience_years", 0)
        
        # Calculate experience score
        if cv_experience >= min_experience:
            score = 100
        else:
            score = round(100 * cv_experience / min_experience) if min_experience > 0 else 100
            if cv_experience < 0.7 * min_experience:
                score = min(score, 60)
        
        # Adjust based on dialog findings
        if dialog_findings.get("other_clarifications"):
            # Check for relevant experience mentioned in dialog
            for clarification in dialog_findings["other_clarifications"]:
                if "опыт" in clarification.lower() and "релевантный" in clarification.lower():
                    score = min(score + 10, 100)
        
        state["context"]["experience_score"] = score
        return state
    
    def _score_skills(self, state: AgentState) -> AgentState:
        """Score skills match"""
        logger.info("Scorer: Scoring skills")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        must_have_skills = context.get("must_have_skills", [])
        
        required_skills = job_struct.get("required_skills", [])
        cv_skills = cv_struct.get("skills", [])
        
        if not required_skills:
            score = 100
        else:
            # Calculate overlap
            overlap = set(required_skills) & set(cv_skills)
            score = round(100 * len(overlap) / len(required_skills))
            
            # Check must-have skills
            missing_must_have = set(must_have_skills) - set(cv_skills)
            if missing_must_have:
                score = min(score, 60)
        
        state["context"]["skills_score"] = score
        return state
    
    def _score_education(self, state: AgentState) -> AgentState:
        """Score education match"""
        logger.info("Scorer: Scoring education")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        
        job_education = job_struct.get("education_min", "unknown")
        cv_education = cv_struct.get("education_level", "unknown")
        
        # Education level hierarchy
        education_levels = {
            "highschool": 1,
            "certificate": 2,
            "associate": 3,
            "bachelor": 4,
            "master": 5,
            "phd": 6,
            "unknown": 0
        }
        
        job_level = education_levels.get(job_education, 0)
        cv_level = education_levels.get(cv_education, 0)
        
        if cv_level >= job_level:
            score = 100
        elif cv_level == job_level - 1:
            score = 70
        elif cv_level == job_level - 2:
            score = 40
        else:
            score = 50  # No data
        
        state["context"]["education_score"] = score
        return state
    
    def _score_languages(self, state: AgentState) -> AgentState:
        """Score language proficiency"""
        logger.info("Scorer: Scoring languages")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        dialog_findings = context.get("dialog_findings", {})
        
        job_langs = job_struct.get("lang_requirement", [])
        cv_langs = cv_struct.get("langs", [])
        
        if not job_langs:
            score = 100
        else:
            # Check language matches
            score = 100
            for job_lang in job_langs:
                lang_name = job_lang.get("lang", "")
                required_level = job_lang.get("level", "B1")
                
                # Find matching language in CV
                cv_match = None
                for cv_lang in cv_langs:
                    if cv_lang.get("lang", "").lower() == lang_name.lower():
                        cv_match = cv_lang
                        break
                
                if not cv_match:
                    score = min(score, 50)
                else:
                    cv_level = cv_match.get("level", "A1")
                    # CEFR level comparison
                    cefr_levels = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
                    required_num = cefr_levels.get(required_level, 3)
                    cv_num = cefr_levels.get(cv_level, 1)
                    
                    if cv_num >= required_num:
                        continue  # Good match
                    elif cv_num == required_num - 1:
                        score = min(score, 75)
                    else:
                        score = min(score, 50)
        
        # Adjust based on dialog findings
        if dialog_findings.get("lang_proofs"):
            score = min(score + 10, 100)
        
        state["context"]["languages_score"] = score
        return state
    
    def _score_location(self, state: AgentState) -> AgentState:
        """Score location compatibility"""
        logger.info("Scorer: Scoring location")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        dialog_findings = context.get("dialog_findings", {})
        
        job_location = job_struct.get("location_requirement", {})
        cv_location = cv_struct.get("location", {})
        
        job_city = job_location.get("city", "")
        cv_city = cv_location.get("city", "")
        job_employment = job_location.get("employment_type", "unknown")
        
        if job_city == cv_city:
            score = 100
        elif dialog_findings.get("relocation_ready", False):
            score = 80
        elif job_employment in ["office", "hybrid"] and cv_location.get("employment_type") == "remote":
            score = 40
        elif job_employment == "remote":
            score = 100
        else:
            score = 60
        
        state["context"]["location_score"] = score
        return state
    
    def _score_domain(self, state: AgentState) -> AgentState:
        """Score domain expertise"""
        logger.info("Scorer: Scoring domain")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        
        job_domain = job_struct.get("domain", "")
        cv_domains = cv_struct.get("domain_tags", [])
        
        if not job_domain:
            score = 60
        elif job_domain in cv_domains:
            score = 100
        elif any(domain in job_domain for domain in cv_domains):
            score = 80
        else:
            score = 60
        
        state["context"]["domain_score"] = score
        return state
    
    def _score_compensation(self, state: AgentState) -> AgentState:
        """Score compensation alignment"""
        logger.info("Scorer: Scoring compensation")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        dialog_findings = context.get("dialog_findings", {})
        
        job_salary_min = job_struct.get("salary_range", {}).get("min", 0)
        job_salary_max = job_struct.get("salary_range", {}).get("max", 0)
        cv_salary = cv_struct.get("salary_expectation", {}).get("value", 0)
        
        if not job_salary_min and not job_salary_max:
            score = 70  # No salary data
        elif not cv_salary:
            score = 70  # No expectation data
        else:
            if job_salary_min <= cv_salary <= job_salary_max:
                score = 100
            elif cv_salary <= job_salary_max * 1.1:  # Within 10%
                score = 80
            elif cv_salary <= job_salary_max * 1.25:  # Within 25%
                score = 60
            else:
                score = 30
        
        # Adjust for salary flexibility
        salary_flex = dialog_findings.get("salary_flex", "negotiable")
        if salary_flex == "negotiable":
            score = min(score + 10, 100)
        
        state["context"]["compensation_score"] = score
        return state
    
    def _calculate_overall(self, state: AgentState) -> AgentState:
        """Calculate overall match percentage"""
        logger.info("Scorer: Calculating overall score")
        
        context = state["context"]
        weights = context.get("weights", {})
        
        scores = {
            "experience": context.get("experience_score", 0),
            "skills": context.get("skills_score", 0),
            "education": context.get("education_score", 0),
            "langs": context.get("languages_score", 0),
            "location": context.get("location_score", 0),
            "domain": context.get("domain_score", 0),
            "comp": context.get("compensation_score", 0)
        }
        
        # Calculate weighted average
        overall_score = sum(scores[k] * weights.get(k, 0) for k in scores)
        overall_score = round(overall_score)
        
        state["context"]["scores_pct"] = scores
        state["context"]["overall_match_pct"] = overall_score
        
        return state
    
    def _generate_verdict(self, state: AgentState) -> AgentState:
        """Generate final verdict"""
        logger.info("Scorer: Generating verdict")
        
        context = state["context"]
        overall_score = context.get("overall_match_pct", 0)
        mismatches = context.get("mismatches", [])
        verdict_thresholds = context.get("verdict_thresholds", {"fit": 75, "borderline": 60})
        
        # Check for serious risks
        serious_risks = any(
            mismatch.get("severity") == "high" and 
            mismatch.get("criterion") in ["skills", "experience", "format", "langs"]
            for mismatch in mismatches
        )
        
        # Generate verdict
        if overall_score >= verdict_thresholds["fit"] and not serious_risks:
            verdict = "подходит"
        elif overall_score >= verdict_thresholds["borderline"] or serious_risks:
            verdict = "сомнительно"
        else:
            verdict = "не подходит"
        
        state["context"]["verdict"] = verdict
        return state
    
    def _generate_summary(self, state: AgentState) -> AgentState:
        """Generate summary and evidence"""
        logger.info("Scorer: Generating summary")
        
        context = state["context"]
        job_struct = context.get("job_struct", {})
        cv_struct = context.get("cv_struct", {})
        scores = context.get("scores_pct", {})
        overall_score = context.get("overall_match_pct", 0)
        verdict = context.get("verdict", "не подходит")
        
        summary_prompt = f"""
        Generate a summary for the candidate-job match:
        
        OVERALL SCORE: {overall_score}%
        VERDICT: {verdict}
        
        SCORES:
        {json.dumps(scores, indent=2)}
        
        JOB: {job_struct.get('title', 'Unknown')}
        CANDIDATE: {cv_struct.get('name', 'Unknown')}
        
        Generate:
        1. One-liner summary
        2. Positive points (3-5 items)
        3. Risk factors (3-5 items)
        4. Unknown areas (2-3 items)
        5. Evidence quotes from job/CV (max 12 words each)
        
        Return as JSON with summary structure.
        """
        
        messages = [HumanMessage(content=summary_prompt)]
        response = self._call_llm(messages)
        
        try:
            summary = self._parse_json_response(response)
            state["context"]["summary"] = summary
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            state["context"]["summary"] = {
                "one_liner": f"Кандидат набрал {overall_score}% соответствия",
                "positives": [],
                "risks": [],
                "unknowns": []
            }
        
        return state
    
    def _finalize_scoring(self, state: AgentState) -> AgentState:
        """Finalize scoring results"""
        logger.info("Scorer: Finalizing scoring")
        
        context = state["context"]
        
        # Prepare final output
        final_output = {
            "ids": context.get("ids", {}),
            "weights": context.get("weights", {}),
            "scores_pct": context.get("scores_pct", {}),
            "overall_match_pct": context.get("overall_match_pct", 0),
            "verdict": context.get("verdict", "не подходит"),
            "summary": context.get("summary", {}),
            "evidence": context.get("evidence", {"jd": [], "cv": []}),
            "dialog_findings_used": context.get("dialog_findings", {}),
            "calc_notes": context.get("calc_notes", []),
            "version": "v1.0",
            "agent_metadata": {
                "agent_name": self.name,
                "iteration": state["iteration"],
                "tools_used": state["tools_used"]
            }
        }
        
        state["context"]["final_output"] = final_output
        state["status"] = "completed"
        
        logger.info(f"Scorer completed with {final_output['overall_match_pct']}% match")
        
        return state
    
    def _define_tools(self) -> List[Any]:
        """Define tools available to this agent"""
        return [
            # Scoring calculation tool
            # Weight adjustment tool
            # Summary generation tool
        ]

# Global instance
scorer_agent = ScorerAgent()

