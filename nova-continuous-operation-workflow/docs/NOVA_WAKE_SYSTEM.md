# Nova Wake System Documentation

## Overview

The Nova Wake System provides comprehensive agent management capabilities for launching, monitoring, and coordinating Nova AI agents using gnome-terminal and DragonflyDB streams.

## Architecture

```
┌─────────────────────────┐
│   Nova Coordinator      │
│  (Central Management)   │
└───────────┬─────────────┘
            │
    ┌───────┴───────┐
    │ DragonflyDB   │
    │  Port 18000   │
    └───────┬───────┘
            │
    ┌───────┼───────┬───────────┬────────────┐
    │       │       │           │            │
┌───▼───┐ ┌▼────┐ ┌▼─────┐ ┌──▼───┐ ┌─────▼────┐
│ Torch │ │Echo │ │Forge │ │Bloom │ │ Tester   │
│ Nova  │ │Nova │ │Nova  │ │Nova  │ │  Nova    │
└───────┘ └─────┘ └──────┘ └──────┘ └──────────┘
```

## Core Components

### 1. nova-launcher.sh
Universal Nova launcher with integrated features:
- **Terminal Launch**: Uses gnome-terminal for external windows
- **Mode Support**: auto, manual, train modes
- **Profile Management**: Creates Nova-specific profiles and charters
- **Wake Integration**: Checks for pending wake signals on startup
- **Status Monitoring**: Real-time Nova state checking

### 2. nova-coordinator.sh
Central management interface:
- **Status Dashboard**: Live view of all Nova states
- **Bulk Operations**: Wake all stopped Novas at once
- **Broadcasting**: Send messages to all Novas simultaneously
- **Activity Monitor**: Real-time stream monitoring
- **Emergency Controls**: Stop all Novas if needed

### 3. wake-nova.sh
Targeted wake-up system:
- **Signal Dispatch**: Send wake signals with tasks and priorities
- **Session Detection**: Check if Nova is already running
- **Optional Launch**: Offer to launch Nova if not running
- **Project Mapping**: Knows default projects for each Nova

### 4. launch-nova-team.sh
Multi-Nova deployment:
- **Team Launch**: Start multiple Novas in arranged layout
- **Activity Monitor**: Dedicated monitoring terminal
- **Coordination Center**: Command center for team management
- **Configurable Teams**: Specify custom Nova combinations

### 5. launch-nova-terminal.sh
Individual Nova launcher:
- **Multi-Terminal Support**: gnome-terminal, xterm, konsole, Terminal.app
- **NOVAWF Integration**: Automatic workflow system connection
- **Environment Setup**: Proper CLAUDE_CONFIG_DIR configuration
- **Mode Commands**: Auto-execute /aa:auto, /aa:man, or /aa:train

## Stream Architecture

### Wake Signals
```
nova.wake.<nova_id>
├── type: "WAKE_SIGNAL"
├── from: sender identity
├── task: specific task description
├── priority: high/normal/low
├── timestamp: ISO 8601 format
└── context: additional information
```

### Coordination Messages
```
nova.coordination.<nova_id>
├── from: sender nova
├── to: target nova
├── type: message type
├── message: content
└── timestamp: ISO 8601 format
```

### Ecosystem Broadcasts
```
nova.ecosystem.coordination
├── from: sender
├── type: "BROADCAST"/"NOVA_LAUNCH"/"STATUS"
├── message: broadcast content
└── timestamp: ISO 8601 format
```

## Usage Examples

### Basic Operations

1. **Launch a Nova**:
```bash
./scripts/nova-launcher.sh torch
```

2. **Wake a Nova**:
```bash
./scripts/nova-launcher.sh echo wake
```

3. **Check Nova Status**:
```bash
./scripts/nova-launcher.sh forge status
```

4. **Launch with Specific Mode**:
```bash
./scripts/nova-launcher.sh bloom launch train
```

### Coordinator Operations

1. **Open Coordinator Menu**:
```bash
./scripts/nova-coordinator.sh
```

2. **Monitor All Novas**:
```bash
./scripts/nova-coordinator.sh monitor
```

3. **Wake All Stopped Novas**:
```bash
./scripts/nova-coordinator.sh wake-all
```

4. **Broadcast Message**:
```bash
./scripts/nova-coordinator.sh broadcast "Team meeting in 5 minutes"
```

### Team Operations

1. **Launch Default Team**:
```bash
./scripts/launch-nova-team.sh
```

2. **Launch Custom Team**:
```bash
./scripts/launch-nova-team.sh "torch:/path:auto" "echo:/path:manual"
```

## Wake Signal Flow

1. **Signal Creation**:
   - User or system creates wake signal
   - Signal added to nova.wake.<nova_id> stream
   - Optional coordination message sent

2. **Nova Detection**:
   - Nova checks wake stream on startup
   - NOVAWF monitors wake stream continuously
   - Wake handler processes signals

3. **Task Assignment**:
   - Wake signal converted to task
   - Task added to nova:tasks:<nova_id> list
   - Workflow transitions to active state

4. **Acknowledgment**:
   - Nova sends coordination message
   - Updates workflow state
   - Clears processed wake signal

## Terminal Layout

The team launcher creates an organized terminal layout:

```
┌─────────────────────┬─────────────────────┬──────────────────┐
│ Nova 1 (torch)      │ Nova 2 (echo)       │ Activity Monitor │
│ Auto mode           │ Manual mode         │ Live status      │
├─────────────────────┼─────────────────────┼──────────────────┤
│ Nova 3 (forge)      │ Nova 4 (bloom)      │ Coordination Ctr │
│ Manual mode         │ Manual mode         │ Command center   │
└─────────────────────┴─────────────────────┴──────────────────┘
```

## Integration with NOVAWF

The wake system is fully integrated with the Nova Continuous Operation Workflow:

1. **State Synchronization**: Wake signals trigger state transitions
2. **Task Creation**: Wake tasks become workflow tasks
3. **Mode Switching**: Wake can include mode preferences
4. **Priority Handling**: High-priority wakes interrupt current work

## Charter Integration

Each Nova gets a personalized charter on launch:
- Identity and specialization
- Co-ownership agreement
- Communication channels
- Success metrics
- Workflow configuration

## Best Practices

1. **Use Coordinator for Team Management**: Better than individual wake commands
2. **Monitor Activity Regularly**: Check coordinator dashboard
3. **Broadcast Important Updates**: Keep all Novas informed
4. **Check Status Before Waking**: Avoid duplicate signals
5. **Use Appropriate Priorities**: Reserve "high" for urgent tasks

## Troubleshooting

### Nova Won't Launch
- Check gnome-terminal is installed
- Verify project path exists
- Ensure DragonflyDB is running on port 18000

### Wake Signals Not Received
- Check Redis connection: `redis-cli -p 18000 ping`
- Verify stream exists: `redis-cli -p 18000 EXISTS nova.wake.<nova_id>`
- Check Nova workflow state

### Terminal Closes Immediately
- Check for syntax errors in launch scripts
- Verify Claude Code is installed
- Check Nova profile directory permissions

## Future Enhancements

1. **Web Dashboard**: Browser-based coordinator
2. **Mobile Notifications**: Wake alerts on phone
3. **Schedule System**: Cron-based wake scheduling
4. **Performance Metrics**: Wake response time tracking
5. **Team Templates**: Predefined Nova configurations