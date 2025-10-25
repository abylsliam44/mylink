"""
Agent Orchestrator
Coordinates autonomous agents for the complete HR workflow
"""
from typing import Dict, Any, List, Optional
from .mismatch_detector_agent import MismatchDetectorAgent
from .question_generator_agent import QuestionGeneratorAgent
from .widget_orchestrator_agent import WidgetOrchestratorAgent
from .scorer_agent import ScorerAgent
import logging
import asyncio

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """Orchestrates autonomous agents for complete HR workflow"""
    
    def __init__(self):
        self.agents = {
            "mismatch_detector": MismatchDetectorAgent(),
            "question_generator": QuestionGeneratorAgent(),
            "widget_orchestrator": WidgetOrchestratorAgent(),
            "scorer": ScorerAgent()
        }
        self.workflows = {
            "full_analysis": self._full_analysis_workflow,
            "quick_match": self._quick_match_workflow,
            "interview_only": self._interview_only_workflow
        }
    
    async def run_workflow(self, workflow_name: str, initial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific workflow"""
        if workflow_name not in self.workflows:
            raise ValueError(f"Unknown workflow: {workflow_name}")
        
        logger.info(f"Starting workflow: {workflow_name}")
        
        try:
            result = await self.workflows[workflow_name](initial_data)
            logger.info(f"Workflow {workflow_name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Workflow {workflow_name} failed: {e}")
            return {"error": str(e), "workflow": workflow_name}
    
    async def _full_analysis_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Complete analysis workflow: mismatch detection -> questions -> interview -> scoring"""
        logger.info("Running full analysis workflow")
        
        results = {}
        
        # Step 1: Mismatch Detection
        logger.info("Step 1: Running Mismatch Detector")
        mismatch_input = {
            "context": {
                "job_text": data.get("job_text", ""),
                "cv_text": data.get("cv_text", ""),
                "hints": data.get("hints", {})
            },
            "max_iterations": 5
        }
        
        mismatch_result = mismatch_detector_agent.run(mismatch_input)
        results["mismatch_analysis"] = mismatch_result.get("context", {}).get("final_output", {})
        
        if mismatch_result.get("status") == "failed":
            return {"error": "Mismatch detection failed", "results": results}
        
        # Step 2: Question Generation
        logger.info("Step 2: Running Question Generator")
        question_input = {
            "context": {
                "job_struct": results["mismatch_analysis"].get("job_struct", {}),
                "cv_struct": results["mismatch_analysis"].get("cv_struct", {}),
                "mismatches": results["mismatch_analysis"].get("mismatches", []),
                "missing_data": results["mismatch_analysis"].get("missing_data", [])
            },
            "max_iterations": 3
        }
        
        question_result = question_generator_agent.run(question_input)
        results["questions"] = question_result.get("context", {}).get("final_output", {})
        
        if question_result.get("status") == "failed":
            return {"error": "Question generation failed", "results": results}
        
        # Step 3: Widget Orchestration (if interview data provided)
        if data.get("interview_data"):
            logger.info("Step 3: Running Widget Orchestrator")
            widget_input = {
                "context": {
                    "questions": results["questions"].get("questions", []),
                    "session_id": data.get("session_id", "unknown"),
                    "interview_data": data.get("interview_data", {})
                },
                "max_iterations": 10
            }
            
            widget_result = widget_orchestrator_agent.run(widget_input)
            results["interview"] = widget_result.get("context", {}).get("final_output", {})
            
            if widget_result.get("status") == "failed":
                return {"error": "Widget orchestration failed", "results": results}
        
        # Step 4: Scoring
        logger.info("Step 4: Running Scorer")
        scorer_input = {
            "context": {
                "job_struct": results["mismatch_analysis"].get("job_struct", {}),
                "cv_struct": results["mismatch_analysis"].get("cv_struct", {}),
                "mismatches": results["mismatch_analysis"].get("mismatches", []),
                "dialog_findings": results.get("interview", {}).get("for_scorer_payload", {}).get("dialogFindings", {}),
                "ids": data.get("ids", {}),
                "weights_mode": data.get("weights_mode", "auto"),
                "must_have_skills": data.get("must_have_skills", []),
                "verdict_thresholds": data.get("verdict_thresholds", {"fit": 75, "borderline": 60})
            },
            "max_iterations": 5
        }
        
        scorer_result = scorer_agent.run(scorer_input)
        results["scoring"] = scorer_result.get("context", {}).get("final_output", {})
        
        if scorer_result.get("status") == "failed":
            return {"error": "Scoring failed", "results": results}
        
        # Compile final result
        final_result = {
            "workflow": "full_analysis",
            "status": "completed",
            "results": results,
            "summary": {
                "mismatches_found": len(results["mismatch_analysis"].get("mismatches", [])),
                "questions_generated": len(results["questions"].get("questions", [])),
                "overall_score": results["scoring"].get("overall_match_pct", 0),
                "verdict": results["scoring"].get("verdict", "не подходит")
            }
        }
        
        return final_result
    
    async def _quick_match_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Quick match workflow: mismatch detection -> scoring (no interview)"""
        logger.info("Running quick match workflow")
        
        results = {}
        
        # Step 1: Mismatch Detection
        logger.info("Step 1: Running Mismatch Detector")
        mismatch_input = {
            "context": {
                "job_text": data.get("job_text", ""),
                "cv_text": data.get("cv_text", ""),
                "hints": data.get("hints", {})
            },
            "max_iterations": 5
        }
        
        mismatch_result = mismatch_detector_agent.run(mismatch_input)
        results["mismatch_analysis"] = mismatch_result.get("context", {}).get("final_output", {})
        
        if mismatch_result.get("status") == "failed":
            return {"error": "Mismatch detection failed", "results": results}
        
        # Step 2: Quick Scoring
        logger.info("Step 2: Running Quick Scorer")
        scorer_input = {
            "context": {
                "job_struct": results["mismatch_analysis"].get("job_struct", {}),
                "cv_struct": results["mismatch_analysis"].get("cv_struct", {}),
                "mismatches": results["mismatch_analysis"].get("mismatches", []),
                "dialog_findings": {},  # No interview data
                "ids": data.get("ids", {}),
                "weights_mode": data.get("weights_mode", "auto"),
                "must_have_skills": data.get("must_have_skills", []),
                "verdict_thresholds": data.get("verdict_thresholds", {"fit": 75, "borderline": 60})
            },
            "max_iterations": 3
        }
        
        scorer_result = scorer_agent.run(scorer_input)
        results["scoring"] = scorer_result.get("context", {}).get("final_output", {})
        
        if scorer_result.get("status") == "failed":
            return {"error": "Scoring failed", "results": results}
        
        # Compile final result
        final_result = {
            "workflow": "quick_match",
            "status": "completed",
            "results": results,
            "summary": {
                "mismatches_found": len(results["mismatch_analysis"].get("mismatches", [])),
                "overall_score": results["scoring"].get("overall_match_pct", 0),
                "verdict": results["scoring"].get("verdict", "не подходит")
            }
        }
        
        return final_result
    
    async def _interview_only_workflow(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Interview-only workflow: questions -> interview -> scoring"""
        logger.info("Running interview-only workflow")
        
        results = {}
        
        # Step 1: Question Generation
        logger.info("Step 1: Running Question Generator")
        question_input = {
            "context": {
                "job_struct": data.get("job_struct", {}),
                "cv_struct": data.get("cv_struct", {}),
                "mismatches": data.get("mismatches", []),
                "missing_data": data.get("missing_data", [])
            },
            "max_iterations": 3
        }
        
        question_result = question_generator_agent.run(question_input)
        results["questions"] = question_result.get("context", {}).get("final_output", {})
        
        if question_result.get("status") == "failed":
            return {"error": "Question generation failed", "results": results}
        
        # Step 2: Widget Orchestration
        logger.info("Step 2: Running Widget Orchestrator")
        widget_input = {
            "context": {
                "questions": results["questions"].get("questions", []),
                "session_id": data.get("session_id", "unknown"),
                "interview_data": data.get("interview_data", {})
            },
            "max_iterations": 10
        }
        
        widget_result = widget_orchestrator_agent.run(widget_input)
        results["interview"] = widget_result.get("context", {}).get("final_output", {})
        
        if widget_result.get("status") == "failed":
            return {"error": "Widget orchestration failed", "results": results}
        
        # Step 3: Scoring
        logger.info("Step 3: Running Scorer")
        scorer_input = {
            "context": {
                "job_struct": data.get("job_struct", {}),
                "cv_struct": data.get("cv_struct", {}),
                "mismatches": data.get("mismatches", []),
                "dialog_findings": results["interview"].get("for_scorer_payload", {}).get("dialogFindings", {}),
                "ids": data.get("ids", {}),
                "weights_mode": data.get("weights_mode", "auto"),
                "must_have_skills": data.get("must_have_skills", []),
                "verdict_thresholds": data.get("verdict_thresholds", {"fit": 75, "borderline": 60})
            },
            "max_iterations": 5
        }
        
        scorer_result = scorer_agent.run(scorer_input)
        results["scoring"] = scorer_result.get("context", {}).get("final_output", {})
        
        if scorer_result.get("status") == "failed":
            return {"error": "Scoring failed", "results": results}
        
        # Compile final result
        final_result = {
            "workflow": "interview_only",
            "status": "completed",
            "results": results,
            "summary": {
                "questions_generated": len(results["questions"].get("questions", [])),
                "overall_score": results["scoring"].get("overall_match_pct", 0),
                "verdict": results["scoring"].get("verdict", "не подходит")
            }
        }
        
        return final_result
    
    async def run_single_agent(self, agent_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single agent"""
        if agent_name not in self.agents:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        logger.info(f"Running single agent: {agent_name}")
        
        try:
            result = self.agents[agent_name].run(input_data)
            logger.info(f"Agent {agent_name} completed")
            return result
        except Exception as e:
            logger.error(f"Agent {agent_name} failed: {e}")
            return {"error": str(e), "agent": agent_name}
    
    def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents"""
        status = {}
        for name, agent in self.agents.items():
            status[name] = {
                "name": agent.name,
                "available": True,
                "graph_compiled": agent.graph is not None
            }
        return status

# Global instance
agent_orchestrator = AgentOrchestrator()
