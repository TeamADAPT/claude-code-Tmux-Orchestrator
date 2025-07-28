# Nova Workflow Control System

## Overview
The NOVAWF control system allows you to switch any Nova between manual and autonomous operation modes using simple commands.

## Quick Commands

```bash
# Enter manual mode (pause autonomous workflow)
python3 control_workflow.py <nova_id> /man

# Enter autonomous mode (resume workflow)  
python3 control_workflow.py <nova_id> /auto
```

## Examples

```bash
# Pause Torch's workflow for manual control
python3 control_workflow.py torch /man

# Resume Torch's autonomous operation
python3 control_workflow.py torch /auto

# Control other Novas
python3 control_workflow.py echo /man
python3 control_workflow.py forge /auto
```

## How It Works

### Manual Mode (`/man`)
- **Effect**: Nova enters `MANUAL_MODE` state
- **Behavior**: Workflow engine pauses, waits for `/auto` command
- **Use Case**: When you want direct control over the Nova
- **Monitoring**: Enterprise monitoring shows "WORKFLOW_PAUSED_BY_USER"

### Autonomous Mode (`/auto`)
- **Effect**: Nova exits manual mode, resumes workflow
- **Behavior**: Returns to normal anti-drift state machine operation  
- **Use Case**: Resume hands-off continuous operation
- **Monitoring**: Enterprise monitoring shows normal workflow states

## Technical Details

### Stream Communication
- Commands sent to: `nova.coordination.{nova_id}`
- Messages include: type, timestamp, command, reason
- Nova checks for commands before each workflow cycle

### State Integration
- New state: `WorkflowState.MANUAL_MODE` 
- Control detection: `_check_control_commands()`
- Manual handler: `_handle_manual_mode()`
- Seamless integration with existing safety systems

### Enterprise Monitoring
- Manual mode events logged to: `nova.enterprise.control.{nova_id}`
- Status tracking: WORKFLOW_PAUSED_BY_USER / AUTONOMOUS_OPERATION
- Full audit trail of mode changes

## Safety Features

- Commands only affect workflow states, not safety systems
- Safety Orchestrator remains active in both modes
- Error recovery mechanisms still function
- All mode changes logged for audit

## Requirements

- DragonflyDB running on port 18000 (APEX infrastructure)
- Nova running NOVAWF workflow engine
- Python 3 with redis library

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Manual/Autonomous Control System v1.0