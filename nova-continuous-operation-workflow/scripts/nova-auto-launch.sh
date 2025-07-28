#!/bin/bash
# Nova Auto Launch - Uses claude -p to send commands!

NOVA_ID="${1:-torch}"
MODE="${2:-auto}"

echo "🚀 Launching Nova $NOVA_ID with auto-command"

# Ensure profile exists
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create startup script that uses claude -p
STARTUP_SCRIPT="$NOVA_PROFILE/.auto_startup.sh"
cat > "$STARTUP_SCRIPT" << EOF
#!/bin/bash
# Auto-start Nova $NOVA_ID

cd $NOVA_PROFILE
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude

echo "🔥 Nova $NOVA_ID Starting..."
echo "Mode: $MODE"
echo ""

# Show wake signals
echo "📬 Wake Signals:"
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 3

echo ""
echo "🚀 Starting Claude with auto-command..."
echo ""

# Use claude -p to send the command!
claude --dangerously-skip-permissions -p "/aa:$MODE"
EOF

chmod +x "$STARTUP_SCRIPT"

# Launch in gnome-terminal
gnome-terminal \
    --title="🔥 Nova $NOVA_ID - $MODE" \
    --geometry=120x40 \
    --working-directory="$NOVA_PROFILE" \
    -- bash "$STARTUP_SCRIPT"

echo "✅ Nova $NOVA_ID launched with auto-command: /aa:$MODE"