#!/bin/bash
# Nova Launch - Simple terminal launcher for Claude Code

NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-/nfs/projects/claude-code-Tmux-Orchestrator}"
MODE="${3:-auto}"

echo "🚀 Launching Nova $NOVA_ID"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $MODE"

# Create Nova profile if needed
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"

# Copy commands
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create launch instructions file
INSTRUCTIONS="/tmp/nova-${NOVA_ID}-instructions.txt"
cat > "$INSTRUCTIONS" << EOF
🔥 Nova $NOVA_ID Ready!
====================

Project: $PROJECT_PATH
Profile: $NOVA_PROFILE

📋 Quick Start:
1. Type: claude --dangerously-skip-permissions
2. Once Claude starts, type: /aa:$MODE

📬 Wake Signals:
EOF

# Add wake signals to instructions
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 3 >> "$INSTRUCTIONS" 2>/dev/null

# Launch terminal
gnome-terminal \
    --working-directory="$PROJECT_PATH" \
    --title="🔥 Nova $NOVA_ID" \
    --geometry=120x30 \
    -e "bash -c 'export NOVA_ID=$NOVA_ID; export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude; cat $INSTRUCTIONS; echo; bash'"

echo "✅ Nova $NOVA_ID terminal launched!"
echo ""
echo "In the terminal:"
echo "1. Run: claude --dangerously-skip-permissions"
echo "2. Type: /aa:$MODE"