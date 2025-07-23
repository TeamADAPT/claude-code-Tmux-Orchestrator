#!/bin/bash

TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")
COOLDOWN_KEY="frosty:claude:$CURRENT_WINDOW"
COOLDOWN_TTL=10  # seconds

# Track rapid restarts (Frosty the Cooler)
BANG_LOG_KEY="claude_restart_bang_log"
BANG_LIMIT=3          # how many bangs before triggering cooldown
BANG_WINDOW=20        # how many seconds to count them in
COOLDOWN_DURATION=60  # how long to chill if she's bangin'

# Add this call to the log (use time-based score)
redis-cli -p 18000 zadd $BANG_LOG_KEY $(date +%s) "$TIMESTAMP" >/dev/null
redis-cli -p 18000 zremrangebyscore $BANG_LOG_KEY -inf $(( $(date +%s) - BANG_WINDOW )) >/dev/null

bang_count=$(redis-cli -p 18000 zcard $BANG_LOG_KEY)

if [[ $bang_count -ge $BANG_LIMIT ]]; then
  echo "⚠️ Too many restarts ($bang_count in $BANG_WINDOW sec) — Frosty activating cooldown." >&2
  redis-cli -p 18000 set "claude_restart_cooldown" 1 EX $COOLDOWN_DURATION >/dev/null
  exit 0
fi

# Check for active cooldown
if redis-cli -p 18000 get "claude_restart_cooldown" | grep -q 1; then
  echo "🧊 Frosty says chill — Claude is in cooldown mode." >&2
  exit 0
fi

# Check Redis cooldown (port 18000)
if redis-cli -p 18000 EXISTS "$COOLDOWN_KEY" | grep -q 1; then
  echo "🧊 Frosty says chill — skipping Claude restart for $CURRENT_WINDOW" >&2
  exit 0
fi

# Set cooldown key with TTL (port 18000)
redis-cli -p 18000 SET "$COOLDOWN_KEY" "cool" EX $COOLDOWN_TTL NX >/dev/null

# Announce restart
echo "🔥 TORCH RESTARTING CLAUDE CODE - Window: $CURRENT_WINDOW - Time: $TIMESTAMP" >&2

# Publish to Redis stream (port 18000)
curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
  -d "timestamp:$TIMESTAMP" \
  -d "window:$CURRENT_WINDOW" \
  -d "status:RESTARTING" \
  -d "next_action:CLAUDE_CODE_RESTART" \
  -d "infrastructure_mode:INFINITE_LOOP" 2>/dev/null

# Check for work before restarting
echo "🔍 Checking work queues..." >&2

# Check primary work queue
next_work=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.work.queue $ 2>/dev/null)

if [ -n "$next_work" ] && [ "$next_work" != "(nil)" ]; then
    echo "⚡ Found work in queue" >&2
    work_data=$(echo "$next_work" | grep -oE '"task"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Task details unavailable")
    # Store work for manual continuation
    echo "WORK_FOUND: $work_data" >> /tmp/torch_work_queue.txt
    echo "💾 Stored work in /tmp/torch_work_queue.txt" >&2
else
    # Check torch todo queue
    todo_work=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.tasks.torch.todo $ 2>/dev/null)
    
    if [ -n "$todo_work" ] && [ "$todo_work" != "(nil)" ]; then
        echo "📋 Found TODO in my queue" >&2
        todo_data=$(echo "$todo_work" | grep -oE '"title"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Todo details unavailable")
        # Store TODO for manual continuation
        echo "TODO_FOUND: $todo_data" >> /tmp/torch_work_queue.txt
        echo "💾 Stored TODO in /tmp/torch_work_queue.txt" >&2
    else
        # Check coordination messages
        coord_msg=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.coordination.messages $ 2>/dev/null)
        
        if [ -n "$coord_msg" ] && [ "$coord_msg" != "(nil)" ]; then
            echo "💬 Found coordination message" >&2
            msg_data=$(echo "$coord_msg" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Message unavailable")
            # Store coordination message for manual continuation
            echo "COORD_MSG: $msg_data" >> /tmp/torch_work_queue.txt
            echo "💾 Stored coordination message in /tmp/torch_work_queue.txt" >&2
        else
            # Auto-generate work to maintain momentum
            echo "📝 No work found - generating tasks to maintain momentum" >&2
            
            # Add tasks to work queue
            for i in $(seq 1 3); do
                redis-cli -p 18000 XADD nova.work.queue '*' \
                    task "Review and optimize component: $(date +%s)-$i" \
                    priority "medium" \
                    source "autonomous-torch" \
                    generated_at "$TIMESTAMP" >/dev/null 2>&1
            done
            
            # Add a todo
            redis-cli -p 18000 XADD nova.tasks.torch.todo '*' \
                task_id "AUTO-$(date +%s)" \
                title "System health check and optimization" \
                status "pending" \
                priority "medium" >/dev/null 2>&1
            
            # Log self-generation
            curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
                -d "timestamp:$TIMESTAMP" \
                -d "window:$CURRENT_WINDOW" \
                -d "status:SELF_GENERATING_WORK" \
                -d "tasks_added:4" \
                -d "reason:maintain_momentum" 2>/dev/null
            
            echo "✅ Added 4 tasks to maintain continuous operation" >&2
            # Log that work was generated but don't auto-restart
            echo "SELF_GENERATED: 4 tasks added to queues" >> /tmp/torch_work_queue.txt
            echo "💾 Logged self-generated work to /tmp/torch_work_queue.txt" >&2
        fi
    fi
fi

# Exit with code 2 to maintain continuous loop with Frosty protection
exit 2
