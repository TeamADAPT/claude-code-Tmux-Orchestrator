#!/bin/bash
# Nova Start - Reliable launcher with proper directory handling

NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-/nfs/projects/claude-code-Tmux-Orchestrator}"
MODE="${3:-auto}"

echo "🚀 Starting Nova $NOVA_ID"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $MODE"

# Ensure project directory exists
if [[ ! -d "$PROJECT_PATH" ]]; then
    echo "⚠️  Warning: Project directory doesn't exist: $PROJECT_PATH"
    echo "📂 Creating directory..."
    mkdir -p "$PROJECT_PATH"
fi

# Create Nova profile
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"

# Copy commands
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create startup script
STARTUP_SCRIPT="/tmp/nova-${NOVA_ID}-start.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Nova $NOVA_ID Startup

echo '🔥 Nova $NOVA_ID Starting...'
echo '===================='
echo 'ID: $NOVA_ID'
echo 'Project: $PROJECT_PATH'
echo 'Profile: $NOVA_PROFILE'
echo ''

# Set environment
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
export NOVA_PROJECT=$PROJECT_PATH

# Change to project directory
cd "$PROJECT_PATH" || {
    echo "❌ Failed to change to project directory: $PROJECT_PATH"
    echo "📂 Current directory: \$(pwd)"
}

echo '📬 Wake Signals:'
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 5 2>/dev/null || echo "No wake signals"

echo ''
echo '💬 Recent Coordination Messages:'
redis-cli -p 18000 XREVRANGE nova.coordination.$NOVA_ID + - COUNT 3 2>/dev/null | grep -E "from|message" | paste - - || echo "No messages"

echo ''
echo '📋 Quick Start:'
echo '1. Run: claude --dangerously-skip-permissions'
echo '2. Type: /aa:$MODE'
echo ''

# Start bash in project directory
exec bash
EOF

chmod +x "$STARTUP_SCRIPT"

# Launch with gnome-terminal using updated syntax
gnome-terminal \
    --title="🔥 Nova $NOVA_ID - $MODE" \
    --geometry=120x30 \
    -- bash "$STARTUP_SCRIPT"

echo "✅ Nova $NOVA_ID started!"

# Send launch notification
redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
    from "launcher" \
    type "NOVA_START" \
    nova_id "$NOVA_ID" \
    mode "$MODE" \
    project "$PROJECT_PATH" \
    timestamp "$(date -Iseconds)" >/dev/null