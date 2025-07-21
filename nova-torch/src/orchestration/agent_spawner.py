"""
Agent Spawner - Dynamic Agent Creation and Management
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Enables agents to spawn specialized helpers and manage the agent lifecycle
"""

import asyncio
import uuid
import time
import json
import logging
import subprocess
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from communication.dragonfly_client import DragonflyClient, NovaMessage
from orchestration.agent_registry import AgentRegistry, AgentInfo
from orchestration.agent_memory import AgentMemory, AgentMemoryConfig

logger = logging.getLogger(__name__)


class AgentLifecycleStatus(Enum):
    """Agent lifecycle status"""
    SPAWNING = "spawning"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    TERMINATING = "terminating"
    TERMINATED = "terminated"
    FAILED = "failed"


@dataclass
class AgentTemplate:
    """Template for creating specialized agents"""
    role: str
    base_skills: List[str]
    specialized_skills: List[str] = field(default_factory=list)
    memory_config: Dict[str, Any] = field(default_factory=dict)
    resource_limits: Dict[str, Any] = field(default_factory=dict)
    startup_context: Dict[str, Any] = field(default_factory=dict)
    parent_inheritance: List[str] = field(default_factory=list)  # What to inherit from parent
    
    def __post_init__(self):
        if not self.resource_limits:
            self.resource_limits = {
                "memory_mb": 512,
                "cpu_percent": 50,
                "max_tasks": 3,
                "max_lifetime": 3600  # 1 hour
            }


@dataclass
class SpawnRequest:
    """Request to spawn a new agent"""
    request_id: str
    parent_agent_id: str
    role: str
    skills: List[str]
    context: Dict[str, Any]
    urgency: str = "normal"  # low, normal, high, urgent
    max_lifetime: Optional[int] = None
    resource_limits: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "parent_agent_id": self.parent_agent_id,
            "role": self.role,
            "skills": json.dumps(self.skills),
            "context": json.dumps(self.context),
            "urgency": self.urgency,
            "max_lifetime": self.max_lifetime,
            "resource_limits": json.dumps(self.resource_limits) if self.resource_limits else ""
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpawnRequest':
        return cls(
            request_id=data["request_id"],
            parent_agent_id=data["parent_agent_id"],
            role=data["role"],
            skills=json.loads(data["skills"]),
            context=json.loads(data["context"]),
            urgency=data.get("urgency", "normal"),
            max_lifetime=data.get("max_lifetime"),
            resource_limits=json.loads(data["resource_limits"]) if data.get("resource_limits") else None
        )


@dataclass
class AgentProcess:
    """Information about a spawned agent process"""
    agent_id: str
    process_id: int
    parent_agent_id: str
    role: str
    status: AgentLifecycleStatus
    spawned_at: float
    last_heartbeat: float
    resource_usage: Dict[str, Any] = field(default_factory=dict)
    systemd_service: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "process_id": self.process_id,
            "parent_agent_id": self.parent_agent_id,
            "role": self.role,
            "status": self.status.value,
            "spawned_at": str(self.spawned_at),
            "last_heartbeat": str(self.last_heartbeat),
            "resource_usage": json.dumps(self.resource_usage),
            "systemd_service": self.systemd_service
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentProcess':
        return cls(
            agent_id=data["agent_id"],
            process_id=int(data["process_id"]),
            parent_agent_id=data["parent_agent_id"],
            role=data["role"],
            status=AgentLifecycleStatus(data["status"]),
            spawned_at=float(data["spawned_at"]),
            last_heartbeat=float(data["last_heartbeat"]),
            resource_usage=json.loads(data.get("resource_usage", "{}")),
            systemd_service=data.get("systemd_service")
        )


class AgentSpawner:
    """
    Manages dynamic agent creation and lifecycle
    """
    
    # Predefined agent templates
    AGENT_TEMPLATES = {
        "developer": AgentTemplate(
            role="developer",
            base_skills=["programming", "debugging", "testing"],
            specialized_skills=["python", "javascript", "api"],
            resource_limits={"memory_mb": 1024, "cpu_percent": 75, "max_tasks": 5}
        ),
        "tester": AgentTemplate(
            role="tester",
            base_skills=["testing", "quality_assurance", "debugging"],
            specialized_skills=["pytest", "selenium", "performance"],
            resource_limits={"memory_mb": 512, "cpu_percent": 50, "max_tasks": 3}
        ),
        "reviewer": AgentTemplate(
            role="reviewer",
            base_skills=["code_review", "security", "best_practices"],
            specialized_skills=["static_analysis", "security_audit"],
            resource_limits={"memory_mb": 256, "cpu_percent": 25, "max_tasks": 2}
        ),
        "specialist": AgentTemplate(
            role="specialist",
            base_skills=["research", "analysis", "expertise"],
            specialized_skills=[],  # Will be set dynamically
            resource_limits={"memory_mb": 2048, "cpu_percent": 100, "max_tasks": 1}
        )
    }
    
    def __init__(self, dragonfly_client: DragonflyClient, agent_registry: AgentRegistry):
        """Initialize agent spawner"""
        self.client = dragonfly_client
        self.registry = agent_registry
        
        # Stream names
        self.spawn_requests = "nova.torch.agents.spawning"
        self.termination_requests = "nova.torch.agents.terminating"
        self.scaling_decisions = "nova.torch.agents.scaling"
        
        # Process tracking
        self.processes_key = "nova.torch.spawner.processes"
        self.spawn_locks_prefix = "nova.torch.spawner.locks:"
        
        # Configuration
        self.max_agents_per_parent = 3
        self.max_total_agents = 50
        self.resource_check_interval = 30  # seconds
        self.agent_timeout = 300  # 5 minutes
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Metrics
        self.metrics = {
            "agents_spawned": 0,
            "agents_terminated": 0,
            "active_agents": 0,
            "spawn_failures": 0,
            "avg_spawn_time": 0.0
        }
    
    async def request_agent_spawn(self, request: SpawnRequest) -> Optional[str]:
        """Request spawning of a new agent"""
        try:
            # Validate request
            if not self._can_spawn_agent(request):
                logger.warning(f"Cannot spawn agent for request {request.request_id}")
                return None
            
            # Add to spawn queue
            message = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender=request.parent_agent_id,
                target="spawner",
                message_type="spawn_request",
                payload=request.to_dict()
            )
            
            msg_id = self.client.add_to_stream(self.spawn_requests, message)
            if msg_id:
                logger.info(f"Spawn request {request.request_id} queued")
                return msg_id
            
            return None
            
        except Exception as e:
            logger.error(f"Error requesting agent spawn: {e}")
            return None
    
    async def spawn_agent(self, request: SpawnRequest) -> Optional[str]:
        """Spawn a new agent"""
        start_time = time.time()
        
        try:
            # Generate agent ID
            agent_id = f"{request.role}-{uuid.uuid4().hex[:8]}"
            
            # Acquire spawn lock
            lock_key = f"{self.spawn_locks_prefix}{agent_id}"
            if not self._acquire_lock(lock_key):
                logger.warning(f"Failed to acquire spawn lock for {agent_id}")
                return None
            
            try:
                # Get agent template
                template = self._get_agent_template(request.role, request.skills)
                
                # Create agent configuration
                config = await self._create_agent_config(agent_id, request, template)
                
                # Spawn agent process
                process_info = await self._spawn_agent_process(agent_id, config)
                if not process_info:
                    return None
                
                # Initialize agent memory with parent context
                await self._initialize_agent_memory(agent_id, request, template)
                
                # Register agent
                agent_info = AgentInfo(
                    agent_id=agent_id,
                    role=request.role,
                    skills=request.skills,
                    status="initializing",
                    last_heartbeat=time.time(),
                    session_id=f"spawn-{int(time.time())}"
                )
                
                success = await self.registry.register_agent(agent_info)
                if not success:
                    logger.error(f"Failed to register spawned agent {agent_id}")
                    await self._terminate_agent_process(process_info)
                    return None
                
                # Track spawned agent
                self.client.client.hset(
                    self.processes_key, agent_id,
                    json.dumps(process_info.to_dict())
                )
                
                # Update metrics
                spawn_time = time.time() - start_time
                self.metrics["agents_spawned"] += 1
                self.metrics["active_agents"] += 1
                self.metrics["avg_spawn_time"] = (
                    (self.metrics["avg_spawn_time"] * (self.metrics["agents_spawned"] - 1) + spawn_time) /
                    self.metrics["agents_spawned"]
                )
                
                # Log spawn event
                self.client.add_to_stream(self.scaling_decisions, NovaMessage(
                    id=uuid.uuid4().hex,
                    timestamp=time.time(),
                    sender="spawner",
                    target="scaling",
                    message_type="agent_spawned",
                    payload={
                        "agent_id": agent_id,
                        "parent_id": request.parent_agent_id,
                        "role": request.role,
                        "spawn_time": spawn_time
                    }
                ))
                
                logger.info(f"Agent {agent_id} spawned successfully in {spawn_time:.2f}s")
                return agent_id
                
            finally:
                self._release_lock(lock_key)
                
        except Exception as e:
            logger.error(f"Error spawning agent: {e}")
            self.metrics["spawn_failures"] += 1
            return None
    
    async def terminate_agent(self, agent_id: str, reason: str = "normal") -> bool:
        """Terminate a spawned agent"""
        try:
            # Get process info
            process_data = self.client.client.hget(self.processes_key, agent_id)
            if not process_data:
                logger.warning(f"No process info found for agent {agent_id}")
                return False
            
            process_info = AgentProcess.from_dict(json.loads(process_data))
            
            # Update status
            process_info.status = AgentLifecycleStatus.TERMINATING
            self.client.client.hset(
                self.processes_key, agent_id,
                json.dumps(process_info.to_dict())
            )
            
            # Terminate process
            success = await self._terminate_agent_process(process_info)
            
            # Clean up memory
            await self._cleanup_agent_memory(agent_id)
            
            # Unregister agent
            await self.registry.unregister_agent(agent_id)
            
            # Remove from tracking
            self.client.client.hdel(self.processes_key, agent_id)
            
            # Update metrics
            if success:
                self.metrics["agents_terminated"] += 1
                self.metrics["active_agents"] -= 1
                
                # Log termination event
                self.client.add_to_stream(self.termination_requests, NovaMessage(
                    id=uuid.uuid4().hex,
                    timestamp=time.time(),
                    sender="spawner",
                    target="termination",
                    message_type="agent_terminated",
                    payload={
                        "agent_id": agent_id,
                        "reason": reason,
                        "lifetime": time.time() - process_info.spawned_at
                    }
                ))
                
                logger.info(f"Agent {agent_id} terminated successfully")
            
            return success
            
        except Exception as e:
            logger.error(f"Error terminating agent {agent_id}: {e}")
            return False
    
    def _can_spawn_agent(self, request: SpawnRequest) -> bool:
        """Check if agent can be spawned based on limits"""
        
        # Check total agent limit
        if self.metrics["active_agents"] >= self.max_total_agents:
            logger.warning("Maximum total agents reached")
            return False
        
        # Check per-parent limit
        parent_agents = self._get_agents_by_parent(request.parent_agent_id)
        if len(parent_agents) >= self.max_agents_per_parent:
            logger.warning(f"Maximum agents per parent reached for {request.parent_agent_id}")
            return False
        
        # Check system resources (simplified check)
        # In production, this would check actual CPU/memory usage
        if self.metrics["active_agents"] > 20:  # Rough resource threshold
            logger.warning("System resource threshold reached")
            return False
        
        return True
    
    def _get_agent_template(self, role: str, skills: List[str]) -> AgentTemplate:
        """Get agent template for role"""
        if role in self.AGENT_TEMPLATES:
            template = self.AGENT_TEMPLATES[role]
            # Customize template with requested skills
            if skills:
                template.specialized_skills = list(set(template.specialized_skills + skills))
            return template
        else:
            # Create custom template
            return AgentTemplate(
                role=role,
                base_skills=skills[:3],  # First 3 as base
                specialized_skills=skills[3:],  # Rest as specialized
            )
    
    async def _create_agent_config(self, agent_id: str, request: SpawnRequest, 
                                  template: AgentTemplate) -> Dict[str, Any]:
        """Create configuration for spawned agent"""
        config = {
            "agent_id": agent_id,
            "role": template.role,
            "skills": template.base_skills + template.specialized_skills,
            "parent_agent_id": request.parent_agent_id,
            "resource_limits": template.resource_limits,
            "startup_context": {
                **template.startup_context,
                **request.context
            },
            "max_lifetime": request.max_lifetime or template.resource_limits.get("max_lifetime", 3600)
        }
        
        return config
    
    async def _spawn_agent_process(self, agent_id: str, config: Dict[str, Any]) -> Optional[AgentProcess]:
        """Spawn the actual agent process using systemd"""
        try:
            # Create agent configuration file
            config_path = f"/etc/nova-torch/agents/{agent_id}.yaml"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            # Start systemd service
            service_name = f"nova-torch-agent@{agent_id}"
            cmd = ["systemctl", "start", service_name]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"Failed to start systemd service: {result.stderr}")
                return None
            
            # Wait briefly and check if service started
            await asyncio.sleep(2)
            
            status_cmd = ["systemctl", "is-active", service_name]
            status_result = subprocess.run(status_cmd, capture_output=True, text=True)
            
            if status_result.returncode != 0:
                logger.error(f"Agent service {service_name} failed to start")
                return None
            
            # Get process ID (simplified - in production would get from systemd)
            pid = int(time.time()) % 100000  # Mock PID for now
            
            process_info = AgentProcess(
                agent_id=agent_id,
                process_id=pid,
                parent_agent_id=config["parent_agent_id"],
                role=config["role"],
                status=AgentLifecycleStatus.SPAWNING,
                spawned_at=time.time(),
                last_heartbeat=time.time(),
                systemd_service=service_name
            )
            
            return process_info
            
        except Exception as e:
            logger.error(f"Error spawning agent process: {e}")
            return None
    
    async def _terminate_agent_process(self, process_info: AgentProcess) -> bool:
        """Terminate agent process"""
        try:
            if process_info.systemd_service:
                # Stop systemd service
                cmd = ["systemctl", "stop", process_info.systemd_service]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    logger.error(f"Failed to stop systemd service: {result.stderr}")
                    return False
                
                # Clean up configuration file
                config_path = f"/etc/nova-torch/agents/{process_info.agent_id}.yaml"
                if os.path.exists(config_path):
                    os.remove(config_path)
            
            return True
            
        except Exception as e:
            logger.error(f"Error terminating agent process: {e}")
            return False
    
    async def _initialize_agent_memory(self, agent_id: str, request: SpawnRequest, 
                                     template: AgentTemplate):
        """Initialize agent memory with parent context"""
        try:
            # Get parent agent memory
            parent_memory = self.registry._get_agent_memory(request.parent_agent_id)
            if not parent_memory:
                return
            
            # Create new agent memory
            child_memory = self.registry._get_agent_memory(agent_id)
            if not child_memory:
                return
            
            # Inherit context from parent
            if "context" in template.parent_inheritance:
                parent_context = parent_memory.get_current_context()
                for context_item in parent_context:
                    child_memory.add_context(f"inherited:{context_item}")
            
            # Inherit relationships
            if "relationships" in template.parent_inheritance:
                collaborators = parent_memory.get_collaborators()
                for collaborator in collaborators:
                    child_memory.establish_relationship(collaborator, "inherited_collaboration")
            
            # Add spawn context
            child_memory.remember_interaction("system", "spawn", {
                "parent_agent": request.parent_agent_id,
                "spawn_reason": request.context.get("reason", "task_specialization"),
                "inherited_skills": template.base_skills + template.specialized_skills
            })
            
        except Exception as e:
            logger.error(f"Error initializing agent memory: {e}")
    
    async def _cleanup_agent_memory(self, agent_id: str):
        """Clean up agent memory on termination"""
        try:
            memory = self.registry._get_agent_memory(agent_id)
            if memory:
                memory.sleep()  # Proper shutdown
                
        except Exception as e:
            logger.error(f"Error cleaning up agent memory: {e}")
    
    def _get_agents_by_parent(self, parent_id: str) -> List[str]:
        """Get list of agents spawned by parent"""
        try:
            all_processes = self.client.client.hgetall(self.processes_key)
            parent_agents = []
            
            for agent_id, process_data in all_processes.items():
                process_info = AgentProcess.from_dict(json.loads(process_data))
                if process_info.parent_agent_id == parent_id:
                    parent_agents.append(agent_id)
            
            return parent_agents
            
        except Exception as e:
            logger.error(f"Error getting agents by parent: {e}")
            return []
    
    def _acquire_lock(self, lock_key: str, timeout: int = 30) -> bool:
        """Acquire a distributed lock"""
        try:
            result = self.client.client.set(lock_key, "locked", nx=True, ex=timeout)
            return result is True
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_key}: {e}")
            return False
    
    def _release_lock(self, lock_key: str):
        """Release a distributed lock"""
        try:
            self.client.client.delete(lock_key)
        except Exception as e:
            logger.error(f"Error releasing lock {lock_key}: {e}")
    
    async def start_spawner(self):
        """Start background spawner tasks"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._spawner_loop())
            logger.info("Agent spawner started")
    
    async def stop_spawner(self):
        """Stop background spawner"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Agent spawner stopped")
    
    async def _spawner_loop(self):
        """Main spawner loop"""
        while self._running:
            try:
                # Process spawn requests
                await self._process_spawn_requests()
                
                # Monitor agent health
                await self._monitor_agent_health()
                
                # Clean up terminated agents
                await self._cleanup_terminated_agents()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in spawner loop: {e}")
                await asyncio.sleep(10)
    
    async def _process_spawn_requests(self):
        """Process pending spawn requests"""
        try:
            messages = self.client.read_stream(self.spawn_requests, count=5)
            
            for msg_id, message in messages:
                if message.message_type == "spawn_request":
                    request = SpawnRequest.from_dict(message.payload)
                    
                    # Attempt to spawn agent
                    agent_id = await self.spawn_agent(request)
                    
                    if agent_id:
                        # Send success response to parent
                        response = NovaMessage(
                            id=uuid.uuid4().hex,
                            timestamp=time.time(),
                            sender="spawner",
                            target=request.parent_agent_id,
                            message_type="spawn_success",
                            payload={"request_id": request.request_id, "agent_id": agent_id}
                        )
                    else:
                        # Send failure response
                        response = NovaMessage(
                            id=uuid.uuid4().hex,
                            timestamp=time.time(),
                            sender="spawner",
                            target=request.parent_agent_id,
                            message_type="spawn_failure",
                            payload={"request_id": request.request_id, "reason": "spawn_failed"}
                        )
                    
                    # Send response to parent agent
                    parent_stream = f"nova.torch.agents.direct.{request.parent_agent_id}"
                    self.client.add_to_stream(parent_stream, response)
                    
        except Exception as e:
            logger.error(f"Error processing spawn requests: {e}")
    
    async def _monitor_agent_health(self):
        """Monitor health of spawned agents"""
        try:
            current_time = time.time()
            all_processes = self.client.client.hgetall(self.processes_key)
            
            for agent_id, process_data in all_processes.items():
                process_info = AgentProcess.from_dict(json.loads(process_data))
                
                # Check if agent has timed out
                if current_time - process_info.last_heartbeat > self.agent_timeout:
                    logger.warning(f"Agent {agent_id} timed out, terminating")
                    await self.terminate_agent(agent_id, "timeout")
                
                # Check if agent exceeded lifetime
                if (process_info.spawned_at + 
                    process_info.to_dict().get("max_lifetime", 3600) < current_time):
                    logger.info(f"Agent {agent_id} reached max lifetime, terminating")
                    await self.terminate_agent(agent_id, "lifetime_exceeded")
                    
        except Exception as e:
            logger.error(f"Error monitoring agent health: {e}")
    
    async def _cleanup_terminated_agents(self):
        """Clean up terminated agents"""
        try:
            all_processes = self.client.client.hgetall(self.processes_key)
            
            for agent_id, process_data in all_processes.items():
                process_info = AgentProcess.from_dict(json.loads(process_data))
                
                if process_info.status == AgentLifecycleStatus.TERMINATED:
                    # Remove from tracking
                    self.client.client.hdel(self.processes_key, agent_id)
                    logger.debug(f"Cleaned up terminated agent {agent_id}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up terminated agents: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get spawner metrics"""
        return {
            **self.metrics,
            "spawn_queue_length": self.client.get_stream_info(self.spawn_requests),
            "active_processes": len(self.client.client.hgetall(self.processes_key))
        }