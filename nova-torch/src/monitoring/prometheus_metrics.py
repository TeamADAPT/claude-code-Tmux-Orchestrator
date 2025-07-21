"""
Prometheus Metrics for Nova-Torch
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Comprehensive metrics collection for monitoring system performance
"""

import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from prometheus_client import (
    Counter, Histogram, Gauge, Info, Enum,
    start_http_server, CollectorRegistry, generate_latest
)
import threading

logger = logging.getLogger(__name__)


class PrometheusMetrics:
    """
    Centralized Prometheus metrics collection for Nova-Torch
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None, namespace: str = "nova_torch"):
        """Initialize Prometheus metrics"""
        self.registry = registry or CollectorRegistry()
        self.namespace = namespace
        self._server_thread = None
        self._metrics_port = None
        
        # Initialize all metrics
        self._init_system_metrics()
        self._init_agent_metrics()
        self._init_task_metrics()
        self._init_communication_metrics()
        self._init_orchestrator_metrics()
        
        logger.info("Prometheus metrics initialized")
    
    def _init_system_metrics(self):
        """Initialize system-level metrics"""
        # System info
        self.system_info = Info(
            f'{self.namespace}_system',
            'Nova-Torch system information',
            registry=self.registry
        )
        
        # Uptime
        self.uptime_seconds = Gauge(
            f'{self.namespace}_uptime_seconds',
            'System uptime in seconds',
            registry=self.registry
        )
        
        # Component status
        self.component_status = Enum(
            f'{self.namespace}_component_status',
            'Status of system components',
            ['component'],
            states=['starting', 'running', 'stopping', 'stopped', 'error'],
            registry=self.registry
        )
        
        # Memory usage
        self.memory_usage_bytes = Gauge(
            f'{self.namespace}_memory_usage_bytes',
            'Memory usage in bytes',
            ['component'],
            registry=self.registry
        )
    
    def _init_agent_metrics(self):
        """Initialize agent-related metrics"""
        # Agent counts
        self.agents_total = Gauge(
            f'{self.namespace}_agents_total',
            'Total number of registered agents',
            ['status'],
            registry=self.registry
        )
        
        # Agent lifecycle
        self.agent_registrations_total = Counter(
            f'{self.namespace}_agent_registrations_total',
            'Total agent registrations',
            ['role'],
            registry=self.registry
        )
        
        self.agent_deregistrations_total = Counter(
            f'{self.namespace}_agent_deregistrations_total',
            'Total agent deregistrations',
            ['role', 'reason'],
            registry=self.registry
        )
        
        # Agent performance
        self.agent_task_completion_time = Histogram(
            f'{self.namespace}_agent_task_completion_seconds',
            'Agent task completion time',
            ['agent_id', 'task_type'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry
        )
        
        self.agent_success_rate = Gauge(
            f'{self.namespace}_agent_success_rate',
            'Agent task success rate',
            ['agent_id'],
            registry=self.registry
        )
        
        # Heartbeats
        self.agent_heartbeats_total = Counter(
            f'{self.namespace}_agent_heartbeats_total',
            'Total agent heartbeats',
            ['agent_id'],
            registry=self.registry
        )
        
        self.agent_heartbeat_failures_total = Counter(
            f'{self.namespace}_agent_heartbeat_failures_total',
            'Total agent heartbeat failures',
            ['agent_id'],
            registry=self.registry
        )
        
        # Agent spawning
        self.agent_spawns_total = Counter(
            f'{self.namespace}_agent_spawns_total',
            'Total agent spawns',
            ['role', 'reason'],
            registry=self.registry
        )
        
        self.agent_spawn_time = Histogram(
            f'{self.namespace}_agent_spawn_seconds',
            'Time to spawn a new agent',
            ['role'],
            buckets=[1, 2, 5, 10, 20, 30, 60],
            registry=self.registry
        )
    
    def _init_task_metrics(self):
        """Initialize task-related metrics"""
        # Task counts
        self.tasks_total = Gauge(
            f'{self.namespace}_tasks_total',
            'Total number of tasks',
            ['status'],
            registry=self.registry
        )
        
        # Task lifecycle
        self.task_submissions_total = Counter(
            f'{self.namespace}_task_submissions_total',
            'Total task submissions',
            ['task_type', 'priority'],
            registry=self.registry
        )
        
        self.task_completions_total = Counter(
            f'{self.namespace}_task_completions_total',
            'Total task completions',
            ['task_type', 'status'],
            registry=self.registry
        )
        
        # Task performance
        self.task_duration_seconds = Histogram(
            f'{self.namespace}_task_duration_seconds',
            'Task execution duration',
            ['task_type'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800, 3600],
            registry=self.registry
        )
        
        self.task_queue_time_seconds = Histogram(
            f'{self.namespace}_task_queue_time_seconds',
            'Time tasks spend in queue',
            ['priority'],
            buckets=[0.1, 0.5, 1, 5, 10, 30, 60, 300],
            registry=self.registry
        )
        
        # Task assignment
        self.task_assignments_total = Counter(
            f'{self.namespace}_task_assignments_total',
            'Total task assignments',
            ['agent_id', 'task_type'],
            registry=self.registry
        )
        
        self.task_assignment_time = Histogram(
            f'{self.namespace}_task_assignment_seconds',
            'Time to assign tasks to agents',
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5],
            registry=self.registry
        )
    
    def _init_communication_metrics(self):
        """Initialize communication metrics"""
        # Message counts
        self.messages_sent_total = Counter(
            f'{self.namespace}_messages_sent_total',
            'Total messages sent',
            ['message_type', 'target_type'],
            registry=self.registry
        )
        
        self.messages_received_total = Counter(
            f'{self.namespace}_messages_received_total',
            'Total messages received',
            ['message_type', 'sender_type'],
            registry=self.registry
        )
        
        # Message performance
        self.message_send_duration = Histogram(
            f'{self.namespace}_message_send_seconds',
            'Time to send messages',
            ['message_type'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1],
            registry=self.registry
        )
        
        self.message_roundtrip_duration = Histogram(
            f'{self.namespace}_message_roundtrip_seconds',
            'Message request-response roundtrip time',
            ['message_type'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10],
            registry=self.registry
        )
        
        # Message failures
        self.message_send_failures_total = Counter(
            f'{self.namespace}_message_send_failures_total',
            'Total message send failures',
            ['message_type', 'error_type'],
            registry=self.registry
        )
        
        self.message_timeouts_total = Counter(
            f'{self.namespace}_message_timeouts_total',
            'Total message timeouts',
            ['message_type'],
            registry=self.registry
        )
        
        # Stream metrics
        self.stream_messages_total = Counter(
            f'{self.namespace}_stream_messages_total',
            'Total stream messages',
            ['stream_name', 'operation'],
            registry=self.registry
        )
        
        self.stream_lag_seconds = Gauge(
            f'{self.namespace}_stream_lag_seconds',
            'Stream consumer lag',
            ['stream_name', 'consumer_group'],
            registry=self.registry
        )
    
    def _init_orchestrator_metrics(self):
        """Initialize orchestrator metrics"""
        # Orchestrator status
        self.orchestrator_status = Enum(
            f'{self.namespace}_orchestrator_status',
            'Orchestrator status',
            states=['starting', 'running', 'stopping', 'stopped', 'error'],
            registry=self.registry
        )
        
        # Collaboration metrics
        self.collaborations_total = Counter(
            f'{self.namespace}_collaborations_total',
            'Total agent collaborations',
            ['collaboration_type', 'status'],
            registry=self.registry
        )
        
        self.team_formations_total = Counter(
            f'{self.namespace}_team_formations_total',
            'Total team formations',
            ['team_size'],
            registry=self.registry
        )
        
        # Resource utilization
        self.resource_utilization = Gauge(
            f'{self.namespace}_resource_utilization',
            'Resource utilization percentage',
            ['resource_type'],
            registry=self.registry
        )
        
        # Error rates
        self.error_rate = Gauge(
            f'{self.namespace}_error_rate',
            'Error rate per minute',
            ['component'],
            registry=self.registry
        )
    
    def start_metrics_server(self, port: int = 8000):
        """Start Prometheus metrics HTTP server"""
        try:
            # Start server in background thread
            self._metrics_port = port
            self._server_thread = threading.Thread(
                target=self._start_server,
                args=(port,),
                daemon=True
            )
            self._server_thread.start()
            
            # Set system info
            self.system_info.info({
                'version': '0.2.0',
                'component': 'nova-torch',
                'environment': 'production',
                'metrics_port': str(port),
                'started_at': datetime.utcnow().isoformat()
            })
            
            # Set initial component status
            self.component_status.labels(component='metrics').state('running')
            
            logger.info(f"Prometheus metrics server started on port {port}")
            
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise
    
    def _start_server(self, port: int):
        """Start the actual HTTP server"""
        start_http_server(port, registry=self.registry)
    
    def stop_metrics_server(self):
        """Stop metrics server"""
        # Note: prometheus_client doesn't provide a direct way to stop the server
        # In production, this would be handled by the container orchestrator
        self.component_status.labels(component='metrics').state('stopped')
        logger.info("Metrics server marked as stopped")
    
    # Agent metrics methods
    def record_agent_registration(self, agent_id: str, role: str):
        """Record agent registration"""
        self.agent_registrations_total.labels(role=role).inc()
        self.agents_total.labels(status='active').inc()
        logger.debug(f"Recorded agent registration: {agent_id} ({role})")
    
    def record_agent_deregistration(self, agent_id: str, role: str, reason: str):
        """Record agent deregistration"""
        self.agent_deregistrations_total.labels(role=role, reason=reason).inc()
        self.agents_total.labels(status='active').dec()
        logger.debug(f"Recorded agent deregistration: {agent_id} ({reason})")
    
    def record_agent_heartbeat(self, agent_id: str, success: bool = True):
        """Record agent heartbeat"""
        if success:
            self.agent_heartbeats_total.labels(agent_id=agent_id).inc()
        else:
            self.agent_heartbeat_failures_total.labels(agent_id=agent_id).inc()
    
    def record_agent_spawn(self, role: str, reason: str, spawn_time: float):
        """Record agent spawn"""
        self.agent_spawns_total.labels(role=role, reason=reason).inc()
        self.agent_spawn_time.labels(role=role).observe(spawn_time)
    
    def update_agent_success_rate(self, agent_id: str, success_rate: float):
        """Update agent success rate"""
        self.agent_success_rate.labels(agent_id=agent_id).set(success_rate)
    
    def record_agent_task_completion(self, agent_id: str, task_type: str, duration: float):
        """Record agent task completion"""
        self.agent_task_completion_time.labels(
            agent_id=agent_id, 
            task_type=task_type
        ).observe(duration)
    
    # Task metrics methods
    def record_task_submission(self, task_type: str, priority: str):
        """Record task submission"""
        self.task_submissions_total.labels(task_type=task_type, priority=priority).inc()
        self.tasks_total.labels(status='pending').inc()
    
    def record_task_completion(self, task_type: str, status: str, duration: float):
        """Record task completion"""
        self.task_completions_total.labels(task_type=task_type, status=status).inc()
        self.task_duration_seconds.labels(task_type=task_type).observe(duration)
        self.tasks_total.labels(status='pending').dec()
        self.tasks_total.labels(status=status).inc()
    
    def record_task_assignment(self, agent_id: str, task_type: str, assignment_time: float):
        """Record task assignment"""
        self.task_assignments_total.labels(agent_id=agent_id, task_type=task_type).inc()
        self.task_assignment_time.observe(assignment_time)
    
    def record_task_queue_time(self, priority: str, queue_time: float):
        """Record time task spent in queue"""
        self.task_queue_time_seconds.labels(priority=priority).observe(queue_time)
    
    # Communication metrics methods
    def record_message_sent(self, message_type: str, target_type: str, duration: float):
        """Record message sent"""
        self.messages_sent_total.labels(
            message_type=message_type, 
            target_type=target_type
        ).inc()
        self.message_send_duration.labels(message_type=message_type).observe(duration)
    
    def record_message_received(self, message_type: str, sender_type: str):
        """Record message received"""
        self.messages_received_total.labels(
            message_type=message_type,
            sender_type=sender_type
        ).inc()
    
    def record_message_roundtrip(self, message_type: str, duration: float):
        """Record message roundtrip time"""
        self.message_roundtrip_duration.labels(message_type=message_type).observe(duration)
    
    def record_message_failure(self, message_type: str, error_type: str):
        """Record message send failure"""
        self.message_send_failures_total.labels(
            message_type=message_type,
            error_type=error_type
        ).inc()
    
    def record_message_timeout(self, message_type: str):
        """Record message timeout"""
        self.message_timeouts_total.labels(message_type=message_type).inc()
    
    def record_stream_operation(self, stream_name: str, operation: str):
        """Record stream operation"""
        self.stream_messages_total.labels(
            stream_name=stream_name,
            operation=operation
        ).inc()
    
    def update_stream_lag(self, stream_name: str, consumer_group: str, lag_seconds: float):
        """Update stream consumer lag"""
        self.stream_lag_seconds.labels(
            stream_name=stream_name,
            consumer_group=consumer_group
        ).set(lag_seconds)
    
    # Orchestrator metrics methods
    def set_orchestrator_status(self, status: str):
        """Set orchestrator status"""
        self.orchestrator_status.state(status)
    
    def record_collaboration(self, collaboration_type: str, status: str):
        """Record agent collaboration"""
        self.collaborations_total.labels(
            collaboration_type=collaboration_type,
            status=status
        ).inc()
    
    def record_team_formation(self, team_size: int):
        """Record team formation"""
        self.team_formations_total.labels(team_size=str(team_size)).inc()
    
    def update_resource_utilization(self, resource_type: str, utilization: float):
        """Update resource utilization"""
        self.resource_utilization.labels(resource_type=resource_type).set(utilization)
    
    def update_error_rate(self, component: str, error_rate: float):
        """Update error rate"""
        self.error_rate.labels(component=component).set(error_rate)
    
    def update_uptime(self, start_time: float):
        """Update system uptime"""
        uptime = time.time() - start_time
        self.uptime_seconds.set(uptime)
    
    def update_memory_usage(self, component: str, memory_bytes: int):
        """Update memory usage"""
        self.memory_usage_bytes.labels(component=component).set(memory_bytes)
    
    def get_metrics_text(self) -> str:
        """Get metrics in Prometheus text format"""
        return generate_latest(self.registry).decode('utf-8')
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get high-level metrics summary"""
        try:
            # This would collect current values from gauges
            # Implementation would depend on specific requirements
            return {
                "timestamp": time.time(),
                "uptime": self.uptime_seconds._value._value if hasattr(self.uptime_seconds, '_value') else 0,
                "agents": {
                    "total": sum(self.agents_total._metrics.values()) if hasattr(self.agents_total, '_metrics') else 0,
                    "registrations": sum(self.agent_registrations_total._metrics.values()) if hasattr(self.agent_registrations_total, '_metrics') else 0
                },
                "tasks": {
                    "submissions": sum(self.task_submissions_total._metrics.values()) if hasattr(self.task_submissions_total, '_metrics') else 0,
                    "completions": sum(self.task_completions_total._metrics.values()) if hasattr(self.task_completions_total, '_metrics') else 0
                },
                "messages": {
                    "sent": sum(self.messages_sent_total._metrics.values()) if hasattr(self.messages_sent_total, '_metrics') else 0,
                    "received": sum(self.messages_received_total._metrics.values()) if hasattr(self.messages_received_total, '_metrics') else 0
                }
            }
        except Exception as e:
            logger.error(f"Error getting metrics summary: {e}")
            return {
                "error": str(e),
                "timestamp": time.time()
            }