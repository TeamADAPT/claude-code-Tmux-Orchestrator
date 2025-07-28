#!/bin/bash
# Launch Nova in External Terminal with NOVAWF Integration
# Supports both gnome-terminal and other terminal emulators

# Parse arguments
NOVA_ID="${1:-torch}"
PROJECT_PATH="${2:-$(pwd)}"
START_MODE="${3:-auto}"  # auto, manual, or train

echo "🚀 Launching Nova: $NOVA_ID"
echo "📁 Project: $PROJECT_PATH"
echo "⚙️  Mode: $START_MODE"
echo "========================================"

# Create Nova profile directory if needed
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
if [[ ! -d "$NOVA_PROFILE" ]]; then
    echo "📂 Creating Nova profile directory..."
    mkdir -p "$NOVA_PROFILE/.claude"
fi

# Check if gnome-terminal is available
if command -v gnome-terminal >/dev/null 2>&1; then
    echo "✅ Using gnome-terminal..."
    
    gnome-terminal \
        --working-directory="$PROJECT_PATH" \
        --title="🔥 Nova $NOVA_ID - NOVAWF Ready" \
        --geometry=120x30 \
        -- bash -c "
        echo '🔥 Nova $NOVA_ID Session'
        echo '========================='
        echo 'Project: $PROJECT_PATH'
        echo 'Profile: $NOVA_PROFILE'
        echo 'Workflow: NOVAWF Integrated'
        echo '========================='
        echo ''
        echo '📋 AVAILABLE COMMANDS:'
        echo '  /aa:auto   - Start/resume autonomous operation'
        echo '  /aa:man    - Enter manual mode'
        echo '  /aa:train  - Enter training mode (torch only)'
        echo '  /aa:status - Check workflow status'
        echo '  /aa:help   - Show all commands'
        echo ''
        echo '🔄 WORKFLOW INTEGRATION:'
        echo '  - DragonflyDB on port 18000'
        echo '  - Stream: nova.coordination.$NOVA_ID'
        echo '  - Wake signals: nova.wake.$NOVA_ID'
        echo ''
        
        # Set Nova environment
        export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
        export NOVA_ID=$NOVA_ID
        export NOVA_PROJECT=$PROJECT_PATH
        
        # Check for wake signals
        echo '🔍 Checking for wake signals...'
        redis-cli -p 18000 XREVRANGE nova.wake.$NOVA_ID + - COUNT 1 2>/dev/null
        
        echo ''
        echo '🎯 Starting Claude Code...'
        echo ''
        
        # Start Claude with initial command based on mode
        if [[ '$START_MODE' == 'auto' ]]; then
            echo 'Entering autonomous mode automatically...'
            echo '/aa:auto' | claude --dangerously-skip-permissions
        elif [[ '$START_MODE' == 'manual' ]]; then
            echo 'Starting in manual mode...'
            echo '/aa:man' | claude --dangerously-skip-permissions
        elif [[ '$START_MODE' == 'train' ]]; then
            echo 'Starting in training mode...'
            echo '/aa:train' | claude --dangerously-skip-permissions
        else
            claude --dangerously-skip-permissions
        fi
        
        echo ''
        echo '✅ Session ended'
        echo 'Press any key to close...'
        read -n 1
    "
    
elif command -v xterm >/dev/null 2>&1; then
    echo "✅ Using xterm..."
    
    xterm -T "Nova $NOVA_ID" \
        -geometry 120x30 \
        -e bash -c "
        cd $PROJECT_PATH
        export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
        export NOVA_ID=$NOVA_ID
        echo 'Nova $NOVA_ID ready. Use /aa:auto to start.'
        claude --dangerously-skip-permissions
        read -p 'Press enter to close...'
    "
    
elif command -v konsole >/dev/null 2>&1; then
    echo "✅ Using konsole..."
    
    konsole --workdir "$PROJECT_PATH" \
        -p tabtitle="Nova $NOVA_ID" \
        -e bash -c "
        export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
        export NOVA_ID=$NOVA_ID
        echo 'Nova $NOVA_ID ready. Use /aa:auto to start.'
        claude --dangerously-skip-permissions
        read -p 'Press enter to close...'
    "
    
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "✅ Using Terminal.app (macOS)..."
    
    osascript -e "
    tell application \"Terminal\"
        do script \"cd $PROJECT_PATH && export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude && export NOVA_ID=$NOVA_ID && echo 'Nova $NOVA_ID ready. Use /aa:auto to start.' && claude --dangerously-skip-permissions\"
    end tell
    "
    
else
    echo "❌ No supported terminal emulator found!"
    echo "Please install gnome-terminal, xterm, or konsole"
    exit 1
fi

echo ""
echo "✅ Nova $NOVA_ID launched!"
echo ""
echo "💡 TIPS:"
echo "  - Use /aa:status to check workflow state"
echo "  - Use /aa:auto to ensure autonomous operation"
echo "  - Check charter at .claude/CHARTER.md for context"
echo ""
echo "📊 Monitor with:"
echo "  redis-cli -p 18000 XRANGE nova.coordination.$NOVA_ID - +"