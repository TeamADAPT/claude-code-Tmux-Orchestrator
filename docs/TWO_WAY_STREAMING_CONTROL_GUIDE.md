# Two-Way Streaming Control Guide for Continuous Claude Operations

## Overview

This guide explains how to implement real-time control over Claude's continuous loop using two-way Redis Streams. You can steer Claude's behavior dynamically without killing the loop - pause, reflect, dream, or change modes on the fly.

## Core Concept

Claude reads from a control stream (`torch.control.claude`) while maintaining its continuous operation. Control messages determine behavior without stopping the process.

## Control Stream Commands

### Basic Control Messages

Send commands via Redis on port 18000:

```
mode: continue    - Normal operation
mode: pause       - Temporary suspension
mode: reflect     - Enter reflection state
mode: dream       - Background processing mode
mode: stop        - Graceful shutdown
```

### Advanced Control Patterns

- **Timed Pause**: Include duration in seconds
- **Prompt Override**: Change the next prompt dynamically
- **Memory Control**: Flush or update memory state
- **Priority Shift**: Change task priorities

## Integration Points

### 1. Early in Loop Script

The control check happens FIRST, before any Claude execution:
- Check control stream for commands
- If pause/stop signal exists, handle appropriately
- If no signal, continue normal operation

### 2. Cycle-Based Reflection

After X number of cycles:
- Automatically enter reflection mode
- Reset counter after reflection
- Still responsive to override signals

### 3. Time-Based Patterns

Options for timing control:
- **Hourly reflection**: Check elapsed time since start
- **Daily rhythms**: Different modes at different times
- **Work/rest cycles**: Active periods followed by rest

## Timer Storage Options

1. **Redis with TTL**: Lightweight, auto-expiring
2. **Log files**: Persistent history of mode changes
3. **DragonflyDB streams**: Full audit trail
4. **In-memory variables**: Simple but non-persistent

## Wake-Up Mechanisms

Even during pause/reflect modes:
- Continue monitoring control stream
- Instant response to wake signals
- Priority interrupts for urgent tasks
- Graceful mode transitions

## Mood Agent Integration

**Frosty the Cooler**: Rate limiting and cooldowns
**Really Chill Willy**: Deep freeze and extended reflection
**Future agents**: Task-specific mood controllers

## Implementation Strategy

1. **Control Stream First**: Always check signals before action
2. **Non-Blocking Reads**: Use XREAD with timeout, not infinite block
3. **State Persistence**: Track current mode in Redis
4. **Graceful Transitions**: Clean handoff between modes
5. **Audit Trail**: Log all mode changes with timestamps

## Benefits

- No API hammering during quiet periods
- Responsive to urgent needs
- Natural work/rest rhythms
- External control without process restarts
- Preserves context across mode changes

## Example Flow

1. Claude starts in continuous mode
2. After 30 cycles → auto-reflect for 5 minutes
3. During reflection, urgent signal arrives
4. Immediately exits reflection, handles urgent task
5. Returns to normal cycle counting
6. External pause command → enters pause mode
7. Waits for continue signal while monitoring streams

## Best Practices

- Keep control commands simple and clear
- Use meaningful mode names
- Include reason/context in control messages
- Set reasonable timeouts on all operations
- Monitor control stream health
- Implement fallback behaviors

## Integration with Nova Ecosystem

This control system integrates with:
- Nova memory layers for state persistence
- Bloom consciousness continuity
- Cross-Nova coordination streams
- Orchestrator oversight patterns
- PM task distribution

---

*Built for 24/7 autonomous operation with human-in-the-loop control*
*Part of the Nova-Torch continuous infrastructure*