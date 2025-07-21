"""
Agent Registry with Heartbeat Mechanism
Author: Torch (pm-torch)
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Manages agent registration, discovery, and health monitoring
"""

import time
import json
import logging
import asyncio
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from communication.dragonfly_client import DragonflyClient
from orchestration.agent_memory import AgentMemory, AgentMemoryConfig

logger = logging.getLogger(__name__)


@dataclass
class AgentInfo:
    """Information about a registered agent"""
    agent_id: str
    role: str
    skills: List[str]
    status: str  # active, busy, idle, offline
    last_heartbeat: float
    current_task: Optional[str] = None
    session_id: Optional[str] = None
    performance: Dict[str, float] = None
    
    def __post_init__(self):
        if self.performance is None:
            self.performance = {
                "tasks_completed": 0,
                "success_rate": 0.0,
                "avg_completion_time": 0.0
            }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "skills": json.dumps(self.skills),
            "status": self.status,
            "last_heartbeat": str(self.last_heartbeat),
            "current_task": self.current_task or "",
            "session_id": self.session_id or "",
            "performance": json.dumps(self.performance)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentInfo':
        """Create from stored dictionary"""
        return cls(
            agent_id=data.get("agent_id", ""),
            role=data.get("role", ""),
            skills=json.loads(data.get("skills", "[]")),
            status=data.get("status", "offline"),
            last_heartbeat=float(data.get("last_heartbeat", 0)),
            current_task=data.get("current_task") or None,
            session_id=data.get("session_id") or None,
            performance=json.loads(data.get("performance", "{}"))
        )


class AgentRegistry:
    """
    Distributed agent registry using DragonflyDB
    Handles registration, discovery, and health monitoring
    """
    
    def __init__(self, dragonfly_client: DragonflyClient, 
                 heartbeat_timeout: int = 120,
                 enable_memory: bool = True):
        """
        Initialize agent registry
        
        Args:
            dragonfly_client: Connected DragonflyDB client
            heartbeat_timeout: Seconds before agent considered offline
            enable_memory: Enable bloom-memory integration
        """
        self.client = dragonfly_client
        self.heartbeat_timeout = heartbeat_timeout
        self.enable_memory = enable_memory
        
        # Registry keys
        self.registry_key = "nova:torch:registry:agents"
        self.role_index_prefix = "nova:torch:registry:role:"
        self.skill_index_prefix = "nova:torch:registry:skill:"
        self.heartbeat_stream = "nova:torch:registry:heartbeats"
        
        # Memory configuration
        self.memory_config = AgentMemoryConfig(
            dragonfly_host=dragonfly_client.host,
            dragonfly_port=dragonfly_client.port,
            enable_persistence=enable_memory
        )
        
        # Agent memories cache
        self._agent_memories: Dict[str, AgentMemory] = {}
        
        # Background task tracking
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    def _get_agent_memory(self, agent_id: str) -> Optional[AgentMemory]:
        """Get or create agent memory instance"""
        if not self.enable_memory:
            return None
            
        if agent_id not in self._agent_memories:
            self._agent_memories[agent_id] = AgentMemory(agent_id, self.memory_config)
            
        return self._agent_memories[agent_id]
    
    async def register_agent(self, agent_info: AgentInfo) -> bool:
        """
        Register a new agent or update existing
        
        Args:
            agent_info: Agent information
            
        Returns:
            True if successful
        """
        try:
            # Store agent info
            agent_data = agent_info.to_dict()
            self.client.client.hset(self.registry_key, agent_info.agent_id, json.dumps(agent_data))
            
            # Update role index
            role_key = f"{self.role_index_prefix}{agent_info.role}"
            self.client.client.sadd(role_key, agent_info.agent_id)
            
            # Update skill indices
            for skill in agent_info.skills:
                skill_key = f"{self.skill_index_prefix}{skill}"
                self.client.client.sadd(skill_key, agent_info.agent_id)
            
            # Initialize agent memory if enabled
            if self.enable_memory:
                memory = self._get_agent_memory(agent_info.agent_id)
                if memory:
                    memory.wake_up()
                    memory.set_agent_info(agent_info.role, agent_info.skills, agent_info.status)
                    memory.remember_interaction("registry", "registration", {
                        "action": "agent_registered",
                        "session_id": agent_info.session_id
                    })
            
            logger.info(f"Registered agent {agent_info.agent_id} with role {agent_info.role}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent {agent_info.agent_id}: {e}")
            return False
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent"""
        try:
            # Get agent info for cleanup
            agent_data = self.client.client.hget(self.registry_key, agent_id)
            if not agent_data:
                return True  # Already unregistered
            
            agent_info = AgentInfo.from_dict(json.loads(agent_data))
            
            # Clean up memory if enabled
            if self.enable_memory and agent_id in self._agent_memories:
                memory = self._agent_memories[agent_id]
                memory.sleep()
                del self._agent_memories[agent_id]
            
            # Remove from registry
            self.client.client.hdel(self.registry_key, agent_id)
            
            # Remove from role index
            role_key = f"{self.role_index_prefix}{agent_info.role}"
            self.client.client.srem(role_key, agent_id)
            
            # Remove from skill indices
            for skill in agent_info.skills:
                skill_key = f"{self.skill_index_prefix}{skill}"
                self.client.client.srem(skill_key, agent_id)
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to unregister agent {agent_id}: {e}")
            return False
    
    async def heartbeat(self, agent_id: str, status: str = "active", 
                       current_task: Optional[str] = None) -> bool:
        """
        Update agent heartbeat
        
        Args:
            agent_id: Agent ID
            status: Current status
            current_task: Current task ID if any
            
        Returns:
            True if successful
        """
        try:
            # Get current agent info
            agent_data = self.client.client.hget(self.registry_key, agent_id)
            if not agent_data:
                logger.warning(f"Heartbeat from unregistered agent {agent_id}")
                return False
            
            agent_info = AgentInfo.from_dict(json.loads(agent_data))
            
            # Update agent info
            agent_info.last_heartbeat = time.time()
            agent_info.status = status
            agent_info.current_task = current_task
            
            # Store updated info
            self.client.client.hset(
                self.registry_key, agent_id, 
                json.dumps(agent_info.to_dict())
            )
            
            # Log heartbeat to stream for monitoring
            heartbeat_data = {
                "agent_id": agent_id,
                "status": status,
                "timestamp": str(time.time()),
                "current_task": current_task or ""
            }
            self.client.client.xadd(self.heartbeat_stream, heartbeat_data, maxlen=10000)
            
            # Update memory if enabled
            if self.enable_memory:
                memory = self._get_agent_memory(agent_id)
                if memory:
                    memory.update_state("last_heartbeat", time.time())
                    memory.update_state("status", status)
                    if current_task:
                        memory.add_context(f"task:{current_task}", priority=5)
            
            logger.debug(f"Heartbeat from agent {agent_id}: {status}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update heartbeat for {agent_id}: {e}")
            return False
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get information about a specific agent"""
        try:
            agent_data = self.client.client.hget(self.registry_key, agent_id)
            if agent_data:
                return AgentInfo.from_dict(json.loads(agent_data))
            return None
        except Exception as e:
            logger.error(f"Failed to get agent {agent_id}: {e}")
            return None
    
    async def find_agents(self, role: Optional[str] = None, 
                         skills: Optional[List[str]] = None,
                         status: Optional[str] = None,
                         available_only: bool = True) -> List[AgentInfo]:
        """
        Find agents matching criteria
        
        Args:
            role: Filter by role
            skills: Required skills (agent must have all)
            status: Filter by status
            available_only: Only return active/idle agents
            
        Returns:
            List of matching agents
        """
        try:
            # Start with all agents or role-filtered set
            if role:
                role_key = f"{self.role_index_prefix}{role}"
                agent_ids = self.client.client.smembers(role_key)
            else:
                # Get all agent IDs from registry
                all_agents = self.client.client.hgetall(self.registry_key)
                agent_ids = set(all_agents.keys())
            
            # If skills specified, intersect with skill indices
            if skills:
                for skill in skills:
                    skill_key = f"{self.skill_index_prefix}{skill}"
                    skill_agents = self.client.client.smembers(skill_key)
                    agent_ids = agent_ids.intersection(skill_agents)
            
            # Get agent info and filter
            matching_agents = []
            current_time = time.time()
            
            for agent_id in agent_ids:
                agent_data = self.client.client.hget(self.registry_key, agent_id)
                if not agent_data:
                    continue
                    
                agent_info = AgentInfo.from_dict(json.loads(agent_data))
                
                # Check if agent is online (recent heartbeat)
                if current_time - agent_info.last_heartbeat > self.heartbeat_timeout:
                    agent_info.status = "offline"
                
                # Apply filters
                if status and agent_info.status != status:
                    continue
                    
                if available_only and agent_info.status not in ["active", "idle"]:
                    continue
                
                matching_agents.append(agent_info)
            
            # Sort by performance (success rate * availability)
            matching_agents.sort(
                key=lambda a: a.performance.get("success_rate", 0) * (1 if a.status == "idle" else 0.5),
                reverse=True
            )
            
            return matching_agents
            
        except Exception as e:
            logger.error(f"Failed to find agents: {e}")
            return []
    
    async def update_agent_performance(self, agent_id: str, 
                                     task_completed: bool,
                                     task_duration: float) -> bool:
        """Update agent performance metrics"""
        try:
            agent = await self.get_agent(agent_id)
            if not agent:
                return False
            
            # Update performance metrics
            perf = agent.performance
            perf["tasks_completed"] += 1
            
            # Update success rate (exponential moving average)
            alpha = 0.1  # Smoothing factor
            current_success = 1.0 if task_completed else 0.0
            perf["success_rate"] = (alpha * current_success + 
                                   (1 - alpha) * perf["success_rate"])
            
            # Update average completion time
            total_time = perf["avg_completion_time"] * (perf["tasks_completed"] - 1)
            perf["avg_completion_time"] = (total_time + task_duration) / perf["tasks_completed"]
            
            # Save updated agent info
            self.client.client.hset(
                self.registry_key, agent_id,
                json.dumps(agent.to_dict())
            )
            
            # Update memory if enabled
            if self.enable_memory:
                memory = self._get_agent_memory(agent_id)
                if memory:
                    memory.remember_task(
                        task_id=str(uuid.uuid4()),
                        task_type="generic",
                        result="success" if task_completed else "failure",
                        details={"duration": task_duration}
                    )
            
            logger.info(f"Updated performance for agent {agent_id}: "
                       f"success_rate={perf['success_rate']:.2f}, "
                       f"avg_time={perf['avg_completion_time']:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update performance for {agent_id}: {e}")
            return False
    
    async def get_agent_memory_summary(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get memory summary for an agent"""
        if not self.enable_memory:
            return None
            
        memory = self._get_agent_memory(agent_id)
        if memory:
            return memory.get_memory_summary()
        return None
    
    async def start_monitoring(self):
        """Start background monitoring task"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_agents())
            logger.info("Started agent registry monitoring")
    
    async def stop_monitoring(self):
        """Stop background monitoring"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped agent registry monitoring")
    
    async def _monitor_agents(self):
        """Background task to monitor agent health"""
        while self._running:
            try:
                current_time = time.time()
                all_agents = self.client.client.hgetall(self.registry_key)
                
                for agent_id, agent_data in all_agents.items():
                    agent_info = AgentInfo.from_dict(json.loads(agent_data))
                    
                    # Check if agent is offline
                    if current_time - agent_info.last_heartbeat > self.heartbeat_timeout:
                        if agent_info.status != "offline":
                            agent_info.status = "offline"
                            self.client.client.hset(
                                self.registry_key, agent_id,
                                json.dumps(agent_info.to_dict())
                            )
                            logger.warning(f"Agent {agent_id} marked offline (no heartbeat)")
                
                # Sleep before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in monitor task: {e}")
                await asyncio.sleep(5)