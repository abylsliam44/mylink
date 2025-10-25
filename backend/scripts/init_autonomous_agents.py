#!/usr/bin/env python3
"""
Initialize Autonomous Agents System
Sets up the autonomous agents system with initial data and configuration
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.autonomous_agents import autonomous_agent_orchestrator
from app.services.autonomous_agents.integration import autonomous_agent_integration
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def init_autonomous_agents():
    """Initialize the autonomous agents system"""
    try:
        logger.info("Starting autonomous agents initialization...")
        
        # Start the orchestrator
        await autonomous_agent_orchestrator.start()
        logger.info("Autonomous agents orchestrator started")
        
        # Add initial HR knowledge to RAG system
        await add_initial_hr_knowledge()
        
        # Test the system
        await test_system()
        
        logger.info("Autonomous agents system initialized successfully!")
        
    except Exception as e:
        logger.error(f"Failed to initialize autonomous agents: {e}")
        raise


async def add_initial_hr_knowledge():
    """Add initial HR knowledge to the RAG system"""
    try:
        logger.info("Adding initial HR knowledge...")
        
        hr_knowledge = [
            {
                "category": "hiring_best_practices",
                "title": "Effective Candidate Screening",
                "content": """
                Best practices for candidate screening:
                1. Define clear job requirements and must-have skills
                2. Use structured interviews with consistent questions
                3. Focus on behavioral questions that predict job performance
                4. Check references thoroughly
                5. Consider cultural fit alongside technical skills
                6. Use multiple assessment methods (technical tests, case studies)
                7. Document all decisions with clear rationale
                """,
                "source": "hr_knowledge_base",
                "type": "hr_knowledge"
            },
            {
                "category": "interview_techniques",
                "title": "Interview Question Frameworks",
                "content": """
                Effective interview question frameworks:
                
                STAR Method Questions:
                - Tell me about a time when you had to solve a difficult technical problem
                - Describe a situation where you had to work with a difficult team member
                - Give me an example of when you had to learn a new technology quickly
                
                Technical Assessment:
                - Code review exercises
                - System design discussions
                - Problem-solving scenarios
                - Technology-specific questions
                
                Cultural Fit Questions:
                - How do you handle conflicting priorities?
                - Describe your ideal work environment
                - How do you stay updated with industry trends?
                """,
                "source": "hr_knowledge_base",
                "type": "hr_knowledge"
            },
            {
                "category": "salary_benchmarking",
                "title": "Salary Benchmarking Guidelines",
                "content": """
                Salary benchmarking best practices:
                
                1. Research market rates for the role and location
                2. Consider candidate's experience level and skills
                3. Factor in company size and industry
                4. Account for benefits and perks
                5. Be transparent about salary ranges
                6. Consider negotiation room (10-15% above initial offer)
                7. Document salary decisions for consistency
                
                Common salary ranges in Kazakhstan (2024):
                - Junior Developer: 200,000 - 400,000 KZT
                - Mid-level Developer: 400,000 - 800,000 KZT
                - Senior Developer: 800,000 - 1,500,000 KZT
                - Tech Lead: 1,200,000 - 2,000,000 KZT
                """,
                "source": "hr_knowledge_base",
                "type": "hr_knowledge"
            },
            {
                "category": "candidate_evaluation",
                "title": "Candidate Evaluation Criteria",
                "content": """
                Comprehensive candidate evaluation criteria:
                
                Technical Skills (40%):
                - Required technical competencies
                - Problem-solving ability
                - Code quality and best practices
                - Technology stack familiarity
                
                Experience (25%):
                - Relevant work experience
                - Project complexity and scope
                - Industry experience
                - Leadership experience
                
                Soft Skills (20%):
                - Communication skills
                - Team collaboration
                - Adaptability
                - Learning agility
                
                Cultural Fit (15%):
                - Values alignment
                - Work style compatibility
                - Motivation and drive
                - Long-term potential
                """,
                "source": "hr_knowledge_base",
                "type": "hr_knowledge"
            },
            {
                "category": "red_flags",
                "title": "Red Flags in Candidate Evaluation",
                "content": """
                Warning signs to watch for during candidate evaluation:
                
                Technical Red Flags:
                - Cannot explain basic concepts clearly
                - Overstates technical abilities
                - Cannot provide specific examples of work
                - Shows resistance to learning new technologies
                
                Behavioral Red Flags:
                - Speaks negatively about previous employers
                - Cannot work well with others
                - Shows lack of accountability
                - Has unrealistic salary expectations
                
                Process Red Flags:
                - Inconsistent information across interviews
                - Poor communication or follow-up
                - Unprofessional behavior
                - Lack of preparation for interviews
                """,
                "source": "hr_knowledge_base",
                "type": "hr_knowledge"
            }
        ]
        
        result = await autonomous_agent_integration.add_hr_knowledge(hr_knowledge)
        
        if result.get("success"):
            logger.info(f"Added {len(hr_knowledge)} HR knowledge documents")
        else:
            logger.warning(f"Failed to add HR knowledge: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Failed to add initial HR knowledge: {e}")


async def test_system():
    """Test the autonomous agents system"""
    try:
        logger.info("Testing autonomous agents system...")
        
        # Test knowledge base search
        search_result = await autonomous_agent_integration.search_hr_knowledge(
            query="interview best practices",
            limit=3
        )
        
        if search_result.get("success"):
            logger.info(f"Knowledge base search test passed: {len(search_result.get('results', []))} results")
        else:
            logger.warning(f"Knowledge base search test failed: {search_result.get('error')}")
        
        # Test system metrics
        metrics = await autonomous_agent_integration.get_system_metrics()
        if metrics.get("autonomous_agents"):
            logger.info("System metrics test passed")
        else:
            logger.warning("System metrics test failed")
        
        logger.info("System tests completed")
        
    except Exception as e:
        logger.error(f"System test failed: {e}")


async def main():
    """Main function"""
    try:
        await init_autonomous_agents()
        logger.info("Initialization completed successfully!")
    except Exception as e:
        logger.error(f"Initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
