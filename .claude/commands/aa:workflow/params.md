---
allowed-tools: Read
description: View current workflow parameter values
---

# View Current Workflow Parameters

I'll show you the current workflow parameter configuration.

@/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/core/workflow_parameters.py

The parameters shown above control various aspects of the workflow:

## Timing Parameters
- **stream_check_interval**: How often to check coordination streams
- **task_execution_timeout**: Maximum time for task execution
- **phase_transition_cooldown**: Pause between phase transitions
- **safety_pause_duration**: Length of safety pauses

## Safety Parameters  
- **api_rate_limit**: API calls per minute limit
- **error_threshold**: Consecutive errors before safety pause
- **loop_detection_threshold**: Iterations before loop intervention
- **concurrent_request_limit**: Max concurrent API requests

## Workflow Parameters
- **momentum_task_threshold**: Tasks before generating momentum work
- **tasks_per_phase**: Target tasks per workflow phase
- **completion_celebration_duration**: Time in completion state
- **stream_priority_threshold**: Message priority threshold

To modify these parameters, use:
- `/aa:train` to enter training mode
- `/aa:train:timing <param> <value>`
- `/aa:train:safety <param> <value>`
- `/aa:train:workflow <param> <value>`