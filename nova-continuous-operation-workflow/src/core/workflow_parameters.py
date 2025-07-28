#!/usr/bin/env python3
"""
Nova Workflow Tunable Parameters
Centralized configuration for all workflow parameters that can be modified during training

This file is designed to be modified by the training system with automatic git commits
"""

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TimingParameters:
    """Timing-related parameters for workflow execution"""
    stream_check_interval: int = 60  # seconds between stream checks
    task_execution_timeout: int = 300  # max seconds for task execution
    phase_transition_cooldown: int = 30  # seconds between phase transitions
    safety_pause_duration: int = 300  # seconds for safety pauses
    manual_mode_check_interval: int = 2  # seconds between manual mode checks
    training_mode_check_interval: int = 2  # seconds between training mode checks
    
@dataclass
class SafetyParameters:
    """Safety system parameters and thresholds"""
    api_rate_limit: int = 25  # requests per minute
    error_threshold: int = 3  # consecutive errors before safety pause
    loop_detection_threshold: int = 5  # iterations before loop intervention
    concurrent_request_limit: int = 3  # max concurrent API requests
    burst_threshold: int = 10  # rapid requests triggering safety
    cooldown_multiplier: float = 1.5  # multiplier for progressive cooldowns
    
@dataclass
class WorkflowParameters:
    """Core workflow behavior parameters"""
    momentum_task_threshold: int = 5  # tasks before generating momentum work
    tasks_per_phase: int = 20  # target tasks per workflow phase
    completion_celebration_duration: int = 10  # seconds in completion state
    stream_priority_threshold: float = 0.7  # priority level for urgent messages
    max_consecutive_errors: int = 5  # errors before entering recovery
    enterprise_metric_window: int = 3600  # seconds for metric calculations
    
@dataclass
class TrainingParameters:
    """Parameters specific to training mode operation"""
    performance_degradation_threshold: float = 0.2  # 20% degradation triggers rollback
    parameter_change_cooldown: int = 30  # seconds between parameter changes
    metrics_sampling_interval: int = 10  # seconds between metric captures
    auto_merge_improvement_threshold: float = 0.1  # 10% improvement for auto-merge
    max_training_duration: int = 3600  # max seconds in training mode
    
class WorkflowConfig:
    """Central configuration management for workflow parameters"""
    
    def __init__(self):
        self.timing = TimingParameters()
        self.safety = SafetyParameters()
        self.workflow = WorkflowParameters()
        self.training = TrainingParameters()
        
        # Track parameter modifications for training mode
        self._modification_history: list = []
        
    def get_parameter(self, param_type: str, param_name: str) -> Any:
        """Get a parameter value by type and name"""
        param_group = getattr(self, param_type, None)
        if param_group:
            return getattr(param_group, param_name, None)
        return None
        
    def set_parameter(self, param_type: str, param_name: str, value: Any) -> bool:
        """Set a parameter value with history tracking"""
        param_group = getattr(self, param_type, None)
        if param_group and hasattr(param_group, param_name):
            old_value = getattr(param_group, param_name)
            setattr(param_group, param_name, value)
            
            # Track modification
            self._modification_history.append({
                'param_type': param_type,
                'param_name': param_name,
                'old_value': old_value,
                'new_value': value,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            })
            
            return True
        return False
        
    def get_all_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get all current parameter values"""
        return {
            'timing': self.timing.__dict__,
            'safety': self.safety.__dict__,
            'workflow': self.workflow.__dict__,
            'training': self.training.__dict__
        }
        
    def get_modification_history(self) -> list:
        """Get history of parameter modifications"""
        return self._modification_history.copy()

# Global configuration instance
WORKFLOW_CONFIG = WorkflowConfig()

# Export for easy access
timing = WORKFLOW_CONFIG.timing
safety = WORKFLOW_CONFIG.safety  
workflow = WORKFLOW_CONFIG.workflow
training = WORKFLOW_CONFIG.training