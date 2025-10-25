"""
Autonomous Agent Registry
Manages autonomous agents and their lifecycle
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type
from datetime import datetime

from .base_autonomous_agent import BaseAutonomousAgent
from .agent_state import AgentType, AgentStatus
from .event_bus import event_bus, Event

logger = logging.getLogger(__name__)


class AutonomousAgentRegistry:
    """Registry for managing autonomous agents"""
    
    def __init__(self):
        self._agents: Dict[str, BaseAutonomousAgent] = {}
        self._agent_types: Dict[AgentType, List[str]] = {}
        self._is_running = False
        self._startup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the agent registry"""
        if self._is_running:
            return
        
        self._is_running = True
        self._startup_task = asyncio.create_task(self._startup_agents())
        logger.info("Autonomous agent registry started")
    
    async def stop(self):
        """Stop the agent registry"""
        self._is_running = False
        
        if self._startup_task:
            self._startup_task.cancel()
            try:
                await self._startup_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all agents
        shutdown_tasks = []
        for agent in self._agents.values():
            shutdown_tasks.append(agent.shutdown())
        
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)
        
        self._agents.clear()
        self._agent_types.clear()
        logger.info("Autonomous agent registry stopped")
    
    async def register_agent(self, agent: BaseAutonomousAgent) -> str:
        """Register an autonomous agent"""
        try:
            # Initialize agent
            await agent.initialize()
            
            # Register in registry
            self._agents[agent.agent_id] = agent
            
            # Add to type index
            agent_type = agent.agent_type
            if agent_type not in self._agent_types:
                self._agent_types[agent_type] = []
            self._agent_types[agent_type].append(agent.agent_id)
            
            logger.info(f"Registered agent {agent.agent_name} ({agent.agent_id})")
            return agent.agent_id
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent.agent_name}: {e}")
            raise
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an autonomous agent"""
        try:
            agent = self._agents.get(agent_id)
            if not agent:
                logger.warning(f"Agent {agent_id} not found")
                return False
            
            # Shutdown agent
            await agent.shutdown()
            
            # Remove from registry
            del self._agents[agent_id]
            
            # Remove from type index
            for agent_type, agent_ids in self._agent_types.items():
                if agent_id in agent_ids:
                    agent_ids.remove(agent_id)
                    break
            
            logger.info(f"Unregistered agent {agent.agent_name} ({agent_id})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    def get_agent(self, agent_id: str) -> Optional[BaseAutonomousAgent]:
        """Get agent by ID"""
        return self._agents.get(agent_id)
    
    def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAutonomousAgent]:
        """Get all agents of specific type"""
        agent_ids = self._agent_types.get(agent_type, [])
        return [self._agents[agent_id] for agent_id in agent_ids if agent_id in self._agents]
    
    def get_all_agents(self) -> List[BaseAutonomousAgent]:
        """Get all registered agents"""
        return list(self._agents.values())
    
    def get_agent_count(self) -> int:
        """Get total number of agents"""
        return len(self._agents)
    
    def get_agent_count_by_type(self, agent_type: AgentType) -> int:
        """Get number of agents by type"""
        return len(self._agent_types.get(agent_type, []))
    
    async def broadcast_event(self, event: Event):
        """Broadcast event to all agents"""
        for agent in self._agents.values():
            try:
                await agent.process_event(event)
            except Exception as e:
                logger.error(f"Error broadcasting event to agent {agent.agent_id}: {e}")
    
    async def broadcast_to_type(self, event: Event, agent_type: AgentType):
        """Broadcast event to agents of specific type"""
        agents = self.get_agents_by_type(agent_type)
        for agent in agents:
            try:
                await agent.process_event(event)
            except Exception as e:
                logger.error(f"Error broadcasting event to agent {agent.agent_id}: {e}")
    
    def get_registry_metrics(self) -> Dict[str, any]:
        """Get registry metrics"""
        total_agents = len(self._agents)
        healthy_agents = sum(1 for agent in self._agents.values() if agent.is_healthy())
        
        agent_metrics = {}
        for agent_type in AgentType:
            agents = self.get_agents_by_type(agent_type)
            agent_metrics[agent_type.value] = {
                "count": len(agents),
                "healthy": sum(1 for agent in agents if agent.is_healthy()),
                "statuses": {
                    status.value: sum(1 for agent in agents if agent.state.status == status)
                    for status in AgentStatus
                }
            }
        
        return {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": total_agents - healthy_agents,
            "agent_types": agent_metrics,
            "is_running": self._is_running,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, any]]:
        """Get metrics for specific agent"""
        agent = self.get_agent(agent_id)
        if not agent:
            return None
        return agent.get_metrics()
    
    def get_all_agent_metrics(self) -> Dict[str, Dict[str, any]]:
        """Get metrics for all agents"""
        return {
            agent_id: agent.get_metrics()
            for agent_id, agent in self._agents.items()
        }
    
    async def _startup_agents(self):
        """Startup all registered agents"""
        # This method can be used to initialize default agents
        # or perform any startup tasks
        logger.info("Agent registry startup completed")
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all agents"""
        health_status = {}
        for agent_id, agent in self._agents.items():
            try:
                health_status[agent_id] = agent.is_healthy()
            except Exception as e:
                logger.error(f"Health check failed for agent {agent_id}: {e}")
                health_status[agent_id] = False
        
        return health_status
    
    async def restart_unhealthy_agents(self) -> int:
        """Restart unhealthy agents"""
        restarted_count = 0
        for agent_id, agent in self._agents.items():
            if not agent.is_healthy():
                try:
                    logger.info(f"Restarting unhealthy agent {agent_id}")
                    await agent.shutdown()
                    await agent.initialize()
                    restarted_count += 1
                except Exception as e:
                    logger.error(f"Failed to restart agent {agent_id}: {e}")
        
        return restarted_count


# Global registry instance
autonomous_agent_registry = AutonomousAgentRegistry()
