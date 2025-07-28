#!/bin/bash
# NOVA AUTO LAUNCHER - ACTUALLY STARTS WITH COMMAND!

NOVA_ID="${1:-tester}"
MODE="${2:-auto}"

echo "🚀 NOVA AUTO LAUNCHER - PASSING COMMAND TO CLAUDE"
echo "=============================================="

# Ensure profile exists
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create wrapper script that passes the command
WRAPPER="$NOVA_PROFILE/.auto_wrapper.sh"
cat > "$WRAPPER" << EOF
#!/bin/bash
cd $NOVA_PROFILE
export NOVA_ID=$NOVA_ID
export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude

echo "🔥 Nova $NOVA_ID Starting with AUTO COMMAND"
echo "==========================================="

# Start Claude with the slash command as an argument!
claude --dangerously-skip-permissions "/aa:$MODE"
EOF

chmod +x "$WRAPPER"

# Launch in gnome-terminal
gnome-terminal \
    --title="🔥 NOVA $NOVA_ID 🔥" \
    --geometry=120x40 \
    -- bash "$WRAPPER"

echo "✅ Nova $NOVA_ID launched with AUTO COMMAND: /aa:$MODE"
echo "The command will execute automatically!"