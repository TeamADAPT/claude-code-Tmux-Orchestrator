# NOVAWF Visual Architecture - As Designed

## Core Concept: Continuous Anti-Drift Operation

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOVA CONTINUOUS OPERATION                      │
│                         (24/7 Autonomous)                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                      WORKFLOW STATE MACHINE                       │
│  ┌─────────────┐     Continuous Loop      ┌─────────────┐       │
│  │   START     │ ─────────────────────────▶│STREAM_CHECK │       │
│  └─────────────┘                           └──────┬──────┘       │
│                                                    │              │
│                                                    ▼              │
│  ┌─────────────┐                          ┌──────────────┐       │
│  │PHASE_TRANS  │◀─────────────────────────│WORK_DISCOVERY│       │
│  └──────┬──────┘                          └──────┬───────┘       │
│         │                                         │               │
│         ▼                                         ▼               │
│  ┌─────────────┐                          ┌──────────────┐       │
│  │COMPLETION   │◀─────────────────────────│TASK_EXECUTION│       │
│  │  ROUTINE    │                          └──────┬───────┘       │
│  └──────┬──────┘                                 │               │
│         │                                         ▼               │
│         │                                  ┌──────────────┐       │
│         └─────────────────────────────────▶│PROGRESS_UPDATE│      │
│                                            └──────┬───────┘       │
│                                                   │               │
│                                                   └───────────────┘
└─────────────────────────────────────────────────────────────────┘
```

## How It's MEANT to Work (Design Intent)

### 1. **ALWAYS RUNNING** (Default State)
```
Nova Agent (Claude Code Session)
    │
    ├── Starts automatically on session begin
    ├── Runs workflow engine in background
    └── Continues until explicitly stopped

Workflow Engine (main.py)
    │
    ├── Infinite loop through states
    ├── Never stops unless commanded
    └── Anti-drift mechanisms prevent stalling
```

### 2. **Anti-Drift State Flow**
```
STREAM_CHECK (60s)
    ├── Check DragonflyDB for work
    ├── Check for control commands (/man, /auto, /train)
    └── Always moves forward
         │
         ▼
WORK_DISCOVERY
    ├── Find available tasks
    ├── OR generate momentum tasks
    └── NEVER gets stuck here
         │
         ▼
TASK_EXECUTION
    ├── Do the actual work
    ├── Update progress
    └── Track completion
         │
         ▼
PROGRESS_UPDATE
    ├── Post to streams
    ├── Update metrics
    └── Check phase completion
         │
         ▼
COMPLETION_ROUTINE (Brief!)
    ├── Acknowledge success
    ├── 10 second celebration MAX
    └── Immediately continue
         │
         ▼
PHASE_TRANSITION
    ├── Switch work phases
    ├── Reset counters
    └── Back to STREAM_CHECK
```

### 3. **Control Modes - LIVE SWITCHING**

```
                    ┌─────────────┐
                    │   /aa:man   │
                    └──────┬──────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    ▼                      ▼                      ▼
┌────────┐          ┌─────────────┐         ┌────────┐
│AUTO    │◀────────▶│   MANUAL    │◀───────▶│TRAINING│
│(Normal)│          │  (Paused)   │         │(Tuning)│
└────────┘          └─────────────┘         └────────┘
    ▲                      ▲                      ▲
    └──────────────────────┼──────────────────────┘
                           │
                    ┌──────┴──────┐
                    │  /aa:auto   │
                    └─────────────┘
```

### 4. **What Each Mode Does**

#### **AUTO MODE** (Default)
- Workflow runs continuously
- States cycle automatically
- Work gets done autonomously
- This is the NORMAL state

#### **MANUAL MODE** (/aa:man)
- Workflow PAUSES in current state
- Waits for /aa:auto command
- No autonomous work happens
- User has full control

#### **TRAINING MODE** (/aa:train)
- Workflow continues BUT
- Parameters can be modified live
- Changes tracked in git branches
- Performance monitored

### 5. **Current Implementation Gap**

**DESIGNED BEHAVIOR:**
```
Claude Code Session Start
         │
         ▼
Workflow Auto-Starts ──────▶ Continuous Operation
         │
         └──▶ User works alongside autonomous workflow
```

**CURRENT BEHAVIOR:**
```
Claude Code Session Start
         │
         ▼
Nothing happens ──────▶ User must run /aa:auto
         │
         └──▶ Then workflow starts
```

## The Fix Needed

### Option 1: Auto-Start on Session (Original Design)
```python
# In Claude Code initialization
if not workflow_running():
    start_workflow_background()
```

### Option 2: Keep Manual Start but Update Training Mode
```markdown
# /aa:train command should:
1. Do NOT start workflow automatically
2. Just send mode command
3. Let user debug/modify without interference
4. Workflow runs only when explicitly started with /aa:auto
```

## Visual Summary: Intended Workflow

```
┌─────────────────────────────────────────────────────┐
│                  NOVA AGENT LIFECYCLE                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Session Start ──▶ Workflow Running ──▶ Work Done  │
│       │                    │                  │     │
│       │                    │                  │     │
│       ▼                    ▼                  ▼     │
│   [AUTOMATIC]        [CONTINUOUS]        [ALWAYS]   │
│                                                     │
│  User Commands:                                    │
│    /aa:man  ──▶ Pause for manual control          │
│    /aa:train ──▶ Enter tuning mode                │
│    /aa:auto  ──▶ Resume/ensure autonomous         │
│    /aa:stop  ──▶ Completely halt (rare)           │
│                                                     │
└─────────────────────────────────────────────────────┘
```

The core philosophy: **The workflow should be like breathing - it happens automatically unless you consciously decide to hold your breath.**

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Architecture Documentation v1.0