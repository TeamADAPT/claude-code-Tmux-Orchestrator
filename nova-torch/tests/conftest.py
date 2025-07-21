"""
Nova-Torch Test Configuration
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Pytest configuration and fixtures for async testing
"""

import asyncio
import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch
import time
import uuid
import json
from typing import Dict, Any, List

# Add src to path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from communication.dragonfly_client import DragonflyClient, NovaMessage
from communication.nova_orchestrator import NovaOrchestrator, OrchestratorConfig
from orchestration.agent_registry import AgentRegistry, AgentInfo
from orchestration.task_orchestrator import TaskOrchestrator, TaskSpec, TaskPriority
from orchestration.agent_spawner import AgentSpawner, SpawnRequest
from orchestration.collaboration_manager import CollaborationManager, CollaborationRequest


# Configure pytest for async tests
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for DragonflyDB"""
    client = Mock()
    
    # Mock basic Redis operations
    client.ping.return_value = True
    client.set.return_value = True
    client.get.return_value = None
    client.delete.return_value = 1
    client.exists.return_value = 0
    
    # Mock hash operations
    client.hset.return_value = 1
    client.hget.return_value = None
    client.hgetall.return_value = {}
    client.hdel.return_value = 1
    
    # Mock set operations
    client.sadd.return_value = 1
    client.srem.return_value = 1
    client.smembers.return_value = set()
    
    # Mock stream operations
    client.xadd.return_value = f"1234567890-0"
    client.xread.return_value = []
    client.xrange.return_value = []
    client.xgroup_create.return_value = True
    client.xreadgroup.return_value = []
    client.xack.return_value = 1
    client.xinfo_stream.return_value = {"length": 0}
    
    return client


@pytest.fixture
def dragonfly_client(mock_redis_client):
    """Create a DragonflyClient with mocked Redis"""
    with patch('redis.Redis', return_value=mock_redis_client):
        client = DragonflyClient(host='localhost', port=6379, password='test')
        client.client = mock_redis_client
        client.connected = True
        return client


@pytest.fixture
def sample_nova_message():
    """Create a sample NovaMessage for testing"""
    return NovaMessage(
        id=uuid.uuid4().hex,
        timestamp=time.time(),
        sender="test-agent",
        target="test-target",
        message_type="test_message",
        payload={"test": "data", "value": 42}
    )


@pytest.fixture
def sample_agent_info():
    """Create a sample AgentInfo for testing"""
    return AgentInfo(
        agent_id="test-agent-001",
        role="developer",
        skills=["python", "testing"],
        status="active",
        last_heartbeat=time.time(),
        session_id="test-session",
        performance={
            "tasks_completed": 10,
            "success_rate": 0.9,
            "avg_completion_time": 120.0
        }
    )


@pytest.fixture
def sample_task_spec():
    """Create a sample TaskSpec for testing"""
    return TaskSpec(
        task_id="task-001",
        title="Implement test feature",
        description="Create comprehensive unit tests for the authentication module",
        task_type="implementation",
        priority=TaskPriority.HIGH,
        required_skills=["python", "testing", "pytest"],
        max_duration=3600,
        dependencies=[],
        context={"module": "auth", "coverage_target": 0.95}
    )


@pytest.fixture
def sample_spawn_request():
    """Create a sample SpawnRequest for testing"""
    return SpawnRequest(
        request_id="spawn-001",
        parent_agent_id="parent-agent-001",
        role="tester",
        skills=["pytest", "coverage"],
        context={"reason": "High test workload", "task_type": "testing"},
        urgency="high",
        max_lifetime=7200
    )


@pytest.fixture
def sample_collaboration_request():
    """Create a sample CollaborationRequest for testing"""
    return CollaborationRequest(
        request_id="collab-001",
        requester_id="agent-001",
        target_id="agent-002",
        collaboration_type="code_review",
        task_id="task-001",
        description="Need code review for authentication module",
        required_skills=["security", "python"],
        urgency="normal",
        context={"pr_number": 42, "files_changed": 5}
    )


@pytest.fixture
async def agent_registry(dragonfly_client):
    """Create an AgentRegistry instance"""
    registry = AgentRegistry(dragonfly_client, heartbeat_timeout=60, enable_memory=False)
    yield registry
    # Cleanup
    await registry.stop_monitoring()


@pytest.fixture
async def task_orchestrator(dragonfly_client, agent_registry):
    """Create a TaskOrchestrator instance"""
    orchestrator = TaskOrchestrator(dragonfly_client, agent_registry)
    yield orchestrator
    await orchestrator.stop_orchestration()


@pytest.fixture
async def agent_spawner(dragonfly_client, agent_registry):
    """Create an AgentSpawner instance"""
    spawner = AgentSpawner(dragonfly_client, agent_registry)
    yield spawner
    await spawner.stop_spawner()


@pytest.fixture
async def collaboration_manager(dragonfly_client, agent_registry):
    """Create a CollaborationManager instance"""
    manager = CollaborationManager(dragonfly_client, agent_registry)
    yield manager
    await manager.stop_collaboration_manager()


@pytest.fixture
def mock_async_response():
    """Helper to create async mock responses"""
    async def _create_response(return_value):
        return return_value
    return _create_response


# Test data generators
def generate_agent_id(role: str = "agent") -> str:
    """Generate a unique agent ID"""
    return f"{role}-{uuid.uuid4().hex[:8]}"


def generate_task_id() -> str:
    """Generate a unique task ID"""
    return f"task-{uuid.uuid4().hex[:8]}"


def generate_agents(count: int, role: str = "developer") -> List[AgentInfo]:
    """Generate multiple agent infos for testing"""
    agents = []
    for i in range(count):
        agent = AgentInfo(
            agent_id=f"{role}-{i:03d}",
            role=role,
            skills=["python", "testing"] if role == "developer" else ["management", "planning"],
            status="active" if i % 2 == 0 else "idle",
            last_heartbeat=time.time(),
            session_id=f"session-{i}",
            performance={
                "tasks_completed": i * 10,
                "success_rate": 0.8 + (i * 0.02),
                "avg_completion_time": 100 + (i * 5)
            }
        )
        agents.append(agent)
    return agents


# Async test helpers
async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1):
    """Wait for a condition to become true"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await condition_func():
            return True
        await asyncio.sleep(interval)
    return False


# Mock responses for DragonflyDB operations
def mock_stream_response(messages: List[NovaMessage]) -> List[tuple]:
    """Create mock response for xread operations"""
    return [(msg.id, msg.to_dict()) for msg in messages]


def mock_hash_response(data: Dict[str, Any]) -> Dict[bytes, bytes]:
    """Create mock response for hgetall operations"""
    return {k.encode(): json.dumps(v).encode() for k, v in data.items()}