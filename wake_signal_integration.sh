#!/bin/bash
# Wake Signal Integration - Connects prioritizer to hook system
# Processes incoming signals and determines appropriate wake actions

TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")

# Check for immediate wake signals that bypass all cooldowns
immediate_wake=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.immediate.wake $ 2>/dev/null)

if [ -n "$immediate_wake" ] && [ "$immediate_wake" != "(nil)" ]; then
    echo "🚨 IMMEDIATE WAKE SIGNAL RECEIVED - Bypassing all cooldowns" >&2
    
    # Extract message from stream
    wake_reason=$(echo "$immediate_wake" | grep -oE '"reason"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "immediate_wake")
    wake_message=$(echo "$immediate_wake" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Critical signal received")
    
    # Clear all cooldowns immediately
    redis-cli -p 18000 DEL "claude_restart_cooldown" >/dev/null
    redis-cli -p 18000 DEL "frosty:claude:$CURRENT_WINDOW" >/dev/null
    redis-cli -p 18000 DEL "frosty:cooldown:count" >/dev/null
    
    # Log the critical wake
    echo "CRITICAL_WAKE: $wake_reason - $wake_message" >> /tmp/torch_work_queue.txt
    
    # Send immediate coordination message
    curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
        -d "timestamp:$TIMESTAMP" \
        -d "window:$CURRENT_WINDOW" \
        -d "status:CRITICAL_WAKE_EXECUTED" \
        -d "reason:$wake_reason" \
        -d "message:$wake_message" 2>/dev/null
    
    echo "⚡ Critical wake signal processed - system resuming immediately" >&2
    exit 2  # Signal hook to restart Claude immediately
fi

# Check for priority wake signals (short delay)
priority_wake=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.priority.wake.queue $ 2>/dev/null)

if [ -n "$priority_wake" ] && [ "$priority_wake" != "(nil)" ]; then
    echo "⚡ Priority wake signal found" >&2
    
    # Check if scheduled time has arrived
    scheduled_time=$(echo "$priority_wake" | grep -oE '"scheduled_for"[[:space:]]*"[^"]*"' | cut -d'"' -f4)
    current_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    
    # Simple time comparison (basic implementation)
    if [[ "$current_time" > "$scheduled_time" ]] || [[ "$current_time" == "$scheduled_time" ]]; then
        wake_message=$(echo "$priority_wake" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Priority task")
        
        # Apply short cooldown bypass
        redis-cli -p 18000 SET "frosty:priority:override" "1" EX 60 >/dev/null
        
        echo "PRIORITY_WAKE: $wake_message" >> /tmp/torch_work_queue.txt
        
        curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
            -d "timestamp:$TIMESTAMP" \
            -d "window:$CURRENT_WINDOW" \
            -d "status:PRIORITY_WAKE_EXECUTED" \
            -d "message:$wake_message" 2>/dev/null
        
        echo "⚡ Priority wake executed - reduced cooldown active" >&2
        exit 2
    else
        echo "⏳ Priority wake scheduled for $scheduled_time (not yet time)" >&2
    fi
fi

# Check for scheduled wake signals (normal delay)
scheduled_wake=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.scheduled.wake.queue $ 2>/dev/null)

if [ -n "$scheduled_wake" ] && [ "$scheduled_wake" != "(nil)" ]; then
    echo "📅 Scheduled wake signal found" >&2
    
    scheduled_time=$(echo "$scheduled_wake" | grep -oE '"scheduled_for"[[:space:]]*"[^"]*"' | cut -d'"' -f4)
    current_time=$(date -u +%Y-%m-%dT%H:%M:%S)
    
    if [[ "$current_time" > "$scheduled_time" ]]; then
        wake_message=$(echo "$scheduled_wake" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Scheduled task")
        
        echo "SCHEDULED_WAKE: $wake_message" >> /tmp/torch_work_queue.txt
        
        curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
            -d "timestamp:$TIMESTAMP" \
            -d "window:$CURRENT_WINDOW" \
            -d "status:SCHEDULED_WAKE_EXECUTED" \
            -d "message:$wake_message" 2>/dev/null
        
        echo "📅 Scheduled wake executed" >&2
        exit 2
    else
        echo "⏳ Wake scheduled for $scheduled_time (waiting)" >&2
    fi
fi

# Process any deferred signals during natural wake cycles
deferred_signals=$(redis-cli -p 18000 XRANGE nova.deferred.signals - + COUNT 3 2>/dev/null)

if [ -n "$deferred_signals" ] && [ "$deferred_signals" != "(nil)" ]; then
    echo "📝 Processing deferred signals during natural cycle" >&2
    
    # Extract first deferred message
    deferred_message=$(echo "$deferred_signals" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 | head -1)
    
    if [ -n "$deferred_message" ]; then
        echo "DEFERRED_PROCESSED: $deferred_message" >> /tmp/torch_work_queue.txt
        
        curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
            -d "timestamp:$TIMESTAMP" \
            -d "window:$CURRENT_WINDOW" \
            -d "status:DEFERRED_SIGNAL_PROCESSED" \
            -d "message:$deferred_message" 2>/dev/null
        
        echo "📝 Deferred signal processed: $deferred_message" >&2
    fi
fi

# Store wake integration metrics
curl -X POST http://localhost:18000/xadd/nova.wake.metrics \
    -d "timestamp:$TIMESTAMP" \
    -d "window:$CURRENT_WINDOW" \
    -d "integration_active:true" \
    -d "signals_processed:$(wc -l < /tmp/torch_work_queue.txt 2>/dev/null || echo 0)" 2>/dev/null

echo "💤 Wake signal integration check complete" >&2
exit 0