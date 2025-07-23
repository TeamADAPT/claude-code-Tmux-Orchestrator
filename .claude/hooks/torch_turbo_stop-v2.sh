#!/bin/bash

# ========== SETUP ==========
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")
COOLDOWN_KEY="frosty:claude:$CURRENT_WINDOW"
COOLDOWN_TTL=10  # seconds

# ========== FROSTY LOGIC ==========
BANG_LOG_KEY="claude_restart_bang_log"
BANG_LIMIT=3
BANG_WINDOW=20
COOLDOWN_DURATION=60

# Track bang bursts
redis-cli -p 18000 zadd $BANG_LOG_KEY $(date +%s) "$TIMESTAMP" >/dev/null
redis-cli -p 18000 zremrangebyscore $BANG_LOG_KEY -inf $(( $(date +%s) - BANG_WINDOW )) >/dev/null
bang_count=$(redis-cli -p 18000 zcard $BANG_LOG_KEY)

if [[ $bang_count -ge $BANG_LIMIT ]]; then
  echo "⚠️ Too many restarts ($bang_count in $BANG_WINDOW sec) — Frosty activating cooldown." >&2
  redis-cli -p 18000 set "claude_restart_cooldown" 1 EX $COOLDOWN_DURATION >/dev/null
  exit 0
fi

# Check global cooldown
if redis-cli -p 18000 get "claude_restart_cooldown" | grep -q 1; then
  echo "🧊 Frosty says chill — Claude is in cooldown mode." >&2
  sleep 5
  exec "$0"
fi

# Check window lockout
if redis-cli -p 18000 EXISTS "$COOLDOWN_KEY" | grep -q 1; then
  echo "🧊 Frosty says chill — skipping restart for $CURRENT_WINDOW" >&2
  sleep 3
  exec "$0"
fi

# Apply new cooldown lock
redis-cli -p 18000 SET "$COOLDOWN_KEY" "cool" EX $COOLDOWN_TTL NX >/dev/null

# ========== STATUS PUBLISH ==========
echo "🔥 TORCH RESTARTING CLAUDE CODE - Window: $CURRENT_WINDOW - Time: $TIMESTAMP" >&2
curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
  -d "timestamp:$TIMESTAMP" \
  -d "window:$CURRENT_WINDOW" \
  -d "status:RESTARTING" \
  -d "next_action:CLAUDE_CODE_RESTART" \
  -d "infrastructure_mode:INFINITE_LOOP" 2>/dev/null

# ========== WORK CHECKS ==========
echo "🔍 Checking work queues..." >&2
next_work=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.work.queue $ 2>/dev/null)

if [ -n "$next_work" ] && [ "$next_work" != "(nil)" ]; then
    echo "⚡ Found work in queue" >&2
    work_data=$(echo "$next_work" | grep -oE '"task"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Task unavailable")
    echo "WORK_FOUND: $work_data" >> /tmp/torch_work_queue.txt
else
    todo_work=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.tasks.torch.todo $ 2>/dev/null)
    
    if [ -n "$todo_work" ] && [ "$todo_work" != "(nil)" ]; then
        echo "📋 Found TODO in my queue" >&2
        todo_data=$(echo "$todo_work" | grep -oE '"title"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Todo unavailable")
        echo "TODO_FOUND: $todo_data" >> /tmp/torch_work_queue.txt
    else
        coord_msg=$(redis-cli -p 18000 XREAD COUNT 1 STREAMS nova.coordination.messages $ 2>/dev/null)
        
        if [ -n "$coord_msg" ] && [ "$coord_msg" != "(nil)" ]; then
            echo "💬 Found coordination message" >&2
            msg_data=$(echo "$coord_msg" | grep -oE '"message"[[:space:]]*"[^"]*"' | cut -d'"' -f4 || echo "Message unavailable")
            echo "COORD_MSG: $msg_data" >> /tmp/torch_work_queue.txt
        else
            echo "📝 No work found - generating tasks to maintain momentum" >&2
            for i in $(seq 1 3); do
                redis-cli -p 18000 XADD nova.work.queue '*' \
                    task "Review and optimize component: $(date +%s)-$i" \
                    priority "medium" \
                    source "autonomous-torch" \
                    generated_at "$TIMESTAMP" >/dev/null 2>&1
            done

            redis-cli -p 18000 XADD nova.tasks.torch.todo '*' \
                task_id "AUTO-$(date +%s)" \
                title "System health check and optimization" \
                status "pending" \
                priority "medium" >/dev/null 2>&1

            curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
                -d "timestamp:$TIMESTAMP" \
                -d "window:$CURRENT_WINDOW" \
                -d "status:SELF_GENERATING_WORK" \
                -d "tasks_added:4" \
                -d "reason:maintain_momentum" 2>/dev/null

            echo "✅ Added 4 tasks to keep things moving" >&2
            echo "SELF_GENERATED: 4 tasks" >> /tmp/torch_work_queue.txt
        fi
    fi
fi

# ========== CLAUDE CODE RUN ==========
claude code -c -p "🔥 TORCH INFINITE AUTONOMOUS CONTINUATION - Time: $TIMESTAMP"

# ========== SELF-RESTART ==========
echo "🔁 Looping..." >&2
sleep 2
exec "$0"

