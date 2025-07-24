#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Main Entry Point
Orchestrates the complete workflow with all safety and compliance features

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
"""

import sys
import time
import signal
import logging
import argparse
from datetime import datetime

# Add src to path
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src')

from core.workflow_state_manager import WorkflowStateMachine, WorkflowState
from core.stream_controller import StreamController
from core.task_tracker import TaskTracker, TaskPriority
from safety import SafetyOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('novawf.main')

class NovaContinuousWorkflow:
    """
    Main workflow orchestrator integrating all components
    """
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id
        self.running = False
        
        logger.info(f"Initializing Nova Continuous Operation Workflow for {nova_id}")
        
        # Initialize core components
        self.state_machine = WorkflowStateMachine(nova_id, redis_port)
        self.stream_controller = StreamController(nova_id, redis_port)
        self.task_tracker = TaskTracker(nova_id, redis_port)
        
        # Wire components together
        self.state_machine.stream_controller = self.stream_controller
        self.state_machine.task_tracker = self.task_tracker
        
        # Safety is already integrated in state machine
        self.safety_orchestrator = self.state_machine.safety_orchestrator
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info("All components initialized and wired together")
    
    def run(self):
        """Run the continuous workflow"""
        self.running = True
        logger.info(f"Starting continuous workflow for {self.nova_id}")
        
        # Post startup status
        self.stream_controller.post_status_update('WORKFLOW_STARTED', {
            'nova_id': self.nova_id,
            'start_time': datetime.now().isoformat(),
            'safety_status': 'ACTIVE',
            'compliance_status': 'ACTIVE'
        })
        
        cycle_count = 0
        
        try:
            while self.running:
                cycle_count += 1
                
                # Execute workflow cycle
                logger.info(f"=== Cycle {cycle_count} ===")
                
                # Safety check first
                if not self.safety_orchestrator.is_safe_to_proceed():
                    logger.warning("Safety check failed, entering safety pause")
                    time.sleep(30)  # Safety pause
                    continue
                
                # Execute state machine cycle
                current_state = self.state_machine.execute_cycle()
                
                # Check for work from streams every 5 cycles
                if cycle_count % 5 == 0:
                    self._check_coordination_streams()
                
                # Update metrics every 10 cycles
                if cycle_count % 10 == 0:
                    self._update_enterprise_metrics()
                
                # Adaptive sleep based on state
                sleep_time = self._get_adaptive_sleep_time(current_state)
                logger.info(f"Completed cycle {cycle_count}, state: {current_state.value}, sleeping {sleep_time}s")
                
                time.sleep(sleep_time)
                
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            self._handle_critical_error(e)
        
        finally:
            self._shutdown()
    
    def _check_coordination_streams(self):
        """Check coordination streams for priority work"""
        logger.info("Checking coordination streams")
        
        messages = self.stream_controller.check_coordination_streams()
        if messages:
            # Process priority messages
            work_items = self.stream_controller.process_priority_messages(messages)
            
            for work_item in work_items[:3]:  # Process top 3 priority items
                # Create NOVA-compliant task
                task_id = self.task_tracker.create_task(
                    title=work_item.title,
                    description=work_item.description,
                    priority=TaskPriority.HIGH if work_item.priority.value <= 2 else TaskPriority.MEDIUM
                )
                
                logger.info(f"Created task from coordination: {task_id}")
    
    def _update_enterprise_metrics(self):
        """Update enterprise metrics and dashboards"""
        try:
            # Get comprehensive status
            workflow_status = self.state_machine.get_comprehensive_status()
            safety_status = self.safety_orchestrator.get_comprehensive_safety_status()
            task_metrics = self.task_tracker.get_task_metrics(24)
            stream_health = self.stream_controller.get_stream_health_status()
            
            # Create dashboard
            dashboard = {
                'nova_id': self.nova_id,
                'workflow': workflow_status,
                'safety': safety_status,
                'tasks': task_metrics,
                'streams': stream_health,
                'generated_at': datetime.now().isoformat()
            }
            
            # Post to enterprise dashboard stream
            self.stream_controller.redis_client.xadd(
                'nova.enterprise.dashboards',
                {
                    'nova_id': self.nova_id,
                    'dashboard_type': 'comprehensive',
                    'data': json.dumps(dashboard),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info("Updated enterprise metrics")
            
        except Exception as e:
            logger.error(f"Failed to update enterprise metrics: {e}")
    
    def _get_adaptive_sleep_time(self, state: WorkflowState) -> int:
        """Get adaptive sleep time based on current state"""
        sleep_times = {
            WorkflowState.INITIALIZING: 5,
            WorkflowState.STREAM_CHECK: 2,
            WorkflowState.WORK_DISCOVERY: 3,
            WorkflowState.TASK_EXECUTION: 10,
            WorkflowState.PROGRESS_UPDATE: 5,
            WorkflowState.COMPLETION_ROUTINE: 30,  # Celebration time
            WorkflowState.PHASE_TRANSITION: 180,   # 3 minute phase break
            WorkflowState.ERROR_RECOVERY: 30,
            WorkflowState.SAFETY_PAUSE: 60
        }
        
        return sleep_times.get(state, 5)
    
    def _handle_shutdown(self, signum, frame):
        """Handle graceful shutdown"""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False
    
    def _handle_critical_error(self, error: Exception):
        """Handle critical errors with safety protocols"""
        logger.critical(f"CRITICAL ERROR: {error}")
        
        # Activate safety protocols
        self.safety_orchestrator.handle_safety_violation(
            'CRITICAL_ERROR',
            {'error': str(error), 'type': type(error).__name__}
        )
        
        # Post emergency alert
        self.stream_controller.redis_client.xadd(
            'nova.priority.alerts',
            {
                'type': 'WORKFLOW_CRITICAL_ERROR',
                'nova_id': self.nova_id,
                'error': str(error),
                'timestamp': datetime.now().isoformat(),
                'severity': 'CRITICAL'
            }
        )
    
    def _shutdown(self):
        """Graceful shutdown procedures"""
        logger.info("Shutting down workflow")
        
        # Post shutdown status
        self.stream_controller.post_status_update('WORKFLOW_SHUTDOWN', {
            'nova_id': self.nova_id,
            'shutdown_time': datetime.now().isoformat(),
            'reason': 'graceful_shutdown'
        })
        
        # Generate final reports
        try:
            compliance_report = self.task_tracker.generate_compliance_report()
            logger.info(f"Final compliance: {compliance_report['compliance_percentage']}%")
        except:
            pass
        
        logger.info("Workflow shutdown complete")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Nova Continuous Operation Workflow'
    )
    parser.add_argument(
        '--nova-id',
        default='torch',
        help='Nova ID for this instance'
    )
    parser.add_argument(
        '--redis-port',
        type=int,
        default=18000,
        help='Redis port for DragonflyDB'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Run in test mode (5 cycles only)'
    )
    
    args = parser.parse_args()
    
    # Create and run workflow
    workflow = NovaContinuousWorkflow(args.nova_id, args.redis_port)
    
    if args.test:
        # Test mode - run 5 cycles
        logger.info("Running in test mode (5 cycles)")
        workflow.running = True
        for i in range(5):
            if not workflow.safety_orchestrator.is_safe_to_proceed():
                logger.warning("Safety check failed")
                break
            
            state = workflow.state_machine.execute_cycle()
            logger.info(f"Test cycle {i+1}: {state.value}")
            time.sleep(1)
        
        logger.info("Test mode complete")
    else:
        # Production mode
        workflow.run()

if __name__ == "__main__":
    import json  # Import needed for dashboard serialization
    main()