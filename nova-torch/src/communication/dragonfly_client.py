"""
DragonflyDB Client for Nova-Torch
Author: Torch (pm-torch)
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16
"""

import redis
import json
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import os

logger = logging.getLogger(__name__)


@dataclass
class NovaMessage:
    """Standard message format for Nova communication"""
    id: str
    timestamp: float
    sender: str
    target: str
    message_type: str
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None
    priority: str = "normal"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Redis storage"""
        return {
            'id': self.id,
            'timestamp': str(self.timestamp),
            'sender': self.sender,
            'target': self.target,
            'type': self.message_type,
            'payload': json.dumps(self.payload),
            'correlation_id': self.correlation_id or '',
            'priority': self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NovaMessage':
        """Create from Redis stream data"""
        return cls(
            id=data.get('id', ''),
            timestamp=float(data.get('timestamp', time.time())),
            sender=data.get('sender', ''),
            target=data.get('target', ''),
            message_type=data.get('type', ''),
            payload=json.loads(data.get('payload', '{}')),
            correlation_id=data.get('correlation_id') or None,
            priority=data.get('priority', 'normal')
        )


class DragonflyClient:
    """
    DragonflyDB client for Nova-Torch communication
    Handles connection, authentication, and basic operations
    """
    
    def __init__(self, host: str = 'localhost', port: int = 18000, 
                 password_file: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize DragonflyDB client
        
        Args:
            host: DragonflyDB host
            port: DragonflyDB port
            password_file: Path to password file (preferred)
            password: Direct password (fallback)
        """
        self.host = host
        self.port = port
        self.password = self._load_password(password_file, password)
        self.client: Optional[redis.Redis] = None
        self.connected = False
        
    def _load_password(self, password_file: Optional[str], password: Optional[str]) -> str:
        """Load password from file or use provided password"""
        if password_file and os.path.exists(password_file):
            try:
                with open(password_file, 'r') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"Failed to read password file: {e}")
                
        # Fallback to direct password or hardcoded from guide
        return password or "dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    
    def connect(self) -> bool:
        """Establish connection to DragonflyDB"""
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info(f"Connected to DragonflyDB at {self.host}:{self.port}")
            return True
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to DragonflyDB: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Close DragonflyDB connection"""
        if self.client:
            self.client.close()
            self.connected = False
            logger.info("Disconnected from DragonflyDB")
    
    def add_to_stream(self, stream: str, message: NovaMessage) -> Optional[str]:
        """
        Add message to a stream
        
        Args:
            stream: Stream name (e.g., 'nova.torch.orchestrator')
            message: NovaMessage to send
            
        Returns:
            Message ID if successful, None otherwise
        """
        if not self.connected:
            logger.error("Not connected to DragonflyDB")
            return None
            
        try:
            msg_id = self.client.xadd(stream, message.to_dict())
            logger.debug(f"Added message {msg_id} to stream {stream}")
            return msg_id
            
        except redis.RedisError as e:
            logger.error(f"Failed to add message to stream {stream}: {e}")
            return None
    
    def read_stream(self, stream: str, last_id: str = '$', 
                   count: Optional[int] = None, block: Optional[int] = None) -> List[Tuple[str, NovaMessage]]:
        """
        Read messages from a stream
        
        Args:
            stream: Stream name
            last_id: Last message ID seen (default '$' for new messages only)
            count: Maximum number of messages to return
            block: Block for N milliseconds if no messages (0 = forever)
            
        Returns:
            List of (message_id, NovaMessage) tuples
        """
        if not self.connected:
            logger.error("Not connected to DragonflyDB")
            return []
            
        try:
            if block is not None:
                # Blocking read
                result = self.client.xread({stream: last_id}, count=count, block=block)
            else:
                # Non-blocking read
                messages = self.client.xrange(stream, min=last_id, count=count)
                result = [(stream, messages)] if messages else []
            
            # Parse messages
            parsed_messages = []
            for stream_name, stream_messages in result:
                for msg_id, data in stream_messages:
                    try:
                        nova_msg = NovaMessage.from_dict(data)
                        parsed_messages.append((msg_id, nova_msg))
                    except Exception as e:
                        logger.error(f"Failed to parse message {msg_id}: {e}")
                        
            return parsed_messages
            
        except redis.RedisError as e:
            logger.error(f"Failed to read from stream {stream}: {e}")
            return []
    
    def get_stream_info(self, stream: str) -> Optional[Dict[str, Any]]:
        """Get information about a stream"""
        if not self.connected:
            return None
            
        try:
            info = self.client.xinfo_stream(stream)
            return info
        except redis.RedisError as e:
            logger.error(f"Failed to get stream info for {stream}: {e}")
            return None
    
    def trim_stream(self, stream: str, maxlen: int = 1000):
        """Trim stream to maximum length"""
        if not self.connected:
            return
            
        try:
            self.client.xtrim(stream, maxlen=maxlen, approximate=True)
            logger.debug(f"Trimmed stream {stream} to ~{maxlen} messages")
        except redis.RedisError as e:
            logger.error(f"Failed to trim stream {stream}: {e}")
    
    def create_consumer_group(self, stream: str, group: str, id: str = '0') -> bool:
        """Create a consumer group for coordinated reading"""
        if not self.connected:
            return False
            
        try:
            self.client.xgroup_create(stream, group, id=id, mkstream=True)
            logger.info(f"Created consumer group {group} for stream {stream}")
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group {group} already exists")
                return True
            logger.error(f"Failed to create consumer group: {e}")
            return False
    
    def read_as_consumer(self, streams: Dict[str, str], group: str, consumer: str,
                        count: Optional[int] = None, block: Optional[int] = None) -> List[Tuple[str, str, NovaMessage]]:
        """
        Read messages as part of a consumer group
        
        Returns:
            List of (stream, message_id, NovaMessage) tuples
        """
        if not self.connected:
            return []
            
        try:
            result = self.client.xreadgroup(
                group, consumer, streams,
                count=count, block=block
            )
            
            parsed_messages = []
            for stream_name, stream_messages in result:
                for msg_id, data in stream_messages:
                    if data:  # Not already claimed
                        try:
                            nova_msg = NovaMessage.from_dict(data)
                            parsed_messages.append((stream_name, msg_id, nova_msg))
                        except Exception as e:
                            logger.error(f"Failed to parse message {msg_id}: {e}")
                            
            return parsed_messages
            
        except redis.RedisError as e:
            logger.error(f"Failed to read as consumer: {e}")
            return []
    
    def acknowledge_message(self, stream: str, group: str, message_id: str) -> bool:
        """Acknowledge a message in a consumer group"""
        if not self.connected:
            return False
            
        try:
            self.client.xack(stream, group, message_id)
            return True
        except redis.RedisError as e:
            logger.error(f"Failed to acknowledge message: {e}")
            return False