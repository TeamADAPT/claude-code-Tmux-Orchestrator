#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Task Tracking Protocol Compliance
Ensures 100% NOVA Task Tracking Protocol compliance with automated reporting

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 2 - Core Implementation
"""

import redis
import json
import time
import uuid
import logging
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger('novawf.task_tracker')

class TaskStatus(Enum):
    """NOVA protocol task statuses"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    """NOVA protocol priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class NOVATask:
    """NOVA protocol compliant task structure"""
    task_id: str
    title: str
    description: str
    status: TaskStatus
    priority: TaskPriority
    assignee: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    blocked_reason: Optional[str] = None
    progress_percentage: Optional[int] = None
    results: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    parent_task_id: Optional[str] = None
    subtask_ids: Optional[List[str]] = None
    
    def to_stream_format(self) -> Dict[str, str]:
        """Convert to Redis stream format"""
        data = {
            'task_id': self.task_id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'assignee': self.assignee,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # Add optional fields
        if self.started_at:
            data['started_at'] = self.started_at
        if self.completed_at:
            data['completed_at'] = self.completed_at
        if self.blocked_reason:
            data['blocked_reason'] = self.blocked_reason
        if self.progress_percentage is not None:
            data['progress_percentage'] = str(self.progress_percentage)
        if self.results:
            data['results'] = self.results
        if self.metrics:
            data['metrics'] = json.dumps(self.metrics)
        if self.tags:
            data['tags'] = json.dumps(self.tags)
        if self.parent_task_id:
            data['parent_task_id'] = self.parent_task_id
        if self.subtask_ids:
            data['subtask_ids'] = json.dumps(self.subtask_ids)
            
        return data

class NOVAProtocolValidator:
    """Validates task data for NOVA protocol compliance"""
    
    REQUIRED_FIELDS = ['task_id', 'title', 'status', 'assignee', 'created_at']
    VALID_STATUSES = [s.value for s in TaskStatus]
    VALID_PRIORITIES = [p.value for p in TaskPriority]
    
    def validate_task_data(self, task_data: Dict) -> Tuple[bool, List[str]]:
        """Validate task data for protocol compliance"""
        errors = []
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in task_data or not task_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Validate status
        if 'status' in task_data and task_data['status'] not in self.VALID_STATUSES:
            errors.append(f"Invalid status: {task_data['status']}")
        
        # Validate priority if present
        if 'priority' in task_data and task_data['priority'] not in self.VALID_PRIORITIES:
            errors.append(f"Invalid priority: {task_data['priority']}")
        
        # Validate task_id format
        if 'task_id' in task_data:
            if not self._validate_task_id_format(task_data['task_id']):
                errors.append(f"Invalid task_id format: {task_data['task_id']}")
        
        # Validate timestamps
        for field in ['created_at', 'updated_at', 'started_at', 'completed_at']:
            if field in task_data and task_data[field]:
                if not self._validate_timestamp(task_data[field]):
                    errors.append(f"Invalid timestamp format for {field}: {task_data[field]}")
        
        return len(errors) == 0, errors
    
    def _validate_task_id_format(self, task_id: str) -> bool:
        """Validate NOVA task ID format: NOVA-timestamp-hash"""
        parts = task_id.split('-')
        return len(parts) >= 3 and parts[0].isupper()
    
    def _validate_timestamp(self, timestamp: str) -> bool:
        """Validate ISO 8601 timestamp"""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False

class TaskTracker:
    """
    Core task tracking system ensuring 100% NOVA protocol compliance
    with enterprise reporting and cross-Nova coordination
    """
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id.upper()  # Nova IDs are uppercase in task IDs
        self.redis_client = redis.Redis(
            host='localhost', 
            port=redis_port, 
            decode_responses=True, 
            password='adapt123'
        )
        
        # Stream keys
        self.streams = {
            'todo': f'nova.tasks.{nova_id}.todo',
            'progress': f'nova.tasks.{nova_id}.progress',
            'completed': f'nova.tasks.{nova_id}.completed',
            'blocked': f'nova.tasks.{nova_id}.blocked'
        }
        
        # Protocol validator
        self.protocol_validator = NOVAProtocolValidator()
        
        # Task cache for performance
        self.task_cache = {}
        
        logger.info(f"Task Tracker initialized for {nova_id} with NOVA protocol compliance")
    
    def create_task(self, title: str, description: str, 
                   priority: TaskPriority = TaskPriority.MEDIUM,
                   tags: List[str] = None,
                   parent_task_id: Optional[str] = None) -> str:
        """
        Create a new task following NOVA protocol
        Returns the task_id
        """
        # Generate NOVA-compliant task ID
        timestamp = int(time.time())
        unique_hash = uuid.uuid4().hex[:6]
        task_id = f"{self.nova_id}-{timestamp}-{unique_hash}"
        
        # Create task object
        task = NOVATask(
            task_id=task_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            priority=priority,
            assignee=self.nova_id.lower(),
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=tags,
            parent_task_id=parent_task_id
        )
        
        # Validate protocol compliance
        is_valid, errors = self.protocol_validator.validate_task_data(task.to_stream_format())
        if not is_valid:
            raise ValueError(f"Task data violates NOVA protocol: {errors}")
        
        # Post to todo stream
        self.redis_client.xadd(
            self.streams['todo'],
            task.to_stream_format()
        )
        
        # Cache the task
        self.task_cache[task_id] = task
        
        # Update enterprise metrics
        self._update_enterprise_metrics('task_created', {
            'task_id': task_id,
            'priority': priority.value,
            'has_parent': parent_task_id is not None
        })
        
        # Log creation
        logger.info(f"Created NOVA-compliant task: {task_id} - {title}")
        
        return task_id
    
    def start_task(self, task_id: str) -> bool:
        """Mark task as in progress"""
        try:
            # Get current task state
            task = self._get_task(task_id)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return False
            
            # Update status
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = datetime.now().isoformat()
            task.updated_at = datetime.now().isoformat()
            
            # Post to progress stream
            self.redis_client.xadd(
                self.streams['progress'],
                {
                    'task_id': task_id,
                    'status': TaskStatus.IN_PROGRESS.value,
                    'started_at': task.started_at,
                    'updated_at': task.updated_at,
                    'assignee': self.nova_id.lower()
                }
            )
            
            # Update cache
            self.task_cache[task_id] = task
            
            # Update metrics
            self._update_enterprise_metrics('task_started', {'task_id': task_id})
            
            logger.info(f"Started task: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start task {task_id}: {e}")
            return False
    
    def update_progress(self, task_id: str, update_message: str, 
                       progress_percentage: Optional[int] = None) -> bool:
        """Update task progress with NOVA protocol compliance"""
        try:
            # Validate progress percentage
            if progress_percentage is not None:
                if not 0 <= progress_percentage <= 100:
                    logger.warning(f"Invalid progress percentage: {progress_percentage}")
                    progress_percentage = max(0, min(100, progress_percentage))
            
            # Create progress update
            progress_data = {
                'task_id': task_id,
                'status': TaskStatus.IN_PROGRESS.value,
                'update': update_message,
                'updated_at': datetime.now().isoformat(),
                'assignee': self.nova_id.lower()
            }
            
            if progress_percentage is not None:
                progress_data['progress_percentage'] = str(progress_percentage)
            
            # Post to progress stream
            self.redis_client.xadd(
                self.streams['progress'],
                progress_data
            )
            
            # Update cached task
            if task_id in self.task_cache:
                self.task_cache[task_id].updated_at = progress_data['updated_at']
                if progress_percentage is not None:
                    self.task_cache[task_id].progress_percentage = progress_percentage
            
            # Update metrics
            self._update_enterprise_metrics('task_progress', {
                'task_id': task_id,
                'has_percentage': progress_percentage is not None
            })
            
            logger.info(f"Updated progress for task {task_id}: {update_message}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update progress for {task_id}: {e}")
            return False
    
    def complete_task(self, task_id: str, results: str, 
                     metrics: Optional[Dict[str, Any]] = None) -> bool:
        """Complete task with celebration and metrics"""
        try:
            # Get task
            task = self._get_task(task_id)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return False
            
            # Update task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now().isoformat()
            task.updated_at = datetime.now().isoformat()
            task.results = results
            task.progress_percentage = 100
            
            if metrics:
                task.metrics = metrics
            
            # Calculate duration if started_at exists
            duration_minutes = None
            if task.started_at:
                start_time = datetime.fromisoformat(task.started_at)
                end_time = datetime.fromisoformat(task.completed_at)
                duration_minutes = int((end_time - start_time).total_seconds() / 60)
                
                if not task.metrics:
                    task.metrics = {}
                task.metrics['duration_minutes'] = duration_minutes
            
            # Post to completed stream
            self.redis_client.xadd(
                self.streams['completed'],
                task.to_stream_format()
            )
            
            # Trigger completion celebration
            self._trigger_completion_celebration(task)
            
            # Update enterprise metrics
            self._update_enterprise_metrics('task_completed', {
                'task_id': task_id,
                'duration_minutes': duration_minutes,
                'has_metrics': metrics is not None
            })
            
            logger.info(f"Completed task {task_id}: {results}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete task {task_id}: {e}")
            return False
    
    def block_task(self, task_id: str, reason: str) -> bool:
        """Mark task as blocked with reason"""
        try:
            # Update status
            blocked_data = {
                'task_id': task_id,
                'status': TaskStatus.BLOCKED.value,
                'blocked_reason': reason,
                'blocked_at': datetime.now().isoformat(),
                'assignee': self.nova_id.lower()
            }
            
            # Post to blocked stream
            self.redis_client.xadd(
                self.streams['blocked'],
                blocked_data
            )
            
            # Update cache
            if task_id in self.task_cache:
                self.task_cache[task_id].status = TaskStatus.BLOCKED
                self.task_cache[task_id].blocked_reason = reason
            
            # Alert for blocked tasks
            self._alert_blocked_task(task_id, reason)
            
            logger.warning(f"Task blocked: {task_id} - {reason}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to block task {task_id}: {e}")
            return False
    
    def get_active_tasks(self) -> List[NOVATask]:
        """Get all active tasks (pending and in_progress)"""
        active_tasks = []
        
        # Get from todo stream
        todo_messages = self.redis_client.xrevrange(self.streams['todo'], count=100)
        for msg_id, fields in todo_messages:
            if fields.get('status') in [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value]:
                task = self._parse_task_from_stream(fields)
                if task:
                    active_tasks.append(task)
        
        # Get from progress stream
        progress_messages = self.redis_client.xrevrange(self.streams['progress'], count=50)
        task_ids_seen = {t.task_id for t in active_tasks}
        
        for msg_id, fields in progress_messages:
            task_id = fields.get('task_id')
            if task_id and task_id not in task_ids_seen:
                task = self._get_task(task_id)
                if task and task.status == TaskStatus.IN_PROGRESS:
                    active_tasks.append(task)
        
        return active_tasks
    
    def get_task_metrics(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Get task metrics for reporting"""
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        
        # Count tasks by status
        completed_count = 0
        in_progress_count = 0
        blocked_count = 0
        total_duration = 0
        completion_times = []
        
        # Analyze completed tasks
        completed_messages = self.redis_client.xrevrange(self.streams['completed'], count=200)
        for msg_id, fields in completed_messages:
            completed_at = fields.get('completed_at')
            if completed_at:
                completed_time = datetime.fromisoformat(completed_at)
                if completed_time > cutoff_time:
                    completed_count += 1
                    
                    # Get duration if available
                    metrics_str = fields.get('metrics')
                    if metrics_str:
                        try:
                            metrics = json.loads(metrics_str)
                            if 'duration_minutes' in metrics:
                                total_duration += metrics['duration_minutes']
                                completion_times.append(metrics['duration_minutes'])
                        except:
                            pass
        
        # Count active tasks
        active_tasks = self.get_active_tasks()
        for task in active_tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                in_progress_count += 1
        
        # Count blocked tasks
        blocked_messages = self.redis_client.xrevrange(self.streams['blocked'], count=50)
        for msg_id, fields in blocked_messages:
            blocked_at = fields.get('blocked_at')
            if blocked_at:
                blocked_time = datetime.fromisoformat(blocked_at)
                if blocked_time > cutoff_time:
                    blocked_count += 1
        
        # Calculate metrics
        avg_duration = total_duration / len(completion_times) if completion_times else 0
        
        return {
            'time_window_hours': time_window_hours,
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'blocked_count': blocked_count,
            'average_duration_minutes': round(avg_duration, 1),
            'total_duration_minutes': total_duration,
            'completion_rate': round(completed_count / (completed_count + blocked_count) * 100, 1) if (completed_count + blocked_count) > 0 else 0,
            'tasks_per_hour': round(completed_count / time_window_hours, 2),
            'generated_at': datetime.now().isoformat()
        }
    
    def _get_task(self, task_id: str) -> Optional[NOVATask]:
        """Get task by ID from cache or streams"""
        # Check cache first
        if task_id in self.task_cache:
            return self.task_cache[task_id]
        
        # Search streams
        for stream_name, stream_key in self.streams.items():
            messages = self.redis_client.xrevrange(stream_key, count=1000)
            for msg_id, fields in messages:
                if fields.get('task_id') == task_id:
                    task = self._parse_task_from_stream(fields)
                    if task:
                        self.task_cache[task_id] = task
                        return task
        
        return None
    
    def _parse_task_from_stream(self, fields: Dict) -> Optional[NOVATask]:
        """Parse task from stream fields"""
        try:
            # Required fields
            task = NOVATask(
                task_id=fields['task_id'],
                title=fields['title'],
                description=fields.get('description', ''),
                status=TaskStatus(fields['status']),
                priority=TaskPriority(fields.get('priority', 'medium')),
                assignee=fields['assignee'],
                created_at=fields['created_at'],
                updated_at=fields['updated_at']
            )
            
            # Optional fields
            if 'started_at' in fields:
                task.started_at = fields['started_at']
            if 'completed_at' in fields:
                task.completed_at = fields['completed_at']
            if 'blocked_reason' in fields:
                task.blocked_reason = fields['blocked_reason']
            if 'progress_percentage' in fields:
                task.progress_percentage = int(fields['progress_percentage'])
            if 'results' in fields:
                task.results = fields['results']
            if 'metrics' in fields:
                task.metrics = json.loads(fields['metrics'])
            if 'tags' in fields:
                task.tags = json.loads(fields['tags'])
            if 'parent_task_id' in fields:
                task.parent_task_id = fields['parent_task_id']
            if 'subtask_ids' in fields:
                task.subtask_ids = json.loads(fields['subtask_ids'])
            
            return task
            
        except Exception as e:
            logger.error(f"Failed to parse task from stream: {e}")
            return None
    
    def _trigger_completion_celebration(self, task: NOVATask):
        """Trigger structured completion celebration"""
        try:
            celebration_data = {
                'type': 'TASK_COMPLETION_CELEBRATION',
                'task_id': task.task_id,
                'task_title': task.title,
                'nova_id': self.nova_id.lower(),
                'priority': task.priority.value,
                'duration_minutes': task.metrics.get('duration_minutes', 0) if task.metrics else 0,
                'timestamp': datetime.now().isoformat()
            }
            
            # Post to celebrations stream
            self.redis_client.xadd(
                f'nova.celebrations.{self.nova_id.lower()}',
                celebration_data
            )
            
            logger.info(f"🎉 Celebration triggered for task: {task.title}")
            
        except Exception as e:
            logger.error(f"Failed to trigger celebration: {e}")
    
    def _alert_blocked_task(self, task_id: str, reason: str):
        """Alert for blocked tasks requiring attention"""
        try:
            alert_data = {
                'type': 'TASK_BLOCKED_ALERT',
                'task_id': task_id,
                'blocked_reason': reason,
                'nova_id': self.nova_id.lower(),
                'timestamp': datetime.now().isoformat(),
                'severity': 'HIGH'
            }
            
            # Post to priority alerts
            self.redis_client.xadd(
                'nova.priority.alerts',
                alert_data
            )
            
        except Exception as e:
            logger.error(f"Failed to post blocked task alert: {e}")
    
    def _update_enterprise_metrics(self, metric_type: str, details: Dict):
        """Update enterprise metrics for reporting"""
        try:
            metric_data = {
                'type': f'TASK_{metric_type.upper()}',
                'nova_id': self.nova_id.lower(),
                'metric_type': metric_type,
                'timestamp': datetime.now().isoformat(),
                **details
            }
            
            # Post to enterprise metrics stream
            self.redis_client.xadd(
                'nova.enterprise.metrics',
                {k: str(v) if not isinstance(v, str) else v for k, v in metric_data.items()}
            )
            
        except Exception as e:
            logger.error(f"Failed to update enterprise metrics: {e}")
    
    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate NOVA protocol compliance report"""
        # Get recent tasks
        recent_tasks = []
        for stream_key in self.streams.values():
            messages = self.redis_client.xrevrange(stream_key, count=100)
            for msg_id, fields in messages:
                recent_tasks.append(fields)
        
        # Validate all tasks
        compliant_count = 0
        non_compliant_count = 0
        violations_by_type = {}
        
        for task_data in recent_tasks:
            is_valid, errors = self.protocol_validator.validate_task_data(task_data)
            if is_valid:
                compliant_count += 1
            else:
                non_compliant_count += 1
                for error in errors:
                    error_type = error.split(':')[0]
                    violations_by_type[error_type] = violations_by_type.get(error_type, 0) + 1
        
        compliance_percentage = (compliant_count / (compliant_count + non_compliant_count) * 100) if (compliant_count + non_compliant_count) > 0 else 100
        
        return {
            'nova_id': self.nova_id.lower(),
            'total_tasks_analyzed': len(recent_tasks),
            'compliant_tasks': compliant_count,
            'non_compliant_tasks': non_compliant_count,
            'compliance_percentage': round(compliance_percentage, 2),
            'violations_by_type': violations_by_type,
            'protocol_version': '1.0',
            'generated_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the task tracker
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing Task Tracker for {nova_id}")
    
    tracker = TaskTracker(nova_id)
    
    # Create a test task
    task_id = tracker.create_task(
        title="Test NOVA Protocol Compliance",
        description="Validate that task tracking follows NOVA protocol standards",
        priority=TaskPriority.HIGH,
        tags=["test", "protocol"]
    )
    print(f"Created task: {task_id}")
    
    # Start the task
    tracker.start_task(task_id)
    
    # Update progress
    tracker.update_progress(task_id, "Validating protocol fields", 50)
    
    # Complete the task
    tracker.complete_task(task_id, "Protocol validation successful", {
        'tests_passed': 10,
        'tests_failed': 0
    })
    
    # Get metrics
    metrics = tracker.get_task_metrics(24)
    print(f"\nTask Metrics: {json.dumps(metrics, indent=2)}")
    
    # Get compliance report
    compliance = tracker.generate_compliance_report()
    print(f"\nCompliance Report: {json.dumps(compliance, indent=2)}")