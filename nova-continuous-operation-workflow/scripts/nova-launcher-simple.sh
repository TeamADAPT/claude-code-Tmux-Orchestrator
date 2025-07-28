#!/bin/bash
# Simple Nova Launcher - Avoids raw mode issues

NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-/nfs/projects/claude-code-Tmux-Orchestrator}"
MODE="${3:-auto}"

echo "🚀 Launching Nova $NOVA_ID (Simple Mode)"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $MODE"

# Launch terminal with a simple shell first
gnome-terminal \
    --working-directory="$PROJECT_PATH" \
    --title="🔥 Nova $NOVA_ID - Ready" \
    --geometry=120x30 \
    -- bash -c "
    echo '🔥 Nova $NOVA_ID Terminal'
    echo '========================'
    echo 'Project: $PROJECT_PATH'
    echo 'Mode: $MODE'
    echo ''
    echo '📋 MANUAL STARTUP COMMANDS:'
    echo ''
    echo '1. Set Nova environment:'
    echo '   export NOVA_ID=$NOVA_ID'
    echo '   export CLAUDE_CONFIG_DIR=/nfs/novas/profiles/$NOVA_ID/.claude'
    echo ''
    echo '2. Check wake signals:'
    echo '   redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - +'
    echo ''
    echo '3. Start Claude Code:'
    echo '   claude --dangerously-skip-permissions'
    echo ''
    echo '4. Once in Claude, run:'
    echo '   /aa:$MODE'
    echo ''
    echo '🎯 Ready for manual startup'
    echo ''
    
    # Set environment
    export NOVA_ID=$NOVA_ID
    export CLAUDE_CONFIG_DIR=/nfs/novas/profiles/$NOVA_ID/.claude
    export NOVA_PROJECT=$PROJECT_PATH
    
    # Start bash shell (not Claude directly)
    bash
    "