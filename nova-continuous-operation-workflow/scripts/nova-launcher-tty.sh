#!/bin/bash
# Nova Launcher with TTY allocation to support raw mode

NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-/nfs/projects/claude-code-Tmux-Orchestrator}"
MODE="${3:-auto}"

echo "🚀 Launching Nova $NOVA_ID (TTY Mode)"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $MODE"

# Create profile directory if needed
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"

# Copy aa: commands if they exist
if [[ -d "/nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands" ]]; then
    cp /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true
fi

# Launch with script command to allocate a proper TTY
gnome-terminal \
    --working-directory="$PROJECT_PATH" \
    --title="🔥 Nova $NOVA_ID - $MODE mode" \
    --geometry=120x30 \
    -- bash -c "
    echo '🔥 Nova $NOVA_ID Terminal'
    echo '========================'
    echo 'Project: $PROJECT_PATH'
    echo 'Mode: $MODE'
    echo ''
    
    # Set environment
    export NOVA_ID=$NOVA_ID
    export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
    export NOVA_PROJECT=$PROJECT_PATH
    
    # Check wake signals
    echo '📬 Checking wake signals...'
    redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 3
    
    echo ''
    echo '🚀 Starting Claude Code with proper TTY...'
    echo ''
    echo 'Once Claude starts, type: /aa:$MODE'
    echo ''
    sleep 2
    
    # Use script command to allocate a TTY
    script -q -c 'claude --dangerously-skip-permissions' /dev/null
    
    echo ''
    echo '✅ Nova session ended'
    echo 'Press any key to close...'
    read -n 1
    "