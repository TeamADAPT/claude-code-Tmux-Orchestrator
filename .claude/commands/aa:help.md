---
allowed-tools: Bash
description: Show all NOVAWF slash commands
---

# NOVAWF Slash Commands Help

## Core Control Commands
- `/aa:auto` - Start or resume autonomous operation (works from stopped state)
- `/aa:man` - Enter manual mode (pause workflow)
- `/aa:train` - Enter training mode for adaptive tuning
- `/aa:stop` - Stop workflow completely
- `/aa:status` - Check current workflow status

## Training Commands
- `/aa:train:list` - List all tunable parameters
- `/aa:train:timing <param> <value>` - Adjust timing parameters
- `/aa:train:safety <param> <value>` - Adjust safety parameters  
- `/aa:train:workflow <param> <value>` - Adjust workflow parameters

## Monitoring Commands
- `/aa:workflow:params` - View current parameter values

## Command Features
✅ Commands work from any state (stopped, manual, training, auto)
✅ `/aa:auto` can start workflow from completely stopped state
✅ Mode switching happens instantly without restart
✅ All commands sorted at top with `aa:` prefix

## Example Usage
```
/aa:status                        # Check if running
/aa:auto                          # Start/resume workflow
/aa:train                         # Enter training mode
/aa:train:timing stream_check_interval 30   # Speed up checks
/aa:man                           # Pause for manual work
/aa:auto                          # Resume autonomous work
/aa:stop                          # Stop completely
```