# Nova Training Mode - Adaptive Parameter Tuning

## Overview
Training mode enables Nova agents to modify their own workflow parameters in real-time during development, creating a self-improving system with versioned experimentation.

## Quick Start

### 1. Enter Training Mode
```bash
# Only available for torch during development
python3 control_workflow.py torch /train
```

### 2. Modify Parameters
```bash
# Adjust workflow timing
python3 training_control.py torch timing stream_check_interval 30

# Tune safety limits
python3 training_control.py torch safety api_rate_limit 50

# Change workflow behavior
python3 training_control.py torch workflow momentum_task_threshold 3
```

### 3. List Available Parameters
```bash
python3 training_control.py --list
```

### 4. Exit Training Mode
```bash
python3 control_workflow.py torch /auto
```

## Tunable Parameters

### Timing Parameters
- **stream_check_interval** (5-300 seconds): How often to check coordination streams
- **task_execution_timeout** (60-1800 seconds): Maximum time for task execution
- **phase_transition_cooldown** (10-120 seconds): Pause between phase transitions
- **safety_pause_duration** (30-600 seconds): Length of safety pauses

### Safety Parameters
- **api_rate_limit** (10-100 requests/min): API call rate limiting
- **error_threshold** (1-10 errors): Consecutive errors before safety pause
- **loop_detection_threshold** (3-20 iterations): Loop iterations before intervention
- **concurrent_request_limit** (1-10 requests): Maximum concurrent API requests

### Workflow Parameters
- **momentum_task_threshold** (1-10 tasks): Tasks before generating momentum work
- **tasks_per_phase** (5-100 tasks): Tasks to complete per workflow phase
- **completion_celebration_duration** (1-30 seconds): Time spent in completion state
- **stream_priority_threshold** (0.0-1.0 priority): Message priority threshold

## How Training Mode Works

### 1. Automatic Git Branching
```
training-torch-20250127-050500
│
├── Each parameter change = auto-commit
├── Performance metrics tracked
└── Poor changes auto-reverted
```

### 2. Real-time Application
- Parameters applied immediately to running workflow
- No restart required
- Performance impact measured instantly

### 3. Performance Monitoring
```
Baseline Metrics → Apply Change → Measure Impact → Keep/Revert
```

### 4. Automatic Safety
- Changes that degrade performance >20% auto-revert
- Safety systems remain active during training
- All changes logged for audit

## Training Session Example

```bash
# 1. Enter training mode
$ python3 control_workflow.py torch /train
🧪 torch workflow will enter TRAINING MODE
   Git branch created: training-torch-20250127-050500

# 2. Speed up stream checking
$ python3 training_control.py torch timing stream_check_interval 15
✅ Parameter change sent to torch
   Parameter: timing.stream_check_interval
   New Value: 15 seconds

# 3. Increase API rate limit for faster operation
$ python3 training_control.py torch safety api_rate_limit 75
✅ Parameter change sent to torch
   Parameter: safety.api_rate_limit  
   New Value: 75 requests/min

# 4. Monitor performance via streams
# (Nova tracks tasks/hour, cycle times, error rates)

# 5. Exit training - changes preserved if beneficial
$ python3 control_workflow.py torch /auto
```

## Future Vision

### Phase 2: Task-Specific Profiles
```python
# Nova auto-selects optimal parameters based on work type
if analyzing_large_codebase:
    load_profile("deep_analysis_mode.json")
elif rapid_prototyping:
    load_profile("high_throughput_mode.json")
```

### Phase 3: Fleet-Wide Learning
- Successful parameter combinations shared across Novas
- A/B testing of configurations automatically
- Collective optimization of all workflows

### Phase 4: Context-Aware Adaptation
- Time-of-day adjustments (faster mornings, careful evenings)
- Project-type optimization (web dev vs data science)
- Workload-based tuning (busy vs idle periods)

## Technical Architecture

### Stream Communication
- Control commands: `nova.coordination.{nova_id}`
- Parameter changes: `nova.training.{nova_id}`
- Performance metrics: `nova.training.performance.{nova_id}`
- Session tracking: `nova.training.sessions.{nova_id}`

### Git Integration
- Branch per session: `training-{nova_id}-{timestamp}`
- Auto-commit on changes: `Training: Adjust {param}.{name} to {value}`
- Performance tags: `performance-improved-{metric}-{percent}`

### Safety Mechanisms
- Baseline metrics captured at session start
- Continuous performance delta calculation
- Automatic rollback triggers
- Manual override always available via /auto

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Training Mode - Self-Improving AI Infrastructure v1.0