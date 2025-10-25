"""
Event Bus for Autonomous Agents
Event-driven communication between agents
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Callable, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import uuid
from collections import defaultdict

from .agent_state import EventType, AgentType

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Event structure"""
    event_id: str
    event_type: EventType
    source_agent_id: Optional[str]
    target_agent_id: Optional[str]
    payload: Dict[str, Any]
    timestamp: datetime
    priority: int = 0  # Higher number = higher priority
    retry_count: int = 0
    max_retries: int = 3
    correlation_id: Optional[str] = None  # For tracking related events
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_agent_id": self.source_agent_id,
            "target_agent_id": self.target_agent_id,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            event_id=data["event_id"],
            event_type=EventType(data["event_type"]),
            source_agent_id=data.get("source_agent_id"),
            target_agent_id=data.get("target_agent_id"),
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=data.get("priority", 0),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
            correlation_id=data.get("correlation_id")
        )


class EventBus:
    """Event bus for agent communication"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, Set[str]] = defaultdict(set)
        self._agent_handlers: Dict[str, Callable[[Event], Any]] = {}
        self._event_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._dead_letter_queue: List[Event] = []
        self._is_running = False
        self._processing_task: Optional[asyncio.Task] = None
        self._metrics = {
            "events_processed": 0,
            "events_failed": 0,
            "events_retried": 0,
            "events_dlq": 0
        }
    
    async def start(self):
        """Start event bus processing"""
        if self._is_running:
            return
        
        self._is_running = True
        self._processing_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")
    
    async def stop(self):
        """Stop event bus processing"""
        self._is_running = False
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
        logger.info("Event bus stopped")
    
    def subscribe(self, agent_id: str, event_types: List[EventType], handler: Callable[[Event], Any]):
        """Subscribe agent to event types"""
        for event_type in event_types:
            self._subscribers[event_type].add(agent_id)
        self._agent_handlers[agent_id] = handler
        logger.info(f"Agent {agent_id} subscribed to {[et.value for et in event_types]}")
    
    def unsubscribe(self, agent_id: str, event_types: List[EventType]):
        """Unsubscribe agent from event types"""
        for event_type in event_types:
            self._subscribers[event_type].discard(agent_id)
        if agent_id in self._agent_handlers:
            del self._agent_handlers[agent_id]
        logger.info(f"Agent {agent_id} unsubscribed from {[et.value for et in event_types]}")
    
    async def publish(self, event: Event):
        """Publish event to bus"""
        # Add to priority queue (negative priority for max-heap behavior)
        await self._event_queue.put((-event.priority, event.timestamp.timestamp(), event))
        logger.debug(f"Published event {event.event_id} of type {event.event_type.value}")
    
    async def publish_simple(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        source_agent_id: Optional[str] = None,
        target_agent_id: Optional[str] = None,
        priority: int = 0,
        correlation_id: Optional[str] = None
    ):
        """Publish simple event"""
        event = Event(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            payload=payload,
            timestamp=datetime.utcnow(),
            priority=priority,
            correlation_id=correlation_id
        )
        await self.publish(event)
    
    async def _process_events(self):
        """Process events from queue"""
        while self._is_running:
            try:
                # Get event from queue (with timeout to allow checking _is_running)
                _, _, event = await asyncio.wait_for(
                    self._event_queue.get(), 
                    timeout=1.0
                )
                
                await self._handle_event(event)
                self._metrics["events_processed"] += 1
                
            except asyncio.TimeoutError:
                # Normal timeout, continue loop
                continue
            except Exception as e:
                logger.error(f"Error processing events: {e}")
                await asyncio.sleep(1)
    
    async def _handle_event(self, event: Event):
        """Handle single event"""
        try:
            # Get subscribers for this event type
            subscribers = self._subscribers.get(event.event_type, set())
            
            if not subscribers:
                logger.warning(f"No subscribers for event type {event.event_type.value}")
                return
            
            # If target_agent_id is specified, only send to that agent
            if event.target_agent_id:
                if event.target_agent_id in subscribers:
                    await self._deliver_to_agent(event, event.target_agent_id)
                else:
                    logger.warning(f"Target agent {event.target_agent_id} not subscribed to {event.event_type.value}")
            else:
                # Send to all subscribers
                tasks = []
                for agent_id in subscribers:
                    task = asyncio.create_task(self._deliver_to_agent(event, agent_id))
                    tasks.append(task)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
        except Exception as e:
            logger.error(f"Error handling event {event.event_id}: {e}")
            await self._handle_event_failure(event, str(e))
    
    async def _deliver_to_agent(self, event: Event, agent_id: str):
        """Deliver event to specific agent"""
        try:
            handler = self._agent_handlers.get(agent_id)
            if not handler:
                logger.warning(f"No handler for agent {agent_id}")
                return
            
            # Call handler
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                handler(event)
                
            logger.debug(f"Delivered event {event.event_id} to agent {agent_id}")
            
        except Exception as e:
            logger.error(f"Error delivering event {event.event_id} to agent {agent_id}: {e}")
            await self._handle_event_failure(event, str(e))
    
    async def _handle_event_failure(self, event: Event, error: str):
        """Handle event processing failure"""
        event.retry_count += 1
        self._metrics["events_failed"] += 1
        
        if event.retry_count < event.max_retries:
            # Retry with exponential backoff
            delay = min(2 ** event.retry_count, 60)  # Max 60 seconds
            await asyncio.sleep(delay)
            await self.publish(event)
            self._metrics["events_retried"] += 1
            logger.info(f"Retrying event {event.event_id} (attempt {event.retry_count})")
        else:
            # Move to dead letter queue
            self._dead_letter_queue.append(event)
            self._metrics["events_dlq"] += 1
            logger.error(f"Event {event.event_id} moved to DLQ after {event.max_retries} retries")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get event bus metrics"""
        return {
            **self._metrics,
            "queue_size": self._event_queue.qsize(),
            "dlq_size": len(self._dead_letter_queue),
            "subscribers": {
                event_type.value: list(agents) 
                for event_type, agents in self._subscribers.items()
            }
        }
    
    def get_dead_letter_queue(self) -> List[Dict[str, Any]]:
        """Get dead letter queue events"""
        return [event.to_dict() for event in self._dead_letter_queue]
    
    def clear_dead_letter_queue(self):
        """Clear dead letter queue"""
        self._dead_letter_queue.clear()
        logger.info("Dead letter queue cleared")


# Global event bus instance
event_bus = EventBus()
