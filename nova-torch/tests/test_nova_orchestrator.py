"""
Unit Tests for NovaOrchestrator
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Comprehensive tests for Nova orchestrator functionality
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, AsyncMock, patch, call
import asyncio
import time
import json
import uuid
from typing import Dict, Any, List

from communication.nova_orchestrator import NovaOrchestrator, OrchestratorConfig
from communication.dragonfly_client import NovaMessage


class TestOrchestratorConfig:
    """Test suite for OrchestratorConfig"""
    
    def test_config_initialization(self):
        """Test orchestrator config initialization"""
        # Test with defaults
        config = OrchestratorConfig()
        assert config.dragonfly_host == 'localhost'
        assert config.dragonfly_port == 18000
        assert config.password_file == '/etc/nova-torch/dragonfly-password'
        assert config.orchestrator_stream == 'nova.torch.orchestrator'
        assert config.heartbeat_interval == 30
        assert config.agent_timeout == 120
        assert config.max_agents == 50
        
        # Test with custom values
        config = OrchestratorConfig(
            dragonfly_host='custom-host',
            dragonfly_port=6379,
            orchestrator_name='test-orchestrator',
            heartbeat_interval=10,
            max_agents=100
        )
        assert config.dragonfly_host == 'custom-host'
        assert config.dragonfly_port == 6379
        assert config.orchestrator_name == 'test-orchestrator'
        assert config.heartbeat_interval == 10
        assert config.max_agents == 100


class TestNovaOrchestrator:
    """Test suite for NovaOrchestrator"""
    
    @pytest.fixture
    def mock_dragonfly_client(self):
        """Create a mock DragonflyClient"""
        client = Mock()
        client.connected = False
        client.connect.return_value = True
        client.disconnect.return_value = None
        client.add_to_stream.return_value = "msg-123"
        client.read_stream.return_value = []
        client.create_consumer_group.return_value = True
        client.read_as_consumer.return_value = []
        client.acknowledge_message.return_value = True
        return client
    
    @pytest.fixture
    def orchestrator_config(self):
        """Create test orchestrator config"""
        return OrchestratorConfig(
            orchestrator_name='test-orchestrator',
            heartbeat_interval=5,
            agent_timeout=10
        )
    
    @pytest.fixture
    async def orchestrator(self, orchestrator_config, mock_dragonfly_client):
        """Create orchestrator with mocked client"""
        with patch('communication.nova_orchestrator.DragonflyClient', return_value=mock_dragonfly_client):
            orch = NovaOrchestrator(orchestrator_config)
            orch.client = mock_dragonfly_client
            yield orch
            # Cleanup
            if orch._running:
                await orch.stop()
    
    def test_orchestrator_initialization(self, orchestrator_config):
        """Test orchestrator initialization"""
        with patch('communication.nova_orchestrator.DragonflyClient') as mock_client:
            orch = NovaOrchestrator(orchestrator_config)
            
            assert orch.config == orchestrator_config
            assert orch._running is False
            assert len(orch._handlers) == 0
            assert len(orch._pending_responses) == 0
            mock_client.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_start_orchestrator(self, orchestrator, mock_dragonfly_client):
        """Test starting the orchestrator"""
        # Mock registry import
        with patch('orchestration.agent_registry.AgentRegistry') as mock_registry:
            mock_registry_instance = Mock()
            mock_registry_instance.start_monitoring = AsyncMock()
            mock_registry.return_value = mock_registry_instance
            
            result = await orchestrator.start()
            
            assert result is True
            assert orchestrator._running is True
            assert mock_dragonfly_client.connect.called
            assert len(orchestrator._tasks) > 0  # Should have started background tasks
    
    @pytest.mark.asyncio
    async def test_start_orchestrator_connection_failure(self, orchestrator, mock_dragonfly_client):
        """Test orchestrator start with connection failure"""
        mock_dragonfly_client.connect.return_value = False
        
        result = await orchestrator.start()
        
        assert result is False
        assert orchestrator._running is False
    
    @pytest.mark.asyncio
    async def test_stop_orchestrator(self, orchestrator):
        """Test stopping the orchestrator"""
        # Start first
        with patch('communication.nova_orchestrator.AgentRegistry'):
            await orchestrator.start()
        
        # Now stop
        await orchestrator.stop()
        
        assert orchestrator._running is False
        assert orchestrator.client.disconnect.called
    
    def test_register_handler(self, orchestrator):
        """Test registering message handlers"""
        handler = Mock()
        
        orchestrator.register_handler('test_message', handler)
        
        assert 'test_message' in orchestrator._handlers
        assert handler in orchestrator._handlers['test_message']
    
    def test_register_multiple_handlers(self, orchestrator):
        """Test registering multiple handlers"""
        handler1 = Mock()
        handler2 = Mock()
        
        orchestrator.register_handler('message1', handler1)
        orchestrator.register_handler('message2', handler2)
        
        assert len(orchestrator._handlers) == 2
        assert handler1 in orchestrator._handlers['message1']
        assert handler2 in orchestrator._handlers['message2']
    
    @pytest.mark.asyncio
    async def test_send_message(self, orchestrator, mock_dragonfly_client):
        """Test sending a message"""
        msg_id = await orchestrator.send_message(
            'test-target', 
            'test_message', 
            {'data': 'test'}
        )
        
        assert msg_id == "msg-123"
        assert mock_dragonfly_client.add_to_stream.called
        
        # Check the message was properly formatted
        call_args = mock_dragonfly_client.add_to_stream.call_args
        stream_name = call_args[0][0]
        message = call_args[0][1]
        
        assert stream_name == 'nova.torch.agents.direct.test-target'
        assert isinstance(message, NovaMessage)
        assert message.sender == orchestrator.config.orchestrator_id
        assert message.target == 'test-target'
        assert message.message_type == 'test_message'
        assert message.payload == {'data': 'test'}
    
    @pytest.mark.asyncio
    async def test_broadcast_message(self, orchestrator, mock_dragonfly_client):
        """Test broadcasting a message"""
        msg_id = await orchestrator.broadcast(
            'announcement', 
            {'message': 'Hello everyone'}
        )
        
        assert msg_id == "msg-123"
        
        # Check broadcast stream was used
        call_args = mock_dragonfly_client.add_to_stream.call_args
        stream_name = call_args[0][0]
        message = call_args[0][1]
        
        assert stream_name == 'nova.torch.orchestrator'  # Uses orchestrator stream for broadcast
        assert message.target == 'broadcast'
    
    @pytest.mark.asyncio
    async def test_request_with_timeout(self, orchestrator, mock_dragonfly_client):
        """Test request with timeout"""
        # Don't provide a response
        result = await orchestrator.request(
            'test-agent',
            'test_request',
            {'query': 'test'},
            timeout=0.1  # 100ms timeout
        )
        
        assert result is None  # Should timeout
    
    @pytest.mark.asyncio
    async def test_request_with_response(self, orchestrator, mock_dragonfly_client):
        """Test request with successful response"""
        # Create a response message
        response_msg = NovaMessage(
            id='resp-123',
            timestamp=time.time(),
            sender='test-agent',
            target='test-orchestrator',
            message_type='response',
            payload={'result': 'success'},
            correlation_id='test-correlation'
        )
        
        # Simulate response handling
        async def delayed_response():
            await asyncio.sleep(0.05)
            # Find the correlation ID from the request
            call_args = mock_dragonfly_client.add_to_stream.call_args_list[-1]
            sent_msg = call_args[0][1]
            response_msg.correlation_id = sent_msg.correlation_id
            
            # Process the response directly using orchestrator method
            await orchestrator._process_message('test-stream', 'resp-123', response_msg)
        
        # Start the delayed response
        asyncio.create_task(delayed_response())
        
        # Make request
        result = await orchestrator.request(
            'test-agent',
            'test_request',
            {'query': 'test'},
            timeout=1.0
        )
        
        assert result == {'result': 'success'}
    
    @pytest.mark.asyncio
    async def test_handle_message_with_handler(self, orchestrator):
        """Test handling message with registered handler"""
        handler = AsyncMock()
        orchestrator.register_handler('test_message', handler)
        
        message = NovaMessage(
            id='msg-123',
            timestamp=time.time(),
            sender='test-sender',
            target=orchestrator.config.orchestrator_id,
            message_type='test_message',
            payload={'data': 'test'}
        )
        
        await orchestrator._process_message('test-stream', 'msg-123', message)
        
        handler.assert_called_once_with(message)
    
    @pytest.mark.asyncio
    async def test_handle_message_without_handler(self, orchestrator):
        """Test handling message without registered handler"""
        message = NovaMessage(
            id='msg-123',
            timestamp=time.time(),
            sender='test-sender',
            target=orchestrator.config.orchestrator_id,
            message_type='unknown_message',
            payload={'data': 'test'}
        )
        
        # Should not raise exception
        await orchestrator._process_message('test-stream', 'msg-123', message)
    
    @pytest.mark.asyncio
    async def test_handle_response_message(self, orchestrator):
        """Test handling response message"""
        correlation_id = 'test-correlation'
        future = asyncio.Future()
        orchestrator._pending_responses[correlation_id] = future
        
        message = NovaMessage(
            id='msg-123',
            timestamp=time.time(),
            sender='test-sender',
            target=orchestrator.config.orchestrator_id,
            message_type='response',
            payload={'result': 'success'},
            correlation_id=correlation_id
        )
        
        await orchestrator._process_message('test-stream', 'msg-123', message)
        
        assert future.done()
        assert future.result() == {'result': 'success'}
    
    @pytest.mark.asyncio
    async def test_heartbeat_functionality(self, orchestrator, mock_dragonfly_client):
        """Test heartbeat sending"""
        orchestrator.config.heartbeat_interval = 0.1  # 100ms for testing
        
        # Start orchestrator
        with patch('orchestration.agent_registry.AgentRegistry') as mock_registry:
            mock_registry_instance = Mock()
            mock_registry_instance.start_monitoring = AsyncMock()
            mock_registry.return_value = mock_registry_instance
            
            await orchestrator.start()
        
        # Wait for at least one heartbeat
        await asyncio.sleep(0.15)
        
        # Check heartbeat was sent to monitoring stream
        heartbeat_calls = [
            call for call in mock_dragonfly_client.add_to_stream.call_args_list
            if 'nova.torch.monitoring' in str(call)
        ]
        
        assert len(heartbeat_calls) > 0
        
        # Stop orchestrator
        await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, orchestrator, mock_dragonfly_client):
        """Test handling multiple concurrent requests"""
        # Make multiple requests concurrently
        requests = [
            orchestrator.request(f'agent-{i}', 'test', {'n': i}, timeout=0.1)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*requests, return_exceptions=True)
        
        # All should timeout (return None)
        assert all(r is None for r in results)
        assert mock_dragonfly_client.add_to_stream.call_count == 5