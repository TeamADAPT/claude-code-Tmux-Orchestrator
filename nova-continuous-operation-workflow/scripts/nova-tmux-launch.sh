#!/bin/bash
# Nova Tmux Launch - Launch in tmux where we CAN send commands

NOVA_ID="${1:-tester}"
MODE="${2:-auto}"

echo "🚀 Launching Nova $NOVA_ID in tmux"

# Ensure profile exists
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create or attach to tmux session
SESSION_NAME="nova-$NOVA_ID"
tmux has-session -t "$SESSION_NAME" 2>/dev/null && tmux kill-session -t "$SESSION_NAME"

# Create new session
tmux new-session -d -s "$SESSION_NAME" -c "$NOVA_PROFILE"

# Set environment
tmux send-keys -t "$SESSION_NAME" "export NOVA_ID=$NOVA_ID" Enter
tmux send-keys -t "$SESSION_NAME" "export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude" Enter

# Start Claude
echo "📋 Starting Claude in tmux..."
tmux send-keys -t "$SESSION_NAME" "claude --dangerously-skip-permissions" Enter

# Wait for Claude to start
echo "⏳ Waiting for Claude..."
sleep 5

# Send the command
echo "📨 Sending /aa:$MODE command..."
tmux send-keys -t "$SESSION_NAME" "/aa:$MODE" Enter

echo "✅ Nova $NOVA_ID launched in tmux!"
echo ""
echo "📊 Monitor with:"
echo "   tmux attach -t $SESSION_NAME"
echo "   tmux capture-pane -t $SESSION_NAME -p"