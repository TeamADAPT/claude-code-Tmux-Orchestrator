#!/usr/bin/env python3
"""
Test script to validate safety system integration
"""

import sys
import time
import logging

# Add src to path
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src')

from core.workflow_state_manager import WorkflowStateMachine
from safety import SafetyOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('test_safety')

def test_basic_safety():
    """Test basic safety integration"""
    print("=== Testing Safety Integration ===\n")
    
    # Create workflow with integrated safety
    nova_id = "torch"
    workflow = WorkflowStateMachine(nova_id)
    
    print(f"1. Workflow initialized for {nova_id}")
    print(f"   Safety orchestrator active: {workflow.safety_orchestrator is not None}")
    
    # Test safety check
    print("\n2. Testing safety check...")
    is_safe = workflow._is_safe_to_proceed()
    print(f"   Safe to proceed: {is_safe}")
    
    # Get safety status
    print("\n3. Safety status:")
    safety_status = workflow.safety_orchestrator.get_comprehensive_safety_status()
    print(f"   Safety level: {safety_status['safety_level']}")
    print(f"   Active violations: {safety_status['active_violations']}")
    print(f"   API limits: {safety_status['components']['api_guardian']['limits']}")
    
    # Test dangerous hook validation
    print("\n4. Testing dangerous hook detection...")
    dangerous_hook = """
    while true; do
        claude code -c -p "continue"
    done
    """
    
    is_safe, violations = workflow.safety_orchestrator.validate_hook_content(dangerous_hook)
    print(f"   Hook safe: {is_safe}")
    if violations:
        print(f"   Violations detected: {len(violations)}")
        for v in violations:
            print(f"     - {v['description']}")
    
    # Test API rate limiting
    print("\n5. Testing API rate limiting...")
    for i in range(5):
        validation = workflow.safety_orchestrator.validate_api_request("test")
        print(f"   Request {i+1}: {'ALLOWED' if validation.is_safe else 'BLOCKED'}")
        if not validation.is_safe:
            print(f"     Reason: {validation.violation_type}")
            break
    
    # Test workflow cycle with safety
    print("\n6. Testing workflow cycle with safety...")
    for i in range(3):
        state = workflow.execute_cycle()
        print(f"   Cycle {i+1}: {state.value}")
        time.sleep(1)
    
    print("\n=== Safety Integration Test Complete ===")

if __name__ == "__main__":
    test_basic_safety()