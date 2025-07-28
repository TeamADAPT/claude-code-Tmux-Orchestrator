#!/bin/bash
# NOVA LAUNCHER FINAL - THE ONE THAT ACTUALLY WORKS
# This launches Nova with NOVAWF auto-starting

NOVA_ID="${1:-torch}"
MODE="${2:-auto}"  # auto, manual, train

echo "🚀 LAUNCHING NOVA $NOVA_ID WITH AUTO-START"
echo "==========================================="

# Step 1: Ensure Nova profile exists
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"

# Step 2: Copy NOVAWF commands (CRITICAL!)
echo "📋 Installing NOVAWF commands..."
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Update nova_id in the commands
sed -i "s/--nova-id', 'torch'/--nova-id', '$NOVA_ID'/g" "$NOVA_PROFILE/.claude/commands/aa:auto.md"
sed -i "s/workflow:state:torch/workflow:state:$NOVA_ID/g" "$NOVA_PROFILE/.claude/commands/aa:*.md"
sed -i "s/nova.wake.torch/nova.wake.$NOVA_ID/g" "$NOVA_PROFILE/.claude/commands/aa:*.md"
sed -i "s/control_workflow.py torch/control_workflow.py $NOVA_ID/g" "$NOVA_PROFILE/.claude/commands/aa:*.md"

# Step 3: Create startup script that will launch Claude
STARTUP_SCRIPT="$NOVA_PROFILE/.nova_startup.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Nova $NOVA_ID Auto-Start Script

echo '🔥 Nova $NOVA_ID Initializing...'
echo '================================'
echo ''

# Set environment
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
cd $NOVA_PROFILE

# Show wake signals
echo '📬 Wake Signals:'
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 5
echo ''

# Create a command file
echo "/aa:$MODE" > .startup_command

echo '🎯 Starting Claude Code...'
echo 'Once Claude loads, it will execute: /aa:$MODE'
echo ''

# Start Claude
claude --dangerously-skip-permissions

# Cleanup on exit
rm -f .startup_command
EOF

chmod +x "$STARTUP_SCRIPT"

# Step 4: Launch using Forge's session manager approach
gnome-terminal \
    --title="🔥 Nova $NOVA_ID - $MODE mode" \
    --geometry=120x40 \
    -- bash "$STARTUP_SCRIPT"

echo "✅ Nova $NOVA_ID launched!"
echo ""
echo "The Nova will:"
echo "1. Show wake signals"
echo "2. Start Claude Code"
echo "3. YOU type: /aa:$MODE"
echo "4. NOVAWF starts automatically and runs autonomously"
echo ""
echo "📊 Monitor with:"
echo "   ps aux | grep 'main.py.*$NOVA_ID'"
echo "   redis-cli -p 18000 HGETALL workflow:state:$NOVA_ID"