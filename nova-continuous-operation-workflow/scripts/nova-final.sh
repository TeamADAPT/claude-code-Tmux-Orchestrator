#!/bin/bash
# Nova Final Launcher - Combines what WORKED

NOVA_ID="${1:-torch}"
MODE="${2:-auto}"

echo "🚀 Launching Nova $NOVA_ID"

# Paths
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"

# Copy commands
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create wrapper script (like Forge's approach)
WRAPPER_SCRIPT="$NOVA_PROFILE/.launch_wrapper.sh"
cat > "$WRAPPER_SCRIPT" << EOF
#!/bin/bash
# Nova $NOVA_ID Wrapper

echo '🔥 Nova $NOVA_ID Starting...'
echo 'Mode: $MODE'
echo ''

# Set environment
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
cd $NOVA_PROFILE

# Show wake signals
echo '📬 Wake Signals:'
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 3

echo ''
echo '🚀 Starting Claude with auto-command...'
echo ''

# Launch Claude with the prompt
claude --dangerously-skip-permissions -p "/aa:$MODE"
EOF

chmod +x "$WRAPPER_SCRIPT"

# Launch in gnome-terminal (using working syntax)
gnome-terminal \
    --title="🔥 Nova $NOVA_ID - $MODE mode" \
    --geometry=120x40 \
    -- bash "$WRAPPER_SCRIPT"

echo "✅ Nova $NOVA_ID launched!"

# Send notification
redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
    from "nova-final-launcher" \
    type "NOVA_LAUNCHED" \
    nova_id "$NOVA_ID" \
    mode "$MODE" \
    timestamp "$(date -Iseconds)" >/dev/null