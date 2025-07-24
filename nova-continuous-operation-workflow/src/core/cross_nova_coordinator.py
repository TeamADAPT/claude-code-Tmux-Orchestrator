#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Cross-Nova Coordination Protocol
Enables collaborative work and knowledge sharing between Nova instances

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 3 - Cross-Nova Integration
"""

import redis
import json
import uuid
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger('novawf.cross_nova')

class CoordinationType(Enum):
    """Types of cross-Nova coordination"""
    WORK_REQUEST = "work_request"
    COLLABORATION_REQUEST = "collaboration_request"
    KNOWLEDGE_SHARE = "knowledge_share"
    STATUS_UPDATE = "status_update"
    RESOURCE_REQUEST = "resource_request"
    EMERGENCY_ASSIST = "emergency_assist"

class RequestPriority(Enum):
    """Priority levels for coordination requests"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKGROUND = 5

@dataclass
class CoordinationRequest:
    """Cross-Nova coordination request"""
    request_id: str
    request_type: CoordinationType
    priority: RequestPriority
    from_nova: str
    to_nova: Optional[str]  # None means broadcast
    subject: str
    details: Dict[str, Any]
    created_at: str
    expires_at: Optional[str] = None
    response_required: bool = True
    
    def to_stream_format(self) -> Dict[str, str]:
        """Convert to Redis stream format"""
        data = {
            'request_id': self.request_id,
            'request_type': self.request_type.value,
            'priority': str(self.priority.value),
            'from_nova': self.from_nova,
            'subject': self.subject,
            'details': json.dumps(self.details),
            'created_at': self.created_at,
            'response_required': str(self.response_required)
        }
        
        if self.to_nova:
            data['to_nova'] = self.to_nova
        if self.expires_at:
            data['expires_at'] = self.expires_at
            
        return data

@dataclass
class CoordinationResponse:
    """Response to coordination request"""
    response_id: str
    request_id: str
    from_nova: str
    status: str  # accepted, declined, acknowledged
    message: str
    data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    
    def to_stream_format(self) -> Dict[str, str]:
        """Convert to Redis stream format"""
        data = {
            'response_id': self.response_id,
            'request_id': self.request_id,
            'from_nova': self.from_nova,
            'status': self.status,
            'message': self.message,
            'created_at': self.created_at or datetime.now().isoformat()
        }
        
        if self.data:
            data['data'] = json.dumps(self.data)
            
        return data

class CrossNovaCoordinator:
    """
    Manages cross-Nova coordination and collaboration.
    Enables work distribution, knowledge sharing, and emergency assistance.
    """
    
    # Coordination streams
    STREAMS = {
        'broadcast': 'nova.cross.coordination',
        'emergency': 'nova.emergency.coordination',
        'knowledge': 'nova.knowledge.share'
    }
    
    # Response timeout defaults (seconds)
    TIMEOUTS = {
        CoordinationType.EMERGENCY_ASSIST: 60,      # 1 minute
        CoordinationType.WORK_REQUEST: 300,         # 5 minutes
        CoordinationType.COLLABORATION_REQUEST: 600, # 10 minutes
        CoordinationType.KNOWLEDGE_SHARE: 1800,     # 30 minutes
        CoordinationType.STATUS_UPDATE: 0,          # No response needed
        CoordinationType.RESOURCE_REQUEST: 300      # 5 minutes
    }
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id.lower()
        self.redis_client = redis.Redis(
            host='localhost',
            port=redis_port,
            decode_responses=True,
            password='adapt123'
        )
        
        # Personal coordination stream
        self.personal_stream = f'nova.coordination.{self.nova_id}'
        
        # Track pending requests
        self.pending_requests = {}
        
        # Nova registry cache
        self.nova_registry = self._load_nova_registry()
        
        logger.info(f"Cross-Nova coordinator initialized for {nova_id}")
    
    def send_work_request(self, work_description: str, required_skills: List[str] = None,
                         target_nova: Optional[str] = None, priority: RequestPriority = RequestPriority.MEDIUM) -> str:
        """
        Request help with work from other Novas.
        Returns request_id for tracking.
        """
        request = CoordinationRequest(
            request_id=f"WORK-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_type=CoordinationType.WORK_REQUEST,
            priority=priority,
            from_nova=self.nova_id,
            to_nova=target_nova,
            subject=f"Work assistance needed: {work_description[:50]}",
            details={
                'work_description': work_description,
                'required_skills': required_skills or [],
                'estimated_effort': 'medium',
                'can_be_split': True
            },
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(seconds=self.TIMEOUTS[CoordinationType.WORK_REQUEST])).isoformat()
        )
        
        # Post to appropriate stream
        stream = self.personal_stream if target_nova else self.STREAMS['broadcast']
        self.redis_client.xadd(stream, request.to_stream_format())
        
        # Track pending request
        self.pending_requests[request.request_id] = request
        
        logger.info(f"Sent work request {request.request_id} to {target_nova or 'all Novas'}")
        
        return request.request_id
    
    def request_collaboration(self, project: str, role_needed: str, 
                            duration_estimate: str = "1-2 hours", 
                            target_nova: Optional[str] = None) -> str:
        """Request collaboration on a project"""
        request = CoordinationRequest(
            request_id=f"COLLAB-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_type=CoordinationType.COLLABORATION_REQUEST,
            priority=RequestPriority.HIGH,
            from_nova=self.nova_id,
            to_nova=target_nova,
            subject=f"Collaboration needed on {project}",
            details={
                'project': project,
                'role_needed': role_needed,
                'duration_estimate': duration_estimate,
                'collaboration_type': 'synchronous',
                'communication_stream': f'nova.collab.{project.lower().replace(" ", "_")}'
            },
            created_at=datetime.now().isoformat()
        )
        
        stream = f'nova.coordination.{target_nova}' if target_nova else self.STREAMS['broadcast']
        self.redis_client.xadd(stream, request.to_stream_format())
        
        self.pending_requests[request.request_id] = request
        
        logger.info(f"Sent collaboration request {request.request_id} for project {project}")
        
        return request.request_id
    
    def share_knowledge(self, topic: str, knowledge_type: str, content: Dict[str, Any]) -> str:
        """Share knowledge with other Novas"""
        request = CoordinationRequest(
            request_id=f"KNOW-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_type=CoordinationType.KNOWLEDGE_SHARE,
            priority=RequestPriority.LOW,
            from_nova=self.nova_id,
            to_nova=None,  # Always broadcast knowledge
            subject=f"Knowledge share: {topic}",
            details={
                'topic': topic,
                'knowledge_type': knowledge_type,  # 'solution', 'pattern', 'warning', 'optimization'
                'content': content,
                'tags': self._extract_knowledge_tags(topic, content)
            },
            created_at=datetime.now().isoformat(),
            response_required=False
        )
        
        self.redis_client.xadd(self.STREAMS['knowledge'], request.to_stream_format())
        
        logger.info(f"Shared knowledge about {topic}")
        
        return request.request_id
    
    def broadcast_status(self, status: str, metrics: Dict[str, Any] = None):
        """Broadcast status update to all Novas"""
        request = CoordinationRequest(
            request_id=f"STATUS-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_type=CoordinationType.STATUS_UPDATE,
            priority=RequestPriority.BACKGROUND,
            from_nova=self.nova_id,
            to_nova=None,
            subject=f"Status update from {self.nova_id}",
            details={
                'status': status,
                'metrics': metrics or {},
                'capabilities': self._get_current_capabilities(),
                'availability': self._calculate_availability()
            },
            created_at=datetime.now().isoformat(),
            response_required=False
        )
        
        self.redis_client.xadd(self.STREAMS['broadcast'], request.to_stream_format())
        
        # Update nova registry
        self._update_nova_registry(status, metrics)
    
    def request_emergency_assistance(self, issue: str, severity: str = "high") -> str:
        """Request emergency help from any available Nova"""
        request = CoordinationRequest(
            request_id=f"EMRG-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_type=CoordinationType.EMERGENCY_ASSIST,
            priority=RequestPriority.CRITICAL,
            from_nova=self.nova_id,
            to_nova=None,  # Broadcast to all
            subject=f"EMERGENCY: {issue[:50]}",
            details={
                'issue': issue,
                'severity': severity,
                'timestamp': datetime.now().isoformat(),
                'immediate_action_needed': True
            },
            created_at=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(seconds=self.TIMEOUTS[CoordinationType.EMERGENCY_ASSIST])).isoformat()
        )
        
        # Post to emergency stream
        self.redis_client.xadd(self.STREAMS['emergency'], request.to_stream_format())
        
        # Also post to broadcast for visibility
        self.redis_client.xadd(self.STREAMS['broadcast'], request.to_stream_format())
        
        self.pending_requests[request.request_id] = request
        
        logger.critical(f"Sent emergency request {request.request_id}: {issue}")
        
        return request.request_id
    
    def check_incoming_requests(self) -> List[CoordinationRequest]:
        """Check for incoming coordination requests"""
        incoming_requests = []
        
        # Check personal stream
        personal_messages = self.redis_client.xread({self.personal_stream: '$'}, block=0, count=10)
        
        # Check broadcast streams
        broadcast_messages = self.redis_client.xread({
            self.STREAMS['broadcast']: '$',
            self.STREAMS['emergency']: '$'
        }, block=0, count=10)
        
        # Parse all messages
        all_messages = personal_messages + broadcast_messages
        
        for stream, messages in all_messages:
            for msg_id, fields in messages:
                # Skip if from self
                if fields.get('from_nova') == self.nova_id:
                    continue
                
                # Skip if targeted to someone else
                if 'to_nova' in fields and fields['to_nova'] != self.nova_id:
                    continue
                
                # Parse request
                try:
                    request = self._parse_coordination_request(fields)
                    if request:
                        incoming_requests.append(request)
                except Exception as e:
                    logger.error(f"Failed to parse coordination request: {e}")
        
        return incoming_requests
    
    def respond_to_request(self, request_id: str, accept: bool, 
                          message: str = "", data: Dict[str, Any] = None) -> str:
        """Respond to a coordination request"""
        response = CoordinationResponse(
            response_id=f"RESP-{self.nova_id.upper()}-{uuid.uuid4().hex[:8]}",
            request_id=request_id,
            from_nova=self.nova_id,
            status='accepted' if accept else 'declined',
            message=message or f"Request {'accepted' if accept else 'declined'} by {self.nova_id}",
            data=data
        )
        
        # Find original request to determine response stream
        # (In production, would query from stream history)
        response_stream = 'nova.cross.responses'
        
        self.redis_client.xadd(response_stream, response.to_stream_format())
        
        logger.info(f"Responded to request {request_id}: {response.status}")
        
        return response.response_id
    
    def get_available_novas(self) -> List[Dict[str, Any]]:
        """Get list of available Novas and their capabilities"""
        available = []
        
        # Check nova registry
        for nova_id, info in self.nova_registry.items():
            if nova_id == self.nova_id:
                continue
            
            # Check if recently active (within 5 minutes)
            last_seen = info.get('last_seen')
            if last_seen:
                last_seen_time = datetime.fromisoformat(last_seen)
                if datetime.now() - last_seen_time < timedelta(minutes=5):
                    available.append({
                        'nova_id': nova_id,
                        'status': info.get('status', 'unknown'),
                        'capabilities': info.get('capabilities', []),
                        'availability': info.get('availability', 0),
                        'last_seen': last_seen
                    })
        
        return available
    
    def _parse_coordination_request(self, fields: Dict) -> Optional[CoordinationRequest]:
        """Parse coordination request from stream fields"""
        try:
            return CoordinationRequest(
                request_id=fields['request_id'],
                request_type=CoordinationType(fields['request_type']),
                priority=RequestPriority(int(fields['priority'])),
                from_nova=fields['from_nova'],
                to_nova=fields.get('to_nova'),
                subject=fields['subject'],
                details=json.loads(fields['details']),
                created_at=fields['created_at'],
                expires_at=fields.get('expires_at'),
                response_required=fields.get('response_required', 'True') == 'True'
            )
        except Exception as e:
            logger.error(f"Failed to parse request: {e}")
            return None
    
    def _load_nova_registry(self) -> Dict[str, Dict]:
        """Load Nova registry from Redis"""
        try:
            registry_data = self.redis_client.get('nova:registry')
            if registry_data:
                return json.loads(registry_data)
        except:
            pass
        
        return {}
    
    def _update_nova_registry(self, status: str, metrics: Dict[str, Any] = None):
        """Update Nova's entry in the registry"""
        self.nova_registry[self.nova_id] = {
            'status': status,
            'last_seen': datetime.now().isoformat(),
            'capabilities': self._get_current_capabilities(),
            'availability': self._calculate_availability(),
            'metrics': metrics or {}
        }
        
        try:
            self.redis_client.set('nova:registry', json.dumps(self.nova_registry))
        except Exception as e:
            logger.error(f"Failed to update nova registry: {e}")
    
    def _get_current_capabilities(self) -> List[str]:
        """Get current Nova capabilities"""
        # This would be personalized per Nova
        base_capabilities = [
            'task_execution',
            'stream_monitoring',
            'safety_compliance'
        ]
        
        # Add Nova-specific capabilities
        if self.nova_id == 'torch':
            base_capabilities.extend(['workflow_orchestration', 'safety_testing'])
        elif self.nova_id == 'echo':
            base_capabilities.extend(['communication', 'coordination'])
        
        return base_capabilities
    
    def _calculate_availability(self) -> float:
        """Calculate current availability (0-1)"""
        # In production, would check actual workload
        # For now, return a reasonable default
        return 0.8
    
    def _extract_knowledge_tags(self, topic: str, content: Dict) -> List[str]:
        """Extract tags from knowledge content"""
        tags = [topic.lower()]
        
        # Extract additional tags from content
        if 'technology' in content:
            tags.append(content['technology'])
        if 'category' in content:
            tags.append(content['category'])
        
        return tags

if __name__ == "__main__":
    # Test cross-Nova coordination
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    coordinator = CrossNovaCoordinator(nova_id)
    
    # Test sending work request
    print(f"=== Testing Cross-Nova Coordination for {nova_id} ===\n")
    
    # Send work request
    request_id = coordinator.send_work_request(
        "Need help optimizing API performance",
        required_skills=["performance", "optimization"],
        priority=RequestPriority.HIGH
    )
    print(f"Sent work request: {request_id}")
    
    # Share knowledge
    knowledge_id = coordinator.share_knowledge(
        "API Rate Limiting Best Practices",
        "pattern",
        {
            "pattern": "exponential_backoff",
            "description": "Use exponential backoff with jitter for rate limiting",
            "implementation": "backoff = base * 2^attempts + random_jitter"
        }
    )
    print(f"Shared knowledge: {knowledge_id}")
    
    # Check available Novas
    available = coordinator.get_available_novas()
    print(f"\nAvailable Novas: {len(available)}")
    for nova in available:
        print(f"  - {nova['nova_id']}: {nova['status']} (availability: {nova['availability']})")