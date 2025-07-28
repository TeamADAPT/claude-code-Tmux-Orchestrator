---
allowed-tools: Bash, mcp__dragonflydb__stream_publish, Read, Write
description: Start or resume autonomous operation - works from any state including stopped
---

# Start/Resume Autonomous Operation

## 🚀 Nova Continuous Operation Workflow (NOVAWF)

This will enable autonomous task execution, allowing me to work continuously without manual intervention.

### What this does:
- Starts the workflow state machine if not running
- Switches to autonomous mode for continuous operation  
- Monitors for tasks and executes them automatically

### Pre-flight checks:

!python3 -c "
import redis
import subprocess
import sys
import os
import signal
import time

print('\n[1/4] 🔍 Checking for existing workflow processes...')

# Check for existing processes
existing = os.popen('ps aux | grep -E \"main\\\\.py.*torch\" | grep -v grep').read().strip()
if existing:
    lines = existing.split('\n')
    print(f'  Found {len(lines)} existing process(es)')
    for line in lines:
        pid = line.split()[1]
        print(f'  - PID {pid}: {\" \".join(line.split()[10:])[:50]}...')
    
    # Clean up old processes
    print('\n[2/4] 🧹 Cleaning up old processes...')
    os.system('pkill -f \"main\\\\.py.*torch\" 2>/dev/null')
    time.sleep(2)
    print('  ✓ Cleanup complete')
else:
    print('  ✓ No existing processes found')
    print('\n[2/4] ⏭️  Skipping cleanup...')

print('\n[3/4] 🚀 Starting NOVAWF process...')

# Ensure logs directory exists
log_dir = '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/logs'
os.makedirs(log_dir, exist_ok=True)
print(f'  ✓ Logs directory ready')

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

try:
    # Start main.py in background
    process = subprocess.Popen([
        'python3', 
        '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/main.py',
        '--nova-id', 'torch'
    ], 
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    start_new_session=True)
    
    print(f'  ✓ Process started (PID: {process.pid})')
    time.sleep(3)  # Give it time to initialize
    
    # Verify it's running
    if process.poll() is None:
        print('  ✓ Process is running')
    else:
        print('  ❌ Process exited unexpectedly')
        sys.exit(1)
        
except Exception as e:
    print(f'  ❌ Failed to start workflow: {e}')
    sys.exit(1)

print('\n[4/4] 🔄 Activating autonomous mode...')
"

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /auto

### 📊 Status Summary:

!python3 -c "
import redis
import os
import time

time.sleep(2)  # Let command process

r = redis.Redis(host='localhost', port=18000, decode_responses=True)
state_data = r.hgetall('workflow:state:torch')

# Get process info
process_info = os.popen('ps aux | grep -E \"main\\\\.py.*torch\" | grep -v grep').read().strip()
if process_info:
    pid = process_info.split()[1]
    print(f'✅ NOVAWF Active')
    print(f'  Mode: {state_data.get(\"current_state\", \"initializing\").replace(\"_\", \" \").title()}')
    print(f'  PID: {pid}')
    print(f'  Logs: ./nova-continuous-operation-workflow/logs/torch_workflow.log')
    print(f'\n💡 Monitor with: ./nova-monitor.sh torch')
else:
    print('⚠️  Process not found - may still be initializing')
    print('  Check status with: ./nova-monitor.sh torch')
"

---

The workflow is now in autonomous operation mode. I'll continue working on tasks automatically without manual intervention.

## 💡 Tips:
- Use `/aa:status` to check workflow status without restarting
- Run `/aa:auto --follow` to start and tail the logs (coming soon)
- Monitor with: `./nova-monitor.sh {nova_id}`