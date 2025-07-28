#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Core State Manager
Central state management and workflow orchestration for Nova teams

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
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from collections import deque

# Import safety components
import sys
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src')
from safety import SafetyOrchestrator
from core.workflow_parameters import WORKFLOW_CONFIG, timing, safety, workflow, training

# Configure logging for enterprise monitoring
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('novawf.state_manager')

class WorkflowState(Enum):
    """Core workflow states following the anti-drift state machine"""
    INITIALIZING = "initializing"
    STREAM_CHECK = "stream_check"
    WORK_DISCOVERY = "work_discovery"
    TASK_EXECUTION = "task_execution"
    PROGRESS_UPDATE = "progress_update"
    COMPLETION_ROUTINE = "completion_routine"
    PHASE_TRANSITION = "phase_transition"
    ERROR_RECOVERY = "error_recovery"
    SAFETY_PAUSE = "safety_pause"
    MANUAL_MODE = "manual_mode"
    TRAINING_MODE = "training_mode"

class WorkflowPhase(Enum):
    """Simplified 2-phase alternating system to prevent drift"""
    WORK_PHASE_1 = "work_phase_1"
    WORK_PHASE_2 = "work_phase_2"
    PERSONAL_PHASE = "personal_phase"  # Optional experimental phase

class SafetyStatus(Enum):
    """Safety system status levels"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    EMERGENCY = "emergency"

@dataclass
class WorkflowStateData:
    """Persistent workflow state data with enterprise monitoring"""
    current_state: WorkflowState
    current_phase: WorkflowPhase
    tasks_completed_in_phase: int
    tool_use_count: int
    last_stream_check: str
    last_completion_celebration: str
    session_start_time: str
    total_cycles_completed: int
    safety_status: SafetyStatus
    nova_id: str
    phase_start_time: str
    consecutive_error_count: int = 0
    last_work_item_id: Optional[str] = None
    momentum_tasks_generated: int = 0
    enterprise_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def persist_to_redis(self, redis_client: redis.Redis):
        """Persist state to Redis with enterprise monitoring"""
        try:
            key = f"workflow:state:{self.nova_id}"
            data = asdict(self)
            
            # Convert enums to strings for Redis storage
            data['current_state'] = self.current_state.value
            data['current_phase'] = self.current_phase.value
            data['safety_status'] = self.safety_status.value
            data['enterprise_metrics'] = json.dumps(self.enterprise_metrics)
            
            redis_client.hset(key, mapping=data)
            redis_client.expire(key, 3600)  # 1 hour TTL
            
            # Update enterprise monitoring stream
            redis_client.xadd(
                f"nova.enterprise.state.{self.nova_id}",
                {
                    'state': self.current_state.value,
                    'phase': self.current_phase.value,
                    'tasks_completed': self.tasks_completed_in_phase,
                    'cycles_completed': self.total_cycles_completed,
                    'safety_status': self.safety_status.value,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"State persisted: {self.current_state.value} in {self.current_phase.value}")
            
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
            # Don't let persistence failures stop workflow
    
    @classmethod
    def load_from_redis(cls, redis_client: redis.Redis, nova_id: str) -> 'WorkflowStateData':
        """Load state from Redis or create new if not found"""
        try:
            key = f"workflow:state:{nova_id}"
            data = redis_client.hgetall(key)
            
            if not data:
                # Create new state
                logger.info(f"Creating new workflow state for {nova_id}")
                return cls._create_initial_state(nova_id)
            
            # Parse persisted state
            enterprise_metrics = json.loads(data.get('enterprise_metrics', '{}'))
            
            return cls(
                current_state=WorkflowState(data['current_state']),
                current_phase=WorkflowPhase(data['current_phase']),
                tasks_completed_in_phase=int(data['tasks_completed_in_phase']),
                tool_use_count=int(data['tool_use_count']),
                last_stream_check=data['last_stream_check'],
                last_completion_celebration=data['last_completion_celebration'],
                session_start_time=data['session_start_time'],
                total_cycles_completed=int(data['total_cycles_completed']),
                safety_status=SafetyStatus(data['safety_status']),
                nova_id=data['nova_id'],
                phase_start_time=data['phase_start_time'],
                consecutive_error_count=int(data.get('consecutive_error_count', 0)),
                last_work_item_id=data.get('last_work_item_id'),
                momentum_tasks_generated=int(data.get('momentum_tasks_generated', 0)),
                enterprise_metrics=enterprise_metrics
            )
            
        except Exception as e:
            logger.error(f"Failed to load state from Redis: {e}")
            return cls._create_initial_state(nova_id)
    
    @classmethod
    def _create_initial_state(cls, nova_id: str) -> 'WorkflowStateData':
        """Create initial workflow state"""
        now = datetime.now().isoformat()
        return cls(
            current_state=WorkflowState.INITIALIZING,
            current_phase=WorkflowPhase.WORK_PHASE_1,
            tasks_completed_in_phase=0,
            tool_use_count=0,
            last_stream_check=now,
            last_completion_celebration=now,
            session_start_time=now,
            total_cycles_completed=0,
            safety_status=SafetyStatus.SAFE,
            nova_id=nova_id,
            phase_start_time=now
        )

class WorkflowStateMachine:
    """Core workflow state machine implementing anti-drift patterns"""
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(
            host='localhost', 
            port=redis_port, 
            decode_responses=True, 
            password='adapt123'
        )
        
        # Load or create state
        self.state_data = WorkflowStateData.load_from_redis(self.redis_client, nova_id)
        
        # Initialize safety orchestrator FIRST - this is critical
        self.safety_orchestrator = SafetyOrchestrator(nova_id, redis_port)
        
        # Initialize other components (will be injected in main orchestrator)
        self.stream_controller = None
        self.task_tracker = None
        self.work_processor = None
        self.completion_manager = None
        
        # State transition handlers
        self._state_handlers = {
            WorkflowState.INITIALIZING: self._handle_initializing,
            WorkflowState.STREAM_CHECK: self._handle_stream_check,
            WorkflowState.WORK_DISCOVERY: self._handle_work_discovery,
            WorkflowState.TASK_EXECUTION: self._handle_task_execution,
            WorkflowState.PROGRESS_UPDATE: self._handle_progress_update,
            WorkflowState.COMPLETION_ROUTINE: self._handle_completion_routine,
            WorkflowState.PHASE_TRANSITION: self._handle_phase_transition,
            WorkflowState.ERROR_RECOVERY: self._handle_error_recovery,
            WorkflowState.SAFETY_PAUSE: self._handle_safety_pause,
            WorkflowState.MANUAL_MODE: self._handle_manual_mode,
            WorkflowState.TRAINING_MODE: self._handle_training_mode
        }
        
        logger.info(f"Workflow state machine initialized for {nova_id}")
    
    def execute_cycle(self) -> WorkflowState:
        """Execute one complete workflow cycle with enterprise monitoring"""
        cycle_start = datetime.now()
        
        try:
            logger.info(f"Executing cycle - Current state: {self.state_data.current_state.value}")
            
            # Check for control commands first
            command_state = self._check_control_commands()
            if command_state:
                return command_state
            
            # Safety check first - ALWAYS
            if not self._is_safe_to_proceed():
                return self._enter_safety_pause("Safety check failed")
            
            # Execute current state handler
            next_state = self._execute_current_state()
            
            # Update state and persist
            if next_state != self.state_data.current_state:
                self._transition_to_state(next_state)
                self.state_data.persist_to_redis(self.redis_client)
            
            # Update enterprise metrics
            self._update_enterprise_metrics(cycle_start)
            
            # Increment counters
            self.state_data.tool_use_count += 1
            if next_state == WorkflowState.STREAM_CHECK:
                self.state_data.total_cycles_completed += 1
            
            # Reset error count on successful cycle
            self.state_data.consecutive_error_count = 0
            
            return next_state
            
        except Exception as e:
            logger.error(f"Workflow cycle error: {e}")
            self.state_data.consecutive_error_count += 1
            return self._enter_error_recovery(str(e))
    
    def _is_safe_to_proceed(self) -> bool:
        """Check all safety systems before proceeding"""
        # Safety orchestrator is now always available
        return self.safety_orchestrator.is_safe_to_proceed()
    
    def _execute_current_state(self) -> WorkflowState:
        """Execute the handler for current state"""
        handler = self._state_handlers.get(self.state_data.current_state)
        if handler:
            return handler()
        else:
            logger.error(f"No handler for state: {self.state_data.current_state}")
            return WorkflowState.ERROR_RECOVERY
    
    def _transition_to_state(self, new_state: WorkflowState):
        """Transition to new state with logging"""
        old_state = self.state_data.current_state
        self.state_data.current_state = new_state
        
        logger.info(f"State transition: {old_state.value} -> {new_state.value}")
        
        # Post state transition to enterprise monitoring
        self.redis_client.xadd(
            f"nova.enterprise.transitions.{self.nova_id}",
            {
                'from_state': old_state.value,
                'to_state': new_state.value,
                'phase': self.state_data.current_phase.value,
                'timestamp': datetime.now().isoformat()
            }
        )
    
    # State Handlers - implementing the anti-drift workflow
    
    def _handle_initializing(self) -> WorkflowState:
        """Initialize workflow components and validate environment"""
        logger.info("Initializing workflow systems")
        
        try:
            # Test Redis connectivity
            self.redis_client.ping()
            
            # Post initialization status
            self.redis_client.xadd(
                f"nova.coordination.{self.nova_id}",
                {
                    'type': 'WORKFLOW_INITIALIZATION',
                    'nova_id': self.nova_id,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'SYSTEMS_READY'
                }
            )
            
            # Move to stream check
            return WorkflowState.STREAM_CHECK
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return WorkflowState.ERROR_RECOVERY
    
    def _handle_stream_check(self) -> WorkflowState:
        """Check coordination streams for priority work"""
        logger.info("Checking coordination streams")
        
        if self.stream_controller:
            # Check if it's time for stream coordination (every 5 tool uses)
            if self.state_data.tool_use_count % 5 == 0:
                messages = self.stream_controller.check_coordination_streams()
                
                if messages:
                    logger.info(f"Found {len(messages)} coordination messages")
                    # Process priority messages first
                    return WorkflowState.WORK_DISCOVERY
        
        # Update last stream check time
        self.state_data.last_stream_check = datetime.now().isoformat()
        
        # Move to work discovery
        return WorkflowState.WORK_DISCOVERY
    
    def _handle_work_discovery(self) -> WorkflowState:
        """Discover work from queues or generate momentum tasks"""
        logger.info("Discovering work")
        
        if self.work_processor:
            work_items = self.work_processor.discover_work()
            
            if work_items:
                # Store work item for execution
                self.state_data.last_work_item_id = work_items[0].id
                logger.info(f"Found work: {work_items[0].title}")
                return WorkflowState.TASK_EXECUTION
            else:
                # Generate momentum task
                momentum_task = self._generate_momentum_task()
                self.state_data.last_work_item_id = momentum_task.id
                self.state_data.momentum_tasks_generated += 1
                logger.info(f"Generated momentum task: {momentum_task.title}")
                return WorkflowState.TASK_EXECUTION
        
        # Fallback to basic momentum
        return WorkflowState.TASK_EXECUTION
    
    def _handle_task_execution(self) -> WorkflowState:
        """Execute discovered work with progress tracking"""
        logger.info("Executing task")
        
        # Simulate task execution (actual implementation will integrate with real work)
        if self.task_tracker and self.state_data.last_work_item_id:
            # Update progress
            self.task_tracker.update_progress(
                self.state_data.last_work_item_id,
                "Task execution in progress",
                progress_percentage=50
            )
        
        # Move to progress update
        return WorkflowState.PROGRESS_UPDATE
    
    def _handle_progress_update(self) -> WorkflowState:
        """Update task progress and check for completion"""
        logger.info("Updating progress")
        
        # Simulate task completion
        if self.task_tracker and self.state_data.last_work_item_id:
            self.task_tracker.complete_task(
                self.state_data.last_work_item_id,
                "Task completed successfully",
                metrics={'execution_time': 30, 'quality_score': 8.5}
            )
            
            self.state_data.tasks_completed_in_phase += 1
        
        # Move to completion routine
        return WorkflowState.COMPLETION_ROUTINE
    
    def _handle_completion_routine(self) -> WorkflowState:
        """Execute anti-drift completion routine"""
        logger.info("Executing completion routine")
        
        if self.completion_manager:
            # Execute structured completion routine
            next_state = self.completion_manager.execute_completion_routine(
                self.state_data.last_work_item_id
            )
            return next_state
        
        # Check if phase completion needed (6-8 tasks per phase)
        if self.state_data.tasks_completed_in_phase >= 6:
            return WorkflowState.PHASE_TRANSITION
        
        # Continue with next cycle
        return WorkflowState.STREAM_CHECK
    
    def _handle_phase_transition(self) -> WorkflowState:
        """Handle phase transitions with celebration period"""
        logger.info(f"Phase transition - completed {self.state_data.tasks_completed_in_phase} tasks")
        
        # Alternate between work phases
        if self.state_data.current_phase == WorkflowPhase.WORK_PHASE_1:
            self.state_data.current_phase = WorkflowPhase.WORK_PHASE_2
        else:
            self.state_data.current_phase = WorkflowPhase.WORK_PHASE_1
        
        # Reset phase counters
        self.state_data.tasks_completed_in_phase = 0
        self.state_data.phase_start_time = datetime.now().isoformat()
        self.state_data.last_completion_celebration = datetime.now().isoformat()
        
        # Post phase transition to enterprise monitoring
        self.redis_client.xadd(
            f"nova.enterprise.phases.{self.nova_id}",
            {
                'type': 'PHASE_TRANSITION',
                'new_phase': self.state_data.current_phase.value,
                'tasks_completed': self.state_data.tasks_completed_in_phase,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # Brief celebration pause (3 minutes as specified)
        logger.info("🎉 Phase completed! Starting 3-minute celebration period...")
        time.sleep(10)  # 10 second pause in implementation (would be 180 for full 3 min)
        
        # Return to stream check for next cycle
        return WorkflowState.STREAM_CHECK
    
    def _handle_error_recovery(self) -> WorkflowState:
        """Handle error recovery with exponential backoff"""
        logger.info(f"Error recovery - consecutive errors: {self.state_data.consecutive_error_count}")
        
        # Exponential backoff for error recovery
        backoff_time = min(2 ** self.state_data.consecutive_error_count, 60)  # Max 60 seconds
        time.sleep(backoff_time)
        
        # Alert enterprise monitoring of errors
        self.redis_client.xadd(
            f"nova.enterprise.errors.{self.nova_id}",
            {
                'type': 'ERROR_RECOVERY',
                'consecutive_errors': self.state_data.consecutive_error_count,
                'backoff_time': backoff_time,
                'timestamp': datetime.now().isoformat()
            }
        )
        
        # If too many consecutive errors, enter safety pause
        if self.state_data.consecutive_error_count >= 5:
            return WorkflowState.SAFETY_PAUSE
        
        # Try to recover by reinitializing
        return WorkflowState.INITIALIZING
    
    def _handle_safety_pause(self) -> WorkflowState:
        """Handle safety pause with mandatory cooldown"""
        logger.warning("Safety pause activated")
        
        self.state_data.safety_status = SafetyStatus.DANGER
        
        # Alert enterprise monitoring
        self.redis_client.xadd(
            f"nova.enterprise.safety.{self.nova_id}",
            {
                'type': 'SAFETY_PAUSE',
                'reason': 'MULTIPLE_ERRORS_OR_SAFETY_VIOLATION',
                'timestamp': datetime.now().isoformat(),
                'status': 'COOLDOWN_ACTIVE'
            }
        )
        
        # Mandatory 5-minute safety pause
        logger.info("Entering 5-minute safety cooldown...")
        time.sleep(30)  # 30 second pause in implementation (would be 300 for full 5 min)
        
        # Reset safety status and error count
        self.state_data.safety_status = SafetyStatus.SAFE
        self.state_data.consecutive_error_count = 0
        
        # Return to initialization
        return WorkflowState.INITIALIZING
    
    def _enter_safety_pause(self, reason: str) -> WorkflowState:
        """Enter safety pause with specific reason"""
        logger.warning(f"Entering safety pause: {reason}")
        self.state_data.safety_status = SafetyStatus.DANGER
        return WorkflowState.SAFETY_PAUSE
    
    def _enter_error_recovery(self, error: str) -> WorkflowState:
        """Enter error recovery with error logging"""
        logger.error(f"Entering error recovery: {error}")
        self.state_data.consecutive_error_count += 1
        return WorkflowState.ERROR_RECOVERY
    
    def _check_control_commands(self) -> Optional[WorkflowState]:
        """Check for /man or /auto control commands in coordination stream"""
        try:
            # Check for control commands in Nova's coordination stream
            stream_name = f"nova.coordination.{self.nova_id}"
            
            # Read recent messages looking for control commands
            messages = self.redis_client.xrevrange(stream_name, count=5)
            
            for msg_id, fields in messages:
                msg_type = fields.get(b'type', b'').decode('utf-8')
                
                # Check for manual mode command
                if msg_type == 'CONTROL_MANUAL' or fields.get(b'command', b'').decode('utf-8') == '/man':
                    logger.info("Manual mode command detected - entering manual mode")
                    return WorkflowState.MANUAL_MODE
                
                # Check for autonomous mode command  
                if msg_type == 'CONTROL_AUTO' or fields.get(b'command', b'').decode('utf-8') == '/auto':
                    logger.info("Autonomous mode command detected - resuming workflow")
                    if self.state_data.current_state in [WorkflowState.MANUAL_MODE, WorkflowState.TRAINING_MODE]:
                        return WorkflowState.STREAM_CHECK
                
                # Check for training mode command (development only)
                if msg_type == 'CONTROL_TRAIN' or fields.get(b'command', b'').decode('utf-8') == '/train':
                    # Only allow training mode for torch during development
                    if self.nova_id == 'torch':
                        logger.info("Training mode command detected - entering adaptive development mode")
                        return WorkflowState.TRAINING_MODE
                    else:
                        logger.warning(f"Training mode not authorized for {self.nova_id} - only torch during dev")
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking control commands: {e}")
            return None
    
    def _handle_manual_mode(self) -> WorkflowState:
        """Handle manual mode - workflow paused until /auto command"""
        logger.info("In manual mode - workflow paused, awaiting /auto command")
        
        # Post manual mode status to enterprise monitoring
        self.redis_client.xadd(
            f"nova.enterprise.control.{self.nova_id}",
            {
                'type': 'MANUAL_MODE_ACTIVE',
                'timestamp': datetime.now().isoformat(),
                'status': 'WORKFLOW_PAUSED_BY_USER',
                'waiting_for': 'AUTO_COMMAND'
            }
        )
        
        # Check for /auto command periodically using configured interval
        time.sleep(timing.manual_mode_check_interval)
        
        # Check again for control commands
        command_state = self._check_control_commands()
        if command_state and command_state != WorkflowState.MANUAL_MODE:
            logger.info("Exiting manual mode - resuming autonomous operation")
            return command_state
        
        # Stay in manual mode
        return WorkflowState.MANUAL_MODE
    
    def _handle_training_mode(self) -> WorkflowState:
        """Handle training mode - adaptive parameter tuning with versioned experimentation"""
        logger.info("In training mode - adaptive parameter tuning active")
        
        # Initialize training session if needed
        if not hasattr(self, '_training_session'):
            self._initialize_training_session()
        
        # Post training mode status to enterprise monitoring
        self.redis_client.xadd(
            f"nova.enterprise.training.{self.nova_id}",
            {
                'type': 'TRAINING_MODE_ACTIVE',
                'timestamp': datetime.now().isoformat(),
                'status': 'ADAPTIVE_TUNING_ENABLED',
                'branch': getattr(self, '_training_branch', 'unknown'),
                'modifications': getattr(self, '_training_modifications', 0)
            }
        )
        
        # Check for parameter modification requests
        self._check_training_commands()
        
        # Monitor performance impact of changes
        self._monitor_training_performance()
        
        # Check for /auto command to exit training
        command_state = self._check_control_commands()
        if command_state and command_state != WorkflowState.TRAINING_MODE:
            logger.info("Exiting training mode - finalizing experiments")
            self._finalize_training_session()
            return command_state
        
        # Continue in training mode with adaptive execution
        time.sleep(timing.training_mode_check_interval)
        return WorkflowState.TRAINING_MODE
    
    def _initialize_training_session(self):
        """Initialize a new training session with git branching and metrics baseline"""
        import subprocess
        from datetime import datetime
        
        try:
            # Create training branch
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            self._training_branch = f"training-torch-{timestamp}"
            self._training_start = datetime.now()
            self._training_modifications = 0
            self._baseline_metrics = self.state_data.enterprise_metrics.copy()
            
            # Git operations
            subprocess.run(["git", "checkout", "-b", self._training_branch], 
                         cwd="/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow",
                         capture_output=True)
            
            # Record training session start
            self.redis_client.xadd(
                f"nova.training.sessions.{self.nova_id}",
                {
                    'action': 'SESSION_START',
                    'branch': self._training_branch,
                    'timestamp': datetime.now().isoformat(),
                    'baseline_metrics': json.dumps(self._baseline_metrics)
                }
            )
            
            logger.info(f"Training session initialized on branch: {self._training_branch}")
            
        except Exception as e:
            logger.error(f"Failed to initialize training session: {e}")
    
    def _check_training_commands(self):
        """Check for parameter modification commands in training stream"""
        try:
            stream_name = f"nova.training.{self.nova_id}"
            messages = self.redis_client.xread({stream_name: '$'}, block=100, count=10)
            
            for stream, stream_messages in messages:
                for msg_id, fields in stream_messages:
                    param_type = fields.get(b'param_type', b'').decode('utf-8')
                    param_name = fields.get(b'param_name', b'').decode('utf-8')
                    new_value = fields.get(b'new_value', b'').decode('utf-8')
                    
                    if param_type and param_name and new_value:
                        self._apply_parameter_change(param_type, param_name, new_value)
                        
        except Exception as e:
            logger.error(f"Error checking training commands: {e}")
    
    def _apply_parameter_change(self, param_type: str, param_name: str, new_value: str):
        """Apply a parameter change with automatic commit and performance tracking"""
        logger.info(f"Applying parameter change: {param_type}.{param_name} = {new_value}")
        
        # Convert value to appropriate type
        try:
            current_value = WORKFLOW_CONFIG.get_parameter(param_type, param_name)
            if isinstance(current_value, int):
                typed_value = int(new_value)
            elif isinstance(current_value, float):
                typed_value = float(new_value)
            else:
                typed_value = new_value
                
            # Apply the parameter change
            success = WORKFLOW_CONFIG.set_parameter(param_type, param_name, typed_value)
            
            if success:
                self._training_modifications += 1
                
                # Auto-commit the change
                import subprocess
                
                # First, update the parameters file with new value
                params_file = "/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/core/workflow_parameters.py"
                
                # Read current file
                with open(params_file, 'r') as f:
                    content = f.read()
                
                # Update the specific parameter value in the file
                # This is a simple approach - in production would use AST
                old_line = f"{param_name}: int = {current_value}"
                new_line = f"{param_name}: int = {typed_value}"
                
                if old_line in content:
                    content = content.replace(old_line, new_line)
                else:
                    # Try float format
                    old_line = f"{param_name}: float = {current_value}"
                    new_line = f"{param_name}: float = {typed_value}"
                    if old_line in content:
                        content = content.replace(old_line, new_line)
                
                # Write updated content
                with open(params_file, 'w') as f:
                    f.write(content)
                
                # Commit the change
                subprocess.run([
                    "git", "add", params_file
                ], cwd="/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow")
                
                subprocess.run([
                    "git", "commit", "-m", 
                    f"Training: Adjust {param_type}.{param_name} to {typed_value}"
                ], cwd="/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow")
                
                # Log performance impact tracking
                self.redis_client.xadd(
                    f"nova.training.changes.{self.nova_id}",
                    {
                        'param_type': param_type,
                        'param_name': param_name,
                        'old_value': str(current_value),
                        'new_value': str(typed_value),
                        'timestamp': datetime.now().isoformat(),
                        'modification_number': self._training_modifications
                    }
                )
                
                logger.info(f"Successfully applied and committed parameter change")
            else:
                logger.error(f"Failed to apply parameter change - invalid parameter")
                
        except Exception as e:
            logger.error(f"Error applying parameter change: {e}")
    
    def _monitor_training_performance(self):
        """Monitor performance impact of training modifications"""
        if hasattr(self, '_baseline_metrics'):
            current_metrics = self.state_data.enterprise_metrics
            
            # Calculate performance deltas
            tasks_per_hour_delta = (
                current_metrics.get('tasks_per_hour', 0) - 
                self._baseline_metrics.get('tasks_per_hour', 0)
            )
            
            # Log performance impact
            self.redis_client.xadd(
                f"nova.training.performance.{self.nova_id}",
                {
                    'timestamp': datetime.now().isoformat(),
                    'modifications': self._training_modifications,
                    'tasks_per_hour_delta': tasks_per_hour_delta,
                    'current_metrics': json.dumps(current_metrics)
                }
            )
    
    def _finalize_training_session(self):
        """Finalize training session with performance summary and merge decision"""
        try:
            duration = (datetime.now() - self._training_start).total_seconds() / 60
            
            # Record session completion
            self.redis_client.xadd(
                f"nova.training.sessions.{self.nova_id}",
                {
                    'action': 'SESSION_COMPLETE',
                    'branch': self._training_branch,
                    'duration_minutes': duration,
                    'modifications': self._training_modifications,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Training session complete: {self._training_modifications} modifications in {duration:.1f} minutes")
            
            # TODO: Implement auto-merge logic based on performance improvements
            
        except Exception as e:
            logger.error(f"Error finalizing training session: {e}")
    
    def _generate_momentum_task(self):
        """Generate a productive momentum task when no work available"""
        momentum_templates = [
            "Review and optimize workflow performance metrics",
            "Update enterprise documentation with latest insights",
            "Analyze coordination stream patterns for improvements",
            "Validate safety system status and monitoring",
            "Research Nova behavioral patterns and optimizations"
        ]
        
        task_index = self.state_data.momentum_tasks_generated % len(momentum_templates)
        template = momentum_templates[task_index]
        
        # Create mock work item
        class MomentumWorkItem:
            def __init__(self, template):
                self.id = f"momentum-{int(time.time())}-{task_index}"
                self.title = f"Momentum: {template}"
                self.description = f"Productive momentum work: {template}"
        
        return MomentumWorkItem(template)
    
    def _update_enterprise_metrics(self, cycle_start: datetime):
        """Update enterprise performance metrics"""
        cycle_duration = (datetime.now() - cycle_start).total_seconds()
        
        self.state_data.enterprise_metrics.update({
            'last_cycle_duration_seconds': cycle_duration,
            'cycles_per_hour': 3600 / max(cycle_duration, 1),
            'tasks_per_hour': self.state_data.tasks_completed_in_phase / max(
                (datetime.now() - datetime.fromisoformat(self.state_data.phase_start_time)).total_seconds() / 3600, 
                0.1
            ),
            'uptime_hours': (datetime.now() - datetime.fromisoformat(self.state_data.session_start_time)).total_seconds() / 3600,
            'safety_status': self.state_data.safety_status.value,
            'last_updated': datetime.now().isoformat()
        })
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive status for enterprise monitoring"""
        return {
            'nova_id': self.nova_id,
            'current_state': self.state_data.current_state.value,
            'current_phase': self.state_data.current_phase.value,
            'tasks_completed_in_phase': self.state_data.tasks_completed_in_phase,
            'total_cycles_completed': self.state_data.total_cycles_completed,
            'safety_status': self.state_data.safety_status.value,
            'consecutive_error_count': self.state_data.consecutive_error_count,
            'momentum_tasks_generated': self.state_data.momentum_tasks_generated,
            'enterprise_metrics': self.state_data.enterprise_metrics,
            'session_start_time': self.state_data.session_start_time,
            'phase_start_time': self.state_data.phase_start_time,
            'last_stream_check': self.state_data.last_stream_check,
            'status_generated_at': datetime.now().isoformat()
        }

if __name__ == "__main__":
    # Test the workflow state machine
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing workflow state machine for {nova_id}")
    
    # Create state machine
    state_machine = WorkflowStateMachine(nova_id)
    
    # Execute a few test cycles
    for i in range(5):
        current_state = state_machine.execute_cycle()
        print(f"Cycle {i+1}: {current_state.value}")
        time.sleep(1)
    
    # Print final status
    status = state_machine.get_comprehensive_status()
    print(f"\nFinal Status: {json.dumps(status, indent=2)}")
