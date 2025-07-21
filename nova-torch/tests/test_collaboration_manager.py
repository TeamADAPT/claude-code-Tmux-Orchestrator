"""
Unit Tests for CollaborationManager
Author: Torch
Department: QA/DevOps
Project: Nova-Torch
Date: 2025-01-21

Comprehensive unit tests for agent collaboration and team formation
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from collaboration.collaboration_manager import (
    CollaborationManager, 
    CollaborationRequest, 
    CollaborationSession,
    CollaborationStatus,
    TeamFormationStrategy
)
from communication.dragonfly_client import DragonflyClient, NovaMessage
from registry.agent_registry import AgentRegistry, AgentInfo


@pytest.fixture
def mock_dragonfly_client():
    """Mock DragonflyClient for testing"""
    client = Mock(spec=DragonflyClient)
    client.send_message = AsyncMock(return_value="msg_12345")
    client.broadcast_message = AsyncMock(return_value=["msg_001", "msg_002"])
    client.listen_to_stream = AsyncMock()
    client.acknowledge_message = AsyncMock()
    client.get_stream_length = AsyncMock(return_value=0)
    client.add_to_stream = AsyncMock(return_value="stream_id_123")
    client.create_stream = AsyncMock()
    return client


@pytest.fixture
def mock_agent_registry():
    """Mock AgentRegistry for testing"""
    registry = Mock(spec=AgentRegistry)
    
    # Sample agent data for collaboration testing
    sample_agents = [
        AgentInfo(
            agent_id="dev_001",
            agent_type="developer",
            capabilities=["python", "react", "testing", "git"],
            host="localhost",
            port=8001,
            status="idle"
        ),
        AgentInfo(
            agent_id="qa_001",
            agent_type="qa", 
            capabilities=["testing", "automation", "selenium", "cypress"],
            host="localhost",
            port=8002,
            status="idle"
        ),
        AgentInfo(
            agent_id="pm_001",
            agent_type="project_manager",
            capabilities=["planning", "coordination", "reporting", "scrum"],
            host="localhost",
            port=8003,
            status="active"
        ),
        AgentInfo(
            agent_id="devops_001",
            agent_type="devops",
            capabilities=["docker", "kubernetes", "ci_cd", "monitoring"],
            host="localhost",
            port=8004,
            status="idle"
        ),
        AgentInfo(
            agent_id="dev_002",
            agent_type="developer",
            capabilities=["javascript", "vue", "node", "express"],
            host="localhost",
            port=8005,
            status="busy"
        )
    ]
    
    registry.find_agents = AsyncMock(return_value=sample_agents)
    registry.get_agent = AsyncMock(side_effect=lambda agent_id: next(
        (agent for agent in sample_agents if agent.agent_id == agent_id), None
    ))
    registry.update_agent_status = AsyncMock()
    registry.get_agent_load = AsyncMock(return_value=0.5)
    registry.get_agent_availability = AsyncMock(return_value=True)
    
    return registry


@pytest.fixture
def sample_collaboration_request():
    """Sample collaboration request for testing"""
    return CollaborationRequest(
        request_id="collab_001",
        initiator_id="dev_001",
        project_id="proj_001",
        collaboration_type="code_review",
        description="Need code review for authentication module",
        required_skills=["security", "python", "testing"],
        preferred_agent_types=["developer", "security_expert"],
        priority=7,
        estimated_duration=3600,
        deadline=time.time() + 7200,
        max_team_size=3,
        metadata={
            "pull_request": "PR-123",
            "repository": "user-auth-service",
            "branch": "feature/jwt-auth"
        }
    )


@pytest.fixture
def sample_collaboration_session():
    """Sample collaboration session for testing"""
    return CollaborationSession(
        session_id="session_001",
        request_id="collab_001",
        participants=["dev_001", "qa_001", "pm_001"],
        leader_id="pm_001",
        collaboration_type="feature_development",
        status=CollaborationStatus.ACTIVE,
        created_at=time.time(),
        project_id="proj_001"
    )


@pytest.fixture
async def collaboration_manager(mock_dragonfly_client, mock_agent_registry):
    """CollaborationManager instance for testing"""
    manager = CollaborationManager(
        dragonfly_client=mock_dragonfly_client,
        agent_registry=mock_agent_registry,
        orchestrator_id="test_orchestrator"
    )
    
    # Initialize without starting background processes
    manager._running = False
    return manager


class TestCollaborationManager:
    """Test cases for CollaborationManager"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_dragonfly_client, mock_agent_registry):
        """Test CollaborationManager initialization"""
        manager = CollaborationManager(
            dragonfly_client=mock_dragonfly_client,
            agent_registry=mock_agent_registry,
            orchestrator_id="test_orchestrator"
        )
        
        assert manager.orchestrator_id == "test_orchestrator"
        assert manager.dragonfly_client == mock_dragonfly_client
        assert manager.agent_registry == mock_agent_registry
        assert manager._running == False
        assert len(manager.collaboration_requests) == 0
        assert len(manager.collaboration_sessions) == 0
        assert manager.max_team_size == 5
        assert manager.default_collaboration_timeout == 1800
    
    @pytest.mark.asyncio
    async def test_create_collaboration_request(self, collaboration_manager, sample_collaboration_request):
        """Test collaboration request creation"""
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id=sample_collaboration_request.initiator_id,
            project_id=sample_collaboration_request.project_id,
            collaboration_type=sample_collaboration_request.collaboration_type,
            description=sample_collaboration_request.description,
            required_skills=sample_collaboration_request.required_skills,
            preferred_agent_types=sample_collaboration_request.preferred_agent_types,
            priority=sample_collaboration_request.priority,
            estimated_duration=sample_collaboration_request.estimated_duration,
            deadline=sample_collaboration_request.deadline,
            max_team_size=sample_collaboration_request.max_team_size,
            metadata=sample_collaboration_request.metadata
        )
        
        assert request_id is not None
        assert request_id in collaboration_manager.collaboration_requests
        
        created_request = collaboration_manager.collaboration_requests[request_id]
        assert created_request.initiator_id == sample_collaboration_request.initiator_id
        assert created_request.collaboration_type == sample_collaboration_request.collaboration_type
        assert created_request.status == CollaborationStatus.PENDING
        assert created_request.required_skills == sample_collaboration_request.required_skills
    
    @pytest.mark.asyncio
    async def test_get_collaboration_request(self, collaboration_manager, sample_collaboration_request):
        """Test collaboration request retrieval"""
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id=sample_collaboration_request.initiator_id,
            project_id=sample_collaboration_request.project_id,
            collaboration_type=sample_collaboration_request.collaboration_type,
            description=sample_collaboration_request.description,
            required_skills=sample_collaboration_request.required_skills
        )
        
        retrieved_request = await collaboration_manager.get_collaboration_request(request_id)
        assert retrieved_request is not None
        assert retrieved_request.request_id == request_id
        assert retrieved_request.collaboration_type == sample_collaboration_request.collaboration_type
        
        # Test non-existent request
        non_existent = await collaboration_manager.get_collaboration_request("non_existent")
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_find_suitable_collaborators(self, collaboration_manager, sample_collaboration_request, mock_agent_registry):
        """Test finding suitable agents for collaboration"""
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id=sample_collaboration_request.initiator_id,
            project_id=sample_collaboration_request.project_id,
            collaboration_type=sample_collaboration_request.collaboration_type,
            description=sample_collaboration_request.description,
            required_skills=["python", "testing"],  # Skills that exist in mock agents
            preferred_agent_types=["developer", "qa"]
        )
        
        suitable_agents = await collaboration_manager._find_suitable_collaborators(request_id)
        
        assert len(suitable_agents) > 0
        
        # Verify agents have required skills
        for agent in suitable_agents:
            has_required_skill = any(skill in agent.capabilities for skill in ["python", "testing"])
            assert has_required_skill
        
        # Verify agent registry was called with correct criteria
        mock_agent_registry.find_agents.assert_called()
    
    @pytest.mark.asyncio
    async def test_form_collaboration_team(self, collaboration_manager, sample_collaboration_request, mock_agent_registry):
        """Test team formation for collaboration"""
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id=sample_collaboration_request.initiator_id,
            project_id=sample_collaboration_request.project_id,
            collaboration_type=sample_collaboration_request.collaboration_type,
            description=sample_collaboration_request.description,
            required_skills=["python", "testing"],
            max_team_size=3
        )
        
        # Mock agent availability
        mock_agent_registry.get_agent_availability.return_value = True
        
        team = await collaboration_manager._form_collaboration_team(
            request_id, TeamFormationStrategy.SKILL_BASED
        )
        
        assert team is not None
        assert len(team) <= 3  # Respects max_team_size
        assert sample_collaboration_request.initiator_id in team  # Initiator included
        
        # Verify team members have complementary skills
        all_skills = set()
        for agent_id in team:
            agent = await mock_agent_registry.get_agent(agent_id)
            if agent:
                all_skills.update(agent.capabilities)
        
        # Should cover required skills
        required_skills = set(["python", "testing"])
        assert required_skills.intersection(all_skills) == required_skills
    
    @pytest.mark.asyncio
    async def test_form_team_insufficient_agents(self, collaboration_manager, mock_agent_registry):
        """Test team formation when insufficient agents are available"""
        # Mock no available agents
        mock_agent_registry.find_agents.return_value = []
        
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id="dev_001",
            project_id="proj_001",
            collaboration_type="code_review",
            description="Need review",
            required_skills=["rare_skill"],
            min_team_size=3
        )
        
        team = await collaboration_manager._form_collaboration_team(
            request_id, TeamFormationStrategy.SKILL_BASED
        )
        
        # Should still include initiator even if no other agents found
        assert team == ["dev_001"]
    
    @pytest.mark.asyncio
    async def test_start_collaboration_session(self, collaboration_manager, sample_collaboration_request, mock_dragonfly_client):
        """Test starting a collaboration session"""
        request_id = await collaboration_manager.create_collaboration_request(
            initiator_id=sample_collaboration_request.initiator_id,
            project_id=sample_collaboration_request.project_id,
            collaboration_type=sample_collaboration_request.collaboration_type,
            description=sample_collaboration_request.description,
            required_skills=["python", "testing"]
        )
        
        # Mock successful team formation
        with patch.object(collaboration_manager, '_form_collaboration_team', 
                         return_value=["dev_001", "qa_001", "pm_001"]) as mock_form_team:
            
            session_id = await collaboration_manager.start_collaboration_session(
                request_id, TeamFormationStrategy.SKILL_BASED
            )
            
            assert session_id is not None
            assert session_id in collaboration_manager.collaboration_sessions
            
            session = collaboration_manager.collaboration_sessions[session_id]
            assert session.request_id == request_id
            assert session.status == CollaborationStatus.ACTIVE
            assert len(session.participants) == 3
            assert session.leader_id is not None
            
            # Verify collaboration stream was created
            mock_dragonfly_client.create_stream.assert_called()
            
            # Verify participants were notified
            assert mock_dragonfly_client.send_message.call_count >= 3  # One per participant
    
    @pytest.mark.asyncio
    async def test_join_collaboration_session(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test agent joining an existing collaboration session"""
        # Add session to manager
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        new_agent_id = "dev_002"
        
        success = await collaboration_manager.join_collaboration_session(
            session_id=sample_collaboration_session.session_id,
            agent_id=new_agent_id,
            invitation_code="invite_123"
        )
        
        assert success == True
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert new_agent_id in session.participants
        
        # Verify existing participants were notified
        mock_dragonfly_client.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_join_collaboration_session_full_team(self, collaboration_manager, mock_dragonfly_client):
        """Test joining collaboration when team is at capacity"""
        # Create session at max capacity
        full_session = CollaborationSession(
            session_id="full_session",
            request_id="collab_001",
            participants=["agent_1", "agent_2", "agent_3", "agent_4", "agent_5"],  # Max 5
            leader_id="agent_1",
            collaboration_type="development",
            status=CollaborationStatus.ACTIVE,
            max_participants=5
        )
        
        collaboration_manager.collaboration_sessions["full_session"] = full_session
        
        success = await collaboration_manager.join_collaboration_session(
            session_id="full_session",
            agent_id="agent_6"
        )
        
        assert success == False
        assert "agent_6" not in full_session.participants
    
    @pytest.mark.asyncio
    async def test_leave_collaboration_session(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test agent leaving collaboration session"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        leaving_agent = "qa_001"
        
        success = await collaboration_manager.leave_collaboration_session(
            session_id=sample_collaboration_session.session_id,
            agent_id=leaving_agent,
            reason="Task completed"
        )
        
        assert success == True
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert leaving_agent not in session.participants
        
        # Verify remaining participants were notified
        mock_dragonfly_client.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_leave_collaboration_session_leader(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test leader leaving collaboration session"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        # Leader leaves
        success = await collaboration_manager.leave_collaboration_session(
            session_id=sample_collaboration_session.session_id,
            agent_id=sample_collaboration_session.leader_id,
            reason="Emergency"
        )
        
        assert success == True
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert sample_collaboration_session.leader_id not in session.participants
        
        # Should reassign leadership
        assert session.leader_id != sample_collaboration_session.leader_id
        assert session.leader_id in session.participants
    
    @pytest.mark.asyncio
    async def test_send_collaboration_message(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test sending message within collaboration session"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        message_content = {
            "type": "progress_update",
            "content": "Authentication module is 80% complete",
            "artifacts": ["auth.py", "test_auth.py"]
        }
        
        message_id = await collaboration_manager.send_collaboration_message(
            session_id=sample_collaboration_session.session_id,
            sender_id="dev_001",
            message_type="progress_update",
            content=message_content
        )
        
        assert message_id is not None
        
        # Verify message was sent to collaboration stream
        mock_dragonfly_client.send_message.assert_called()
        call_args = mock_dragonfly_client.send_message.call_args[0]
        assert f"nova.torch.collaboration.{sample_collaboration_session.session_id}" in call_args[0]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_collaboration(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test broadcasting message to all collaboration participants"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        broadcast_content = {
            "announcement": "Code review session starting in 5 minutes",
            "meeting_link": "https://meet.example.com/collab-001"
        }
        
        message_ids = await collaboration_manager.broadcast_to_collaboration(
            session_id=sample_collaboration_session.session_id,
            sender_id="pm_001",
            message_type="announcement",
            content=broadcast_content
        )
        
        assert len(message_ids) == len(sample_collaboration_session.participants)
        
        # Should send individual messages to each participant
        assert mock_dragonfly_client.send_message.call_count == len(sample_collaboration_session.participants)
    
    @pytest.mark.asyncio
    async def test_end_collaboration_session(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test ending collaboration session"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        session_results = {
            "outcome": "success",
            "deliverables": ["auth_module.py", "test_suite.py"],
            "feedback": "Excellent collaboration",
            "duration": 3600,
            "participants_performance": {
                "dev_001": "excellent",
                "qa_001": "good",
                "pm_001": "excellent"
            }
        }
        
        success = await collaboration_manager.end_collaboration_session(
            session_id=sample_collaboration_session.session_id,
            ended_by="pm_001",
            reason="Task completed successfully",
            results=session_results
        )
        
        assert success == True
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert session.status == CollaborationStatus.COMPLETED
        assert session.ended_at is not None
        assert session.results == session_results
        
        # Verify participants were notified
        mock_dragonfly_client.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_collaboration_timeout_handling(self, collaboration_manager, mock_dragonfly_client):
        """Test handling of collaboration session timeouts"""
        # Create session with short timeout
        timeout_session = CollaborationSession(
            session_id="timeout_session",
            request_id="collab_timeout",
            participants=["dev_001", "qa_001"],
            leader_id="dev_001",
            collaboration_type="code_review",
            status=CollaborationStatus.ACTIVE,
            timeout=1,  # 1 second timeout
            created_at=time.time()
        )
        
        collaboration_manager.collaboration_sessions["timeout_session"] = timeout_session
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Simulate timeout check
        await collaboration_manager._check_collaboration_timeouts()
        
        session = collaboration_manager.collaboration_sessions["timeout_session"]
        assert session.status == CollaborationStatus.TIMEOUT
        assert session.ended_at is not None
    
    @pytest.mark.asyncio
    async def test_collaboration_conflict_resolution(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test conflict resolution in collaboration"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        conflict_data = {
            "conflict_type": "design_disagreement",
            "participants": ["dev_001", "qa_001"],
            "issue": "Database schema design approach",
            "proposals": [
                {"author": "dev_001", "approach": "NoSQL"},
                {"author": "qa_001", "approach": "SQL"}
            ]
        }
        
        resolution_id = await collaboration_manager.escalate_conflict(
            session_id=sample_collaboration_session.session_id,
            conflict_data=conflict_data,
            escalated_by="dev_001"
        )
        
        assert resolution_id is not None
        
        # Verify leader was notified
        mock_dragonfly_client.send_message.assert_called()
        
        # Resolve conflict
        resolution = {
            "decision": "Use SQL for initial implementation",
            "reasoning": "Better testing support and team familiarity",
            "decided_by": "pm_001"
        }
        
        success = await collaboration_manager.resolve_conflict(
            session_id=sample_collaboration_session.session_id,
            resolution_id=resolution_id,
            resolution=resolution,
            resolved_by="pm_001"
        )
        
        assert success == True
    
    @pytest.mark.asyncio
    async def test_collaboration_progress_tracking(self, collaboration_manager, sample_collaboration_session):
        """Test tracking collaboration progress"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        progress_updates = [
            {"milestone": "Requirements Analysis", "completion": 100, "agent": "pm_001"},
            {"milestone": "Code Implementation", "completion": 60, "agent": "dev_001"},
            {"milestone": "Testing", "completion": 30, "agent": "qa_001"}
        ]
        
        for update in progress_updates:
            await collaboration_manager.update_collaboration_progress(
                session_id=sample_collaboration_session.session_id,
                milestone=update["milestone"],
                completion_percentage=update["completion"],
                updated_by=update["agent"],
                notes=f"Progress update for {update['milestone']}"
            )
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert len(session.progress_milestones) == 3
        
        # Calculate overall progress
        overall_progress = await collaboration_manager.get_collaboration_progress(
            sample_collaboration_session.session_id
        )
        
        assert overall_progress["overall_completion"] > 0
        assert overall_progress["total_milestones"] == 3
        assert "milestone_details" in overall_progress
    
    @pytest.mark.asyncio
    async def test_collaboration_resource_sharing(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test sharing resources within collaboration"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        shared_resource = {
            "resource_type": "code_snippet",
            "name": "authentication_helper.py",
            "content": "def authenticate_user(token): ...",
            "description": "Helper function for JWT authentication",
            "permissions": ["read", "edit"],
            "tags": ["auth", "jwt", "helper"]
        }
        
        resource_id = await collaboration_manager.share_resource(
            session_id=sample_collaboration_session.session_id,
            shared_by="dev_001",
            resource_data=shared_resource,
            target_participants=["qa_001", "pm_001"]
        )
        
        assert resource_id is not None
        
        # Verify participants were notified
        mock_dragonfly_client.send_message.assert_called()
        
        # Test resource retrieval
        resources = await collaboration_manager.get_shared_resources(
            sample_collaboration_session.session_id
        )
        
        assert len(resources) == 1
        assert resources[0]["resource_id"] == resource_id
        assert resources[0]["name"] == shared_resource["name"]
    
    @pytest.mark.asyncio
    async def test_collaboration_metrics_collection(self, collaboration_manager, sample_collaboration_session):
        """Test collection of collaboration metrics"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        # Simulate some activity
        await collaboration_manager.send_collaboration_message(
            session_id=sample_collaboration_session.session_id,
            sender_id="dev_001",
            message_type="progress",
            content={"status": "working"}
        )
        
        await collaboration_manager.update_collaboration_progress(
            session_id=sample_collaboration_session.session_id,
            milestone="Development",
            completion_percentage=50,
            updated_by="dev_001"
        )
        
        # Get session metrics
        metrics = await collaboration_manager.get_collaboration_metrics(
            sample_collaboration_session.session_id
        )
        
        assert "session_duration" in metrics
        assert "participant_count" in metrics
        assert "message_count" in metrics
        assert "progress_updates" in metrics
        assert "participant_engagement" in metrics
        
        # Verify participant engagement data
        engagement = metrics["participant_engagement"]
        assert "dev_001" in engagement
        assert engagement["dev_001"]["message_count"] > 0
    
    @pytest.mark.asyncio
    async def test_list_collaborations_by_status(self, collaboration_manager, mock_dragonfly_client):
        """Test filtering collaborations by status"""
        # Create sessions with different statuses
        session_data = [
            ("active_session", CollaborationStatus.ACTIVE),
            ("completed_session", CollaborationStatus.COMPLETED),
            ("pending_session", CollaborationStatus.PENDING)
        ]
        
        for session_id, status in session_data:
            session = CollaborationSession(
                session_id=session_id,
                request_id=f"req_{session_id}",
                participants=["dev_001", "qa_001"],
                leader_id="dev_001",
                collaboration_type="development",
                status=status
            )
            collaboration_manager.collaboration_sessions[session_id] = session
        
        # Test filtering
        active_sessions = await collaboration_manager.list_collaborations(
            status=CollaborationStatus.ACTIVE
        )
        assert len(active_sessions) == 1
        assert active_sessions[0].session_id == "active_session"
        
        completed_sessions = await collaboration_manager.list_collaborations(
            status=CollaborationStatus.COMPLETED
        )
        assert len(completed_sessions) == 1
        assert completed_sessions[0].session_id == "completed_session"
        
        # Test listing all
        all_sessions = await collaboration_manager.list_collaborations()
        assert len(all_sessions) == 3
    
    @pytest.mark.asyncio
    async def test_collaboration_recommendations(self, collaboration_manager, mock_agent_registry):
        """Test getting collaboration recommendations for agents"""
        agent_id = "dev_001"
        
        # Mock agent capabilities and current workload
        mock_agent_registry.get_agent.return_value = AgentInfo(
            agent_id=agent_id,
            agent_type="developer",
            capabilities=["python", "react", "testing"],
            host="localhost",
            port=8001,
            status="idle"
        )
        
        # Create some pending collaboration requests
        request_ids = []
        for i in range(3):
            request_id = await collaboration_manager.create_collaboration_request(
                initiator_id="other_agent",
                project_id=f"proj_{i}",
                collaboration_type="code_review",
                description=f"Review needed for project {i}",
                required_skills=["python", "testing"] if i < 2 else ["javascript"],
                preferred_agent_types=["developer"]
            )
            request_ids.append(request_id)
        
        recommendations = await collaboration_manager.get_collaboration_recommendations(
            agent_id=agent_id,
            max_recommendations=5
        )
        
        # Should recommend 2 collaborations (matching skills)
        assert len(recommendations) == 2
        
        for rec in recommendations:
            assert "request_id" in rec
            assert "match_score" in rec
            assert "reason" in rec
            assert rec["match_score"] > 0.5  # Good match
    
    @pytest.mark.asyncio
    async def test_collaboration_statistics(self, collaboration_manager):
        """Test collaboration statistics generation"""
        # Create various collaboration requests and sessions
        request_statuses = [CollaborationStatus.PENDING, CollaborationStatus.ACTIVE, 
                          CollaborationStatus.COMPLETED, CollaborationStatus.CANCELLED]
        
        for i, status in enumerate(request_statuses):
            request = CollaborationRequest(
                request_id=f"req_{i}",
                initiator_id="dev_001",
                project_id="proj_001",
                collaboration_type="development",
                description="Test collaboration",
                status=status
            )
            collaboration_manager.collaboration_requests[f"req_{i}"] = request
        
        # Add some sessions
        for i in range(2):
            session = CollaborationSession(
                session_id=f"session_{i}",
                request_id=f"req_{i}",
                participants=["dev_001", "qa_001"],
                leader_id="dev_001",
                collaboration_type="development",
                status=CollaborationStatus.ACTIVE if i == 0 else CollaborationStatus.COMPLETED
            )
            collaboration_manager.collaboration_sessions[f"session_{i}"] = session
        
        stats = await collaboration_manager.get_collaboration_statistics()
        
        assert stats["total_requests"] == 4
        assert stats["pending_requests"] == 1
        assert stats["active_sessions"] == 1
        assert stats["completed_sessions"] == 1
        assert stats["total_sessions"] == 2
        
        # Test project-specific stats
        project_stats = await collaboration_manager.get_collaboration_statistics(
            project_id="proj_001"
        )
        assert project_stats["total_requests"] == 4  # All belong to proj_001
    
    @pytest.mark.asyncio
    async def test_emergency_collaboration_session(self, collaboration_manager, mock_dragonfly_client, mock_agent_registry):
        """Test creating emergency collaboration session"""
        # Mock agent availability
        mock_agent_registry.get_agent_availability.return_value = True
        
        emergency_data = {
            "issue_type": "production_outage",
            "severity": "critical",
            "affected_systems": ["auth_service", "user_database"],
            "initial_assessment": "Database connection pool exhausted"
        }
        
        session_id = await collaboration_manager.create_emergency_collaboration(
            initiator_id="devops_001",
            emergency_type="production_incident",
            description="Critical auth service outage",
            required_skills=["debugging", "database", "devops"],
            urgency_level=10,
            metadata=emergency_data
        )
        
        assert session_id is not None
        
        session = collaboration_manager.collaboration_sessions[session_id]
        assert session.collaboration_type == "production_incident"
        assert session.status == CollaborationStatus.ACTIVE
        assert session.priority == 10  # Max priority
        
        # Verify emergency notifications were sent
        mock_dragonfly_client.broadcast_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_collaboration_session_handover(self, collaboration_manager, sample_collaboration_session, mock_dragonfly_client):
        """Test handing over collaboration leadership"""
        collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id] = sample_collaboration_session
        
        old_leader = sample_collaboration_session.leader_id
        new_leader = "qa_001"  # Different from current leader
        
        success = await collaboration_manager.handover_collaboration_leadership(
            session_id=sample_collaboration_session.session_id,
            current_leader=old_leader,
            new_leader=new_leader,
            reason="Original leader rotating out"
        )
        
        assert success == True
        
        session = collaboration_manager.collaboration_sessions[sample_collaboration_session.session_id]
        assert session.leader_id == new_leader
        assert session.leadership_history is not None
        assert len(session.leadership_history) > 0
        
        # Verify participants were notified
        mock_dragonfly_client.send_message.assert_called()
    
    @pytest.mark.asyncio
    async def test_bulk_collaboration_operations(self, collaboration_manager, mock_dragonfly_client):
        """Test bulk operations on collaborations"""
        # Create multiple collaboration requests
        request_ids = []
        for i in range(5):
            request_id = await collaboration_manager.create_collaboration_request(
                initiator_id="dev_001",
                project_id="bulk_project",
                collaboration_type="code_review",
                description=f"Bulk collaboration {i}",
                required_skills=["python"]
            )
            request_ids.append(request_id)
        
        # Test bulk status update
        subset_ids = request_ids[:3]
        success = await collaboration_manager.bulk_update_collaboration_status(
            request_ids=subset_ids,
            new_status=CollaborationStatus.CANCELLED,
            reason="Project cancelled"
        )
        
        assert success == True
        
        # Verify updates
        for request_id in subset_ids:
            request = collaboration_manager.collaboration_requests[request_id]
            assert request.status == CollaborationStatus.CANCELLED
        
        # Test bulk retrieval
        project_collaborations = await collaboration_manager.list_collaborations(
            project_id="bulk_project"
        )
        assert len(project_collaborations) == 5
        
        cancelled_collaborations = await collaboration_manager.list_collaborations(
            project_id="bulk_project",
            status=CollaborationStatus.CANCELLED
        )
        assert len(cancelled_collaborations) == 3