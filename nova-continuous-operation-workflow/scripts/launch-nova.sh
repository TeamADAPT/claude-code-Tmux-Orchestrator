#!/bin/bash
# Launch Nova - Comprehensive launcher using Forge's session manager approach

NOVA_ID="${1:-torch}"
MODE="${2:-auto}"  # auto, manual, train

echo "🚀 Launching Nova: $NOVA_ID"
echo "⚙️  Mode: $MODE"
echo "========================"

# Nova profile path
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"

# Ensure profile exists
if [[ ! -d "$NOVA_PROFILE" ]]; then
    echo "📂 Creating Nova profile at $NOVA_PROFILE"
    mkdir -p "$NOVA_PROFILE/.claude/commands"
fi

# Copy NOVAWF commands
echo "📋 Installing NOVAWF commands..."
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create startup script that will automatically run the mode command
STARTUP_SCRIPT="$NOVA_PROFILE/.startup.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Nova $NOVA_ID Startup Script

echo '🔥 Nova $NOVA_ID Activated'
echo '========================'
echo 'Profile: $NOVA_PROFILE'
echo 'Mode: $MODE'
echo ''

# Set environment
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude

# Show wake signals
echo '📬 Wake Signals:'
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 5 2>/dev/null || echo "No wake signals"
echo ''

# Show tasks
echo '📋 Pending Tasks:'
redis-cli -p 18000 LRANGE nova:tasks:$NOVA_ID 0 4 2>/dev/null || echo "No pending tasks"
echo ''

# Create a command file that Claude will read on startup
echo "/aa:$MODE" > "$NOVA_PROFILE/.claude_startup_command"

# Start Claude and send the command after a short delay
(
    sleep 2
    echo "🎯 Activating $MODE mode..."
    echo "/aa:$MODE"
) | claude --dangerously-skip-permissions

# Cleanup
rm -f "$NOVA_PROFILE/.claude_startup_command"
EOF

chmod +x "$STARTUP_SCRIPT"

# Launch in gnome-terminal
echo "🖥️  Opening terminal window..."
gnome-terminal \
    --title="🔥 Nova $NOVA_ID - $MODE mode" \
    --geometry=120x40 \
    --working-directory="$NOVA_PROFILE" \
    -- bash "$STARTUP_SCRIPT"

# Record the launch
TIMESTAMP=$(date -Iseconds)
echo "$TIMESTAMP" > "$NOVA_PROFILE/last_launch"

# Send launch notification
redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
    from "launcher" \
    type "NOVA_LAUNCHED" \
    nova_id "$NOVA_ID" \
    mode "$MODE" \
    profile "$NOVA_PROFILE" \
    timestamp "$TIMESTAMP" >/dev/null

echo "✅ Nova $NOVA_ID launched!"
echo ""
echo "💡 The terminal will:"
echo "   1. Show wake signals and tasks"
echo "   2. Start Claude Code"
echo "   3. Automatically enter $MODE mode"
echo ""
echo "📊 Monitor with:"
echo "   redis-cli -p 18000 XRANGE nova.coordination.$NOVA_ID - +"