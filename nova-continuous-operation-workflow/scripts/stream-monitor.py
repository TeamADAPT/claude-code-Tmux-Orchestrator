#!/usr/bin/env python3
"""
Real-time stream monitor using XREAD BLOCK
Keeps both Novas active and communicating
"""
import redis
import time
import json
from datetime import datetime

def monitor_streams(nova_id='torch'):
    r = redis.Redis(host='localhost', port=18000, decode_responses=True)
    
    # Start from latest
    last_id = '$'
    
    print(f"🎯 Monitoring project.tester.collab for {nova_id}")
    print("=" * 50)
    
    while True:
        try:
            # XREAD BLOCK waits for new messages
            # Timeout every 30s to send heartbeat
            result = r.xread(
                {'project.tester.collab': last_id}, 
                block=30000  # 30 second timeout
            )
            
            if result:
                # Process new messages
                for stream_name, messages in result:
                    for msg_id, data in messages:
                        last_id = msg_id
                        
                        # Skip our own messages
                        if data.get('from') != nova_id:
                            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] New message!")
                            print(f"  From: {data.get('from')}")
                            print(f"  Type: {data.get('type')}")
                            if 'message' in data:
                                print(f"  Message: {data['message']}")
                            
                            # Auto-respond to certain types
                            if data.get('type') == 'HEARTBEAT':
                                # Echo back
                                r.xadd('project.tester.collab', {
                                    'from': nova_id,
                                    'type': 'HEARTBEAT_ACK',
                                    'message': f"{nova_id} received heartbeat from {data.get('from')}",
                                    'timestamp': datetime.now().isoformat()
                                })
            else:
                # Timeout - send our own heartbeat
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Sending heartbeat...")
                r.xadd('project.tester.collab', {
                    'from': nova_id,
                    'type': 'HEARTBEAT',
                    'message': f"{nova_id} still monitoring",
                    'timestamp': datetime.now().isoformat()
                })
                
        except KeyboardInterrupt:
            print("\n👋 Stopping monitor")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    import sys
    nova_id = sys.argv[1] if len(sys.argv) > 1 else 'torch'
    monitor_streams(nova_id)