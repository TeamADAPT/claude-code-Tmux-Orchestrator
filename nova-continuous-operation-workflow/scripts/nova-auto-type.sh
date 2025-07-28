#!/bin/bash
# Nova Auto Type - Launch and automatically type command

NOVA_ID="${1:-tester}"
MODE="${2:-auto}"

echo "🚀 Launching Nova $NOVA_ID with auto-typing"

# Launch with session manager
RESULT=$(python3 ./nova-continuous-operation-workflow/scripts/nova_session_manager.py launch "$NOVA_ID" < /dev/null)
echo "$RESULT"

# Extract terminal PID
if [[ "$RESULT" =~ Terminal\ PID:\ ([0-9]+) ]]; then
    TERM_PID="${BASH_REMATCH[1]}"
    echo "📋 Terminal PID: $TERM_PID"
    
    # Wait for Claude to initialize
    echo "⏳ Waiting for Claude to start..."
    sleep 5
    
    # Find window by PID
    echo "🔍 Finding window..."
    WINDOW_ID=$(xdotool search --pid $TERM_PID 2>/dev/null | tail -1)
    
    if [[ -n "$WINDOW_ID" ]]; then
        echo "✅ Found window: $WINDOW_ID"
        
        # Focus the window
        xdotool windowfocus $WINDOW_ID
        
        # Type the command
        echo "⌨️  Typing /aa:$MODE"
        xdotool type --window $WINDOW_ID "/aa:$MODE"
        sleep 0.5
        xdotool key --window $WINDOW_ID Return
        
        echo "✅ Command sent!"
    else
        echo "❌ Could not find window for PID $TERM_PID"
    fi
else
    echo "❌ Could not extract terminal PID"
fi