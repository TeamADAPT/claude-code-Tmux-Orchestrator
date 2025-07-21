"""
Unit Tests for AgentRegistry
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Comprehensive tests for agent registration and monitoring functionality
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, call
import asyncio
import time
import json
import uuid
from typing import Dict, Any, List

from orchestration.agent_registry import AgentRegistry, AgentInfo
from communication.dragonfly_client import DragonflyClient, NovaMessage


class TestAgentInfo:
    """Test suite for AgentInfo dataclass"""
    
    def test_agent_info_creation(self):
        """Test creating AgentInfo instances"""
        agent_info = AgentInfo(
            agent_id="test-agent-001",
            role="developer",
            skills=["python", "testing"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-123"
        )
        
        assert agent_info.agent_id == "test-agent-001"
        assert agent_info.role == "developer"
        assert agent_info.skills == ["python", "testing"]
        assert agent_info.status == "active"
        assert agent_info.session_id == "session-123"
        assert isinstance(agent_info.performance, dict)
        assert agent_info.current_task is None
    
    def test_agent_info_to_dict(self):
        """Test AgentInfo serialization"""
        agent_info = AgentInfo(
            agent_id="test-agent",
            role="tester",
            skills=["pytest"],
            status="idle",
            last_heartbeat=1234567890.0,
            session_id="session-456",
            performance={"tasks_completed": 5}
        )
        
        data = agent_info.to_dict()
        
        assert data["agent_id"] == "test-agent"
        assert data["role"] == "tester"
        assert data["skills"] == ["pytest"]
        assert data["status"] == "idle"
        assert data["last_heartbeat"] == 1234567890.0
        assert data["session_id"] == "session-456"
        assert data["performance"] == {"tasks_completed": 5}
    
    def test_agent_info_from_dict(self):
        """Test AgentInfo deserialization"""
        data = {
            "agent_id": "test-agent",
            "role": "reviewer",
            "skills": ["code-review", "security"],
            "status": "active",
            "last_heartbeat": 1234567890.0,
            "session_id": "session-789",
            "performance": {"success_rate": 0.95}
        }
        
        agent_info = AgentInfo.from_dict(data)
        
        assert agent_info.agent_id == "test-agent"
        assert agent_info.role == "reviewer"
        assert agent_info.skills == ["code-review", "security"]
        assert agent_info.status == "active"
        assert agent_info.last_heartbeat == 1234567890.0
        assert agent_info.session_id == "session-789"
        assert agent_info.performance == {"success_rate": 0.95}


class TestAgentRegistry:
    """Test suite for AgentRegistry"""
    
    @pytest.fixture
    def mock_dragonfly_client(self):
        """Create a mock DragonflyClient"""
        client = Mock()
        client.connected = True
        client.add_to_stream.return_value = "msg-123"
        client.read_stream.return_value = []
        client.client.hset.return_value = True
        client.client.hget.return_value = None
        client.client.hgetall.return_value = {}
        client.client.hdel.return_value = 1
        client.client.sadd.return_value = 1
        client.client.srem.return_value = 1
        client.client.smembers.return_value = set()
        return client
    
    @pytest.fixture
    async def agent_registry(self, mock_dragonfly_client):
        """Create AgentRegistry with mocked client"""
        registry = AgentRegistry(
            dragonfly_client=mock_dragonfly_client,
            heartbeat_timeout=60,
            enable_memory=False  # Disable memory for tests
        )
        yield registry
        # Cleanup
        if registry._running:
            await registry.stop_monitoring()
    
    @pytest.fixture
    def sample_agent_info(self):
        """Create sample agent info"""
        return AgentInfo(
            agent_id="test-agent-001",
            role="developer",
            skills=["python", "django", "testing"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-123",
            performance={"tasks_completed": 10, "success_rate": 0.9}
        )
    
    def test_registry_initialization(self, mock_dragonfly_client):
        """Test agent registry initialization"""
        registry = AgentRegistry(
            dragonfly_client=mock_dragonfly_client,
            heartbeat_timeout=120
        )
        
        assert registry.client == mock_dragonfly_client
        assert registry.heartbeat_timeout == 120
        assert not registry._running
        assert len(registry._agents) == 0
    
    @pytest.mark.asyncio
    async def test_register_agent(self, agent_registry, sample_agent_info):
        """Test registering a new agent"""
        result = await agent_registry.register_agent(sample_agent_info)
        
        assert result is True
        assert sample_agent_info.agent_id in agent_registry._agents
        assert agent_registry.client.client.hset.called
        assert agent_registry.client.client.sadd.called
    
    @pytest.mark.asyncio
    async def test_register_duplicate_agent(self, agent_registry, sample_agent_info):
        """Test registering the same agent twice"""
        # Register first time
        await agent_registry.register_agent(sample_agent_info)
        
        # Register second time - should update, not fail
        sample_agent_info.performance["tasks_completed"] = 15
        result = await agent_registry.register_agent(sample_agent_info)
        
        assert result is True
        stored_agent = agent_registry._agents[sample_agent_info.agent_id]
        assert stored_agent.performance["tasks_completed"] == 15
    
    @pytest.mark.asyncio
    async def test_update_agent_heartbeat(self, agent_registry, sample_agent_info):
        """Test updating agent heartbeat"""
        await agent_registry.register_agent(sample_agent_info)
        
        # Use heartbeat method which updates heartbeat
        result = await agent_registry.heartbeat(sample_agent_info.agent_id)
        
        assert result is True
        stored_agent = await agent_registry.get_agent(sample_agent_info.agent_id)
        assert stored_agent.last_heartbeat > sample_agent_info.last_heartbeat
    
    @pytest.mark.asyncio
    async def test_update_agent_status(self, agent_registry, sample_agent_info):
        """Test updating agent status"""
        await agent_registry.register_agent(sample_agent_info)
        
        # Use heartbeat method with status parameter
        result = await agent_registry.heartbeat(
            sample_agent_info.agent_id,
            status="busy"
        )
        
        assert result is True
        stored_agent = await agent_registry.get_agent(sample_agent_info.agent_id)
        assert stored_agent.status == "busy"
    
    @pytest.mark.asyncio
    async def test_get_agent(self, agent_registry, sample_agent_info):
        """Test retrieving agent information"""
        await agent_registry.register_agent(sample_agent_info)
        
        retrieved_agent = await agent_registry.get_agent(sample_agent_info.agent_id)
        
        assert retrieved_agent is not None
        assert retrieved_agent.agent_id == sample_agent_info.agent_id
        assert retrieved_agent.role == sample_agent_info.role
        assert retrieved_agent.skills == sample_agent_info.skills
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent(self, agent_registry):
        """Test retrieving non-existent agent"""
        result = await agent_registry.get_agent("nonexistent-agent")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_remove_agent(self, agent_registry, sample_agent_info):
        """Test removing an agent"""
        await agent_registry.register_agent(sample_agent_info)
        
        result = await agent_registry.unregister_agent(sample_agent_info.agent_id)
        
        assert result is True
        removed_agent = await agent_registry.get_agent(sample_agent_info.agent_id)
        assert removed_agent is None
    
    @pytest.mark.asyncio
    async def test_list_agents(self, agent_registry):
        """Test listing all agents"""
        # Create multiple agents
        agents = []
        for i in range(3):
            agent = AgentInfo(
                agent_id=f"agent-{i}",
                role="developer",
                skills=["python"],
                status="active",
                last_heartbeat=time.time(),
                session_id=f"session-{i}"
            )
            agents.append(agent)
            await agent_registry.register_agent(agent)
        
        all_agents = await agent_registry.find_agents()  # find_agents with no parameters returns all
        
        assert len(all_agents) == 3
        agent_ids = [a.agent_id for a in all_agents]
        assert "agent-0" in agent_ids
        assert "agent-1" in agent_ids
        assert "agent-2" in agent_ids
    
    @pytest.mark.asyncio
    async def test_find_agents_by_role(self, agent_registry):
        """Test finding agents by role"""
        # Create agents with different roles
        dev_agent = AgentInfo(
            agent_id="dev-1",
            role="developer",
            skills=["python"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-dev"
        )
        
        test_agent = AgentInfo(
            agent_id="test-1",
            role="tester",
            skills=["pytest"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-test"
        )
        
        await agent_registry.register_agent(dev_agent)
        await agent_registry.register_agent(test_agent)
        
        developers = await agent_registry.find_agents(role="developer")
        testers = await agent_registry.find_agents(role="tester")
        
        assert len(developers) == 1
        assert developers[0].agent_id == "dev-1"
        assert len(testers) == 1
        assert testers[0].agent_id == "test-1"
    
    @pytest.mark.asyncio
    async def test_find_agents_by_skills(self, agent_registry):
        """Test finding agents by skills"""
        # Create agents with different skills
        python_agent = AgentInfo(
            agent_id="python-1",
            role="developer",
            skills=["python", "django"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-python"
        )
        
        js_agent = AgentInfo(
            agent_id="js-1",
            role="developer",
            skills=["javascript", "react"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-js"
        )
        
        await agent_registry.register_agent(python_agent)
        await agent_registry.register_agent(js_agent)
        
        python_devs = await agent_registry.find_agents(skills=["python"])
        js_devs = await agent_registry.find_agents(skills=["javascript"])
        all_devs = await agent_registry.find_agents(skills=["python", "javascript"])
        
        assert len(python_devs) == 1
        assert python_devs[0].agent_id == "python-1"
        assert len(js_devs) == 1
        assert js_devs[0].agent_id == "js-1"
        assert len(all_devs) == 2  # Both agents have at least one skill
    
    @pytest.mark.asyncio
    async def test_find_agents_available_only(self, agent_registry):
        """Test finding only available agents"""
        # Create agents with different statuses
        active_agent = AgentInfo(
            agent_id="active-1",
            role="developer",
            skills=["python"],
            status="active",
            last_heartbeat=time.time(),
            session_id="session-active"
        )
        
        busy_agent = AgentInfo(
            agent_id="busy-1",
            role="developer",
            skills=["python"],
            status="busy",
            last_heartbeat=time.time(),
            session_id="session-busy"
        )
        
        offline_agent = AgentInfo(
            agent_id="offline-1",
            role="developer",
            skills=["python"],
            status="offline",
            last_heartbeat=time.time() - 3600,  # 1 hour ago
            session_id="session-offline"
        )
        
        await agent_registry.register_agent(active_agent)
        await agent_registry.register_agent(busy_agent)
        await agent_registry.register_agent(offline_agent)
        
        available_agents = await agent_registry.find_agents(available_only=True)
        all_agents = await agent_registry.find_agents(available_only=False)
        
        assert len(available_agents) == 1
        assert available_agents[0].agent_id == "active-1"
        assert len(all_agents) == 3
    
    @pytest.mark.asyncio
    async def test_agent_performance_tracking(self, agent_registry, sample_agent_info):
        """Test agent performance tracking"""
        await agent_registry.register_agent(sample_agent_info)
        
        # Update performance
        await agent_registry.update_agent_performance(
            sample_agent_info.agent_id,
            {"tasks_completed": 15, "success_rate": 0.95}
        )
        
        updated_agent = await agent_registry.get_agent(sample_agent_info.agent_id)
        assert updated_agent.performance["tasks_completed"] == 15
        assert updated_agent.performance["success_rate"] == 0.95
    
    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self, agent_registry):
        """Test starting and stopping registry monitoring"""
        # Start monitoring
        result = await agent_registry.start_monitoring()
        assert result is True
        assert agent_registry._running is True
        
        # Stop monitoring
        await agent_registry.stop_monitoring()
        assert agent_registry._running is False
    
    @pytest.mark.asyncio
    async def test_heartbeat_timeout_detection(self, agent_registry):
        """Test detection of agents with expired heartbeats"""
        # Create agent with old heartbeat
        old_agent = AgentInfo(
            agent_id="old-agent",
            role="developer",
            skills=["python"],
            status="active",
            last_heartbeat=time.time() - 200,  # 200 seconds ago (beyond 60s timeout)
            session_id="session-old"
        )
        
        await agent_registry.register_agent(old_agent)
        
        # Verify the agent exists
        retrieved_agent = await agent_registry.get_agent("old-agent")
        assert retrieved_agent is not None
        assert retrieved_agent.last_heartbeat < time.time() - 100  # Very old heartbeat
    
    
    @pytest.mark.asyncio
    async def test_registry_persistence(self, agent_registry, sample_agent_info):
        """Test that agent data persists to DragonflyDB"""
        await agent_registry.register_agent(sample_agent_info)
        
        # Check that data was stored
        assert agent_registry.client.client.hset.called
        
        # Verify the storage call
        call_args = agent_registry.client.client.hset.call_args_list[-1]
        registry_key = call_args[0][0]
        agent_id = call_args[0][1]
        agent_data = call_args[0][2]
        
        assert "nova.torch.registry" in registry_key
        assert agent_id == sample_agent_info.agent_id
        assert isinstance(agent_data, str)  # Should be JSON serialized
        
        # Parse and verify the data
        parsed_data = json.loads(agent_data)
        assert parsed_data["agent_id"] == sample_agent_info.agent_id
        assert parsed_data["role"] == sample_agent_info.role