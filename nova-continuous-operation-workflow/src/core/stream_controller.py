#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Stream Coordination Controller
Manages all DragonflyDB stream communication and coordination for Nova teams

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 2 - Core Implementation
"""

import redis
import json
import time
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from collections import defaultdict

logger = logging.getLogger('novawf.stream_controller')

class MessagePriority(Enum):
    """Message priority levels for stream processing"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5

@dataclass
class StreamMessage:
    """Structured stream message with priority and metadata"""
    stream_id: str
    message_id: str
    timestamp: str
    message_type: str
    content: Dict[str, Any]
    priority: MessagePriority = MessagePriority.MEDIUM
    source_nova: Optional[str] = None
    target_nova: Optional[str] = None
    processed: bool = False

@dataclass
class WorkItem:
    """Work item discovered from streams"""
    id: str
    title: str
    description: str
    priority: MessagePriority
    work_type: str
    estimated_duration: int  # minutes
    source_stream: str
    source_message_id: str
    created_at: str
    metadata: Dict[str, Any]

class StreamController:
    """Core stream coordination controller for Nova workflow integration"""
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(
            host='localhost', 
            port=redis_port, 
            decode_responses=True, 
            password='adapt123'
        )
        
        # Primary coordination streams
        self.streams = {
            'coordination': f'nova.coordination.{nova_id}',
            'work_queue': 'nova.work.queue',
            'priority_alerts': 'nova.priority.alerts',
            'task_todo': f'nova.tasks.{nova_id}.todo',
            'task_progress': f'nova.tasks.{nova_id}.progress',
            'task_completed': f'nova.tasks.{nova_id}.completed',
            'status_updates': f'nova.status.{nova_id}',
            'safety_alerts': f'nova.safety.{nova_id}',
            'enterprise_metrics': f'nova.enterprise.metrics',
            'cross_nova_coordination': 'nova.cross.coordination',
            'wake_signals': 'nova.wake.signals'
        }
        
        # Stream read positions (for incremental reading)
        self.stream_positions = {}
        self.last_coordination_check = datetime.now()
        self.message_cache = defaultdict(list)
        
        logger.info(f"Stream controller initialized for {nova_id}")
    
    def check_coordination_streams(self) -> Dict[str, List[StreamMessage]]:
        """Check all coordination streams for new messages with priority processing"""
        logger.info("Checking coordination streams for new messages")
        
        messages_by_stream = {}
        total_messages = 0
        
        for stream_name, stream_key in self.streams.items():
            try:
                # Get messages since last check
                messages = self._read_stream_messages(stream_name, stream_key)
                
                if messages:
                    messages_by_stream[stream_name] = messages
                    total_messages += len(messages)
                    
                    logger.info(f"Found {len(messages)} new messages in {stream_name}")
                    
            except Exception as e:
                logger.warning(f"Failed to read stream {stream_key}: {e}")
                continue
        
        # Update coordination check time
        self.last_coordination_check = datetime.now()
        
        # Post coordination summary to enterprise monitoring
        self._post_coordination_summary(total_messages, len(messages_by_stream))
        
        logger.info(f"Coordination check complete: {total_messages} messages from {len(messages_by_stream)} streams")
        return messages_by_stream
    
    def _read_stream_messages(self, stream_name: str, stream_key: str, limit: int = 10) -> List[StreamMessage]:
        """Read messages from specific stream with incremental positioning"""
        try:
            # Get last read position for this stream
            last_id = self.stream_positions.get(stream_name, '0')
            
            # Read new messages
            stream_messages = self.redis_client.xread(
                {stream_key: last_id},
                count=limit,
                block=100  # 100ms block
            )
            
            parsed_messages = []
            
            for stream, messages in stream_messages:
                for message_id, fields in messages:
                    try:
                        # Parse message
                        message = self._parse_stream_message(
                            stream_name, message_id, fields
                        )
                        parsed_messages.append(message)
                        
                        # Update stream position
                        self.stream_positions[stream_name] = message_id
                        
                    except Exception as e:
                        logger.error(f"Failed to parse message {message_id}: {e}")
                        continue
            
            return parsed_messages
            
        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                # Stream doesn't exist yet, return empty
                return []
            else:
                logger.error(f"Redis error reading stream {stream_key}: {e}")
                return []
        except Exception as e:
            logger.error(f"Error reading stream {stream_key}: {e}")
            return []
    
    def _parse_stream_message(self, stream_name: str, message_id: str, fields: Dict) -> StreamMessage:
        """Parse raw stream message into structured format"""
        # Determine message priority
        priority = self._classify_message_priority(fields, stream_name)
        
        # Extract metadata
        message_type = fields.get('type', 'UNKNOWN')
        timestamp = fields.get('timestamp', datetime.now().isoformat())
        source_nova = fields.get('from', fields.get('nova_id', fields.get('assignee')))
        
        return StreamMessage(
            stream_id=stream_name,
            message_id=message_id,
            timestamp=timestamp,
            message_type=message_type,
            content=fields,
            priority=priority,
            source_nova=source_nova,
            target_nova=fields.get('target_nova', self.nova_id)
        )
    
    def _classify_message_priority(self, fields: Dict, stream_name: str) -> MessagePriority:
        """Classify message priority based on content and stream"""
        # Critical priorities
        if stream_name == 'safety_alerts':
            return MessagePriority.CRITICAL
        
        if stream_name == 'priority_alerts':
            return MessagePriority.HIGH
        
        # Check message type
        message_type = fields.get('type', '').upper()
        
        if any(keyword in message_type for keyword in ['EMERGENCY', 'CRITICAL', 'URGENT']):
            return MessagePriority.CRITICAL
        
        if any(keyword in message_type for keyword in ['HIGH', 'IMPORTANT', 'PRIORITY']):
            return MessagePriority.HIGH
        
        # Check priority field
        priority_field = fields.get('priority', '').lower()
        if priority_field in ['critical', 'highest']:
            return MessagePriority.CRITICAL
        elif priority_field in ['high', 'important']:
            return MessagePriority.HIGH
        elif priority_field in ['low', 'background']:
            return MessagePriority.LOW
        
        # Default to medium
        return MessagePriority.MEDIUM
    
    def process_priority_messages(self, messages_by_stream: Dict[str, List[StreamMessage]]) -> List[WorkItem]:
        """Process messages and convert high-priority ones to work items"""
        work_items = []
        
        # Flatten and sort all messages by priority
        all_messages = []
        for stream_messages in messages_by_stream.values():
            all_messages.extend(stream_messages)
        
        # Sort by priority (lower enum value = higher priority)
        all_messages.sort(key=lambda m: m.priority.value)
        
        for message in all_messages:
            # Only process high-priority messages as immediate work
            if message.priority.value <= MessagePriority.HIGH.value:
                work_item = self._convert_message_to_work_item(message)
                if work_item:
                    work_items.append(work_item)
                    logger.info(f"Created work item from {message.priority.name} priority message: {work_item.title}")
        
        return work_items
    
    def _convert_message_to_work_item(self, message: StreamMessage) -> Optional[WorkItem]:
        """Convert stream message to actionable work item"""
        try:
            # Generate work item based on message type
            if message.message_type == 'WORK_REQUEST':
                return WorkItem(
                    id=f"work-{message.message_id}",
                    title=message.content.get('title', 'Coordination Work Request'),
                    description=message.content.get('description', f"Work request from {message.source_nova}"),
                    priority=message.priority,
                    work_type='coordination',
                    estimated_duration=int(message.content.get('estimated_duration', 15)),
                    source_stream=message.stream_id,
                    source_message_id=message.message_id,
                    created_at=message.timestamp,
                    metadata=message.content
                )
            
            elif message.message_type == 'URGENT_TASK':
                return WorkItem(
                    id=f"urgent-{message.message_id}",
                    title=message.content.get('task_title', 'Urgent Task'),
                    description=message.content.get('task_description', 'Urgent task requiring immediate attention'),
                    priority=MessagePriority.HIGH,
                    work_type='urgent',
                    estimated_duration=int(message.content.get('estimated_duration', 30)),
                    source_stream=message.stream_id,
                    source_message_id=message.message_id,
                    created_at=message.timestamp,
                    metadata=message.content
                )
            
            elif message.message_type == 'COLLABORATION_REQUEST':
                return WorkItem(
                    id=f"collab-{message.message_id}",
                    title=f"Collaboration: {message.content.get('subject', 'Nova Coordination')}",
                    description=message.content.get('details', f"Collaboration request from {message.source_nova}"),
                    priority=message.priority,
                    work_type='collaboration',
                    estimated_duration=int(message.content.get('estimated_duration', 20)),
                    source_stream=message.stream_id,
                    source_message_id=message.message_id,
                    created_at=message.timestamp,
                    metadata=message.content
                )
            
            # Add more message type handlers as needed
            return None
            
        except Exception as e:
            logger.error(f"Failed to convert message to work item: {e}")
            return None
    
    def post_status_update(self, status_type: str, details: Dict[str, Any]):
        """Post status update to coordination streams"""
        try:
            status_data = {
                'type': status_type,
                'nova_id': self.nova_id,
                'timestamp': datetime.now().isoformat(),
                **details
            }
            
            # Post to status stream
            self.redis_client.xadd(
                self.streams['status_updates'],
                status_data
            )
            
            # Also post to coordination stream for visibility
            self.redis_client.xadd(
                self.streams['coordination'],
                status_data
            )
            
            logger.info(f"Posted status update: {status_type}")
            
        except Exception as e:
            logger.error(f"Failed to post status update: {e}")
    
    def post_work_completion(self, work_item: WorkItem, results: str, metrics: Dict[str, Any]):
        """Post work completion notification to coordination streams"""
        try:
            completion_data = {
                'type': 'WORK_COMPLETION',
                'nova_id': self.nova_id,
                'work_item_id': work_item.id,
                'work_title': work_item.title,
                'work_type': work_item.work_type,
                'results': results,
                'metrics': json.dumps(metrics),
                'source_stream': work_item.source_stream,
                'source_message_id': work_item.source_message_id,
                'timestamp': datetime.now().isoformat()
            }
            
            # Post to coordination stream
            self.redis_client.xadd(
                self.streams['coordination'],
                completion_data
            )
            
            # Post to enterprise metrics
            self.redis_client.xadd(
                self.streams['enterprise_metrics'],
                {
                    'type': 'WORK_COMPLETION_METRIC',
                    'nova_id': self.nova_id,
                    'work_type': work_item.work_type,
                    'duration_minutes': metrics.get('duration_minutes', 0),
                    'quality_score': metrics.get('quality_score', 0),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Posted work completion: {work_item.title}")
            
        except Exception as e:
            logger.error(f"Failed to post work completion: {e}")
    
    def post_coordination_request(self, request_type: str, target_nova: str, details: Dict[str, Any]):
        """Post coordination request to cross-Nova streams"""
        try:
            request_data = {
                'type': 'COORDINATION_REQUEST',
                'request_type': request_type,
                'from_nova': self.nova_id,
                'target_nova': target_nova,
                'timestamp': datetime.now().isoformat(),
                **details
            }
            
            # Post to cross-Nova coordination stream
            self.redis_client.xadd(
                self.streams['cross_nova_coordination'],
                request_data
            )
            
            # Also post to target Nova's coordination stream if specific
            if target_nova != 'all':
                target_stream = f'nova.coordination.{target_nova}'
                self.redis_client.xadd(target_stream, request_data)
            
            logger.info(f"Posted coordination request to {target_nova}: {request_type}")
            
        except Exception as e:
            logger.error(f"Failed to post coordination request: {e}")
    
    def _post_coordination_summary(self, total_messages: int, active_streams: int):
        """Post coordination summary to enterprise monitoring"""
        try:
            summary_data = {
                'type': 'COORDINATION_SUMMARY',
                'nova_id': self.nova_id,
                'total_messages_processed': total_messages,
                'active_streams': active_streams,
                'check_timestamp': self.last_coordination_check.isoformat(),
                'stream_positions': json.dumps(self.stream_positions),
                'timestamp': datetime.now().isoformat()
            }
            
            self.redis_client.xadd(
                self.streams['enterprise_metrics'],
                summary_data
            )
            
        except Exception as e:
            logger.error(f"Failed to post coordination summary: {e}")
    
    def get_stream_health_status(self) -> Dict[str, Any]:
        """Get health status of all coordination streams"""
        stream_health = {}
        
        for stream_name, stream_key in self.streams.items():
            try:
                # Check stream existence and recent activity
                stream_info = self.redis_client.xinfo_stream(stream_key)
                
                stream_health[stream_name] = {
                    'exists': True,
                    'length': stream_info['length'],
                    'last_entry_id': stream_info['last-entry'][0] if stream_info['last-entry'] else None,
                    'first_entry_id': stream_info['first-entry'][0] if stream_info['first-entry'] else None,
                    'last_read_position': self.stream_positions.get(stream_name, '0'),
                    'status': 'healthy'
                }
                
            except redis.ResponseError as e:
                if "no such key" in str(e).lower():
                    stream_health[stream_name] = {
                        'exists': False,
                        'status': 'not_created'
                    }
                else:
                    stream_health[stream_name] = {
                        'exists': True,
                        'status': 'error',
                        'error': str(e)
                    }
            except Exception as e:
                stream_health[stream_name] = {
                    'exists': False,
                    'status': 'error',
                    'error': str(e)
                }
        
        return {
            'nova_id': self.nova_id,
            'stream_health': stream_health,
            'last_coordination_check': self.last_coordination_check.isoformat(),
            'total_streams': len(self.streams),
            'healthy_streams': sum(1 for h in stream_health.values() if h.get('status') == 'healthy'),
            'generated_at': datetime.now().isoformat()
        }
    
    def create_enterprise_coordination_dashboard(self) -> Dict[str, Any]:
        """Create enterprise-grade coordination dashboard data"""
        try:
            # Get recent coordination activity
            recent_messages = []
            for stream_name, stream_key in self.streams.items():
                try:
                    messages = self.redis_client.xrevrange(stream_key, count=5)
                    for msg_id, fields in messages:
                        recent_messages.append({
                            'stream': stream_name,
                            'message_id': msg_id,
                            'timestamp': fields.get('timestamp', ''),
                            'type': fields.get('type', 'UNKNOWN'),
                            'source': fields.get('nova_id', fields.get('from', 'unknown'))
                        })
                except:
                    continue
            
            # Sort by timestamp
            recent_messages.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Calculate coordination metrics
            coordination_metrics = {
                'messages_per_hour': len(recent_messages) * 12,  # Rough estimate
                'active_streams': len([s for s in self.get_stream_health_status()['stream_health'].values() if s.get('status') == 'healthy']),
                'cross_nova_coordination_active': any(msg['stream'] == 'cross_nova_coordination' for msg in recent_messages[:10]),
                'last_coordination_activity': recent_messages[0]['timestamp'] if recent_messages else None
            }
            
            return {
                'nova_id': self.nova_id,
                'coordination_status': 'active',
                'recent_activity': recent_messages[:20],
                'coordination_metrics': coordination_metrics,
                'stream_health': self.get_stream_health_status(),
                'generated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create coordination dashboard: {e}")
            return {
                'nova_id': self.nova_id,
                'coordination_status': 'error',
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }

if __name__ == "__main__":
    # Test the stream controller
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing stream controller for {nova_id}")
    
    # Create stream controller
    controller = StreamController(nova_id)
    
    # Test coordination check
    messages = controller.check_coordination_streams()
    print(f"Found messages: {len(messages)} streams with activity")
    
    # Test work item processing
    work_items = controller.process_priority_messages(messages)
    print(f"Generated work items: {len(work_items)}")
    
    # Test status update
    controller.post_status_update('TEST_STATUS', {'test': True, 'timestamp': datetime.now().isoformat()})
    
    # Test dashboard
    dashboard = controller.create_enterprise_coordination_dashboard()
    print(f"\nCoordination Dashboard: {json.dumps(dashboard, indent=2)}")
