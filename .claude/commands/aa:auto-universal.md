---
allowed-tools: Bash, mcp__dragonflydb__stream_publish, Read, Write
description: Universal auto command that works for ANY Nova
---

# Start/Resume Autonomous Operation - Universal Version

I'll start the NOVAWF autonomous operation for the current Nova.

First, let me determine which Nova I am:

!import os
nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f"Nova ID: {nova_id}")

Now checking if the workflow is running:

!python3 -c "
import redis
import subprocess
import sys
import os

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🔍 Checking workflow for Nova: {nova_id}')

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Check if workflow state exists
state_data = r.hgetall(f'workflow:state:{nova_id}')

if not state_data:
    print('🚀 Workflow not running - starting fresh...')
    # Start the workflow process
    try:
        # Start main.py in background
        subprocess.Popen([
            'python3', 
            '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/main.py',
            '--nova-id', nova_id
        ], 
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True)
        print('✅ Workflow process started!')
    except Exception as e:
        print(f'❌ Failed to start workflow: {e}')
        sys.exit(1)
else:
    current_state = state_data.get('current_state', 'unknown')
    print(f'📊 Workflow already running in state: {current_state}')
    if current_state in ['manual_mode', 'training_mode']:
        print('🔄 Switching to autonomous mode...')

# Send auto command regardless to ensure autonomous mode
print('📨 Sending autonomous mode command...')
"

!python3 -c "
import os
nova_id = os.environ.get('NOVA_ID', 'unknown')
cmd = f'python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py {nova_id} /auto'
os.system(cmd)
"

The workflow is now in autonomous operation mode!