---
allowed-tools: Bash
description: Quick diagnostic for workflow issues
---

# 🔍 Workflow Diagnostics

Running comprehensive diagnostics...

!python3 -c "
import redis
import os
import subprocess

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🤖 Nova: {nova_id}')
print('=' * 40)

# Check processes
print('\\n📊 PROCESS CHECK:')
ps_output = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
workflow_procs = [line for line in ps_output.split('\\n') if f'main.py.*{nova_id}' in line and 'grep' not in line]
if workflow_procs:
    for proc in workflow_procs:
        parts = proc.split()
        print(f'  PID {parts[1]}: Started {parts[8]}')
else:
    print('  ❌ No workflow process found')

# Check Redis state
print('\\n📦 REDIS STATE:')
r = redis.Redis(host='localhost', port=18000, decode_responses=True)
state = r.hgetall(f'workflow:state:{nova_id}')
if state:
    for k, v in state.items():
        print(f'  {k}: {v}')
else:
    print('  ❌ No state in Redis')

# Check streams
print('\\n📬 STREAMS:')
coord_msgs = r.xlen(f'nova.coordination.{nova_id}')
task_msgs = r.xlen(f'nova.tasks.{nova_id}')
wake_msgs = r.xlen(f'nova.wake.{nova_id}')
print(f'  Coordination: {coord_msgs} messages')
print(f'  Tasks: {task_msgs} pending')
print(f'  Wake signals: {wake_msgs} pending')

# Check logs
print('\\n📄 LOG CHECK:')
log_path = f'/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/logs/{nova_id}_workflow.log'
if os.path.exists(log_path):
    size = os.path.getsize(log_path) / 1024
    print(f'  Log exists: {size:.1f}KB')
    # Last few lines
    with open(log_path, 'r') as f:
        lines = f.readlines()
        if lines:
            print('  Last entry:', lines[-1].strip()[:60] + '...')
else:
    print('  ❌ No log file')

print('\\n💊 SUGGESTED FIX:')
if workflow_procs and not state:
    print('  State missing - kill process and restart:')
    print(f'  1. pkill -f \"main.py.*{nova_id}\"')
    print('  2. /aa:auto')
elif not workflow_procs:
    print('  No process running - start with:')
    print('  /aa:auto')
else:
    print('  ✅ Everything looks good!')
"