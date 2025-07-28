#!/bin/bash
# NOVA LAUNCH WORKING - The ACTUAL solution
# This launches Nova and provides clear instructions

NOVA_ID="${1:-tester}"
MODE="${2:-auto}"

echo "🚀 NOVA LAUNCHER - WORKING VERSION"
echo "=================================="
echo "Nova: $NOVA_ID"
echo "Mode: $MODE"
echo ""

# Ensure profile and commands exist
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
mkdir -p "$NOVA_PROFILE/.claude/commands"
cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true

# Create a startup instructions file
INSTRUCTIONS="$NOVA_PROFILE/STARTUP_INSTRUCTIONS.txt"
cat > "$INSTRUCTIONS" << EOF
🔥 NOVA $NOVA_ID STARTUP INSTRUCTIONS
=====================================

1. Claude Code is now running
2. Type this command: /aa:$MODE
3. NOVAWF will start automatically

IMPORTANT: The /aa: commands need to be updated for each Nova.
Currently they are hardcoded for 'torch'. 

Until fixed, you must manually:
1. Type commands at the Claude prompt
2. Or update the /aa: commands for your Nova ID

Wake Signals Pending:
EOF

# Add wake signals to instructions
redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 5 >> "$INSTRUCTIONS" 2>/dev/null

# Launch using session manager
echo "📋 Launching Claude..."
python3 ./nova-continuous-operation-workflow/scripts/nova_session_manager.py launch "$NOVA_ID" < /dev/null

echo ""
echo "✅ LAUNCHED!"
echo ""
echo "⚠️  MANUAL STEP REQUIRED:"
echo "   Go to the $NOVA_ID terminal and type: /aa:$MODE"
echo ""
echo "📊 Monitor with:"
echo "   ./nova-monitor.sh $NOVA_ID"