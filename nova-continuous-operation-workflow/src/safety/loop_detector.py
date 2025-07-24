#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Loop Detector
Critical safety component to prevent infinite loops and recursive patterns

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 2 - Safety Implementation (CRITICAL)
"""

import re
import time
import json
import hashlib
import traceback
import logging
from datetime import datetime, timedelta
from collections import deque, Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

logger = logging.getLogger('novawf.safety.loop_detector')

class LoopType(Enum):
    """Types of loops detected"""
    IDENTICAL_CALLS = "identical_calls"
    PATTERN_REPETITION = "pattern_repetition"
    STACK_OVERFLOW = "stack_overflow"
    HOOK_RECURSION = "hook_recursion"
    RAPID_CYCLING = "rapid_cycling"

@dataclass
class ExecutionRecord:
    """Record of a function execution"""
    function_name: str
    parameters: Dict[str, Any]
    timestamp: datetime
    stack_depth: int
    execution_hash: str
    duration_ms: Optional[int] = None

@dataclass
class LoopDetectionResult:
    """Result of loop detection analysis"""
    loop_detected: bool
    loop_type: Optional[LoopType] = None
    confidence: float = 0.0
    pattern_description: Optional[str] = None
    recommended_action: Optional[str] = None
    evidence: Optional[List[Dict]] = None

class LoopDetector:
    """
    Critical safety component detecting and preventing infinite loops.
    Uses multiple detection strategies to catch various loop patterns.
    """
    
    # Detection thresholds
    THRESHOLDS = {
        'identical_calls_count': 50,        # Same function called 50 times in 60s
        'pattern_length_min': 3,            # Minimum pattern length to detect
        'pattern_repetitions': 5,           # Pattern must repeat 5 times
        'stack_depth_limit': 100,           # Maximum safe stack depth
        'rapid_cycle_threshold': 100,       # 100 cycles in 10 seconds
        'time_window_seconds': 60           # Time window for analysis
    }
    
    # Dangerous hook patterns
    DANGEROUS_HOOK_PATTERNS = [
        r'claude\s+code\s+-c\s+-p',        # Direct API calls in hooks
        r'exec\s+["\']?\$0["\']?',         # Self-execution
        r'while\s+true',                   # Infinite while loops
        r'for\s*\(\s*;\s*;\s*\)',         # Infinite for loops
        r'\{\s*[^}]*\}\s*&\s*wait',       # Background process loops
        r'schedule_with_note.*\$0',        # Self-scheduling
        r'tmux.*send.*claude.*-c\s+-p',   # Tmux recursive calls
    ]
    
    def __init__(self, nova_id: str, window_size: int = 1000):
        self.nova_id = nova_id
        self.execution_history = deque(maxlen=window_size)
        self.pattern_cache = {}
        self.violation_count = 0
        self.last_violation_time = None
        
        logger.info(f"Loop Detector initialized for {nova_id}")
    
    def record_execution(self, function_name: str, parameters: Dict = None, 
                        stack_depth: Optional[int] = None) -> LoopDetectionResult:
        """
        Record function execution and check for loops.
        Returns detection result immediately if loop detected.
        """
        # Create execution record
        if stack_depth is None:
            stack_depth = len(traceback.extract_stack())
        
        execution_hash = self._generate_execution_hash(function_name, parameters)
        
        record = ExecutionRecord(
            function_name=function_name,
            parameters=parameters or {},
            timestamp=datetime.now(),
            stack_depth=stack_depth,
            execution_hash=execution_hash
        )
        
        self.execution_history.append(record)
        
        # Perform all detection checks
        result = self._perform_detection_checks()
        
        if result.loop_detected:
            self._handle_loop_detection(result)
        
        return result
    
    def validate_hook_safety(self, hook_content: str) -> Tuple[bool, List[Dict]]:
        """
        Validate hook content for dangerous patterns.
        Returns (is_safe, violations)
        """
        violations = []
        
        for pattern in self.DANGEROUS_HOOK_PATTERNS:
            matches = re.findall(pattern, hook_content, re.IGNORECASE | re.MULTILINE)
            if matches:
                violations.append({
                    'pattern': pattern,
                    'matches': matches,
                    'severity': 'CRITICAL',
                    'description': self._get_pattern_description(pattern),
                    'required_action': 'REMOVE_PATTERN'
                })
        
        # Check for specific dangerous constructs
        if 'claude code' in hook_content.lower() and '-c' in hook_content and '-p' in hook_content:
            violations.append({
                'pattern': 'claude code -c -p',
                'severity': 'CRITICAL',
                'description': 'Direct claude code API call in hook can cause infinite loops',
                'required_action': 'USE_SAFE_ALTERNATIVE'
            })
        
        is_safe = len(violations) == 0
        
        if not is_safe:
            logger.critical(f"DANGEROUS HOOK PATTERNS DETECTED: {len(violations)} violations")
        
        return is_safe, violations
    
    def _perform_detection_checks(self) -> LoopDetectionResult:
        """Perform all loop detection checks"""
        # Check stack depth first (fastest)
        if self.execution_history and self.execution_history[-1].stack_depth > self.THRESHOLDS['stack_depth_limit']:
            return LoopDetectionResult(
                loop_detected=True,
                loop_type=LoopType.STACK_OVERFLOW,
                confidence=1.0,
                pattern_description=f"Stack depth exceeded safe limit: {self.execution_history[-1].stack_depth}",
                recommended_action="IMMEDIATE_TERMINATION",
                evidence=[{"stack_depth": self.execution_history[-1].stack_depth}]
            )
        
        # Check for identical calls
        identical_result = self._check_identical_calls()
        if identical_result.loop_detected:
            return identical_result
        
        # Check for pattern repetition
        pattern_result = self._check_pattern_repetition()
        if pattern_result.loop_detected:
            return pattern_result
        
        # Check for rapid cycling
        rapid_result = self._check_rapid_cycling()
        if rapid_result.loop_detected:
            return rapid_result
        
        # No loops detected
        return LoopDetectionResult(loop_detected=False)
    
    def _check_identical_calls(self) -> LoopDetectionResult:
        """Check for identical function calls within time window"""
        if not self.execution_history:
            return LoopDetectionResult(loop_detected=False)
        
        # Get recent executions within time window
        cutoff_time = datetime.now() - timedelta(seconds=self.THRESHOLDS['time_window_seconds'])
        recent_executions = [r for r in self.execution_history if r.timestamp > cutoff_time]
        
        if not recent_executions:
            return LoopDetectionResult(loop_detected=False)
        
        # Count execution hashes
        hash_counts = Counter(r.execution_hash for r in recent_executions)
        
        # Check for threshold violations
        for exec_hash, count in hash_counts.items():
            if count >= self.THRESHOLDS['identical_calls_count']:
                # Find the function details
                sample_record = next(r for r in recent_executions if r.execution_hash == exec_hash)
                
                return LoopDetectionResult(
                    loop_detected=True,
                    loop_type=LoopType.IDENTICAL_CALLS,
                    confidence=min(count / self.THRESHOLDS['identical_calls_count'], 1.0),
                    pattern_description=f"Function '{sample_record.function_name}' called {count} times in {self.THRESHOLDS['time_window_seconds']}s",
                    recommended_action="BREAK_LOOP_PATTERN",
                    evidence=[{
                        "function": sample_record.function_name,
                        "count": count,
                        "time_window": self.THRESHOLDS['time_window_seconds']
                    }]
                )
        
        return LoopDetectionResult(loop_detected=False)
    
    def _check_pattern_repetition(self) -> LoopDetectionResult:
        """Check for repeating execution patterns"""
        if len(self.execution_history) < self.THRESHOLDS['pattern_length_min'] * 2:
            return LoopDetectionResult(loop_detected=False)
        
        # Convert recent history to pattern string
        pattern_window = min(100, len(self.execution_history))
        recent_hashes = [r.execution_hash[:8] for r in list(self.execution_history)[-pattern_window:]]
        pattern_string = "".join(recent_hashes)
        
        # Look for repeating patterns
        for pattern_length in range(self.THRESHOLDS['pattern_length_min'], pattern_window // 2):
            for start_pos in range(len(pattern_string) - pattern_length * 2):
                pattern = pattern_string[start_pos:start_pos + pattern_length]
                
                # Count pattern occurrences
                occurrences = 0
                pos = start_pos
                while pos < len(pattern_string) - pattern_length + 1:
                    if pattern_string[pos:pos + pattern_length] == pattern:
                        occurrences += 1
                        pos += pattern_length
                    else:
                        break
                
                if occurrences >= self.THRESHOLDS['pattern_repetitions']:
                    return LoopDetectionResult(
                        loop_detected=True,
                        loop_type=LoopType.PATTERN_REPETITION,
                        confidence=min(occurrences / self.THRESHOLDS['pattern_repetitions'], 1.0),
                        pattern_description=f"Repeating pattern of {pattern_length} operations detected {occurrences} times",
                        recommended_action="DISRUPT_PATTERN",
                        evidence=[{
                            "pattern_length": pattern_length,
                            "repetitions": occurrences,
                            "pattern_hash": pattern[:16]
                        }]
                    )
        
        return LoopDetectionResult(loop_detected=False)
    
    def _check_rapid_cycling(self) -> LoopDetectionResult:
        """Check for rapid execution cycling"""
        if len(self.execution_history) < self.THRESHOLDS['rapid_cycle_threshold']:
            return LoopDetectionResult(loop_detected=False)
        
        # Check execution rate in last 10 seconds
        cutoff_time = datetime.now() - timedelta(seconds=10)
        recent_executions = [r for r in self.execution_history if r.timestamp > cutoff_time]
        
        if len(recent_executions) >= self.THRESHOLDS['rapid_cycle_threshold']:
            execution_rate = len(recent_executions) / 10.0  # per second
            
            return LoopDetectionResult(
                loop_detected=True,
                loop_type=LoopType.RAPID_CYCLING,
                confidence=min(len(recent_executions) / self.THRESHOLDS['rapid_cycle_threshold'], 1.0),
                pattern_description=f"Rapid execution detected: {execution_rate:.1f} calls/second",
                recommended_action="THROTTLE_EXECUTION",
                evidence=[{
                    "execution_count": len(recent_executions),
                    "time_window": 10,
                    "rate_per_second": execution_rate
                }]
            )
        
        return LoopDetectionResult(loop_detected=False)
    
    def _generate_execution_hash(self, function_name: str, parameters: Dict) -> str:
        """Generate hash for execution record"""
        # Create stable string representation
        param_str = json.dumps(parameters, sort_keys=True) if parameters else ""
        execution_str = f"{function_name}:{param_str}"
        
        # Generate hash
        return hashlib.sha256(execution_str.encode()).hexdigest()
    
    def _get_pattern_description(self, pattern: str) -> str:
        """Get human-readable description of dangerous pattern"""
        descriptions = {
            r'claude\s+code\s+-c\s+-p': "Direct Claude API call that can cause infinite loops",
            r'exec\s+["\']?\$0["\']?': "Self-execution pattern that creates infinite recursion",
            r'while\s+true': "Infinite while loop without proper exit condition",
            r'for\s*\(\s*;\s*;\s*\)': "Infinite for loop without termination",
            r'\{\s*[^}]*\}\s*&\s*wait': "Background process loop that never terminates",
            r'schedule_with_note.*\$0': "Self-scheduling pattern creating infinite tasks",
            r'tmux.*send.*claude.*-c\s+-p': "Recursive tmux commands triggering API loops"
        }
        
        return descriptions.get(pattern, "Dangerous loop pattern detected")
    
    def _handle_loop_detection(self, result: LoopDetectionResult):
        """Handle detected loop - logging and alerting"""
        self.violation_count += 1
        self.last_violation_time = datetime.now()
        
        logger.critical(f"""
        INFINITE LOOP DETECTED!
        Type: {result.loop_type.value}
        Confidence: {result.confidence:.2%}
        Description: {result.pattern_description}
        Action: {result.recommended_action}
        Evidence: {result.evidence}
        """)
        
        # TODO: Post to safety alert stream
        # TODO: Trigger emergency protocols
    
    def get_detection_status(self) -> Dict:
        """Get current detection status for monitoring"""
        recent_window = datetime.now() - timedelta(seconds=self.THRESHOLDS['time_window_seconds'])
        recent_count = len([r for r in self.execution_history if r.timestamp > recent_window])
        
        return {
            'nova_id': self.nova_id,
            'total_executions': len(self.execution_history),
            'recent_executions': recent_count,
            'violation_count': self.violation_count,
            'last_violation': self.last_violation_time.isoformat() if self.last_violation_time else None,
            'current_stack_depth': self.execution_history[-1].stack_depth if self.execution_history else 0,
            'detection_active': True,
            'generated_at': datetime.now().isoformat()
        }

class SafetyException(Exception):
    """Raised when safety violation detected"""
    pass

if __name__ == "__main__":
    # Test the loop detector
    import json
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing Loop Detector for {nova_id}")
    
    detector = LoopDetector(nova_id)
    
    # Test hook validation
    dangerous_hook = """
    #!/bin/bash
    while true; do
        claude code -c -p "continue working"
    done
    """
    
    is_safe, violations = detector.validate_hook_safety(dangerous_hook)
    print(f"Hook safety check: {is_safe}")
    if violations:
        print(f"Violations: {json.dumps(violations, indent=2)}")
    
    # Test execution recording
    for i in range(10):
        result = detector.record_execution("test_function", {"iteration": i // 5})
        if result.loop_detected:
            print(f"Loop detected: {result}")
    
    # Get status
    status = detector.get_detection_status()
    print(f"\nDetection Status: {json.dumps(status, indent=2)}")