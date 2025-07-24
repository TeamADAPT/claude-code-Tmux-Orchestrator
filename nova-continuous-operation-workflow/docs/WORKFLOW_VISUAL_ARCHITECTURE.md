# Nova Continuous Operation Workflow - Visual Architecture

## State Machine Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOVA WORKFLOW STATE MACHINE                 │
└─────────────────────────────────────────────────────────────────┘

    ┌─────────────────┐
    │  INITIALIZING   │ ──┐
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │  STREAM_CHECK   │ ◄─┤
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │ WORK_DISCOVERY  │   │
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │ TASK_EXECUTION  │   │
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │PROGRESS_UPDATE  │   │
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │COMPLETION_ROUTINE│   │
    └─────────────────┘   │
             │            │
             ▼            │
    ┌─────────────────┐   │
    │PHASE_TRANSITION │ ──┘
    └─────────────────┘
             │
             ▼
         [Phase 1 ↔ Phase 2]

    ERROR HANDLING:
    ┌─────────────────┐   ┌─────────────────┐
    │ ERROR_RECOVERY  │   │  SAFETY_PAUSE   │
    └─────────────────┘   └─────────────────┘
             ▲                       ▲
             └─── Any State Error ───┘
```

## Two-Phase Alternating System

```
┌─────────────────────────────────────────────────────────────────┐
│                     ANTI-DRIFT PHASE SYSTEM                    │
└─────────────────────────────────────────────────────────────────┘

    WORK PHASE 1                    WORK PHASE 2
    ┌─────────────┐                ┌─────────────┐
    │ Tasks: 6-8  │ ───────────►   │ Tasks: 6-8  │
    │ Duration:   │ ◄─────────────  │ Duration:   │
    │ ~2-3 hours  │                │ ~2-3 hours  │
    └─────────────┘                └─────────────┘
           │                              │
           ▼                              ▼
    ┌─────────────┐                ┌─────────────┐
    │3-min Pause  │                │3-min Pause  │
    │Celebration  │                │Celebration  │
    └─────────────┘                └─────────────┘

    Key Anti-Drift Features:
    • Structured 3-minute celebration periods
    • Automatic phase transitions prevent infinite celebration
    • Momentum task generation maintains forward progress
    • Safety pauses reset on violations
```

## Stream Coordination Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   DRAGONFLY STREAM ECOSYSTEM                   │
│                        (Port 18000)                            │
└─────────────────────────────────────────────────────────────────┘

    Nova Torch Instance
    ┌─────────────────┐
    │ Stream Controller│
    └─────────────────┘
             │
             ▼
    ┌─────────────────────────────────────────────────────────────┐
    │                    STREAM CATEGORIES                        │
    ├─────────────────────────────────────────────────────────────┤
    │ COORDINATION:                                               │
    │ • nova.coordination.torch                                   │
    │ • nova.cross.coordination                                   │
    │ • nova.wake.signals                                         │
    ├─────────────────────────────────────────────────────────────┤
    │ TASK TRACKING:                                              │
    │ • nova.tasks.torch.todo                                     │
    │ • nova.tasks.torch.progress                                 │
    │ • nova.tasks.torch.completed                                │
    ├─────────────────────────────────────────────────────────────┤
    │ ENTERPRISE:                                                 │
    │ • nova.enterprise.metrics                                   │
    │ • nova.enterprise.state.torch                               │
    │ • nova.enterprise.transitions.torch                         │
    ├─────────────────────────────────────────────────────────────┤
    │ SAFETY:                                                     │
    │ • nova.safety.torch                                         │
    │ • nova.priority.alerts                                      │
    └─────────────────────────────────────────────────────────────┘

    Message Flow:
    Nova → Stream → Processing → Work Items → Execution
```

## Safety System Integration

```
┌─────────────────────────────────────────────────────────────────┐
│                     SAFETY ORCHESTRATOR                        │
└─────────────────────────────────────────────────────────────────┘

    SAFETY CHECKS (Every Cycle)
    ┌─────────────────┐
    │ API Guardian    │ ──┐
    └─────────────────┘   │
    ┌─────────────────┐   │
    │ Hook Monitor    │ ──┤
    └─────────────────┘   │    ┌─────────────────┐
    ┌─────────────────┐   ├──► │ Safety Decision │
    │ Resource Monitor│ ──┤    └─────────────────┘
    └─────────────────┘   │             │
    ┌─────────────────┐   │             ▼
    │ Stream Health   │ ──┘    ┌─────────────────┐
    └─────────────────┘        │ SAFE / PAUSE    │
                               └─────────────────┘

    EMERGENCY PROTOCOLS:
    • API Hammering → Circuit Breaker (5 min)
    • Infinite Loop → Process Kill + Recovery
    • Resource Exhaustion → Cleanup + Monitoring
    • Hook Failure → Quarantine + Safe Mode
```

## Momentum Task Generation

```
┌─────────────────────────────────────────────────────────────────┐
│                   WORK DISCOVERY ENGINE                        │
└─────────────────────────────────────────────────────────────────┘

    Priority Order:
    1. CRITICAL Messages (Safety, Alerts)
    2. HIGH Priority Coordination
    3. MEDIUM Stream Work
    4. LOW Background Tasks
    5. MOMENTUM Tasks (Generated)

    Momentum Templates:
    ┌─────────────────────────────────────────────────────────────┐
    │ • Review workflow performance metrics                       │
    │ • Update documentation with insights                        │
    │ • Analyze coordination patterns                             │
    │ • Validate safety system status                             │
    │ • Research Nova behavioral patterns                         │
    └─────────────────────────────────────────────────────────────┘

    Generated when: No high-priority work available
    Purpose: Maintain forward momentum, prevent idle drift
```

## Enterprise Dashboard Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENTERPRISE REPORTING                        │
└─────────────────────────────────────────────────────────────────┘

    Data Sources:
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │ State Tracking  │    │ Stream Activity │    │ Task Metrics    │
    └─────────────────┘    └─────────────────┘    └─────────────────┘
             │                       │                       │
             ▼                       ▼                       ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              METRICS COLLECTOR                              │
    └─────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
    ┌─────────────────────────────────────────────────────────────┐
    │               DASHBOARD GENERATOR                           │
    │                                                             │
    │ • Operational Status       • Safety Compliance             │
    │ • Productivity Metrics     • Task Tracking Status          │
    │ • Quality Indicators       • Collaboration Metrics         │
    └─────────────────────────────────────────────────────────────┘
```

## Cross-Nova Coordination Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                   MULTI-NOVA ECOSYSTEM                         │
└─────────────────────────────────────────────────────────────────┘

    Nova Torch          Nova Echo           Nova Helix
    ┌─────────┐        ┌─────────┐        ┌─────────┐
    │Workflow │        │Workflow │        │Workflow │
    │ Engine  │        │ Engine  │        │ Engine  │
    └─────────┘        └─────────┘        └─────────┘
         │                   │                   │
         └─────────────┬─────────────┬───────────┘
                       │             │
                       ▼             ▼
              ┌─────────────────────────────┐
              │   nova.cross.coordination   │
              │         (Shared)            │
              └─────────────────────────────┘

    Coordination Messages:
    • WORK_REQUEST (Nova → Nova)
    • COLLABORATION_REQUEST (Cross-project)
    • STATUS_UPDATE (Health sharing)
    • RESOURCE_SHARING (Optimization)
```