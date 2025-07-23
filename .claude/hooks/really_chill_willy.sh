#!/bin/bash
# Really Chill Willy - Deep Freeze Mood Agent
# Activates when even Frosty can't handle the heat

TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")

# Check if Willy should activate
EMERGENCY_KEY="willy:emergency:$CURRENT_WINDOW"
WILLY_ACTIVE=$(redis-cli -p 18000 GET "$EMERGENCY_KEY" 2>/dev/null)

if [ "$WILLY_ACTIVE" = "1" ]; then
    echo "🐧❄️ Really Chill Willy: Already chillin', bro... maintaining the vibe" >&2
    
    # Check if emergency is over
    COOLDOWN_CHECK=$(redis-cli -p 18000 GET "claude_restart_cooldown" 2>/dev/null)
    if [ -z "$COOLDOWN_CHECK" ]; then
        echo "🌅 Willy: Emergency's over, returning to normal ops" >&2
        redis-cli -p 18000 DEL "$EMERGENCY_KEY" >/dev/null
        exit 2
    fi
    
    # Still in emergency - maintain chill
    echo "🧘 Willy: Still in deep meditation mode" >&2
    sleep 300  # 5 minute meditation
    exit 0
fi

# Check if we need to activate Willy
BANG_COUNT=$(redis-cli -p 18000 ZCARD "claude_restart_bang_log" 2>/dev/null || echo "0")
MULTIPLE_COOLDOWNS=$(redis-cli -p 18000 KEYS "*cooldown*" | wc -l)

if [ "$BANG_COUNT" -gt 5 ] || [ "$MULTIPLE_COOLDOWNS" -gt 3 ]; then
    echo "🚨 System overheating detected - Really Chill Willy activating!" >&2
    
    # Set Willy's emergency mode
    redis-cli -p 18000 SET "$EMERGENCY_KEY" 1 EX 1800 >/dev/null  # 30 minutes
    
    # Log the emergency
    redis-cli -p 18000 XADD "nova.willy.emergency" '*' \
        timestamp "$TIMESTAMP" \
        window "$CURRENT_WINDOW" \
        bang_count "$BANG_COUNT" \
        cooldown_count "$MULTIPLE_COOLDOWNS" \
        reason "system_overheating" >/dev/null
    
    # Broadcast to all coordination streams
    redis-cli -p 18000 XADD "nova-torch.coord" '*' \
        from "ReallyChillWilly" \
        to "all" \
        type "EMERGENCY_CHILL" \
        message "System overheating detected. Entering deep freeze mode for 30 minutes. All operations will be minimal until recovery." \
        timestamp "$TIMESTAMP" \
        priority "high" >/dev/null
    
    echo "🐧❄️ Really Chill Willy: Time to get REALLY chill, system needs to cool down..." >&2
    echo "🧘 Entering 30-minute meditation cycle" >&2
    
    # Write context for recovery
    echo "WILLY_EMERGENCY: $TIMESTAMP - Bang count: $BANG_COUNT, Cooldowns: $MULTIPLE_COOLDOWNS" >> /tmp/torch_work_queue.txt
    
    # Long meditation period
    sleep 1800  # 30 minutes
    exit 0
fi

# Normal operation - Willy stays in background
echo "🐧 Willy: All's chill, staying ready for emergencies" >&2
exit 2