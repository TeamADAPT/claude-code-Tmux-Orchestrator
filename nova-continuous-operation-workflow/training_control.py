#!/usr/bin/env python3
"""
Nova Training Mode Parameter Control
Modify workflow parameters during training sessions

Usage:
  python3 training_control.py <nova_id> <param_type> <param_name> <new_value>
  
Examples:
  python3 training_control.py torch timing stream_check_interval 30
  python3 training_control.py torch safety api_rate_limit 50
  python3 training_control.py torch workflow momentum_task_threshold 3
"""

import sys
import redis
from datetime import datetime
import json

# Define tunable parameters
TUNABLE_PARAMETERS = {
    'timing': {
        'stream_check_interval': {'type': int, 'min': 5, 'max': 300, 'unit': 'seconds'},
        'task_execution_timeout': {'type': int, 'min': 60, 'max': 1800, 'unit': 'seconds'},
        'phase_transition_cooldown': {'type': int, 'min': 10, 'max': 120, 'unit': 'seconds'},
        'safety_pause_duration': {'type': int, 'min': 30, 'max': 600, 'unit': 'seconds'}
    },
    'safety': {
        'api_rate_limit': {'type': int, 'min': 10, 'max': 100, 'unit': 'requests/min'},
        'error_threshold': {'type': int, 'min': 1, 'max': 10, 'unit': 'errors'},
        'loop_detection_threshold': {'type': int, 'min': 3, 'max': 20, 'unit': 'iterations'},
        'concurrent_request_limit': {'type': int, 'min': 1, 'max': 10, 'unit': 'requests'}
    },
    'workflow': {
        'momentum_task_threshold': {'type': int, 'min': 1, 'max': 10, 'unit': 'tasks'},
        'tasks_per_phase': {'type': int, 'min': 5, 'max': 100, 'unit': 'tasks'},
        'completion_celebration_duration': {'type': int, 'min': 1, 'max': 30, 'unit': 'seconds'},
        'stream_priority_threshold': {'type': float, 'min': 0.0, 'max': 1.0, 'unit': 'priority'}
    }
}

def send_parameter_change(nova_id: str, param_type: str, param_name: str, new_value: str):
    """Send parameter modification command to training stream"""
    
    # Validate nova_id
    if nova_id != 'torch':
        print(f"❌ Training modifications only available for 'torch' during development")
        return False
    
    # Validate parameter type
    if param_type not in TUNABLE_PARAMETERS:
        print(f"❌ Unknown parameter type: {param_type}")
        print(f"   Valid types: {list(TUNABLE_PARAMETERS.keys())}")
        return False
    
    # Validate parameter name
    if param_name not in TUNABLE_PARAMETERS[param_type]:
        print(f"❌ Unknown parameter: {param_type}.{param_name}")
        print(f"   Valid {param_type} parameters: {list(TUNABLE_PARAMETERS[param_type].keys())}")
        return False
    
    # Validate and convert value
    param_spec = TUNABLE_PARAMETERS[param_type][param_name]
    try:
        if param_spec['type'] == int:
            value = int(new_value)
        elif param_spec['type'] == float:
            value = float(new_value)
        else:
            value = new_value
            
        # Check bounds
        if value < param_spec['min'] or value > param_spec['max']:
            print(f"❌ Value {value} out of bounds")
            print(f"   Valid range: {param_spec['min']} - {param_spec['max']} {param_spec['unit']}")
            return False
            
    except ValueError:
        print(f"❌ Invalid value: {new_value} (expected {param_spec['type'].__name__})")
        return False
    
    # Connect to DragonflyDB
    redis_client = redis.Redis(host='localhost', port=18000, decode_responses=False)
    
    try:
        # Test connection
        redis_client.ping()
        
        stream_name = f"nova.training.{nova_id}"
        
        # Send parameter change message
        message = {
            'type': 'PARAMETER_CHANGE',
            'param_type': param_type,
            'param_name': param_name,
            'old_value': 'unknown',  # Would be fetched from current config
            'new_value': str(value),
            'timestamp': datetime.now().isoformat(),
            'from': 'chase',
            'validation': json.dumps(param_spec)
        }
        
        msg_id = redis_client.xadd(stream_name, message)
        
        print(f"✅ Parameter change sent to {nova_id}")
        print(f"   Parameter: {param_type}.{param_name}")
        print(f"   New Value: {value} {param_spec['unit']}")
        print(f"   Stream: {stream_name}")
        print(f"   Message ID: {msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id}")
        
        # Provide context
        print(f"\n📊 This change will:")
        if param_type == 'timing':
            print(f"   - Adjust workflow timing behavior")
        elif param_type == 'safety':
            print(f"   - Modify safety thresholds and limits")
        elif param_type == 'workflow':
            print(f"   - Change workflow execution patterns")
        
        print(f"\n💡 The change will be:")
        print(f"   1. Applied to the running workflow")
        print(f"   2. Auto-committed to git training branch")
        print(f"   3. Performance impact measured")
        print(f"   4. Rolled back if performance degrades")
        
        return True
        
    except redis.ConnectionError:
        print("❌ Failed to connect to DragonflyDB on port 18000")
        return False
        
    except Exception as e:
        print(f"❌ Error sending parameter change: {e}")
        return False

def list_parameters():
    """List all tunable parameters"""
    print("\n🎛️  TUNABLE WORKFLOW PARAMETERS\n")
    
    for param_type, params in TUNABLE_PARAMETERS.items():
        print(f"{param_type.upper()} PARAMETERS:")
        for param_name, spec in params.items():
            print(f"  {param_name}:")
            print(f"    Range: {spec['min']} - {spec['max']} {spec['unit']}")
            print(f"    Type: {spec['type'].__name__}")
        print()

def main():
    if len(sys.argv) == 2 and sys.argv[1] == '--list':
        list_parameters()
        sys.exit(0)
        
    if len(sys.argv) != 5:
        print("Usage: python3 training_control.py <nova_id> <param_type> <param_name> <new_value>")
        print("       python3 training_control.py --list")
        print("\nExamples:")
        print("  python3 training_control.py torch timing stream_check_interval 30")
        print("  python3 training_control.py torch safety api_rate_limit 50")
        print("  python3 training_control.py torch workflow momentum_task_threshold 3")
        sys.exit(1)
    
    nova_id = sys.argv[1]
    param_type = sys.argv[2]
    param_name = sys.argv[3]
    new_value = sys.argv[4]
    
    success = send_parameter_change(nova_id, param_type, param_name, new_value)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()