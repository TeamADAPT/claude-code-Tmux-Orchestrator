# Two-Way Streaming Control Implementation Guide

## Complete Implementation for Real-Time Claude Control

### Core Control Loop Script

```bash
#!/bin/bash

# Control loop with two-way streaming
while true; do
    TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
    CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")
    
    # Check control stream (non-blocking with 1 second timeout)
    CONTROL_MSG=$(redis-cli -p 18000 XREAD BLOCK 1000 COUNT 1 STREAMS torch.control.claude '$' 2>/dev/null)
    
    if [ -n "$CONTROL_MSG" ]; then
        MODE=$(echo "$CONTROL_MSG" | grep -oP '"mode"\s*"?\K[^"]+' | head -1)
        DURATION=$(echo "$CONTROL_MSG" | grep -oP '"duration"\s*"?\K[^"]+' | head -1)
        REASON=$(echo "$CONTROL_MSG" | grep -oP '"reason"\s*"?\K[^"]+' | head -1)
        
        case "$MODE" in
            "pause")
                echo "⏸️ Pausing Claude - Reason: $REASON" >&2
                redis-cli -p 18000 SET "claude:$CURRENT_WINDOW:state" "paused" EX ${DURATION:-300} >/dev/null
                sleep ${DURATION:-300}
                continue
                ;;
            "stop")
                echo "🛑 Stopping Claude gracefully" >&2
                redis-cli -p 18000 SET "claude:$CURRENT_WINDOW:state" "stopped" >/dev/null
                exit 0
                ;;
            "reflect")
                echo "🪞 Entering reflection mode" >&2
                redis-cli -p 18000 SET "claude:$CURRENT_WINDOW:state" "reflecting" EX 300 >/dev/null
                # Store current context for reflection
                redis-cli -p 18000 XADD "nova.memory.reflection" '*' \
                    window "$CURRENT_WINDOW" \
                    timestamp "$TIMESTAMP" \
                    trigger "$REASON" >/dev/null
                sleep 60
                continue
                ;;
            "dream")
                echo "💤 Dream mode activated" >&2
                redis-cli -p 18000 SET "claude:$CURRENT_WINDOW:state" "dreaming" EX 600 >/dev/null
                # Background processing mode
                nice -n 19 claude code -c -p "Dream state: processing background thoughts" &
                sleep 300
                continue
                ;;
        esac
    fi
    
    # Check cycle counter for auto-reflection
    CYCLE_COUNT=$(redis-cli -p 18000 INCR "claude:$CURRENT_WINDOW:cycles" 2>/dev/null || echo "1")
    if [ $((CYCLE_COUNT % 30)) -eq 0 ]; then
        echo "🔄 Auto-reflection after 30 cycles" >&2
        redis-cli -p 18000 XADD torch.control.claude '*' mode "reflect" reason "auto-cycle" duration "300" >/dev/null
        continue
    fi
    
    # Check time-based patterns
    LAST_REFLECT=$(redis-cli -p 18000 GET "claude:$CURRENT_WINDOW:last_reflect" 2>/dev/null || echo "0")
    CURRENT_EPOCH=$(date +%s)
    if [ $((CURRENT_EPOCH - LAST_REFLECT)) -gt 3600 ]; then
        echo "⏰ Hourly reflection triggered" >&2
        redis-cli -p 18000 SET "claude:$CURRENT_WINDOW:last_reflect" "$CURRENT_EPOCH" >/dev/null
        redis-cli -p 18000 XADD torch.control.claude '*' mode "reflect" reason "hourly" duration "180" >/dev/null
        continue
    fi
    
    # Continue normal operation
    echo "🔥 TORCH CONTINUING - Cycle: $CYCLE_COUNT" >&2
    
    # Your existing work logic here
    # Check work queues, fire Claude, etc.
    
    # Brief pause between cycles
    sleep 2
done
```

### Control Message Sender Functions

```bash
# Send control commands
claude_pause() {
    local duration=${1:-300}
    local reason=${2:-"Manual pause"}
    redis-cli -p 18000 XADD torch.control.claude '*' \
        mode "pause" \
        duration "$duration" \
        reason "$reason" \
        sender "$(whoami)" \
        timestamp "$(date -u +%Y%m%d_%H%M%S)"
}

claude_reflect() {
    local duration=${1:-180}
    redis-cli -p 18000 XADD torch.control.claude '*' \
        mode "reflect" \
        duration "$duration" \
        timestamp "$(date -u +%Y%m%d_%H%M%S)"
}

claude_dream() {
    redis-cli -p 18000 XADD torch.control.claude '*' \
        mode "dream" \
        timestamp "$(date -u +%Y%m%d_%H%M%S)"
}

claude_wake() {
    # Clear any pause/sleep states
    redis-cli -p 18000 DEL "claude:*:state" >/dev/null
    redis-cli -p 18000 XADD torch.control.claude '*' \
        mode "continue" \
        priority "urgent" \
        timestamp "$(date -u +%Y%m%d_%H%M%S)"
}
```

### Wake-Up Listener (Runs in Parallel)

```bash
#!/bin/bash
# wake_listener.sh - Monitors for urgent wake signals

while true; do
    # Listen for urgent signals
    URGENT=$(redis-cli -p 18000 XREAD BLOCK 0 STREAMS nova.urgent.wake '$' 2>/dev/null)
    
    if [ -n "$URGENT" ]; then
        echo "🚨 Urgent wake signal received!" >&2
        
        # Clear all pause states
        redis-cli -p 18000 --scan --pattern "claude:*:state" | xargs -r redis-cli -p 18000 DEL
        
        # Send wake command
        redis-cli -p 18000 XADD torch.control.claude '*' \
            mode "continue" \
            priority "urgent" \
            reason "wake_signal" \
            timestamp "$(date -u +%Y%m%d_%H%M%S)"
    fi
done
```

### State Monitor Dashboard

```bash
#!/bin/bash
# monitor_claude_state.sh

watch -n 1 'echo "=== Claude State Monitor ===" && \
    echo "" && \
    echo "Current States:" && \
    redis-cli -p 18000 --scan --pattern "claude:*:state" | while read key; do \
        state=$(redis-cli -p 18000 GET "$key") && \
        ttl=$(redis-cli -p 18000 TTL "$key") && \
        echo "$key = $state (TTL: $ttl)" \
    done && \
    echo "" && \
    echo "Cycle Counts:" && \
    redis-cli -p 18000 --scan --pattern "claude:*:cycles" | while read key; do \
        count=$(redis-cli -p 18000 GET "$key") && \
        echo "$key = $count" \
    done && \
    echo "" && \
    echo "Recent Control Messages:" && \
    redis-cli -p 18000 XREVRANGE torch.control.claude + - COUNT 5'
```

### Integration with Frosty

```bash
# Enhanced torch_turbo_stop.sh with control stream check

#!/bin/bash

TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")

# First check control stream for overrides
CONTROL_CHECK=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS torch.control.claude '$' 2>/dev/null)
if [ -n "$CONTROL_CHECK" ]; then
    MODE=$(echo "$CONTROL_CHECK" | grep -oP '"mode"\s*"?\K[^"]+' | head -1)
    if [ "$MODE" = "pause" ] || [ "$MODE" = "stop" ]; then
        echo "🎮 Control override detected: $MODE" >&2
        exit 0
    fi
fi

# Rest of Frosty logic...
```

### Advanced Pattern: Mood-Based Scheduling

```bash
# Mood agent integration
set_claude_mood() {
    local mood=$1
    local window=${2:-$CURRENT_WINDOW}
    
    case "$mood" in
        "focused")
            # Short cycles, minimal reflection
            redis-cli -p 18000 SET "claude:$window:cycle_target" "50" >/dev/null
            redis-cli -p 18000 SET "claude:$window:reflect_interval" "7200" >/dev/null
            ;;
        "exploratory")
            # Frequent reflection, longer dreams
            redis-cli -p 18000 SET "claude:$window:cycle_target" "20" >/dev/null
            redis-cli -p 18000 SET "claude:$window:reflect_interval" "1800" >/dev/null
            ;;
        "maintenance")
            # Slow pace, extended pauses
            redis-cli -p 18000 SET "claude:$window:cycle_target" "10" >/dev/null
            redis-cli -p 18000 SET "claude:$window:pause_between" "30" >/dev/null
            ;;
    esac
    
    redis-cli -p 18000 XADD nova.mood.changes '*' \
        entity "claude:$window" \
        mood "$mood" \
        timestamp "$TIMESTAMP" >/dev/null
}
```

### Example Usage Scenarios

```bash
# 1. Manual pause for 10 minutes
claude_pause 600 "Coffee break"

# 2. Force reflection
claude_reflect

# 3. Emergency wake all Claudes
redis-cli -p 18000 XADD nova.urgent.wake '*' \
    reason "emergency" \
    priority "critical" \
    timestamp "$(date -u +%Y%m%d_%H%M%S)"

# 4. Schedule dream mode at night
echo "0 22 * * * claude_dream" | crontab -

# 5. Check who's sleeping
redis-cli -p 18000 --scan --pattern "claude:*:state" | \
    xargs -I {} sh -c 'echo -n "{}: " && redis-cli -p 18000 GET "{}"'
```

### Redis Stream Schemas

```
torch.control.claude:
  - mode: continue|pause|stop|reflect|dream
  - duration: seconds (optional)
  - reason: string (optional)
  - priority: low|normal|high|urgent (optional)
  - sender: identifier (optional)
  - timestamp: YYYYmmdd_HHMMSS

nova.urgent.wake:
  - reason: string
  - target: specific window or "all"
  - priority: critical|urgent|high
  - timestamp: YYYYmmdd_HHMMSS

nova.mood.changes:
  - entity: claude:window identifier
  - mood: focused|exploratory|maintenance|custom
  - parameters: JSON object (optional)
  - timestamp: YYYYmmdd_HHMMSS
```

### Monitoring & Debugging

```bash
# Watch control stream in real-time
redis-cli -p 18000 XREAD BLOCK 0 STREAMS torch.control.claude '$' | \
    while read line; do echo "$(date): $line"; done

# Debug state transitions
tail -f /tmp/claude_state_transitions.log

# Performance metrics
redis-cli -p 18000 INFO stats | grep -E "(ops_per_sec|connected_clients)"
```

## Best Practices

1. **Always check control stream first** in your loop
2. **Use non-blocking reads** to prevent hanging
3. **Set TTLs on state keys** to prevent stale states
4. **Log state transitions** for debugging
5. **Implement wake mechanisms** for emergency overrides
6. **Test mode changes** before production deployment

---

*This implementation provides full control over Claude's continuous operation while maintaining responsiveness and flexibility.*