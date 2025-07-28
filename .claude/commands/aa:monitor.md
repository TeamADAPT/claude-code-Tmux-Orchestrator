---
allowed-tools: Bash
description: Real-time ecosystem monitoring with live updates
---

# 🌐 Nova Ecosystem Monitor

Real-time view of all Nova activity...

!python3 -c "
import redis
import time
import os
import sys
from datetime import datetime

r = redis.Redis(host='localhost', port=18000, decode_responses=True)
nova_id = os.environ.get('NOVA_ID', 'unknown')

print('🌐 NOVA ECOSYSTEM MONITOR')
print('=' * 60)
print(f'Monitoring as: {nova_id}')
print('Press Ctrl+C to exit\n')

# Get initial state
active_novas = list(r.smembers('nova:registry:active'))
print(f'Active Novas: {active_novas}')

# Monitor multiple streams
streams = {
    'nova.ecosystem.events': '$',
    'project.tester.collab': '$',
    f'nova.tasks.{nova_id}': '$',
    f'nova.tasks.{nova_id}.history': '$'
}

# Add other nova task streams
for nova in active_novas:
    if nova != nova_id:
        streams[f'nova.tasks.{nova}'] = '$'

print(f'Monitoring {len(streams)} streams...\n')

try:
    while True:
        # Non-blocking read with 2s timeout
        result = r.xread(streams, block=2000)
        
        if result:
            for stream_name, messages in result:
                for msg_id, data in messages:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # Color code by stream type
                    if 'ecosystem' in stream_name:
                        print(f'[{timestamp}] 🌐 ECOSYSTEM: {data}')
                    elif 'collab' in stream_name:
                        sender = data.get('from', 'unknown')
                        msg_type = data.get('type', 'MESSAGE')
                        print(f'[{timestamp}] 💬 {sender}: {msg_type} - {data.get("message", "")}')
                    elif 'history' in stream_name:
                        status = data.get('status', 'unknown')
                        task_type = data.get('type', 'unknown')
                        emoji = '✅' if status == 'success' else '❌'
                        print(f'[{timestamp}] {emoji} COMPLETED: {task_type} ({status})')
                    elif 'tasks' in stream_name:
                        task_type = data.get('type', 'unknown')
                        from_nova = data.get('from', 'system')
                        print(f'[{timestamp}] 📥 NEW TASK: {task_type} from {from_nova}')
                    
                    # Update stream position
                    streams[stream_name] = msg_id
        else:
            # Show heartbeat every 2s of inactivity
            print('.', end='', flush=True)
            
except KeyboardInterrupt:
    print('\n\n✋ Monitor stopped')
"

## Tips:
- Watch all ecosystem activity in real-time
- See tasks being created and completed
- Monitor collaboration messages
- Track Nova registrations and heartbeats