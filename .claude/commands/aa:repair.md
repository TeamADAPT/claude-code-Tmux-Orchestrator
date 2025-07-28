---
allowed-tools: Bash
description: Repair workflow state issues
---

# 🔧 Workflow Repair Tool

Attempting to repair workflow state...

!python3 -c "
import redis
import os
import subprocess
import time
from datetime import datetime

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🔧 Repairing workflow for Nova: {nova_id}')
print('=' * 40)

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Step 1: Find orphaned processes
print('\\n[1/4] 🔍 Finding orphaned processes...')
ps_output = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
workflow_procs = [line for line in ps_output.split('\\n') if f'main.py.*{nova_id}' in line and 'grep' not in line]

if workflow_procs:
    print(f'  Found {len(workflow_procs)} process(es)')
    for proc in workflow_procs:
        pid = proc.split()[1]
        print(f'  Killing PID {pid}...')
        os.system(f'kill -9 {pid} 2>/dev/null')
    time.sleep(2)
    print('  ✓ Cleaned up orphaned processes')
else:
    print('  ✓ No orphaned processes')

# Step 2: Clear stale state
print('\\n[2/4] 🧹 Clearing stale state...')
old_state = r.hgetall(f'workflow:state:{nova_id}')
if old_state:
    r.delete(f'workflow:state:{nova_id}')
    print('  ✓ Cleared old state')
else:
    print('  ✓ No stale state found')

# Step 3: Clear old coordination messages
print('\\n[3/4] 📬 Clearing old messages...')
r.delete(f'nova.coordination.{nova_id}')
r.delete(f'nova.wake.{nova_id}')
print('  ✓ Cleared coordination streams')

# Step 4: Initialize fresh state
print('\\n[4/4] 🚀 Initializing fresh workflow state...')
initial_state = {
    'current_state': 'initializing',
    'nova_id': nova_id,
    'initialized_at': datetime.now().isoformat(),
    'last_heartbeat': datetime.now().isoformat(),
    'mode': 'starting'
}
r.hset(f'workflow:state:{nova_id}', mapping=initial_state)
print('  ✓ Created initial state')

print('\\n✅ REPAIR COMPLETE!')
print('\\nNext steps:')
print('1. Run /aa:auto to start the workflow')
print('2. Run /aa:status to verify it\\'s working')
"