#!/bin/bash
# Auto-starting Nova Launcher - Starts Claude and sends command

NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-/nfs/projects/claude-code-Tmux-Orchestrator}"
MODE="${3:-auto}"

echo "🚀 Launching Nova $NOVA_ID (Auto-Start Mode)"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $MODE"

# Create a startup script that will run Claude and send the command
STARTUP_SCRIPT="/tmp/nova-${NOVA_ID}-startup.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Nova startup script

echo "🔥 Nova $NOVA_ID Starting..."
echo "========================"
echo ""

# Set environment
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=/nfs/novas/profiles/$NOVA_ID/.claude
export NOVA_PROJECT=$PROJECT_PATH

# Check wake signals
echo "📬 Checking wake signals..."
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 3

echo ""
echo "🚀 Starting Claude Code in 3 seconds..."
sleep 3

# Start Claude and pipe in the auto command
(echo "/aa:$MODE"; cat) | claude --dangerously-skip-permissions
EOF

chmod +x "$STARTUP_SCRIPT"

# Launch terminal with the startup script
gnome-terminal \
    --working-directory="$PROJECT_PATH" \
    --title="🔥 Nova $NOVA_ID - $MODE mode" \
    --geometry=120x30 \
    -- bash -c "
    # Set variables for the script
    export NOVA_ID='$NOVA_ID'
    export PROJECT_PATH='$PROJECT_PATH'
    export MODE='$MODE'
    
    # Run the startup script
    bash $STARTUP_SCRIPT
    
    # Keep terminal open after Claude exits
    echo ''
    echo '✅ Nova session ended'
    echo 'Press any key to close...'
    read -n 1
    
    # Cleanup
    rm -f $STARTUP_SCRIPT
    "