---
allowed-tools: Bash, mcp__dragonflydb__stream_publish, Read, Write
description: Start or resume autonomous operation - works from any state including stopped
---

# Start/Resume Autonomous Operation

I'll start or resume the NOVAWF autonomous operation.

First, let me check if the workflow is running:

!python3 -c "
import redis
import subprocess
import sys

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Check if workflow state exists
state_data = r.hgetall('workflow:state:torch')

if not state_data:
    print('🚀 Workflow not running - starting fresh...')
    # Start the workflow process
    try:
        # Start main.py in background
        subprocess.Popen([
            'python3', 
            '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/main.py',
            '--nova-id', 'torch'
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

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /auto

The workflow is now in autonomous operation mode. I'll continue working on tasks automatically.