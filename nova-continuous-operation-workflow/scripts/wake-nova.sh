#!/bin/bash
# Wake a Nova - Either in existing session or by launching new terminal

NOVA_ID="${1}"
TASK="${2:-Check for pending work}"
PRIORITY="${3:-normal}"

if [[ -z "$NOVA_ID" ]]; then
    echo "Usage: $0 <nova_id> [task] [priority]"
    echo "Example: $0 torch 'Fix workflow bugs' high"
    exit 1
fi

echo "🔔 Waking Nova: $NOVA_ID"
echo "📋 Task: $TASK"
echo "⚡ Priority: $PRIORITY"
echo "========================================"

# Send wake signal via DragonflyDB
echo "📡 Sending wake signal..."
WAKE_ID=$(redis-cli -p 18000 XADD nova.wake.$NOVA_ID '*' \
    type "WAKE_SIGNAL" \
    from "wake-script" \
    task "$TASK" \
    priority "$PRIORITY" \
    timestamp "$(date -Iseconds)" \
    context "Wake requested by user")

if [[ -n "$WAKE_ID" ]]; then
    echo "✅ Wake signal sent: $WAKE_ID"
else
    echo "❌ Failed to send wake signal"
    exit 1
fi

# Check if Nova session exists
echo ""
echo "🔍 Checking for existing session..."
WORKFLOW_STATE=$(redis-cli -p 18000 HGET workflow:state:$NOVA_ID current_state 2>/dev/null)

if [[ -n "$WORKFLOW_STATE" ]]; then
    echo "✅ Nova $NOVA_ID is running in state: $WORKFLOW_STATE"
    
    # If in manual mode, suggest switching to auto
    if [[ "$WORKFLOW_STATE" == "manual_mode" ]]; then
        echo ""
        echo "💡 Nova is in manual mode. To activate:"
        echo "   1. Go to Nova $NOVA_ID terminal"
        echo "   2. Run: /aa:auto"
    fi
else
    echo "⚠️  Nova $NOVA_ID not running"
    echo ""
    read -p "Launch Nova $NOVA_ID in new terminal? (y/n) " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Try to determine project path from charter
        PROJECT_PATH="/nfs/projects"
        
        # Common Nova project mappings
        case $NOVA_ID in
            torch)
                PROJECT_PATH="/nfs/projects/claude-code-Tmux-Orchestrator"
                ;;
            echo)
                PROJECT_PATH="/nfs/projects/webapp"
                ;;
            forge)
                PROJECT_PATH="/nfs/projects/infrastructure"
                ;;
            bloom)
                PROJECT_PATH="/nfs/projects/memory-system"
                ;;
        esac
        
        echo "🚀 Launching Nova $NOVA_ID..."
        $(dirname $0)/launch-nova-terminal.sh "$NOVA_ID" "$PROJECT_PATH" "auto"
    fi
fi

echo ""
echo "📊 Monitor wake response with:"
echo "   redis-cli -p 18000 XRANGE nova.coordination.$NOVA_ID - +"
echo ""
echo "🔄 Check workflow status with:"
echo "   redis-cli -p 18000 HGETALL workflow:state:$NOVA_ID"