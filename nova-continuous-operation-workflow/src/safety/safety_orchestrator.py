#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Safety Orchestrator
Central coordination for all safety mechanisms

Owner: Nova Torch  
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 2 - Safety Implementation (CRITICAL)
"""

import json
import time
import redis
import logging
import psutil
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from .api_guardian import APIGuardian, SafetyValidation
from .loop_detector import LoopDetector, LoopDetectionResult

logger = logging.getLogger('novawf.safety.orchestrator')

class SafetyLevel(Enum):
    """Overall safety status levels"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    EMERGENCY = "emergency"

@dataclass
class SafetyStatus:
    """Comprehensive safety status"""
    is_safe: bool
    safety_level: SafetyLevel
    active_violations: List[str]
    recommended_actions: List[str]
    details: Dict[str, Any]
    timestamp: datetime

class ResourceMonitor:
    """Monitor system resource usage"""
    
    RESOURCE_LIMITS = {
        'memory_mb': 500,              # Max 500MB memory usage
        'cpu_percentage': 25,          # Max 25% CPU usage average
        'file_descriptors': 100,       # Max 100 open file descriptors
        'disk_io_mb_per_sec': 10,      # Max 10MB/s disk I/O
    }
    
    def __init__(self):
        self.process = psutil.Process()
        self.cpu_history = []
        
    def check_resources(self) -> Tuple[bool, Dict]:
        """Check current resource usage against limits"""
        try:
            # Memory check
            memory_mb = self.process.memory_info().rss / 1024 / 1024
            
            # CPU check (average over last 5 seconds)
            cpu_percent = self.process.cpu_percent(interval=0.1)
            self.cpu_history.append(cpu_percent)
            if len(self.cpu_history) > 50:  # Keep last 50 samples
                self.cpu_history.pop(0)
            avg_cpu = sum(self.cpu_history) / len(self.cpu_history) if self.cpu_history else 0
            
            # File descriptors
            try:
                fd_count = len(self.process.open_files())
            except:
                fd_count = 0
            
            # Check violations
            violations = []
            if memory_mb > self.RESOURCE_LIMITS['memory_mb']:
                violations.append(f"Memory usage: {memory_mb:.1f}MB > {self.RESOURCE_LIMITS['memory_mb']}MB")
            
            if avg_cpu > self.RESOURCE_LIMITS['cpu_percentage']:
                violations.append(f"CPU usage: {avg_cpu:.1f}% > {self.RESOURCE_LIMITS['cpu_percentage']}%")
            
            if fd_count > self.RESOURCE_LIMITS['file_descriptors']:
                violations.append(f"File descriptors: {fd_count} > {self.RESOURCE_LIMITS['file_descriptors']}")
            
            status = {
                'memory_mb': memory_mb,
                'cpu_percentage': avg_cpu,
                'file_descriptors': fd_count,
                'violations': violations
            }
            
            return len(violations) == 0, status
            
        except Exception as e:
            logger.error(f"Resource monitoring error: {e}")
            return True, {'error': str(e)}  # Fail open, don't block on monitoring errors

class SafetyOrchestrator:
    """
    Central safety coordination system.
    This is the master safety controller that coordinates all safety mechanisms.
    """
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(
            host='localhost', 
            port=redis_port, 
            decode_responses=True, 
            password='adapt123'
        )
        
        # Initialize safety components
        self.api_guardian = APIGuardian(nova_id, redis_port)
        self.loop_detector = LoopDetector(nova_id)
        self.resource_monitor = ResourceMonitor()
        
        # Safety state
        self.safety_level = SafetyLevel.SAFE
        self.active_violations = []
        self.last_safety_check = datetime.now()
        self.emergency_cooldown_until = None
        
        logger.info(f"Safety Orchestrator initialized for {nova_id}")
    
    def is_safe_to_proceed(self) -> bool:
        """
        Master safety check - must pass before any significant operation.
        This is the single source of truth for safety status.
        """
        try:
            # Check emergency cooldown first
            if self.emergency_cooldown_until and datetime.now() < self.emergency_cooldown_until:
                logger.warning("Emergency cooldown active")
                return False
            
            # Run all safety checks
            safety_status = self.perform_comprehensive_safety_check()
            
            # Update internal state
            self.safety_level = safety_status.safety_level
            self.active_violations = safety_status.active_violations
            self.last_safety_check = datetime.now()
            
            # Log if unsafe
            if not safety_status.is_safe:
                logger.warning(f"Safety check failed: {safety_status.active_violations}")
            
            return safety_status.is_safe
            
        except Exception as e:
            logger.error(f"Safety check error: {e}")
            # Fail closed - if we can't check safety, assume unsafe
            return False
    
    def perform_comprehensive_safety_check(self) -> SafetyStatus:
        """Perform all safety checks and return comprehensive status"""
        violations = []
        recommended_actions = []
        details = {}
        
        # 1. API Safety Check
        api_validation = self.api_guardian.validate_request_safety()
        if not api_validation.is_safe:
            violations.append(f"API: {api_validation.violation_type}")
            recommended_actions.append(api_validation.mandatory_action)
            details['api_safety'] = {
                'violation': api_validation.violation_type,
                'cooldown_required': api_validation.cooldown_required,
                'details': api_validation.details
            }
        
        # 2. Resource Check
        resource_safe, resource_status = self.resource_monitor.check_resources()
        if not resource_safe:
            violations.extend(resource_status['violations'])
            recommended_actions.append("RESOURCE_CLEANUP")
            details['resource_status'] = resource_status
        
        # 3. Loop Detection Status
        loop_status = self.loop_detector.get_detection_status()
        if loop_status['violation_count'] > 0:
            violations.append(f"Loop violations: {loop_status['violation_count']}")
            if loop_status['violation_count'] > 5:
                recommended_actions.append("EMERGENCY_STOP")
        details['loop_detection'] = loop_status
        
        # 4. Stream Health Check
        stream_safe, stream_status = self._check_stream_health()
        if not stream_safe:
            violations.append("Stream communication issues")
            recommended_actions.append("STREAM_RECOVERY")
        details['stream_health'] = stream_status
        
        # Determine overall safety level
        if len(violations) == 0:
            safety_level = SafetyLevel.SAFE
        elif len(violations) == 1:
            safety_level = SafetyLevel.WARNING
        elif len(violations) <= 3:
            safety_level = SafetyLevel.DANGER
        else:
            safety_level = SafetyLevel.EMERGENCY
        
        return SafetyStatus(
            is_safe=(safety_level in [SafetyLevel.SAFE, SafetyLevel.WARNING]),
            safety_level=safety_level,
            active_violations=violations,
            recommended_actions=list(set(recommended_actions)),  # Deduplicate
            details=details,
            timestamp=datetime.now()
        )
    
    def validate_api_request(self, request_type: str = "general") -> SafetyValidation:
        """Validate a specific API request"""
        # Record the request
        self.api_guardian.record_api_request(request_type)
        
        # Validate safety
        return self.api_guardian.validate_request_safety()
    
    def record_function_execution(self, function_name: str, parameters: Dict = None) -> LoopDetectionResult:
        """Record function execution for loop detection"""
        return self.loop_detector.record_execution(function_name, parameters)
    
    def validate_hook_content(self, hook_content: str) -> Tuple[bool, List[Dict]]:
        """Validate hook content for dangerous patterns"""
        return self.loop_detector.validate_hook_safety(hook_content)
    
    def handle_safety_violation(self, violation_type: str, details: Dict):
        """
        Handle detected safety violations with appropriate response.
        This is called when a violation is detected by any component.
        """
        logger.critical(f"SAFETY VIOLATION: {violation_type}")
        
        # Record violation
        self.active_violations.append(violation_type)
        
        # Post to safety alert stream
        self._post_safety_alert(violation_type, details)
        
        # Take appropriate action based on violation type
        if violation_type == 'API_HAMMERING':
            self.api_guardian.emergency_shutdown()
            self._activate_emergency_cooldown(300)  # 5 minute emergency
            
        elif violation_type == 'INFINITE_LOOP':
            self._activate_emergency_cooldown(600)  # 10 minute emergency
            # TODO: Trigger process termination
            
        elif violation_type == 'RESOURCE_EXHAUSTION':
            self._trigger_resource_cleanup()
            self._activate_emergency_cooldown(180)  # 3 minute cooldown
            
        elif violation_type == 'HOOK_VIOLATION':
            # TODO: Quarantine dangerous hooks
            self._activate_emergency_cooldown(300)
        
        # Update safety level
        self.safety_level = SafetyLevel.EMERGENCY
    
    def _check_stream_health(self) -> Tuple[bool, Dict]:
        """Check health of critical streams"""
        try:
            critical_streams = [
                f'nova.coordination.{self.nova_id}',
                f'nova.safety.{self.nova_id}',
                'nova.priority.alerts'
            ]
            
            stream_status = {}
            all_healthy = True
            
            for stream in critical_streams:
                try:
                    # Try to read from stream
                    self.redis_client.xinfo_stream(stream)
                    stream_status[stream] = 'healthy'
                except redis.ResponseError:
                    stream_status[stream] = 'missing'
                    all_healthy = False
                except Exception as e:
                    stream_status[stream] = f'error: {str(e)}'
                    all_healthy = False
            
            return all_healthy, stream_status
            
        except Exception as e:
            logger.error(f"Stream health check failed: {e}")
            return False, {'error': str(e)}
    
    def _activate_emergency_cooldown(self, duration_seconds: int):
        """Activate emergency cooldown period"""
        self.emergency_cooldown_until = datetime.now() + timedelta(seconds=duration_seconds)
        logger.critical(f"EMERGENCY COOLDOWN ACTIVATED: {duration_seconds} seconds")
        
        # Persist to Redis
        try:
            key = f"safety:emergency_cooldown:{self.nova_id}"
            self.redis_client.setex(
                key,
                duration_seconds,
                self.emergency_cooldown_until.isoformat()
            )
        except Exception as e:
            logger.error(f"Failed to persist emergency cooldown: {e}")
    
    def _post_safety_alert(self, violation_type: str, details: Dict):
        """Post safety alert to monitoring streams"""
        try:
            alert_data = {
                'type': 'SAFETY_VIOLATION',
                'nova_id': self.nova_id,
                'violation_type': violation_type,
                'safety_level': self.safety_level.value,
                'details': json.dumps(details),
                'timestamp': datetime.now().isoformat(),
                'severity': 'CRITICAL'
            }
            
            # Post to safety stream
            self.redis_client.xadd(
                f'nova.safety.{self.nova_id}',
                alert_data
            )
            
            # Post to priority alerts
            self.redis_client.xadd(
                'nova.priority.alerts',
                alert_data
            )
            
        except Exception as e:
            logger.error(f"Failed to post safety alert: {e}")
    
    def _trigger_resource_cleanup(self):
        """Trigger resource cleanup procedures"""
        logger.info("Triggering resource cleanup")
        # TODO: Implement actual cleanup
        # - Clear caches
        # - Close unused connections
        # - Garbage collection
        # - Trim history buffers
    
    def get_comprehensive_safety_status(self) -> Dict:
        """Get comprehensive safety status for monitoring"""
        safety_status = self.perform_comprehensive_safety_check()
        
        return {
            'nova_id': self.nova_id,
            'safety_level': safety_status.safety_level.value,
            'is_safe': safety_status.is_safe,
            'active_violations': safety_status.active_violations,
            'recommended_actions': safety_status.recommended_actions,
            'components': {
                'api_guardian': self.api_guardian.get_safety_status(),
                'loop_detector': self.loop_detector.get_detection_status(),
                'resource_monitor': safety_status.details.get('resource_status', {}),
                'stream_health': safety_status.details.get('stream_health', {})
            },
            'emergency_cooldown_active': self.emergency_cooldown_until is not None and datetime.now() < self.emergency_cooldown_until,
            'emergency_cooldown_remaining': int((self.emergency_cooldown_until - datetime.now()).total_seconds()) if self.emergency_cooldown_until and datetime.now() < self.emergency_cooldown_until else 0,
            'last_safety_check': self.last_safety_check.isoformat(),
            'generated_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the safety orchestrator
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing Safety Orchestrator for {nova_id}")
    
    orchestrator = SafetyOrchestrator(nova_id)
    
    # Perform safety check
    is_safe = orchestrator.is_safe_to_proceed()
    print(f"Safe to proceed: {is_safe}")
    
    # Get comprehensive status
    status = orchestrator.get_comprehensive_safety_status()
    print(f"\nSafety Status: {json.dumps(status, indent=2)}")
    
    # Test hook validation
    test_hook = "while true; do echo 'safe'; sleep 1; done"
    hook_safe, violations = orchestrator.validate_hook_content(test_hook)
    print(f"\nHook validation: {hook_safe}, violations: {violations}")