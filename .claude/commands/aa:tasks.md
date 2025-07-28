---
allowed-tools: Bash
description: View pending tasks in your queue
---

# 📋 Task Queue Viewer

Checking your pending tasks...

!python3 -c "
import redis
import os
from datetime import datetime

r = redis.Redis(host='localhost', port=18000, decode_responses=True)
nova_id = os.environ.get('NOVA_ID', 'unknown')

print(f'📋 Task Queue for Nova: {nova_id}')
print('=' * 60)

# Get pending tasks
tasks = r.xrange(f'nova.tasks.{nova_id}')

if not tasks:
    print('✨ No pending tasks!')
else:
    print(f'📥 {len(tasks)} pending task(s):\n')
    
    for i, (task_id, data) in enumerate(tasks, 1):
        print(f'{i}. Task ID: {task_id}')
        print(f'   Type: {data.get("type", "unknown")}')
        print(f'   Priority: {data.get("priority", "normal")}')
        
        if 'description' in data:
            print(f'   Description: {data["description"]}')
        
        if 'from' in data:
            print(f'   From: {data["from"]}')
            
        if 'payload' in data:
            print(f'   Payload: {data["payload"][:100]}...')
            
        print()

# Show recent history
print('\n📜 Recent Task History:')
history = r.xrevrange(f'nova.tasks.{nova_id}.history', '+', '-', count=5)

if not history:
    print('   No completed tasks yet')
else:
    for task_id, data in history:
        status = data.get('status', 'unknown')
        task_type = data.get('type', 'unknown')
        completed = data.get('completed_at', 'unknown')
        emoji = '✅' if status == 'success' else '❌'
        print(f'   {emoji} {task_type} - {status} at {completed}')
"

## Next Steps:
- Run `/aa:executor` to start processing these tasks
- Use `/aa:history` for detailed task execution history
- Monitor with `/aa:monitor` for real-time updates