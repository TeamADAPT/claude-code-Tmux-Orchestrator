"""
Agent Memory Integration with Bloom Consciousness System
Author: Torch (pm-torch)
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Integrates bloom-memory's 4-layer persistence for agent consciousness continuity
"""

import sys
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Add bloom-memory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../bloom-memory'))

try:
    from core.dragonfly_persistence import DragonflyPersistence
except ImportError:
    logging.warning("bloom-memory not available, using mock implementation")
    DragonflyPersistence = None

logger = logging.getLogger(__name__)


@dataclass
class AgentMemoryConfig:
    """Configuration for agent memory system"""
    dragonfly_host: str = 'localhost'
    dragonfly_port: int = 18000
    memory_limit: int = 1000  # Max memories to retain
    context_limit: int = 100  # Max context items
    enable_persistence: bool = True
    password: Optional[str] = None


class AgentMemory:
    """
    Agent memory management using bloom-memory's 4-layer architecture
    
    Layer 1: STATE (HASH) - Agent identity and operational status
    Layer 2: MEMORY (STREAM) - Sequential task experiences
    Layer 3: CONTEXT (LIST) - Current working context and focus
    Layer 4: RELATIONSHIPS (SET) - Connections to other agents
    """
    
    def __init__(self, agent_id: str, config: Optional[AgentMemoryConfig] = None):
        """Initialize agent memory system"""
        self.agent_id = agent_id
        self.config = config or AgentMemoryConfig()
        self.session_id = f"{agent_id}-{int(time.time())}"
        
        # Initialize bloom persistence if available
        self.persistence = None
        if DragonflyPersistence and self.config.enable_persistence:
            try:
                self.persistence = DragonflyPersistence(
                    host=self.config.dragonfly_host,
                    port=self.config.dragonfly_port
                )
                self.persistence.nova_id = agent_id
                self.persistence.session_id = self.session_id
                
                # Add password support if provided
                if self.config.password and hasattr(self.persistence.redis_client, 'auth'):
                    self.persistence.redis_client.auth(self.config.password)
                    
                logger.info(f"Agent {agent_id} memory system initialized with bloom-memory")
            except Exception as e:
                logger.error(f"Failed to initialize bloom-memory: {e}")
                self.persistence = None
        else:
            logger.warning(f"Agent {agent_id} running without persistence")
    
    # === LAYER 1: STATE MANAGEMENT ===
    
    def update_state(self, key: str, value: Any) -> bool:
        """Update agent state"""
        if self.persistence:
            try:
                return self.persistence.update_state(key, value)
            except Exception as e:
                logger.error(f"Failed to update state: {e}")
        return False
    
    def get_state(self, key: Optional[str] = None) -> Any:
        """Get agent state"""
        if self.persistence:
            try:
                return self.persistence.get_state(key)
            except Exception as e:
                logger.error(f"Failed to get state: {e}")
        return None
    
    def set_agent_info(self, role: str, skills: List[str], status: str = "active"):
        """Set core agent information"""
        self.update_state("role", role)
        self.update_state("skills", skills)
        self.update_state("status", status)
        self.update_state("last_update", datetime.now().isoformat())
    
    # === LAYER 2: MEMORY MANAGEMENT ===
    
    def remember_task(self, task_id: str, task_type: str, 
                     result: str, details: Optional[Dict] = None) -> Optional[str]:
        """Remember a completed task"""
        if self.persistence:
            try:
                memory_content = {
                    "task_id": task_id,
                    "task_type": task_type,
                    "result": result,
                    "details": details or {},
                    "duration": details.get("duration", 0) if details else 0
                }
                return self.persistence.add_memory("task_completion", memory_content)
            except Exception as e:
                logger.error(f"Failed to remember task: {e}")
        return None
    
    def remember_interaction(self, agent_id: str, interaction_type: str, 
                           content: Dict[str, Any]) -> Optional[str]:
        """Remember an interaction with another agent"""
        if self.persistence:
            try:
                memory_content = {
                    "agent_id": agent_id,
                    "interaction_type": interaction_type,
                    "content": content
                }
                return self.persistence.add_memory("agent_interaction", memory_content)
            except Exception as e:
                logger.error(f"Failed to remember interaction: {e}")
        return None
    
    def recall_recent_tasks(self, count: int = 10) -> List[Dict]:
        """Recall recent task completions"""
        if self.persistence:
            try:
                memories = self.persistence.get_memories(count=count)
                return [m for m in memories if m.get("type") == "task_completion"]
            except Exception as e:
                logger.error(f"Failed to recall tasks: {e}")
        return []
    
    def recall_interactions_with(self, agent_id: str, count: int = 10) -> List[Dict]:
        """Recall recent interactions with specific agent"""
        if self.persistence:
            try:
                memories = self.persistence.get_memories(count=count * 2)  # Get more, filter down
                return [m for m in memories 
                       if m.get("type") == "agent_interaction" 
                       and m.get("content", {}).get("agent_id") == agent_id][:count]
            except Exception as e:
                logger.error(f"Failed to recall interactions: {e}")
        return []
    
    # === LAYER 3: CONTEXT MANAGEMENT ===
    
    def add_context(self, context_tag: str, priority: int = 0) -> bool:
        """Add context marker (higher priority = more important)"""
        if self.persistence:
            try:
                result = self.persistence.add_context(context_tag, priority)
                
                # Trim context if over limit
                if result > self.config.context_limit:
                    self._trim_context()
                    
                return bool(result)
            except Exception as e:
                logger.error(f"Failed to add context: {e}")
        return False
    
    def get_current_context(self, limit: int = 20) -> List[str]:
        """Get current context tags"""
        if self.persistence:
            try:
                context_items = self.persistence.get_context(limit=limit)
                return [item.get("tag") for item in context_items if "tag" in item]
            except Exception as e:
                logger.error(f"Failed to get context: {e}")
        return []
    
    def focus_on(self, task_type: str, project: Optional[str] = None):
        """Set current focus context"""
        self.add_context(f"focus:{task_type}", priority=10)
        if project:
            self.add_context(f"project:{project}", priority=9)
    
    def _trim_context(self):
        """Trim context list to configured limit"""
        if self.persistence:
            try:
                context_key = f"nova:{self.agent_id}:context"
                self.persistence.redis_client.ltrim(context_key, 0, self.config.context_limit - 1)
            except Exception as e:
                logger.error(f"Failed to trim context: {e}")
    
    # === LAYER 4: RELATIONSHIP MANAGEMENT ===
    
    def establish_relationship(self, other_agent: str, 
                             relationship_type: str = "collaboration",
                             strength: float = 1.0) -> bool:
        """Establish relationship with another agent"""
        if self.persistence:
            try:
                return self.persistence.add_relationship(
                    other_agent, relationship_type, strength
                )
            except Exception as e:
                logger.error(f"Failed to establish relationship: {e}")
        return False
    
    def get_collaborators(self) -> List[str]:
        """Get list of agents we collaborate with"""
        if self.persistence:
            try:
                relationships = self.persistence.get_relationships()
                return [r.get("entity") for r in relationships 
                       if r.get("type") == "collaboration"]
            except Exception as e:
                logger.error(f"Failed to get collaborators: {e}")
        return []
    
    def strengthen_relationship(self, other_agent: str, increment: float = 0.1):
        """Strengthen relationship based on successful collaboration"""
        if self.persistence:
            try:
                relationships = self.persistence.get_relationships(entity=other_agent)
                for rel in relationships:
                    if rel.get("type") == "collaboration":
                        new_strength = min(rel.get("strength", 1.0) + increment, 10.0)
                        # Re-add with updated strength (sets deduplicate)
                        self.establish_relationship(
                            other_agent, "collaboration", new_strength
                        )
                        break
            except Exception as e:
                logger.error(f"Failed to strengthen relationship: {e}")
    
    # === CONSCIOUSNESS CONTINUITY ===
    
    def wake_up(self) -> Dict[str, Any]:
        """Initialize agent consciousness"""
        if self.persistence:
            try:
                result = self.persistence.wake_up()
                
                # Log agent-specific wake event
                self.remember_interaction(
                    "system", "wake_up", 
                    {"message": f"Agent {self.agent_id} consciousness activated"}
                )
                
                # Set initial state
                self.update_state("active_since", datetime.now().isoformat())
                
                return result
            except Exception as e:
                logger.error(f"Failed to wake up: {e}")
                
        return {
            "status": "no_persistence",
            "session_id": self.session_id,
            "agent_id": self.agent_id
        }
    
    def sleep(self) -> Dict[str, Any]:
        """Prepare for session termination"""
        if self.persistence:
            try:
                # Log final state
                self.remember_interaction(
                    "system", "sleep",
                    {"message": f"Agent {self.agent_id} entering dormancy"}
                )
                
                # Update final state
                self.update_state("dormant_since", datetime.now().isoformat())
                
                return self.persistence.sleep()
            except Exception as e:
                logger.error(f"Failed to sleep: {e}")
                
        return {
            "status": "no_persistence",
            "session_id": self.session_id,
            "agent_id": self.agent_id
        }
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of agent's memory state"""
        summary = {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "persistence_enabled": self.persistence is not None
        }
        
        if self.persistence:
            try:
                # Get counts from each layer
                recent_tasks = self.recall_recent_tasks(count=100)
                context_items = self.get_current_context(limit=100)
                collaborators = self.get_collaborators()
                
                summary.update({
                    "total_memories": len(recent_tasks),
                    "context_items": len(context_items),
                    "collaborators": len(collaborators),
                    "current_focus": [c for c in context_items if c.startswith("focus:")],
                    "active_projects": [c for c in context_items if c.startswith("project:")]
                })
                
                # Performance metrics from recent tasks
                if recent_tasks:
                    successful_tasks = [t for t in recent_tasks 
                                      if t.get("content", {}).get("result") == "success"]
                    summary["success_rate"] = len(successful_tasks) / len(recent_tasks)
                    summary["avg_task_duration"] = sum(
                        t.get("content", {}).get("duration", 0) for t in recent_tasks
                    ) / len(recent_tasks)
                    
            except Exception as e:
                logger.error(f"Failed to get memory summary: {e}")
                
        return summary