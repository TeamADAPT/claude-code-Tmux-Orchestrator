#!/bin/bash
# Send command to a running Nova Claude session
# This works WITH Forge's session manager

NOVA_ID="${1}"
COMMAND="${2}"

if [[ -z "$NOVA_ID" || -z "$COMMAND" ]]; then
    echo "Usage: $0 <nova_id> <command>"
    echo "Example: $0 tester '/aa:auto'"
    exit 1
fi

echo "📤 Sending command to Nova $NOVA_ID: $COMMAND"

# Get the terminal PID from session manager
NOVA_PATH="/nfs/novas/profiles/$NOVA_ID"
if [[ -f "$NOVA_PATH/nova.terminal_pid" ]]; then
    TERM_PID=$(cat "$NOVA_PATH/nova.terminal_pid")
    echo "Found terminal PID: $TERM_PID"
else
    echo "❌ No terminal PID found for $NOVA_ID"
    exit 1
fi

# Try using xdotool if available
if command -v xdotool >/dev/null 2>&1; then
    # Find window by PID
    WINDOW_ID=$(xdotool search --pid $TERM_PID 2>/dev/null | head -1)
    if [[ -n "$WINDOW_ID" ]]; then
        echo "Found window ID: $WINDOW_ID"
        # Type the command
        xdotool type --window $WINDOW_ID "$COMMAND"
        xdotool key --window $WINDOW_ID Return
        echo "✅ Command sent via xdotool"
    else
        echo "❌ Could not find window for PID $TERM_PID"
    fi
else
    echo "⚠️  xdotool not installed"
    echo "Alternative: Create a command file that Nova can read"
    
    # Create command file
    COMMAND_FILE="$NOVA_PATH/.next_command"
    echo "$COMMAND" > "$COMMAND_FILE"
    
    # Send coordination message
    redis-cli -p 18000 XADD nova.coordination.$NOVA_ID '*' \
        from "command-sender" \
        type "COMMAND_READY" \
        command "$COMMAND" \
        file "$COMMAND_FILE" \
        message "Command saved to $COMMAND_FILE - please execute it" \
        timestamp "$(date -Iseconds)" >/dev/null
    
    echo "✅ Command saved to $COMMAND_FILE"
    echo "📨 Coordination message sent"
fi