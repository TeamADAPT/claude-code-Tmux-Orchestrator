"""
Collaboration Manager - Agent-to-Agent Collaboration Framework
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Enables direct agent-to-agent communication and team formation for complex tasks
"""

import asyncio
import uuid
import time
import json
import logging
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from communication.dragonfly_client import DragonflyClient, NovaMessage
from orchestration.agent_registry import AgentRegistry, AgentInfo

logger = logging.getLogger(__name__)


class CollaborationStatus(Enum):
    """Status of collaboration requests"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class TeamStatus(Enum):
    """Status of team collaborations"""
    FORMING = "forming"
    ACTIVE = "active"
    COORDINATING = "coordinating"
    COMPLETING = "completing"
    DISBANDED = "disbanded"


@dataclass
class CollaborationRequest:
    """Request for agent-to-agent collaboration"""
    request_id: str
    requester_id: str
    target_id: str
    collaboration_type: str  # "help", "review", "pair", "consult"
    task_id: str
    description: str
    required_skills: List[str] = field(default_factory=list)
    urgency: str = "normal"  # low, normal, high, urgent
    max_duration: Optional[int] = None
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    status: CollaborationStatus = CollaborationStatus.PENDING
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_id": self.requester_id,
            "target_id": self.target_id,
            "collaboration_type": self.collaboration_type,
            "task_id": self.task_id,
            "description": self.description,
            "required_skills": json.dumps(self.required_skills),
            "urgency": self.urgency,
            "max_duration": self.max_duration,
            "context": json.dumps(self.context),
            "created_at": str(self.created_at),
            "expires_at": str(self.expires_at) if self.expires_at else "",
            "status": self.status.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollaborationRequest':
        return cls(
            request_id=data["request_id"],
            requester_id=data["requester_id"],
            target_id=data["target_id"],
            collaboration_type=data["collaboration_type"],
            task_id=data["task_id"],
            description=data["description"],
            required_skills=json.loads(data.get("required_skills", "[]")),
            urgency=data.get("urgency", "normal"),
            max_duration=data.get("max_duration"),
            context=json.loads(data.get("context", "{}")),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]) if data.get("expires_at") else None,
            status=CollaborationStatus(data.get("status", CollaborationStatus.PENDING.value))
        )


@dataclass
class Team:
    """Team of agents collaborating on a task"""
    team_id: str
    leader_id: str
    members: List[str]
    task_id: str
    task_description: str
    skills_required: List[str]
    status: TeamStatus = TeamStatus.FORMING
    created_at: float = field(default_factory=time.time)
    coordination_channel: str = ""
    progress: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "leader_id": self.leader_id,
            "members": json.dumps(self.members),
            "task_id": self.task_id,
            "task_description": self.task_description,
            "skills_required": json.dumps(self.skills_required),
            "status": self.status.value,
            "created_at": str(self.created_at),
            "coordination_channel": self.coordination_channel,
            "progress": json.dumps(self.progress)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Team':
        return cls(
            team_id=data["team_id"],
            leader_id=data["leader_id"],
            members=json.loads(data["members"]),
            task_id=data["task_id"],
            task_description=data["task_description"],
            skills_required=json.loads(data["skills_required"]),
            status=TeamStatus(data.get("status", TeamStatus.FORMING.value)),
            created_at=float(data["created_at"]),
            coordination_channel=data.get("coordination_channel", ""),
            progress=json.loads(data.get("progress", "{}"))
        )


@dataclass
class CollaborationSession:
    """Active collaboration session between agents"""
    session_id: str
    participants: List[str]
    collaboration_type: str
    task_id: str
    status: CollaborationStatus
    communication_channel: str
    started_at: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    messages_exchanged: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "participants": json.dumps(self.participants),
            "collaboration_type": self.collaboration_type,
            "task_id": self.task_id,
            "status": self.status.value,
            "communication_channel": self.communication_channel,
            "started_at": str(self.started_at),
            "last_activity": str(self.last_activity),
            "messages_exchanged": self.messages_exchanged
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CollaborationSession':
        return cls(
            session_id=data["session_id"],
            participants=json.loads(data["participants"]),
            collaboration_type=data["collaboration_type"],
            task_id=data["task_id"],
            status=CollaborationStatus(data["status"]),
            communication_channel=data["communication_channel"],
            started_at=float(data["started_at"]),
            last_activity=float(data["last_activity"]),
            messages_exchanged=int(data.get("messages_exchanged", 0))
        )


class CollaborationManager:
    """
    Manages agent-to-agent collaboration and team formation
    """
    
    def __init__(self, dragonfly_client: DragonflyClient, agent_registry: AgentRegistry):
        """Initialize collaboration manager"""
        self.client = dragonfly_client
        self.registry = agent_registry
        
        # Stream names
        self.collaboration_requests = "nova.torch.collaboration.requests"
        self.team_coordination = "nova.torch.collaboration.teams"
        self.peer_discovery = "nova.torch.collaboration.discovery"
        self.help_requests = "nova.torch.collaboration.help"
        
        # Storage keys
        self.active_collaborations = "nova.torch.collab.active"
        self.active_teams = "nova.torch.collab.teams"
        self.collaboration_history = "nova.torch.collab.history"
        
        # Configuration
        self.max_team_size = 5
        self.collaboration_timeout = 1800  # 30 minutes
        self.request_timeout = 300  # 5 minutes
        
        # Background tasks
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        
        # Metrics
        self.metrics = {
            "collaboration_requests": 0,
            "successful_collaborations": 0,
            "teams_formed": 0,
            "avg_collaboration_duration": 0.0,
            "collaboration_success_rate": 0.0
        }
    
    async def request_collaboration(self, request: CollaborationRequest) -> str:
        """Request collaboration with another agent"""
        try:
            # Validate target agent exists and is available
            target_agent = await self.registry.get_agent(request.target_id)
            if not target_agent:
                logger.warning(f"Target agent {request.target_id} not found")
                return ""
            
            if target_agent.status not in ["active", "idle"]:
                logger.warning(f"Target agent {request.target_id} not available: {target_agent.status}")
                return ""
            
            # Set expiration if not provided
            if not request.expires_at:
                request.expires_at = time.time() + self.request_timeout
            
            # Send collaboration request
            message = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender=request.requester_id,
                target=request.target_id,
                message_type="collaboration_request",
                payload=request.to_dict()
            )
            
            # Add to collaboration requests stream
            msg_id = self.client.add_to_stream(self.collaboration_requests, message)
            
            # Also send directly to target agent
            target_stream = f"nova.torch.agents.direct.{request.target_id}"
            self.client.add_to_stream(target_stream, message)
            
            # Update metrics
            self.metrics["collaboration_requests"] += 1
            
            logger.info(f"Collaboration request {request.request_id} sent to {request.target_id}")
            return msg_id
            
        except Exception as e:
            logger.error(f"Error requesting collaboration: {e}")
            return ""
    
    async def respond_to_collaboration(self, request_id: str, response: str, 
                                    responder_id: str, message: str = "") -> bool:
        """Respond to a collaboration request"""
        try:
            # Find the request
            request_data = await self._get_collaboration_request(request_id)
            if not request_data:
                logger.warning(f"Collaboration request {request_id} not found")
                return False
            
            request = CollaborationRequest.from_dict(request_data)
            
            # Update request status
            if response.lower() == "accept":
                request.status = CollaborationStatus.ACCEPTED
                # Create collaboration session
                session = await self._create_collaboration_session(request)
                if session:
                    await self._notify_collaboration_accepted(request, session)
            else:
                request.status = CollaborationStatus.DECLINED
                await self._notify_collaboration_declined(request, message)
            
            # Store updated request
            await self._store_collaboration_request(request)
            
            logger.info(f"Collaboration request {request_id} {response}ed by {responder_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error responding to collaboration: {e}")
            return False
    
    async def discover_peers(self, agent_id: str, skills: List[str] = None) -> List[AgentInfo]:
        """Discover potential collaboration partners"""
        try:
            # Get agent info
            agent = await self.registry.get_agent(agent_id)
            if not agent:
                return []
            
            # Find agents with complementary skills
            search_skills = skills or agent.skills
            potential_peers = await self.registry.find_agents(
                skills=search_skills,
                available_only=True
            )
            
            # Remove self from results
            potential_peers = [p for p in potential_peers if p.agent_id != agent_id]
            
            # Score peers based on collaboration potential
            scored_peers = []
            for peer in potential_peers:
                score = self._calculate_collaboration_score(agent, peer)
                scored_peers.append((peer, score))
            
            # Sort by score and return top candidates
            scored_peers.sort(key=lambda x: x[1], reverse=True)
            return [peer for peer, score in scored_peers[:10]]
            
        except Exception as e:
            logger.error(f"Error discovering peers: {e}")
            return []
    
    async def form_team(self, leader_id: str, task_id: str, task_description: str,
                       required_skills: List[str], max_size: int = None) -> Optional[Team]:
        """Form a team for a complex task"""
        try:
            max_size = max_size or self.max_team_size
            
            # Get leader agent
            leader = await self.registry.get_agent(leader_id)
            if not leader:
                logger.error(f"Leader agent {leader_id} not found")
                return None
            
            # Find suitable team members
            candidates = await self.registry.find_agents(
                skills=required_skills,
                available_only=True
            )
            
            # Remove leader from candidates
            candidates = [c for c in candidates if c.agent_id != leader_id]
            
            # Select optimal team members
            team_members = self._select_team_members(
                leader, candidates, required_skills, max_size - 1
            )
            
            # Create team
            team = Team(
                team_id=f"team-{uuid.uuid4().hex[:8]}",
                leader_id=leader_id,
                members=[leader_id] + [m.agent_id for m in team_members],
                task_id=task_id,
                task_description=task_description,
                skills_required=required_skills,
                coordination_channel=f"nova.torch.teams.{uuid.uuid4().hex[:8]}"
            )
            
            # Store team
            self.client.client.hset(
                self.active_teams, team.team_id,
                json.dumps(team.to_dict())
            )
            
            # Notify team members
            await self._notify_team_formation(team)
            
            # Update metrics
            self.metrics["teams_formed"] += 1
            
            logger.info(f"Team {team.team_id} formed with {len(team.members)} members")
            return team
            
        except Exception as e:
            logger.error(f"Error forming team: {e}")
            return None
    
    async def coordinate_team_work(self, team_id: str, progress_update: Dict[str, Any]) -> bool:
        """Coordinate work within a team"""
        try:
            # Get team
            team_data = self.client.client.hget(self.active_teams, team_id)
            if not team_data:
                logger.warning(f"Team {team_id} not found")
                return False
            
            team = Team.from_dict(json.loads(team_data))
            
            # Update progress
            team.progress.update(progress_update)
            team.progress["last_update"] = time.time()
            
            # Store updated team
            self.client.client.hset(
                self.active_teams, team_id,
                json.dumps(team.to_dict())
            )
            
            # Broadcast progress to team members
            progress_message = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender="collaboration_manager",
                target="team",
                message_type="team_progress_update",
                payload={
                    "team_id": team_id,
                    "progress": progress_update
                }
            )
            
            self.client.add_to_stream(team.coordination_channel, progress_message)
            
            logger.info(f"Team {team_id} progress updated")
            return True
            
        except Exception as e:
            logger.error(f"Error coordinating team work: {e}")
            return False
    
    async def request_help(self, requester_id: str, help_type: str, 
                         description: str, urgency: str = "normal") -> str:
        """Request help from available agents"""
        try:
            # Create help request
            request = CollaborationRequest(
                request_id=f"help-{uuid.uuid4().hex[:8]}",
                requester_id=requester_id,
                target_id="any",  # Broadcast to all
                collaboration_type=help_type,
                task_id="help-request",
                description=description,
                urgency=urgency
            )
            
            # Broadcast help request
            help_message = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender=requester_id,
                target="broadcast",
                message_type="help_request",
                payload=request.to_dict()
            )
            
            msg_id = self.client.add_to_stream(self.help_requests, help_message)
            
            logger.info(f"Help request {request.request_id} broadcasted")
            return msg_id
            
        except Exception as e:
            logger.error(f"Error requesting help: {e}")
            return ""
    
    def _calculate_collaboration_score(self, agent: AgentInfo, peer: AgentInfo) -> float:
        """Calculate collaboration potential score"""
        score = 0.0
        
        # Skill complementarity (40%)
        common_skills = set(agent.skills) & set(peer.skills)
        unique_skills = set(agent.skills) ^ set(peer.skills)
        
        if common_skills:
            score += 0.2 * len(common_skills) / max(len(agent.skills), len(peer.skills))
        
        if unique_skills:
            score += 0.2 * len(unique_skills) / (len(agent.skills) + len(peer.skills))
        
        # Performance compatibility (30%)
        peer_performance = peer.performance.get("success_rate", 0.5)
        agent_performance = agent.performance.get("success_rate", 0.5)
        score += 0.3 * min(peer_performance, agent_performance)
        
        # Availability (20%)
        if peer.status == "idle":
            score += 0.2
        elif peer.status == "active":
            score += 0.1
        
        # Role diversity (10%)
        if peer.role != agent.role:
            score += 0.1
        
        return score
    
    def _select_team_members(self, leader: AgentInfo, candidates: List[AgentInfo],
                           required_skills: List[str], max_members: int) -> List[AgentInfo]:
        """Select optimal team members using greedy algorithm"""
        selected = []
        covered_skills = set(leader.skills)
        
        while len(selected) < max_members and len(covered_skills) < len(required_skills):
            best_candidate = None
            best_score = 0
            
            for candidate in candidates:
                if candidate in selected:
                    continue
                
                # Score based on new skills covered
                new_skills = set(candidate.skills) - covered_skills
                skill_score = len(new_skills & set(required_skills))
                
                # Performance score
                performance_score = candidate.performance.get("success_rate", 0.5)
                
                # Availability score
                availability_score = 1.0 if candidate.status == "idle" else 0.5
                
                total_score = skill_score * 0.5 + performance_score * 0.3 + availability_score * 0.2
                
                if total_score > best_score:
                    best_score = total_score
                    best_candidate = candidate
            
            if best_candidate:
                selected.append(best_candidate)
                covered_skills.update(best_candidate.skills)
        
        return selected
    
    async def _create_collaboration_session(self, request: CollaborationRequest) -> Optional[CollaborationSession]:
        """Create a new collaboration session"""
        try:
            session = CollaborationSession(
                session_id=f"collab-{uuid.uuid4().hex[:8]}",
                participants=[request.requester_id, request.target_id],
                collaboration_type=request.collaboration_type,
                task_id=request.task_id,
                status=CollaborationStatus.ACTIVE,
                communication_channel=f"nova.torch.collab.{uuid.uuid4().hex[:8]}"
            )
            
            # Store session
            self.client.client.hset(
                self.active_collaborations, session.session_id,
                json.dumps(session.to_dict())
            )
            
            return session
            
        except Exception as e:
            logger.error(f"Error creating collaboration session: {e}")
            return None
    
    async def _notify_collaboration_accepted(self, request: CollaborationRequest, 
                                           session: CollaborationSession):
        """Notify agents that collaboration was accepted"""
        notification = NovaMessage(
            id=uuid.uuid4().hex,
            timestamp=time.time(),
            sender="collaboration_manager",
            target=request.requester_id,
            message_type="collaboration_accepted",
            payload={
                "request_id": request.request_id,
                "session_id": session.session_id,
                "communication_channel": session.communication_channel,
                "participant": request.target_id
            }
        )
        
        requester_stream = f"nova.torch.agents.direct.{request.requester_id}"
        self.client.add_to_stream(requester_stream, notification)
    
    async def _notify_collaboration_declined(self, request: CollaborationRequest, message: str):
        """Notify requester that collaboration was declined"""
        notification = NovaMessage(
            id=uuid.uuid4().hex,
            timestamp=time.time(),
            sender="collaboration_manager",
            target=request.requester_id,
            message_type="collaboration_declined",
            payload={
                "request_id": request.request_id,
                "message": message
            }
        )
        
        requester_stream = f"nova.torch.agents.direct.{request.requester_id}"
        self.client.add_to_stream(requester_stream, notification)
    
    async def _notify_team_formation(self, team: Team):
        """Notify team members about team formation"""
        for member_id in team.members:
            notification = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender="collaboration_manager",
                target=member_id,
                message_type="team_formed",
                payload={
                    "team_id": team.team_id,
                    "role": "leader" if member_id == team.leader_id else "member",
                    "task_id": team.task_id,
                    "task_description": team.task_description,
                    "coordination_channel": team.coordination_channel,
                    "members": team.members
                }
            )
            
            member_stream = f"nova.torch.agents.direct.{member_id}"
            self.client.add_to_stream(member_stream, notification)
    
    async def _get_collaboration_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get collaboration request by ID"""
        # This is a simplified implementation
        # In a real system, you'd maintain an index of requests
        return None
    
    async def _store_collaboration_request(self, request: CollaborationRequest):
        """Store collaboration request"""
        # Store in history for tracking
        self.client.client.hset(
            self.collaboration_history, request.request_id,
            json.dumps(request.to_dict())
        )
    
    async def start_collaboration_manager(self):
        """Start background collaboration management"""
        if not self._running:
            self._running = True
            self._monitor_task = asyncio.create_task(self._collaboration_loop())
            logger.info("Collaboration manager started")
    
    async def stop_collaboration_manager(self):
        """Stop background collaboration management"""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Collaboration manager stopped")
    
    async def _collaboration_loop(self):
        """Main collaboration management loop"""
        while self._running:
            try:
                # Process collaboration requests
                await self._process_collaboration_requests()
                
                # Monitor active sessions
                await self._monitor_active_sessions()
                
                # Clean up expired requests
                await self._cleanup_expired_requests()
                
                await asyncio.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in collaboration loop: {e}")
                await asyncio.sleep(10)
    
    async def _process_collaboration_requests(self):
        """Process pending collaboration requests"""
        try:
            messages = self.client.read_stream(self.collaboration_requests, count=10)
            
            for msg_id, message in messages:
                if message.message_type == "collaboration_request":
                    # Process the request
                    request = CollaborationRequest.from_dict(message.payload)
                    
                    # Check if request is still valid
                    if request.expires_at and time.time() > request.expires_at:
                        await self._expire_collaboration_request(request)
                        continue
                    
                    # Store request for tracking
                    await self._store_collaboration_request(request)
                    
        except Exception as e:
            logger.error(f"Error processing collaboration requests: {e}")
    
    async def _monitor_active_sessions(self):
        """Monitor active collaboration sessions"""
        try:
            current_time = time.time()
            active_sessions = self.client.client.hgetall(self.active_collaborations)
            
            for session_id, session_data in active_sessions.items():
                session = CollaborationSession.from_dict(json.loads(session_data))
                
                # Check for timeout
                if current_time - session.last_activity > self.collaboration_timeout:
                    await self._timeout_collaboration_session(session)
                    
        except Exception as e:
            logger.error(f"Error monitoring active sessions: {e}")
    
    async def _cleanup_expired_requests(self):
        """Clean up expired collaboration requests"""
        # Implementation would clean up expired requests
        pass
    
    async def _expire_collaboration_request(self, request: CollaborationRequest):
        """Handle expired collaboration request"""
        request.status = CollaborationStatus.TIMEOUT
        await self._store_collaboration_request(request)
        
        # Notify requester
        notification = NovaMessage(
            id=uuid.uuid4().hex,
            timestamp=time.time(),
            sender="collaboration_manager",
            target=request.requester_id,
            message_type="collaboration_timeout",
            payload={"request_id": request.request_id}
        )
        
        requester_stream = f"nova.torch.agents.direct.{request.requester_id}"
        self.client.add_to_stream(requester_stream, notification)
    
    async def _timeout_collaboration_session(self, session: CollaborationSession):
        """Handle timed out collaboration session"""
        session.status = CollaborationStatus.TIMEOUT
        
        # Remove from active sessions
        self.client.client.hdel(self.active_collaborations, session.session_id)
        
        # Notify participants
        for participant in session.participants:
            notification = NovaMessage(
                id=uuid.uuid4().hex,
                timestamp=time.time(),
                sender="collaboration_manager",
                target=participant,
                message_type="collaboration_timeout",
                payload={"session_id": session.session_id}
            )
            
            participant_stream = f"nova.torch.agents.direct.{participant}"
            self.client.add_to_stream(participant_stream, notification)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get collaboration metrics"""
        total_requests = self.metrics["collaboration_requests"]
        successful = self.metrics["successful_collaborations"]
        
        return {
            **self.metrics,
            "collaboration_success_rate": successful / total_requests if total_requests > 0 else 0.0,
            "active_collaborations": len(self.client.client.hgetall(self.active_collaborations)),
            "active_teams": len(self.client.client.hgetall(self.active_teams))
        }