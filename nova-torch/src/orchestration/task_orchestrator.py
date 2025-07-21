"""
Task Orchestrator - Intelligent Task Routing and Management
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Analyzes tasks and assigns them to optimal agents based on capabilities and workload
"""

import asyncio
import uuid
import time
import json
import logging
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from communication.dragonfly_client import DragonflyClient, NovaMessage
from orchestration.agent_registry import AgentRegistry, AgentInfo

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5


@dataclass
class TaskSpec:
    """Specification for a task to be executed"""
    task_id: str
    title: str
    description: str
    task_type: str
    priority: TaskPriority = TaskPriority.NORMAL
    required_skills: List[str] = field(default_factory=list)
    preferred_agent: Optional[str] = None
    max_duration: Optional[int] = None  # seconds
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    deadline: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "priority": self.priority.value,
            "required_skills": json.dumps(self.required_skills),
            "preferred_agent": self.preferred_agent,
            "max_duration": self.max_duration,
            "dependencies": json.dumps(self.dependencies),
            "context": json.dumps(self.context),
            "deadline": self.deadline,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskSpec':
        """Create from stored dictionary"""
        return cls(
            task_id=data["task_id"],
            title=data["title"],
            description=data["description"],
            task_type=data["task_type"],
            priority=TaskPriority(data.get("priority", TaskPriority.NORMAL.value)),
            required_skills=json.loads(data.get("required_skills", "[]")),
            preferred_agent=data.get("preferred_agent"),
            max_duration=data.get("max_duration"),
            dependencies=json.loads(data.get("dependencies", "[]")),
            context=json.loads(data.get("context", "{}")),
            deadline=data.get("deadline"),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )


@dataclass
class TaskAnalysis:
    """Analysis of task requirements and complexity"""
    complexity_score: float  # 0-1 scale
    estimated_duration: int  # seconds
    required_skills: List[str]
    skill_weights: Dict[str, float]  # skill -> importance weight
    agent_requirements: Dict[str, Any]
    can_be_parallelized: bool
    requires_collaboration: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "complexity_score": self.complexity_score,
            "estimated_duration": self.estimated_duration,
            "required_skills": self.required_skills,
            "skill_weights": self.skill_weights,
            "agent_requirements": self.agent_requirements,
            "can_be_parallelized": self.can_be_parallelized,
            "requires_collaboration": self.requires_collaboration
        }


@dataclass
class TaskAssignment:
    """Assignment of a task to an agent"""
    task_id: str
    agent_id: str
    assigned_at: float
    status: TaskStatus
    progress: float = 0.0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "assigned_at": str(self.assigned_at),
            "status": self.status.value,
            "progress": str(self.progress),
            "result": json.dumps(self.result) if self.result else "",
            "error": self.error or "",
            "started_at": str(self.started_at) if self.started_at else "",
            "completed_at": str(self.completed_at) if self.completed_at else ""
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskAssignment':
        return cls(
            task_id=data["task_id"],
            agent_id=data["agent_id"],
            assigned_at=float(data["assigned_at"]),
            status=TaskStatus(data["status"]),
            progress=float(data["progress"]),
            result=json.loads(data["result"]) if data["result"] else None,
            error=data["error"] if data["error"] else None,
            started_at=float(data["started_at"]) if data["started_at"] else None,
            completed_at=float(data["completed_at"]) if data["completed_at"] else None
        )


class TaskAnalyzer:
    """Analyzes tasks to extract requirements and complexity"""
    
    # Skill keywords for automatic detection
    SKILL_KEYWORDS = {
        "python": ["python", "django", "flask", "fastapi", "pandas", "numpy"],
        "javascript": ["javascript", "js", "node", "react", "vue", "angular"],
        "testing": ["test", "testing", "pytest", "unittest", "qa", "quality"],
        "database": ["database", "sql", "postgresql", "mysql", "mongodb"],
        "devops": ["deploy", "deployment", "docker", "kubernetes", "aws", "ci/cd"],
        "security": ["security", "auth", "authentication", "encryption", "vulnerability"],
        "ui": ["ui", "ux", "interface", "frontend", "css", "html", "design"],
        "api": ["api", "rest", "graphql", "endpoint", "backend", "server"],
        "data": ["data", "analysis", "ml", "machine learning", "analytics"],
        "documentation": ["doc", "documentation", "readme", "guide", "manual"]
    }
    
    # Complexity indicators
    COMPLEXITY_INDICATORS = {
        "high": ["complex", "difficult", "advanced", "sophisticated", "intricate"],
        "medium": ["moderate", "standard", "typical", "regular", "normal"],
        "low": ["simple", "basic", "easy", "straightforward", "quick"]
    }
    
    def analyze_task(self, task: TaskSpec) -> TaskAnalysis:
        """Analyze a task to determine requirements and complexity"""
        text = f"{task.title} {task.description}".lower()
        
        # Detect required skills
        detected_skills = self._detect_skills(text)
        required_skills = list(set(task.required_skills + detected_skills))
        
        # Calculate skill weights
        skill_weights = self._calculate_skill_weights(text, required_skills)
        
        # Determine complexity
        complexity_score = self._calculate_complexity(text, task.task_type)
        
        # Estimate duration
        estimated_duration = self._estimate_duration(complexity_score, required_skills)
        
        # Check for collaboration needs
        requires_collaboration = self._requires_collaboration(text, complexity_score)
        
        # Check if parallelizable
        can_be_parallelized = self._can_be_parallelized(text, task.task_type)
        
        return TaskAnalysis(
            complexity_score=complexity_score,
            estimated_duration=estimated_duration,
            required_skills=required_skills,
            skill_weights=skill_weights,
            agent_requirements={"min_success_rate": 0.7 if complexity_score > 0.7 else 0.5},
            can_be_parallelized=can_be_parallelized,
            requires_collaboration=requires_collaboration
        )
    
    def _detect_skills(self, text: str) -> List[str]:
        """Detect required skills from task text"""
        detected = []
        for skill, keywords in self.SKILL_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                detected.append(skill)
        return detected
    
    def _calculate_skill_weights(self, text: str, skills: List[str]) -> Dict[str, float]:
        """Calculate importance weights for each skill"""
        weights = {}
        for skill in skills:
            # Count keyword occurrences
            count = sum(1 for keyword in self.SKILL_KEYWORDS.get(skill, []) 
                       if keyword in text)
            weights[skill] = min(count * 0.3, 1.0)  # Cap at 1.0
        return weights
    
    def _calculate_complexity(self, text: str, task_type: str) -> float:
        """Calculate complexity score (0-1)"""
        score = 0.5  # Base score
        
        # Adjust based on complexity indicators
        for level, indicators in self.COMPLEXITY_INDICATORS.items():
            if any(indicator in text for indicator in indicators):
                if level == "high":
                    score = max(score, 0.8)
                elif level == "medium":
                    score = max(score, 0.5)
                else:  # low
                    score = min(score, 0.3)
        
        # Adjust based on task type
        type_multipliers = {
            "implementation": 0.7,
            "testing": 0.4,
            "debugging": 0.8,
            "research": 0.6,
            "documentation": 0.3,
            "deployment": 0.5
        }
        
        if task_type in type_multipliers:
            score *= type_multipliers[task_type]
        
        return max(0.1, min(1.0, score))
    
    def _estimate_duration(self, complexity: float, skills: List[str]) -> int:
        """Estimate task duration in seconds"""
        base_duration = 1800  # 30 minutes
        
        # Adjust for complexity
        duration = base_duration * (1 + complexity * 2)
        
        # Adjust for number of skills required
        skill_factor = min(len(skills) * 0.2, 1.0)
        duration *= (1 + skill_factor)
        
        return int(duration)
    
    def _requires_collaboration(self, text: str, complexity: float) -> bool:
        """Determine if task requires multiple agents"""
        collaboration_keywords = [
            "team", "collaborate", "coordination", "multiple", "together",
            "review", "pair", "discussion", "meeting"
        ]
        
        has_keywords = any(keyword in text for keyword in collaboration_keywords)
        is_complex = complexity > 0.7
        
        return has_keywords or is_complex
    
    def _can_be_parallelized(self, text: str, task_type: str) -> bool:
        """Determine if task can be split into parallel subtasks"""
        parallel_keywords = [
            "multiple", "batch", "parallel", "concurrent", "simultaneous",
            "independent", "separate", "split"
        ]
        
        parallelizable_types = ["testing", "data_processing", "deployment"]
        
        has_keywords = any(keyword in text for keyword in parallel_keywords)
        is_parallelizable_type = task_type in parallelizable_types
        
        return has_keywords or is_parallelizable_type


class TaskOrchestrator:
    """
    Intelligent task orchestration system
    Analyzes tasks and assigns them to optimal agents
    """
    
    def __init__(self, dragonfly_client: DragonflyClient, agent_registry: AgentRegistry):
        """Initialize task orchestrator"""
        self.client = dragonfly_client
        self.registry = agent_registry
        self.analyzer = TaskAnalyzer()
        
        # Stream names
        self.task_queue = "nova.torch.tasks.queue"
        self.active_tasks = "nova.torch.tasks.active"
        self.completed_tasks = "nova.torch.tasks.completed"
        self.failed_tasks = "nova.torch.tasks.failed"
        
        # Task tracking
        self.assignments_key = "nova.torch.assignments"
        self.task_locks_prefix = "nova.torch.locks:task:"
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Performance metrics
        self.metrics = {
            "tasks_processed": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "avg_assignment_time": 0.0,
            "avg_completion_time": 0.0
        }
    
    async def submit_task(self, task: TaskSpec) -> str:
        """Submit a task for orchestration"""
        try:
            # Analyze task
            analysis = self.analyzer.analyze_task(task)
            
            # Add to queue
            task_data = task.to_dict()
            task_data["analysis"] = analysis.to_dict()
            task_data["submitted_at"] = str(time.time())
            
            msg_id = self.client.add_to_stream(self.task_queue, NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender="orchestrator",
                target="task_queue",
                message_type="task_submitted",
                payload=task_data
            ))
            
            if msg_id:
                logger.info(f"Task {task.task_id} submitted for orchestration")
                return msg_id
            else:
                logger.error(f"Failed to submit task {task.task_id}")
                return ""
                
        except Exception as e:
            logger.error(f"Error submitting task {task.task_id}: {e}")
            return ""
    
    async def assign_task(self, task: TaskSpec, analysis: TaskAnalysis) -> Optional[TaskAssignment]:
        """Assign a task to the optimal agent"""
        start_time = time.time()
        
        try:
            # Check dependencies
            if not await self._check_dependencies(task.dependencies):
                logger.info(f"Task {task.task_id} waiting for dependencies")
                return None
            
            # Find optimal agent
            agent = await self._find_optimal_agent(task, analysis)
            if not agent:
                logger.warning(f"No suitable agent found for task {task.task_id}")
                return None
            
            # Acquire task lock
            lock_key = f"{self.task_locks_prefix}{task.task_id}"
            if not self._acquire_lock(lock_key):
                logger.debug(f"Task {task.task_id} already being processed")
                return None
            
            try:
                # Create assignment
                assignment = TaskAssignment(
                    task_id=task.task_id,
                    agent_id=agent.agent_id,
                    assigned_at=time.time(),
                    status=TaskStatus.ASSIGNED
                )
                
                # Store assignment
                self.client.client.hset(
                    self.assignments_key, task.task_id, 
                    json.dumps(assignment.to_dict())
                )
                
                # Send task to agent
                success = await self._send_task_to_agent(agent.agent_id, task, analysis)
                if success:
                    # Update assignment status
                    assignment.status = TaskStatus.ACTIVE
                    assignment.started_at = time.time()
                    
                    self.client.client.hset(
                        self.assignments_key, task.task_id,
                        json.dumps(assignment.to_dict())
                    )
                    
                    # Move to active tasks
                    self.client.add_to_stream(self.active_tasks, NovaMessage(
                        id=uuid.uuid4().hex,
                        timestamp=time.time(),
                        sender="orchestrator",
                        target="active_tasks",
                        message_type="task_assigned",
                        payload={
                            "task_id": task.task_id,
                            "agent_id": agent.agent_id,
                            "assigned_at": assignment.assigned_at
                        }
                    ))
                    
                    # Update metrics
                    assignment_time = time.time() - start_time
                    self.metrics["tasks_processed"] += 1
                    self.metrics["avg_assignment_time"] = (
                        (self.metrics["avg_assignment_time"] * (self.metrics["tasks_processed"] - 1) + assignment_time) / 
                        self.metrics["tasks_processed"]
                    )
                    
                    logger.info(f"Task {task.task_id} assigned to agent {agent.agent_id}")
                    return assignment
                else:
                    logger.error(f"Failed to send task {task.task_id} to agent {agent.agent_id}")
                    return None
                    
            finally:
                # Release lock
                self._release_lock(lock_key)
                
        except Exception as e:
            logger.error(f"Error assigning task {task.task_id}: {e}")
            return None
    
    async def _find_optimal_agent(self, task: TaskSpec, analysis: TaskAnalysis) -> Optional[AgentInfo]:
        """Find the optimal agent for a task"""
        
        # Get candidate agents
        candidates = await self.registry.find_agents(
            skills=analysis.required_skills,
            available_only=True
        )
        
        if not candidates:
            return None
        
        # Score each candidate
        scored_candidates = []
        for agent in candidates:
            score = self._score_agent(agent, task, analysis)
            scored_candidates.append((agent, score))
        
        # Sort by score (highest first)
        scored_candidates.sort(key=lambda x: x[1], reverse=True)
        
        # Return best candidate
        return scored_candidates[0][0] if scored_candidates else None
    
    def _score_agent(self, agent: AgentInfo, task: TaskSpec, analysis: TaskAnalysis) -> float:
        """Score an agent's suitability for a task"""
        score = 0.0
        
        # Skill match score (40% weight)
        skill_score = 0.0
        for skill in analysis.required_skills:
            if skill in agent.skills:
                weight = analysis.skill_weights.get(skill, 1.0)
                skill_score += weight
        
        if analysis.required_skills:
            skill_score /= len(analysis.required_skills)
        
        score += skill_score * 0.4
        
        # Performance score (30% weight)
        performance_score = agent.performance.get("success_rate", 0.5)
        score += performance_score * 0.3
        
        # Availability score (20% weight)
        availability_score = 1.0 if agent.status == "idle" else 0.5
        score += availability_score * 0.2
        
        # Priority boost for preferred agent (10% weight)
        if task.preferred_agent == agent.agent_id:
            score += 0.1
        
        return score
    
    async def _send_task_to_agent(self, agent_id: str, task: TaskSpec, analysis: TaskAnalysis) -> bool:
        """Send task assignment to agent"""
        try:
            # Send via registry for proper routing
            message = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender="orchestrator",
                target=agent_id,
                message_type="task_assignment",
                payload={
                    "task": task.to_dict(),
                    "analysis": analysis.to_dict()
                }
            )
            
            # Send to agent's direct stream
            stream = f"nova.torch.agents.direct.{agent_id}"
            msg_id = self.client.add_to_stream(stream, message)
            
            return msg_id is not None
            
        except Exception as e:
            logger.error(f"Error sending task to agent {agent_id}: {e}")
            return False
    
    async def _check_dependencies(self, dependencies: List[str]) -> bool:
        """Check if all task dependencies are completed"""
        if not dependencies:
            return True
        
        for dep_id in dependencies:
            assignment_data = self.client.client.hget(self.assignments_key, dep_id)
            if not assignment_data:
                return False
            
            assignment = TaskAssignment.from_dict(json.loads(assignment_data))
            if assignment.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
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
    
    async def start_orchestration(self):
        """Start background orchestration tasks"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._orchestration_loop())
            logger.info("Task orchestration started")
    
    async def stop_orchestration(self):
        """Stop background orchestration"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Task orchestration stopped")
    
    async def _orchestration_loop(self):
        """Main orchestration loop"""
        while self._running:
            try:
                # Read pending tasks
                messages = self.client.read_stream(self.task_queue, count=10)
                
                for msg_id, message in messages:
                    if message.message_type == "task_submitted":
                        # Parse task and analysis
                        task_data = message.payload
                        task = TaskSpec.from_dict(task_data)
                        analysis = TaskAnalysis(**task_data["analysis"])
                        
                        # Attempt assignment
                        assignment = await self.assign_task(task, analysis)
                        
                        # If assignment failed, leave in queue for retry
                        if assignment is None:
                            continue
                
                # Check for completed/failed tasks
                await self._process_task_updates()
                
                # Brief pause before next iteration
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in orchestration loop: {e}")
                await asyncio.sleep(5)
    
    async def _process_task_updates(self):
        """Process task completion and failure updates"""
        # This would be called by agents reporting task completion
        # For now, it's a placeholder for the completion flow
        pass
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get orchestration metrics"""
        return {
            **self.metrics,
            "queue_length": self.client.get_stream_info(self.task_queue),
            "active_tasks": self.client.get_stream_info(self.active_tasks),
            "completed_tasks": self.client.get_stream_info(self.completed_tasks)
        }