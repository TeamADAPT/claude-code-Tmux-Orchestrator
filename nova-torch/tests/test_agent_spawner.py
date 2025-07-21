"""
Unit Tests for AgentSpawner
Author: Torch
Department: QA/DevOps
Project: Nova-Torch
Date: 2025-01-21

Comprehensive unit tests for agent spawning and lifecycle management
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from agents.agent_spawner import AgentSpawner, AgentTemplate, SpawnRequest, AgentLifecycleState
from communication.dragonfly_client import DragonflyClient, NovaMessage
from registry.agent_registry import AgentRegistry, AgentInfo
from orchestration.nova_orchestrator import NovaOrchestrator


@pytest.fixture
def mock_dragonfly_client():
    """Mock DragonflyClient for testing"""
    client = Mock(spec=DragonflyClient)
    client.send_message = AsyncMock(return_value="msg_12345")
    client.listen_to_stream = AsyncMock()
    client.get_stream_length = AsyncMock(return_value=0)
    client.add_to_stream = AsyncMock(return_value="stream_id_123")
    client.set_key = AsyncMock()
    client.get_key = AsyncMock(return_value=None)
    client.delete_key = AsyncMock()
    return client


@pytest.fixture
def mock_agent_registry():
    """Mock AgentRegistry for testing"""
    registry = Mock(spec=AgentRegistry)
    registry.register_agent = AsyncMock(return_value=True)
    registry.unregister_agent = AsyncMock(return_value=True)
    registry.get_agent = AsyncMock()
    registry.find_agents = AsyncMock(return_value=[])
    registry.update_agent_status = AsyncMock()
    registry.get_agent_count = AsyncMock(return_value=0)
    return registry


@pytest.fixture
def mock_orchestrator():
    """Mock NovaOrchestrator for testing"""
    orchestrator = Mock(spec=NovaOrchestrator)
    orchestrator.orchestrator_id = "test_orchestrator"
    orchestrator.send_message = AsyncMock()
    orchestrator.broadcast_message = AsyncMock()
    return orchestrator


@pytest.fixture
def sample_agent_template():
    """Sample agent template for testing"""
    return AgentTemplate(
        template_id="developer_template",
        agent_type="developer",
        base_capabilities=["python", "javascript", "git"],
        resource_requirements={
            "cpu": 1.0,
            "memory": 2048,
            "disk": 10240
        },
        environment_variables={
            "AGENT_TYPE": "developer",
            "LOG_LEVEL": "INFO"
        },
        startup_timeout=60,
        health_check_interval=30,
        max_idle_time=300
    )


@pytest.fixture
def sample_spawn_request():
    """Sample spawn request for testing"""
    return SpawnRequest(
        request_id="spawn_001",
        agent_type="developer",
        requested_capabilities=["python", "react", "testing"],
        priority=5,
        resource_constraints={
            "max_cpu": 2.0,
            "max_memory": 4096
        },
        project_id="proj_001",
        requester_id="orchestrator",
        spawn_reason="Increased workload"
    )


@pytest.fixture
async def agent_spawner(mock_dragonfly_client, mock_agent_registry, mock_orchestrator):
    """AgentSpawner instance for testing"""
    spawner = AgentSpawner(
        dragonfly_client=mock_dragonfly_client,
        agent_registry=mock_agent_registry,
        orchestrator=mock_orchestrator,
        spawner_id="test_spawner"
    )
    
    # Initialize without starting background processes
    spawner._running = False
    return spawner


class TestAgentSpawner:
    """Test cases for AgentSpawner"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_dragonfly_client, mock_agent_registry, mock_orchestrator):
        """Test AgentSpawner initialization"""
        spawner = AgentSpawner(
            dragonfly_client=mock_dragonfly_client,
            agent_registry=mock_agent_registry,
            orchestrator=mock_orchestrator,
            spawner_id="test_spawner"
        )
        
        assert spawner.spawner_id == "test_spawner"
        assert spawner.dragonfly_client == mock_dragonfly_client
        assert spawner.agent_registry == mock_agent_registry
        assert spawner.orchestrator == mock_orchestrator
        assert spawner._running == False
        assert len(spawner.agent_templates) == 0
        assert len(spawner.spawn_requests) == 0
        assert spawner.max_agents_per_type == 20
    
    @pytest.mark.asyncio
    async def test_register_agent_template(self, agent_spawner, sample_agent_template):
        """Test agent template registration"""
        success = await agent_spawner.register_agent_template(sample_agent_template)
        assert success == True
        
        assert sample_agent_template.template_id in agent_spawner.agent_templates
        stored_template = agent_spawner.agent_templates[sample_agent_template.template_id]
        assert stored_template.agent_type == sample_agent_template.agent_type
        assert stored_template.base_capabilities == sample_agent_template.base_capabilities
        
        # Test duplicate registration
        success = await agent_spawner.register_agent_template(sample_agent_template)
        assert success == False  # Should fail for duplicate
    
    @pytest.mark.asyncio
    async def test_get_agent_template(self, agent_spawner, sample_agent_template):
        """Test agent template retrieval"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Test successful retrieval
        template = await agent_spawner.get_agent_template(sample_agent_template.template_id)
        assert template is not None
        assert template.template_id == sample_agent_template.template_id
        
        # Test by agent type
        template = await agent_spawner.get_agent_template_by_type(sample_agent_template.agent_type)
        assert template is not None
        assert template.agent_type == sample_agent_template.agent_type
        
        # Test non-existent template
        template = await agent_spawner.get_agent_template("non_existent")
        assert template is None
    
    @pytest.mark.asyncio
    async def test_create_spawn_request(self, agent_spawner, sample_spawn_request):
        """Test spawn request creation"""
        request_id = await agent_spawner.create_spawn_request(
            agent_type=sample_spawn_request.agent_type,
            requested_capabilities=sample_spawn_request.requested_capabilities,
            priority=sample_spawn_request.priority,
            resource_constraints=sample_spawn_request.resource_constraints,
            project_id=sample_spawn_request.project_id,
            requester_id=sample_spawn_request.requester_id,
            spawn_reason=sample_spawn_request.spawn_reason
        )
        
        assert request_id is not None
        assert request_id in agent_spawner.spawn_requests
        
        request = agent_spawner.spawn_requests[request_id]
        assert request.agent_type == sample_spawn_request.agent_type
        assert request.requested_capabilities == sample_spawn_request.requested_capabilities
        assert request.status == "pending"
        assert request.created_at is not None
    
    @pytest.mark.asyncio
    async def test_process_spawn_request(self, agent_spawner, sample_agent_template, sample_spawn_request, mock_agent_registry):
        """Test spawn request processing"""
        # Register template first
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock agent count check
        mock_agent_registry.get_agent_count.return_value = 5
        
        # Create and process spawn request
        request_id = await agent_spawner.create_spawn_request(
            agent_type=sample_spawn_request.agent_type,
            requested_capabilities=sample_spawn_request.requested_capabilities,
            priority=sample_spawn_request.priority
        )
        
        with patch.object(agent_spawner, '_spawn_agent_instance', return_value=True) as mock_spawn:
            success = await agent_spawner._process_spawn_request(request_id)
            assert success == True
            mock_spawn.assert_called_once()
        
        request = agent_spawner.spawn_requests[request_id]
        assert request.status == "completed"
        assert request.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_process_spawn_request_no_template(self, agent_spawner, sample_spawn_request):
        """Test spawn request processing when template doesn't exist"""
        request_id = await agent_spawner.create_spawn_request(
            agent_type="unknown_type",
            requested_capabilities=["unknown_skill"]
        )
        
        success = await agent_spawner._process_spawn_request(request_id)
        assert success == False
        
        request = agent_spawner.spawn_requests[request_id]
        assert request.status == "failed"
        assert "template not found" in request.failure_reason.lower()
    
    @pytest.mark.asyncio
    async def test_process_spawn_request_resource_limit(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test spawn request rejection due to resource limits"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock high agent count to exceed limit
        mock_agent_registry.get_agent_count.return_value = 25  # Above max_agents_per_type (20)
        
        request_id = await agent_spawner.create_spawn_request(
            agent_type=sample_agent_template.agent_type,
            requested_capabilities=sample_agent_template.base_capabilities
        )
        
        success = await agent_spawner._process_spawn_request(request_id)
        assert success == False
        
        request = agent_spawner.spawn_requests[request_id]
        assert request.status == "failed"
        assert "resource limit" in request.failure_reason.lower()
    
    @pytest.mark.asyncio
    async def test_spawn_agent_instance(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test actual agent instance spawning"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock successful agent registration
        mock_agent_registry.register_agent.return_value = True
        
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_process.poll.return_value = None  # Process is running
            mock_popen.return_value = mock_process
            
            agent_id = await agent_spawner._spawn_agent_instance(
                template=sample_agent_template,
                spawn_config={
                    "additional_capabilities": ["testing"],
                    "project_id": "proj_001"
                }
            )
            
            assert agent_id is not None
            assert agent_id.startswith("agent_")
            
            # Verify subprocess was called with correct arguments
            mock_popen.assert_called_once()
            call_args = mock_popen.call_args[0][0]
            assert "python" in call_args[0]
            assert any("agent_main.py" in arg for arg in call_args)
    
    @pytest.mark.asyncio
    async def test_terminate_agent(self, agent_spawner, mock_agent_registry):
        """Test agent termination"""
        agent_id = "agent_12345"
        
        # Mock agent exists and is registered
        mock_agent_info = AgentInfo(
            agent_id=agent_id,
            agent_type="developer",
            capabilities=["python"],
            host="localhost",
            port=8001,
            status="active"
        )
        mock_agent_registry.get_agent.return_value = mock_agent_info
        
        # Mock process exists
        agent_spawner.agent_processes[agent_id] = {
            "process": Mock(pid=12345, poll=Mock(return_value=None)),
            "started_at": time.time(),
            "template_id": "developer_template"
        }
        
        with patch('os.kill') as mock_kill:
            success = await agent_spawner.terminate_agent(agent_id, reason="Test termination")
            assert success == True
            
            # Verify process was killed
            mock_kill.assert_called_with(12345, 15)  # SIGTERM
            
            # Verify agent was unregistered
            mock_agent_registry.unregister_agent.assert_called_with(agent_id)
            
            # Verify process was removed from tracking
            assert agent_id not in agent_spawner.agent_processes
    
    @pytest.mark.asyncio
    async def test_terminate_non_existent_agent(self, agent_spawner):
        """Test terminating an agent that doesn't exist"""
        success = await agent_spawner.terminate_agent("non_existent_agent")
        assert success == False
    
    @pytest.mark.asyncio
    async def test_scale_agents_up(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test scaling agents up"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock current agent count
        mock_agent_registry.get_agent_count.return_value = 3
        
        with patch.object(agent_spawner, '_spawn_agent_instance', return_value="new_agent_id") as mock_spawn:
            # Request scaling to 6 agents (should spawn 3 more)
            success = await agent_spawner.scale_agents(
                agent_type=sample_agent_template.agent_type,
                target_count=6
            )
            assert success == True
            
            # Should spawn 3 new agents
            assert mock_spawn.call_count == 3
    
    @pytest.mark.asyncio
    async def test_scale_agents_down(self, agent_spawner, mock_agent_registry):
        """Test scaling agents down"""
        agent_type = "developer"
        
        # Mock current agents
        current_agents = [
            AgentInfo(f"agent_{i}", agent_type, [], "localhost", 8000+i, "idle")
            for i in range(5)
        ]
        mock_agent_registry.find_agents.return_value = current_agents
        
        # Mock agent processes
        for i in range(5):
            agent_id = f"agent_{i}"
            agent_spawner.agent_processes[agent_id] = {
                "process": Mock(pid=1000+i),
                "started_at": time.time(),
                "template_id": "developer_template"
            }
        
        with patch.object(agent_spawner, 'terminate_agent', return_value=True) as mock_terminate:
            # Scale down to 2 agents (should terminate 3)
            success = await agent_spawner.scale_agents(
                agent_type=agent_type,
                target_count=2
            )
            assert success == True
            
            # Should terminate 3 agents
            assert mock_terminate.call_count == 3
    
    @pytest.mark.asyncio
    async def test_auto_scaling_up(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test automatic scaling up based on demand"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock high task queue depth
        with patch.object(agent_spawner.orchestrator, 'get_task_queue_depth', return_value=50):
            # Mock current agent count
            mock_agent_registry.get_agent_count.return_value = 2
            
            with patch.object(agent_spawner, 'scale_agents', return_value=True) as mock_scale:
                await agent_spawner._check_auto_scaling()
                
                # Should trigger scale up
                mock_scale.assert_called()
                call_args = mock_scale.call_args[1]
                assert call_args["target_count"] > 2
    
    @pytest.mark.asyncio
    async def test_auto_scaling_down(self, agent_spawner, mock_agent_registry):
        """Test automatic scaling down due to low demand"""
        agent_type = "developer"
        
        # Mock low task queue depth and idle agents
        with patch.object(agent_spawner.orchestrator, 'get_task_queue_depth', return_value=1):
            idle_agents = [
                AgentInfo(f"agent_{i}", agent_type, [], "localhost", 8000+i, "idle")
                for i in range(8)  # Many idle agents
            ]
            mock_agent_registry.find_agents.return_value = idle_agents
            
            with patch.object(agent_spawner, 'scale_agents', return_value=True) as mock_scale:
                await agent_spawner._check_auto_scaling()
                
                # Should trigger scale down
                mock_scale.assert_called()
                call_args = mock_scale.call_args[1]
                assert call_args["target_count"] < 8
    
    @pytest.mark.asyncio
    async def test_agent_health_monitoring(self, agent_spawner):
        """Test agent health monitoring"""
        # Mock unhealthy agent process
        unhealthy_agent_id = "unhealthy_agent"
        agent_spawner.agent_processes[unhealthy_agent_id] = {
            "process": Mock(pid=12345, poll=Mock(return_value=1)),  # Process died
            "started_at": time.time() - 3600,  # Started 1 hour ago
            "template_id": "developer_template",
            "last_heartbeat": time.time() - 600  # Last heartbeat 10 minutes ago
        }
        
        with patch.object(agent_spawner, 'terminate_agent', return_value=True) as mock_terminate:
            with patch.object(agent_spawner, '_respawn_agent', return_value="new_agent_id") as mock_respawn:
                await agent_spawner._monitor_agent_health()
                
                # Should terminate unhealthy agent and respawn
                mock_terminate.assert_called_with(unhealthy_agent_id, reason="Agent process died")
                mock_respawn.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_agent_resource_monitoring(self, agent_spawner, mock_agent_registry):
        """Test monitoring agent resource usage"""
        agent_id = "resource_test_agent"
        
        # Mock agent with high resource usage
        mock_agent_registry.get_agent.return_value = AgentInfo(
            agent_id=agent_id,
            agent_type="developer",
            capabilities=["python"],
            host="localhost",
            port=8001,
            status="active"
        )
        
        agent_spawner.agent_processes[agent_id] = {
            "process": Mock(pid=12345),
            "started_at": time.time(),
            "template_id": "developer_template"
        }
        
        # Mock high resource usage
        with patch('psutil.Process') as mock_process:
            mock_proc = Mock()
            mock_proc.cpu_percent.return_value = 95.0  # High CPU
            mock_proc.memory_info.return_value.rss = 8 * 1024 * 1024 * 1024  # 8GB RAM
            mock_process.return_value = mock_proc
            
            resources = await agent_spawner._get_agent_resource_usage(agent_id)
            
            assert resources["cpu_percent"] == 95.0
            assert resources["memory_mb"] > 7000  # Should be ~8000MB
            assert resources["status"] == "high_usage"
    
    @pytest.mark.asyncio
    async def test_batch_spawn_requests(self, agent_spawner, sample_agent_template):
        """Test processing multiple spawn requests in batch"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Create multiple spawn requests
        request_ids = []
        for i in range(5):
            request_id = await agent_spawner.create_spawn_request(
                agent_type=sample_agent_template.agent_type,
                requested_capabilities=sample_agent_template.base_capabilities,
                priority=i + 1
            )
            request_ids.append(request_id)
        
        with patch.object(agent_spawner, '_spawn_agent_instance', return_value="agent_id") as mock_spawn:
            # Process all requests in batch
            results = await agent_spawner._process_batch_spawn_requests()
            
            # Should process all 5 requests
            assert len([r for r in results if r]) == 5
            assert mock_spawn.call_count == 5
    
    @pytest.mark.asyncio
    async def test_spawn_request_prioritization(self, agent_spawner, sample_agent_template):
        """Test that spawn requests are processed in priority order"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Create requests with different priorities
        priorities = [3, 1, 5, 2, 4]
        request_ids = []
        
        for priority in priorities:
            request_id = await agent_spawner.create_spawn_request(
                agent_type=sample_agent_template.agent_type,
                requested_capabilities=sample_agent_template.base_capabilities,
                priority=priority
            )
            request_ids.append(request_id)
        
        # Get sorted requests
        sorted_requests = await agent_spawner._get_prioritized_spawn_requests()
        
        # Should be sorted by priority (highest first)
        expected_order = [5, 4, 3, 2, 1]
        actual_order = [req.priority for req in sorted_requests]
        
        assert actual_order == expected_order
    
    @pytest.mark.asyncio
    async def test_agent_lifecycle_management(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test complete agent lifecycle from spawn to termination"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock successful registration
        mock_agent_registry.register_agent.return_value = True
        mock_agent_registry.unregister_agent.return_value = True
        
        # Spawn agent
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock(pid=12345, poll=Mock(return_value=None))
            mock_popen.return_value = mock_process
            
            agent_id = await agent_spawner._spawn_agent_instance(sample_agent_template)
            assert agent_id is not None
            
            # Verify agent is tracked
            assert agent_id in agent_spawner.agent_processes
            
            # Update agent status
            await agent_spawner._update_agent_lifecycle_state(
                agent_id, AgentLifecycleState.RUNNING
            )
            
            lifecycle = agent_spawner.agent_lifecycles[agent_id]
            assert lifecycle.current_state == AgentLifecycleState.RUNNING
            
            # Terminate agent
            with patch('os.kill'):
                success = await agent_spawner.terminate_agent(agent_id)
                assert success == True
                
                # Verify cleanup
                assert agent_id not in agent_spawner.agent_processes
                
                lifecycle = agent_spawner.agent_lifecycles[agent_id]
                assert lifecycle.current_state == AgentLifecycleState.TERMINATED
    
    @pytest.mark.asyncio
    async def test_spawn_request_timeout(self, agent_spawner, sample_agent_template):
        """Test spawn request timeout handling"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Create request with short timeout
        request_id = await agent_spawner.create_spawn_request(
            agent_type=sample_agent_template.agent_type,
            requested_capabilities=sample_agent_template.base_capabilities,
            timeout=1  # 1 second timeout
        )
        
        # Simulate processing delay
        with patch.object(agent_spawner, '_spawn_agent_instance', side_effect=asyncio.sleep(2)):
            # Wait for timeout
            await asyncio.sleep(1.5)
            
            # Check timeout
            await agent_spawner._check_spawn_request_timeouts()
            
            request = agent_spawner.spawn_requests[request_id]
            assert request.status == "failed"
            assert "timeout" in request.failure_reason.lower()
    
    @pytest.mark.asyncio
    async def test_get_spawner_statistics(self, agent_spawner, sample_agent_template):
        """Test spawner statistics collection"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Create various spawn requests
        statuses = ["pending", "in_progress", "completed", "failed"]
        for status in statuses:
            request_id = await agent_spawner.create_spawn_request(
                agent_type=sample_agent_template.agent_type,
                requested_capabilities=sample_agent_template.base_capabilities
            )
            
            # Manually set status for testing
            agent_spawner.spawn_requests[request_id].status = status
        
        # Add some agent processes
        agent_spawner.agent_processes["agent_1"] = {
            "process": Mock(pid=1001),
            "started_at": time.time() - 3600,
            "template_id": sample_agent_template.template_id
        }
        
        stats = await agent_spawner.get_spawner_statistics()
        
        assert stats["total_spawn_requests"] == 4
        assert stats["pending_requests"] == 1
        assert stats["active_agents"] == 1
        assert stats["total_templates"] == 1
        assert sample_agent_template.agent_type in stats["agents_by_type"]
        assert stats["agents_by_type"][sample_agent_template.agent_type] == 1
    
    @pytest.mark.asyncio
    async def test_agent_template_update(self, agent_spawner, sample_agent_template):
        """Test updating agent templates"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Update template
        updated_template = AgentTemplate(
            template_id=sample_agent_template.template_id,
            agent_type=sample_agent_template.agent_type,
            base_capabilities=sample_agent_template.base_capabilities + ["new_skill"],
            resource_requirements={
                "cpu": 2.0,  # Increased CPU
                "memory": 4096,  # Increased memory
                "disk": 20480
            },
            environment_variables=sample_agent_template.environment_variables,
            startup_timeout=sample_agent_template.startup_timeout
        )
        
        success = await agent_spawner.update_agent_template(updated_template)
        assert success == True
        
        # Verify update
        stored_template = agent_spawner.agent_templates[sample_agent_template.template_id]
        assert "new_skill" in stored_template.base_capabilities
        assert stored_template.resource_requirements["cpu"] == 2.0
        assert stored_template.resource_requirements["memory"] == 4096
    
    @pytest.mark.asyncio
    async def test_emergency_agent_spawning(self, agent_spawner, sample_agent_template, mock_agent_registry):
        """Test emergency agent spawning for critical tasks"""
        await agent_spawner.register_agent_template(sample_agent_template)
        
        # Mock no available agents
        mock_agent_registry.find_agents.return_value = []
        
        with patch.object(agent_spawner, '_spawn_agent_instance', return_value="emergency_agent") as mock_spawn:
            # Request emergency spawn
            agent_id = await agent_spawner.emergency_spawn_agent(
                agent_type=sample_agent_template.agent_type,
                required_capabilities=["python"],
                reason="Critical system failure"
            )
            
            assert agent_id == "emergency_agent"
            mock_spawn.assert_called_once()
            
            # Verify emergency spawn request was created
            emergency_requests = [r for r in agent_spawner.spawn_requests.values() 
                                if r.spawn_reason == "Critical system failure"]
            assert len(emergency_requests) == 1
            assert emergency_requests[0].priority == 10  # Max priority