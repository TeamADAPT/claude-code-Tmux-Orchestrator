#!/usr/bin/env python3
"""
Nova Workflow Control Utility
Send /man and /auto commands to control Nova workflow execution

Usage:
  python3 control_workflow.py <nova_id> /man    # Enter manual mode
  python3 control_workflow.py <nova_id> /auto   # Enter autonomous mode
  python3 control_workflow.py torch /man        # Example for torch Nova
"""

import sys
import redis
from datetime import datetime

def send_control_command(nova_id: str, command: str):
    """Send control command to Nova's coordination stream"""
    
    # Connect to DragonflyDB on APEX infrastructure
    redis_client = redis.Redis(host='localhost', port=18000, decode_responses=False)
    
    try:
        # Test connection
        redis_client.ping()
        
        stream_name = f"nova.coordination.{nova_id}"
        
        if command == '/man':
            # Send manual mode command
            message = {
                'type': 'CONTROL_MANUAL',
                'command': '/man',
                'timestamp': datetime.now().isoformat(),
                'from': 'chase',
                'reason': 'USER_REQUESTED_MANUAL_CONTROL'
            }
            
        elif command == '/auto':
            # Send autonomous mode command
            message = {
                'type': 'CONTROL_AUTO', 
                'command': '/auto',
                'timestamp': datetime.now().isoformat(),
                'from': 'chase',
                'reason': 'USER_REQUESTED_AUTONOMOUS_OPERATION'
            }
            
        elif command == '/train':
            # Send training mode command (development only)
            if nova_id != 'torch':
                print(f"❌ Training mode only available for 'torch' during development")
                return False
                
            message = {
                'type': 'CONTROL_TRAIN',
                'command': '/train',
                'timestamp': datetime.now().isoformat(),
                'from': 'chase',
                'reason': 'USER_REQUESTED_TRAINING_MODE'
            }
            
        else:
            print(f"Unknown command: {command}")
            print("Valid commands: /man, /auto, /train (torch only)")
            return False
        
        # Send message to stream
        msg_id = redis_client.xadd(stream_name, message)
        
        print(f"✅ Command sent to {nova_id}")
        print(f"   Stream: {stream_name}")
        print(f"   Command: {command}")
        print(f"   Message ID: {msg_id.decode('utf-8') if isinstance(msg_id, bytes) else msg_id}")
        
        return True
        
    except redis.ConnectionError:
        print("❌ Failed to connect to DragonflyDB on port 18000")
        print("   Make sure DragonflyDB is running on the APEX infrastructure")
        return False
        
    except Exception as e:
        print(f"❌ Error sending command: {e}")
        return False

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 control_workflow.py <nova_id> <command>")
        print("Commands: /man (manual mode), /auto (autonomous mode), /train (torch dev only)")
        print("Example: python3 control_workflow.py torch /man")
        print("Example: python3 control_workflow.py torch /train")
        sys.exit(1)
    
    nova_id = sys.argv[1]
    command = sys.argv[2]
    
    success = send_control_command(nova_id, command)
    
    if success:
        if command == '/man':
            print(f"\n🔴 {nova_id} workflow will enter MANUAL MODE")
            print("   The Nova will pause autonomous operation")
            print("   Send '/auto' to resume autonomous operation")
        elif command == '/auto':
            print(f"\n🟢 {nova_id} workflow will enter AUTONOMOUS MODE")
            print("   The Nova will resume autonomous operation")
            print("   Send '/man' to pause for manual control")
        elif command == '/train':
            print(f"\n🧪 {nova_id} workflow will enter TRAINING MODE")
            print("   Adaptive parameter tuning enabled")
            print("   Git branch created for versioned experiments")
            print("   Send '/auto' to exit training and resume normal operation")
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()