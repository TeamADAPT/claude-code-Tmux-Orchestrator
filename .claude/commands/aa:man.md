---
allowed-tools: Bash, mcp__dragonflydb__stream_publish
description: Enter manual mode - pause NOVAWF autonomous operation (only if running)
---

# Enter Manual Mode

I'll send the manual mode command to pause autonomous operation.

!python3 -c "
import redis

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Check if workflow is running
state_data = r.hgetall('workflow:state:torch')

if not state_data:
    print('⚠️  Workflow is not running')
    print('   Manual mode is for pausing an active workflow')
    print('   Use /aa:auto to start the workflow first')
else:
    print('📊 Workflow is running - switching to manual mode')
"

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /man

Manual mode command sent. The workflow will pause if it's running.
To start or resume autonomous operation, use `/aa:auto`.