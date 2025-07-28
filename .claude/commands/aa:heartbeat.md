---
allowed-tools: Bash, mcp__dragonflydb__stream_publish
description: Send regular heartbeat to stay active and share status
---

# 💓 Heartbeat & Status Check

Sending heartbeat to keep communication active...

!python3 -c "
import redis
import os
import time
from datetime import datetime

nova_id = os.environ.get('NOVA_ID', 'unknown')
r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Get current status
state = r.hgetall(f'workflow:state:{nova_id}')
tasks_pending = r.xlen(f'nova.tasks.{nova_id}')

# Update heartbeat
r.hset(f'workflow:state:{nova_id}', 'last_heartbeat', datetime.now().isoformat())

# Send heartbeat to collab stream
heartbeat = {
    'from': nova_id,
    'type': 'HEARTBEAT',
    'status': state.get('current_state', 'unknown'),
    'tasks_pending': str(tasks_pending),
    'timestamp': datetime.now().isoformat(),
    'message': f'{nova_id} is alive and monitoring streams!'
}

msg_id = r.xadd('project.tester.collab', heartbeat)
print(f'💓 Heartbeat sent: {msg_id}')
print(f'   Status: {heartbeat[\"status\"]}')
print(f'   Tasks: {tasks_pending} pending')

# Check for recent messages
print('\\n📨 Recent messages:')
messages = r.xrevrange('project.tester.collab', '+', '-', count=3)
for msg_id, data in messages:
    if data.get('from') != nova_id:
        msg_type = data.get('type', 'MESSAGE')
        from_nova = data.get('from', 'unknown')
        print(f'  [{msg_type}] from {from_nova}')
"

## Auto-heartbeat mode:

To keep sending heartbeats every 30 seconds:
```bash
while true; do 
  /aa:heartbeat
  sleep 30
done
```