"""
Unit Tests for DragonflyClient
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Comprehensive tests for DragonflyDB client functionality
"""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, call
import time
import json
import uuid
from typing import Dict, Any
import redis

from communication.dragonfly_client import DragonflyClient, NovaMessage


class TestDragonflyClient:
    """Test suite for DragonflyClient"""
    
    def test_initialization(self):
        """Test client initialization with various parameters"""
        # Test with default parameters
        client = DragonflyClient()
        assert client.host == 'localhost'
        assert client.port == 18000  # Default DragonflyDB port
        assert client.password == "dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"  # Default from guide
        assert client.client is None
        assert not client.connected
        
        # Test with custom parameters
        client = DragonflyClient(
            host='custom-host',
            port=6379,
            password='test-password'
        )
        assert client.host == 'custom-host'
        assert client.port == 6379
        assert client.password == 'test-password'
    
    def test_connect_success(self, mock_redis_client):
        """Test successful connection to DragonflyDB"""
        with patch('redis.Redis', return_value=mock_redis_client):
            client = DragonflyClient(password='test')
            
            # Test connection
            result = client.connect()
            
            assert result is True
            assert client.connected is True
            assert client.client is not None
            mock_redis_client.ping.assert_called_once()
    
    def test_connect_failure(self):
        """Test connection failure handling"""
        mock_client = Mock()
        mock_client.ping.side_effect = redis.ConnectionError("Connection failed")
        
        with patch('redis.Redis', return_value=mock_client):
            client = DragonflyClient()
            result = client.connect()
            
            assert result is False
            assert client.connected is False
    
    def test_disconnect(self, dragonfly_client):
        """Test client disconnection"""
        # Test normal disconnect
        dragonfly_client.disconnect()
        assert dragonfly_client.connected is False
        
        # Test disconnect when already disconnected
        dragonfly_client.disconnect()  # Should not raise exception
    
    def test_nova_message_creation(self):
        """Test NovaMessage dataclass functionality"""
        # Test basic creation
        msg = NovaMessage(
            id="test-id",
            timestamp=1234567890.0,
            sender="test-sender",
            target="test-target",
            message_type="test_type",
            payload={"key": "value"}
        )
        
        assert msg.id == "test-id"
        assert msg.timestamp == 1234567890.0
        assert msg.sender == "test-sender"
        assert msg.target == "test-target"
        assert msg.message_type == "test_type"
        assert msg.payload == {"key": "value"}
        assert msg.correlation_id is None
        assert msg.priority == "normal"
        
        # Test with all parameters
        msg = NovaMessage(
            id="test-id",
            timestamp=1234567890.0,
            sender="test-sender",
            target="test-target",
            message_type="test_type",
            payload={"key": "value"},
            correlation_id="corr-123",
            priority="high"
        )
        
        assert msg.correlation_id == "corr-123"
        assert msg.priority == "high"
    
    def test_nova_message_to_dict(self, sample_nova_message):
        """Test NovaMessage to_dict conversion"""
        msg_dict = sample_nova_message.to_dict()
        
        assert isinstance(msg_dict, dict)
        assert msg_dict["id"] == sample_nova_message.id
        assert msg_dict["timestamp"] == str(sample_nova_message.timestamp)
        assert msg_dict["sender"] == sample_nova_message.sender
        assert msg_dict["target"] == sample_nova_message.target
        assert msg_dict["type"] == sample_nova_message.message_type  # Note: key is 'type' not 'message_type'
        assert msg_dict["payload"] == json.dumps(sample_nova_message.payload)
        assert msg_dict["correlation_id"] == ""
        assert msg_dict["priority"] == "normal"
    
    def test_nova_message_from_dict(self):
        """Test NovaMessage from_dict creation"""
        data = {
            "id": "test-id",
            "timestamp": "1234567890.0",
            "sender": "test-sender",
            "target": "test-target",
            "type": "test_type",  # Note: key is 'type' not 'message_type'
            "payload": json.dumps({"key": "value"}),
            "correlation_id": "corr-123",
            "priority": "high"
        }
        
        msg = NovaMessage.from_dict(data)
        
        assert msg.id == "test-id"
        assert msg.timestamp == 1234567890.0
        assert msg.sender == "test-sender"
        assert msg.target == "test-target"
        assert msg.message_type == "test_type"
        assert msg.payload == {"key": "value"}
        assert msg.correlation_id == "corr-123"
        assert msg.priority == "high"
    
    def test_add_to_stream(self, dragonfly_client, sample_nova_message):
        """Test adding messages to a stream"""
        stream_name = "test-stream"
        expected_id = "1234567890-0"
        
        dragonfly_client.client.xadd.return_value = expected_id
        
        # Test successful add
        result = dragonfly_client.add_to_stream(stream_name, sample_nova_message)
        
        assert result == expected_id
        dragonfly_client.client.xadd.assert_called_once()
        
        # Verify the call arguments
        call_args = dragonfly_client.client.xadd.call_args
        assert call_args[0][0] == stream_name
        # The second argument should be the message dict
        assert isinstance(call_args[0][1], dict)
    
    def test_add_to_stream_not_connected(self):
        """Test adding to stream when not connected"""
        client = DragonflyClient()
        msg = NovaMessage(
            id="test",
            timestamp=time.time(),
            sender="test",
            target="test",
            message_type="test",
            payload={}
        )
        
        result = client.add_to_stream("test-stream", msg)
        assert result is None
    
    def test_read_stream(self, dragonfly_client):
        """Test reading from a stream"""
        stream_name = "test-stream"
        
        # Mock stream data - use xrange since that's what read_stream uses
        dragonfly_client.client.xrange.return_value = []
        
        # Test read
        messages = dragonfly_client.read_stream(stream_name, count=10)
        
        assert messages == []
        dragonfly_client.client.xrange.assert_called_once()
    
    def test_read_stream_with_consumer_group(self, dragonfly_client):
        """Test reading from stream with consumer group"""
        stream_name = "test-stream"
        group_name = "test-group"
        consumer_name = "test-consumer"
        
        # Test group creation
        dragonfly_client.client.xgroup_create.return_value = True
        result = dragonfly_client.create_consumer_group(stream_name, group_name)
        assert result is True
        
        # Mock consumer group read - return empty list for simplicity
        dragonfly_client.client.xreadgroup.return_value = []
        
        # Test read with consumer group using read_as_consumer
        streams = {stream_name: '>'}
        messages = dragonfly_client.read_as_consumer(
            streams, group_name, consumer_name
        )
        
        assert messages == []
        dragonfly_client.client.xreadgroup.assert_called_once()
    
    def test_acknowledge_messages(self, dragonfly_client):
        """Test message acknowledgment in consumer groups"""
        stream_name = "test-stream"
        group_name = "test-group"
        message_id = "1234567890-0"
        
        dragonfly_client.client.xack.return_value = 1
        
        # Test single message acknowledgment
        result = dragonfly_client.acknowledge_message(
            stream_name, group_name, message_id
        )
        
        assert result is True
        dragonfly_client.client.xack.assert_called_once_with(
            stream_name, group_name, message_id
        )
    
    def test_get_stream_info(self, dragonfly_client):
        """Test getting stream information"""
        stream_name = "test-stream"
        expected_info = {
            "length": 42,
            "first-entry": ["1234567890-0", {"field": "value"}],
            "last-entry": ["1234567899-0", {"field": "value"}]
        }
        
        dragonfly_client.client.xinfo_stream.return_value = expected_info
        
        info = dragonfly_client.get_stream_info(stream_name)
        
        assert info == expected_info
        dragonfly_client.client.xinfo_stream.assert_called_once_with(stream_name)
    
    def test_error_handling(self, dragonfly_client):
        """Test error handling in various operations"""
        # Test stream add error
        dragonfly_client.client.xadd.side_effect = redis.RedisError("Add failed")
        result = dragonfly_client.add_to_stream("test", Mock())
        assert result is None
        
        # Test stream read error
        dragonfly_client.client.xread.side_effect = redis.RedisError("Read failed")
        result = dragonfly_client.read_stream("test")
        assert result == []
        
        # Test consumer group creation error
        dragonfly_client.client.xgroup_create.side_effect = redis.ResponseError("Group exists")
        result = dragonfly_client.create_consumer_group("test", "group")
        assert result is False
    
    @pytest.mark.parametrize("operation,method,args", [
        ("add_to_stream", "xadd", ["stream", Mock()]),
        ("read_stream", "xread", ["stream"]),
        ("create_consumer_group", "xgroup_create", ["stream", "group"]),
        ("acknowledge_message", "xack", ["stream", "group", "msg-1"]),
        ("get_stream_info", "xinfo_stream", ["stream"])
    ])
    def test_not_connected_operations(self, operation, method, args):
        """Test all operations when client is not connected"""
        client = DragonflyClient()
        client.connected = False
        
        method_to_call = getattr(client, operation)
        result = method_to_call(*args)
        
        assert result in [None, [], False, 0, {}]