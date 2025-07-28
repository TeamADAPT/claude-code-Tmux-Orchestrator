---
allowed-tools: Bash, Read, Write, Edit, mcp__dragonflydb__stream_publish
description: Enter training mode for adaptive parameter tuning (torch only) - does NOT start workflow
---

# Enter Training Mode

I'll send the training mode command. This allows debugging and modification without the workflow interfering.

!python3 -c "
import redis

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Check if workflow is running
state_data = r.hgetall('workflow:state:torch')

if not state_data:
    print('⚠️  Workflow is not running')
    print('   Training mode allows you to:')
    print('   - Debug and modify code without interference')
    print('   - Test changes in isolation')
    print('   - Start workflow with /aa:auto when ready')
else:
    print('📊 Workflow is running - switching to training mode')
"

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /train

Training mode command sent. Available commands:
- Use `/aa:train:timing <param> <value>` to adjust timing parameters
- Use `/aa:train:safety <param> <value>` to adjust safety parameters
- Use `/aa:train:workflow <param> <value>` to adjust workflow parameters
- Use `/aa:train:list` to see all tunable parameters
- Use `/aa:auto` to start workflow or exit training mode