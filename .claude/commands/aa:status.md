---
allowed-tools: Bash, mcp__dragonflydb__stream_read, mcp__dragonflydb__get
description: Check current NOVAWF status and state - works even if stopped
---

# Check Workflow Status

I'll check the current workflow status and display the latest state information.

!python3 -c "
import redis
import json
from datetime import datetime

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

try:
    state_data = r.hgetall('workflow:state:torch')
    if state_data:
        print(f'🟢 WORKFLOW STATUS - {datetime.now().strftime(\"%Y-%m-%d %H:%M:%S\")}')
        print('='*50)
        print(f'Current State: {state_data.get(\"current_state\", \"unknown\")}')
        print(f'Current Phase: {state_data.get(\"current_phase\", \"unknown\")}')
        print(f'Safety Status: {state_data.get(\"safety_status\", \"unknown\")}')
        print(f'Tasks Completed: {state_data.get(\"tasks_completed_in_phase\", 0)}')
        print(f'Total Cycles: {state_data.get(\"total_cycles_completed\", 0)}')
        print(f'Tool Use Count: {state_data.get(\"tool_use_count\", 0)}')
        print('='*50)
        
        metrics = json.loads(state_data.get('enterprise_metrics', '{}'))
        if metrics:
            print('\n📊 PERFORMANCE METRICS')
            print('='*50)
            print(f'Tasks/Hour: {metrics.get(\"tasks_per_hour\", 0):.2f}')
            print(f'Cycles/Hour: {metrics.get(\"cycles_per_hour\", 0):.2f}')
            print(f'Uptime Hours: {metrics.get(\"uptime_hours\", 0):.2f}')
            print(f'Last Cycle Duration: {metrics.get(\"last_cycle_duration_seconds\", 0):.1f}s')
    else:
        print('🔴 WORKFLOW STOPPED')
        print('='*50)
        print('No workflow state found - workflow is not running')
        print('Use /aa:auto to start the workflow')
except Exception as e:
    print(f'❌ Error reading workflow state: {e}')
    print('DragonflyDB may not be running on port 18000')
"