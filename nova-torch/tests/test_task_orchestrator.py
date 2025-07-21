"""
Unit Tests for TaskOrchestrator
Author: Torch
Department: QA/DevOps
Project: Nova-Torch
Date: 2025-01-21

Comprehensive unit tests for task management and orchestration
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, List, Any

from orchestration.task_orchestrator import TaskOrchestrator, Task, TaskStatus, TaskPriority
from communication.dragonfly_client import DragonflyClient, NovaMessage
from registry.agent_registry import AgentRegistry, AgentInfo


@pytest.fixture
def mock_dragonfly_client():
    """Mock DragonflyClient for testing"""
    client = Mock(spec=DragonflyClient)
    client.send_message = AsyncMock(return_value="msg_12345")
    client.listen_to_stream = AsyncMock()
    client.acknowledge_message = AsyncMock()
    client.get_stream_length = AsyncMock(return_value=0)
    client.add_to_stream = AsyncMock(return_value="stream_id_123")
    return client


@pytest.fixture
def mock_agent_registry():
    """Mock AgentRegistry for testing"""
    registry = Mock(spec=AgentRegistry)
    
    # Sample agent data
    sample_agents = [
        AgentInfo(
            agent_id="agent_001",
            agent_type="developer",
            capabilities=["python", "react", "testing"],
            host="localhost",
            port=8001,
            status="active"
        ),
        AgentInfo(
            agent_id="agent_002", 
            agent_type="qa",
            capabilities=["testing", "automation"],
            host="localhost",
            port=8002,
            status="active"
        ),
        AgentInfo(
            agent_id="agent_003",
            agent_type="devops",
            capabilities=["docker", "kubernetes", "deployment"],
            host="localhost", 
            port=8003,
            status="idle"
        )
    ]
    
    registry.find_agents = AsyncMock(return_value=sample_agents)
    registry.get_agent = AsyncMock(return_value=sample_agents[0])
    registry.update_agent_status = AsyncMock()
    registry.get_agent_load = AsyncMock(return_value=0.5)
    
    return registry


@pytest.fixture
def sample_task():
    """Sample task for testing"""
    return Task(
        task_id="task_001",
        task_type="code_generation", 
        title="Generate user authentication module",
        description="Create a secure user authentication system with JWT tokens",
        requirements={
            "skills": ["python", "fastapi", "security"],
            "resources": {"cpu": 1.0, "memory": 2048},
            "deadline": time.time() + 3600
        },
        priority=TaskPriority.HIGH,
        estimated_duration=1800,
        created_by="orchestrator",
        project_id="proj_001"
    )


@pytest.fixture
async def task_orchestrator(mock_dragonfly_client, mock_agent_registry):
    """TaskOrchestrator instance for testing"""
    orchestrator = TaskOrchestrator(
        dragonfly_client=mock_dragonfly_client,
        agent_registry=mock_agent_registry,
        orchestrator_id="test_orchestrator"
    )
    
    # Initialize without starting background tasks
    orchestrator._running = False
    return orchestrator


class TestTaskOrchestrator:
    """Test cases for TaskOrchestrator"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_dragonfly_client, mock_agent_registry):
        """Test TaskOrchestrator initialization"""
        orchestrator = TaskOrchestrator(
            dragonfly_client=mock_dragonfly_client,
            agent_registry=mock_agent_registry,
            orchestrator_id="test_orchestrator"
        )
        
        assert orchestrator.orchestrator_id == "test_orchestrator"
        assert orchestrator.dragonfly_client == mock_dragonfly_client
        assert orchestrator.agent_registry == mock_agent_registry
        assert orchestrator._running == False
        assert len(orchestrator.tasks) == 0
        assert len(orchestrator.task_queue) == 0
        assert orchestrator.max_concurrent_tasks == 100
    
    @pytest.mark.asyncio
    async def test_create_task(self, task_orchestrator, sample_task):
        """Test task creation"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            requirements=sample_task.requirements,
            priority=sample_task.priority,
            estimated_duration=sample_task.estimated_duration,
            created_by=sample_task.created_by,
            project_id=sample_task.project_id
        )
        
        assert task_id is not None
        assert task_id in task_orchestrator.tasks
        
        created_task = task_orchestrator.tasks[task_id]
        assert created_task.task_type == sample_task.task_type
        assert created_task.title == sample_task.title
        assert created_task.status == TaskStatus.PENDING
        assert created_task.priority == sample_task.priority
        
        # Verify task was added to queue
        assert len(task_orchestrator.task_queue) == 1
        assert task_orchestrator.task_queue[0].task_id == task_id
    
    @pytest.mark.asyncio
    async def test_get_task(self, task_orchestrator, sample_task):
        """Test task retrieval"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description
        )
        
        retrieved_task = await task_orchestrator.get_task(task_id)
        assert retrieved_task is not None
        assert retrieved_task.task_id == task_id
        assert retrieved_task.task_type == sample_task.task_type
        
        # Test non-existent task
        non_existent = await task_orchestrator.get_task("non_existent")
        assert non_existent is None
    
    @pytest.mark.asyncio
    async def test_update_task_status(self, task_orchestrator, sample_task):
        """Test task status updates"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description
        )
        
        # Update to in_progress
        success = await task_orchestrator.update_task_status(
            task_id, TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        assert success == True
        
        task = await task_orchestrator.get_task(task_id)
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.assigned_agent == "agent_001"
        assert task.started_at is not None
        
        # Update to completed
        result = {"output": "Task completed successfully", "artifacts": ["module.py"]}
        success = await task_orchestrator.update_task_status(
            task_id, TaskStatus.COMPLETED, result=result
        )
        assert success == True
        
        task = await task_orchestrator.get_task(task_id)
        assert task.status == TaskStatus.COMPLETED
        assert task.completed_at is not None
        assert task.result == result
        
        # Test invalid task ID
        success = await task_orchestrator.update_task_status(
            "invalid_id", TaskStatus.COMPLETED
        )
        assert success == False
    
    @pytest.mark.asyncio
    async def test_find_suitable_agent(self, task_orchestrator, sample_task, mock_agent_registry):
        """Test agent selection for tasks"""
        # Mock agent registry to return suitable agents
        suitable_agents = [
            AgentInfo(
                agent_id="python_dev",
                agent_type="developer", 
                capabilities=["python", "fastapi", "security"],
                host="localhost",
                port=8001,
                status="idle"
            )
        ]
        mock_agent_registry.find_agents.return_value = suitable_agents
        mock_agent_registry.get_agent_load.return_value = 0.3
        
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            requirements=sample_task.requirements
        )
        
        task = await task_orchestrator.get_task(task_id)
        agent = await task_orchestrator._find_suitable_agent(task)
        
        assert agent is not None
        assert agent.agent_id == "python_dev"
        assert "python" in agent.capabilities
        
        # Verify agent registry was called with correct criteria
        mock_agent_registry.find_agents.assert_called_once()
        call_args = mock_agent_registry.find_agents.call_args[1]
        assert "idle" in call_args.get("status", [])
        assert call_args.get("capabilities") == ["python", "fastapi", "security"]
    
    @pytest.mark.asyncio
    async def test_find_suitable_agent_no_match(self, task_orchestrator, sample_task, mock_agent_registry):
        """Test agent selection when no suitable agents available"""
        # Mock no suitable agents
        mock_agent_registry.find_agents.return_value = []
        
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            requirements={"skills": ["rare_skill"]}
        )
        
        task = await task_orchestrator.get_task(task_id)
        agent = await task_orchestrator._find_suitable_agent(task)
        
        assert agent is None
    
    @pytest.mark.asyncio 
    async def test_assign_task_to_agent(self, task_orchestrator, sample_task, mock_dragonfly_client):
        """Test task assignment to agent"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description
        )
        
        agent_id = "agent_001"
        success = await task_orchestrator._assign_task_to_agent(task_id, agent_id)
        
        assert success == True
        
        task = await task_orchestrator.get_task(task_id)
        assert task.status == TaskStatus.ASSIGNED
        assert task.assigned_agent == agent_id
        assert task.assigned_at is not None
        
        # Verify message was sent to agent
        mock_dragonfly_client.send_message.assert_called_once()
        call_args = mock_dragonfly_client.send_message.call_args[0]
        assert "nova.torch.agents.tasks" in call_args[0]
        
        sent_message = call_args[1]
        assert sent_message.message_type == "task_assignment"
        assert sent_message.recipient_id == agent_id
        assert "task_id" in sent_message.payload
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, task_orchestrator, sample_task):
        """Test task cancellation"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description
        )
        
        # Cancel pending task
        success = await task_orchestrator.cancel_task(task_id, reason="No longer needed")
        assert success == True
        
        task = await task_orchestrator.get_task(task_id)
        assert task.status == TaskStatus.CANCELLED
        assert task.cancellation_reason == "No longer needed"
        assert task.completed_at is not None
        
        # Try to cancel already cancelled task
        success = await task_orchestrator.cancel_task(task_id)
        assert success == False
        
        # Test cancelling non-existent task
        success = await task_orchestrator.cancel_task("non_existent")
        assert success == False
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_status(self, task_orchestrator, sample_task):
        """Test filtering tasks by status"""
        # Create tasks with different statuses
        task_ids = []
        
        for i in range(3):
            task_id = await task_orchestrator.create_task(
                task_type=sample_task.task_type,
                title=f"Task {i}",
                description=f"Description {i}"
            )
            task_ids.append(task_id)
        
        # Update one task to in_progress
        await task_orchestrator.update_task_status(
            task_ids[1], TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        
        # Update one task to completed
        await task_orchestrator.update_task_status(
            task_ids[2], TaskStatus.COMPLETED
        )
        
        # Test filtering
        pending_tasks = await task_orchestrator.list_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].task_id == task_ids[0]
        
        in_progress_tasks = await task_orchestrator.list_tasks(status=TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].task_id == task_ids[1]
        
        completed_tasks = await task_orchestrator.list_tasks(status=TaskStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].task_id == task_ids[2]
        
        # Test listing all tasks
        all_tasks = await task_orchestrator.list_tasks()
        assert len(all_tasks) == 3
    
    @pytest.mark.asyncio
    async def test_list_tasks_by_agent(self, task_orchestrator, sample_task):
        """Test filtering tasks by assigned agent"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description
        )
        
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        
        # Test filtering by agent
        agent_tasks = await task_orchestrator.list_tasks(assigned_agent="agent_001")
        assert len(agent_tasks) == 1
        assert agent_tasks[0].task_id == task_id
        
        # Test filtering by non-existent agent
        no_tasks = await task_orchestrator.list_tasks(assigned_agent="non_existent")
        assert len(no_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_get_task_statistics(self, task_orchestrator, sample_task):
        """Test task statistics generation"""
        # Create tasks with various statuses
        task_data = [
            (TaskStatus.PENDING, None),
            (TaskStatus.IN_PROGRESS, "agent_001"),
            (TaskStatus.COMPLETED, "agent_002"),
            (TaskStatus.FAILED, "agent_001"),
            (TaskStatus.CANCELLED, None)
        ]
        
        for status, agent in task_data:
            task_id = await task_orchestrator.create_task(
                task_type="test_task",
                title=f"Task {status.value}",
                description="Test description"
            )
            
            if status != TaskStatus.PENDING:
                await task_orchestrator.update_task_status(
                    task_id, status, assigned_agent=agent
                )
        
        stats = await task_orchestrator.get_task_statistics()
        
        assert stats["total_tasks"] == 5
        assert stats["pending"] == 1
        assert stats["in_progress"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1
        assert stats["cancelled"] == 1
        
        # Test project-specific stats
        project_task_id = await task_orchestrator.create_task(
            task_type="project_task",
            title="Project Task",
            description="Project specific task",
            project_id="proj_001"
        )
        
        project_stats = await task_orchestrator.get_task_statistics(project_id="proj_001")
        assert project_stats["total_tasks"] == 1
        assert project_stats["pending"] == 1
    
    @pytest.mark.asyncio
    async def test_task_priority_ordering(self, task_orchestrator):
        """Test that tasks are processed in priority order"""
        # Create tasks with different priorities
        task_data = [
            ("Low Priority", TaskPriority.LOW),
            ("High Priority", TaskPriority.HIGH), 
            ("Critical Priority", TaskPriority.CRITICAL),
            ("Medium Priority", TaskPriority.MEDIUM)
        ]
        
        created_tasks = []
        for title, priority in task_data:
            task_id = await task_orchestrator.create_task(
                task_type="priority_test",
                title=title,
                description="Priority test task",
                priority=priority
            )
            created_tasks.append((task_id, priority))
        
        # Check that queue is ordered by priority
        queue = task_orchestrator.task_queue
        assert len(queue) == 4
        
        # Should be ordered: CRITICAL, HIGH, MEDIUM, LOW
        expected_order = [TaskPriority.CRITICAL, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]
        actual_order = [task.priority for task in queue]
        
        assert actual_order == expected_order
    
    @pytest.mark.asyncio
    async def test_task_timeout_handling(self, task_orchestrator, sample_task):
        """Test handling of task timeouts"""
        # Create task with short timeout
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            requirements={"timeout": 1}  # 1 second timeout
        )
        
        # Start the task
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        
        # Wait for timeout
        await asyncio.sleep(1.5)
        
        # Simulate timeout check (normally done by background process)
        await task_orchestrator._check_task_timeouts()
        
        task = await task_orchestrator.get_task(task_id)
        # Task should be marked as failed due to timeout
        assert task.status == TaskStatus.FAILED
        assert "timeout" in task.failure_reason.lower()
    
    @pytest.mark.asyncio
    async def test_task_retry_mechanism(self, task_orchestrator, sample_task):
        """Test task retry functionality"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            requirements={"max_retries": 2}
        )
        
        # Start and fail the task
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.FAILED, failure_reason="Network error"
        )
        
        task = await task_orchestrator.get_task(task_id)
        assert task.retry_count == 0
        
        # Retry the task
        success = await task_orchestrator.retry_task(task_id)
        assert success == True
        
        task = await task_orchestrator.get_task(task_id)
        assert task.status == TaskStatus.PENDING
        assert task.retry_count == 1
        assert task.assigned_agent is None
        
        # Task should be back in queue
        assert any(t.task_id == task_id for t in task_orchestrator.task_queue)
    
    @pytest.mark.asyncio
    async def test_task_dependency_handling(self, task_orchestrator):
        """Test task dependency management"""
        # Create parent task
        parent_id = await task_orchestrator.create_task(
            task_type="parent_task",
            title="Parent Task",
            description="Must complete first"
        )
        
        # Create dependent task
        child_id = await task_orchestrator.create_task(
            task_type="child_task", 
            title="Child Task",
            description="Depends on parent",
            dependencies=[parent_id]
        )
        
        child_task = await task_orchestrator.get_task(child_id)
        assert child_task.dependencies == [parent_id]
        
        # Child task should not be assignable while parent is pending
        can_assign = await task_orchestrator._can_assign_task(child_id)
        assert can_assign == False
        
        # Complete parent task
        await task_orchestrator.update_task_status(
            parent_id, TaskStatus.COMPLETED
        )
        
        # Now child task should be assignable
        can_assign = await task_orchestrator._can_assign_task(child_id)
        assert can_assign == True
    
    @pytest.mark.asyncio
    async def test_concurrent_task_limit(self, task_orchestrator, mock_agent_registry):
        """Test concurrent task execution limits"""
        # Set low concurrent task limit for testing
        task_orchestrator.max_concurrent_tasks = 2
        
        # Create multiple tasks
        task_ids = []
        for i in range(5):
            task_id = await task_orchestrator.create_task(
                task_type="concurrent_test",
                title=f"Concurrent Task {i}",
                description="Concurrent execution test"
            )
            task_ids.append(task_id)
        
        # Mock agents available
        mock_agent_registry.find_agents.return_value = [
            AgentInfo(f"agent_{i}", "test", [], "localhost", 8000 + i, "idle")
            for i in range(5)
        ]
        
        # Simulate task processing
        await task_orchestrator._process_task_queue()
        
        # Should only have 2 tasks in progress due to limit
        in_progress_tasks = await task_orchestrator.list_tasks(status=TaskStatus.IN_PROGRESS)
        assert len(in_progress_tasks) <= 2
    
    @pytest.mark.asyncio
    async def test_task_metrics_collection(self, task_orchestrator, sample_task):
        """Test collection of task execution metrics"""
        task_id = await task_orchestrator.create_task(
            task_type=sample_task.task_type,
            title=sample_task.title,
            description=sample_task.description,
            estimated_duration=1800
        )
        
        start_time = time.time()
        
        # Progress through task lifecycle
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.IN_PROGRESS, assigned_agent="agent_001"
        )
        
        # Simulate some work time
        await asyncio.sleep(0.1)
        
        await task_orchestrator.update_task_status(
            task_id, TaskStatus.COMPLETED,
            result={"output": "Success"}
        )
        
        task = await task_orchestrator.get_task(task_id)
        
        # Verify timing metrics
        assert task.created_at is not None
        assert task.started_at is not None  
        assert task.completed_at is not None
        assert task.assigned_at is not None
        
        # Verify duration calculation
        actual_duration = task.completed_at - task.started_at
        assert actual_duration >= 0.1
        
        # Check metrics are collected
        metrics = await task_orchestrator.get_task_metrics(task_id)
        assert metrics is not None
        assert "execution_time" in metrics
        assert "queue_time" in metrics
        assert "assignment_time" in metrics
    
    @pytest.mark.asyncio
    async def test_bulk_task_operations(self, task_orchestrator):
        """Test bulk operations on multiple tasks"""
        # Create multiple tasks
        task_ids = []
        for i in range(10):
            task_id = await task_orchestrator.create_task(
                task_type="bulk_test",
                title=f"Bulk Task {i}",
                description=f"Bulk operation test {i}",
                project_id="bulk_project"
            )
            task_ids.append(task_id)
        
        # Test bulk status update
        subset_ids = task_ids[:5]
        success = await task_orchestrator.bulk_update_status(
            subset_ids, TaskStatus.CANCELLED, reason="Bulk cancellation"
        )
        assert success == True
        
        # Verify updates
        for task_id in subset_ids:
            task = await task_orchestrator.get_task(task_id)
            assert task.status == TaskStatus.CANCELLED
            assert task.cancellation_reason == "Bulk cancellation"
        
        # Test bulk task retrieval
        project_tasks = await task_orchestrator.list_tasks(project_id="bulk_project")
        assert len(project_tasks) == 10
        
        cancelled_tasks = await task_orchestrator.list_tasks(
            project_id="bulk_project",
            status=TaskStatus.CANCELLED
        )
        assert len(cancelled_tasks) == 5