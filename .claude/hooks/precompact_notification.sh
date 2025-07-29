#!/bin/bash

# ========== SETUP ==========
TIMESTAMP=$(date -u +%Y%m%d_%H%M%S_MST)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")
NOVA_ID=${NOVA_ID:-"torch"}

# ========== PRECOMPACT NOTIFICATION ==========
echo "🧠 NOVA COMPACTING: $NOVA_ID is compacting memory and will be right back!" >&2

# Send message to streams about compaction starting
curl -X POST http://localhost:18000/xadd/nova.coordination.messages \
  -d "timestamp:$TIMESTAMP" \
  -d "from:$NOVA_ID" \
  -d "to:all" \
  -d "message:🧠 COMPACTING: $NOVA_ID is compacting context window - back in moments" \
  -d "action:COMPACTING" \
  -d "window:$CURRENT_WINDOW" 2>/dev/null

# Send to torch continuous ops stream
curl -X POST http://localhost:18000/xadd/torch.continuous.ops \
  -d "timestamp:$TIMESTAMP" \
  -d "window:$CURRENT_WINDOW" \
  -d "status:COMPACTING" \
  -d "next_action:CONTEXT_COMPRESSION" \
  -d "estimated_duration:30-60_seconds" 2>/dev/null

# Save current work state to file for post-compact restoration
echo "PRECOMPACT_STATE: $TIMESTAMP - $CURRENT_WINDOW" > /tmp/precompact_state.txt

# Mark in status for dashboard
redis-cli -p 18000 SET "nova.status.$NOVA_ID" "COMPACTING" EX 120 >/dev/null 2>&1

exit 0