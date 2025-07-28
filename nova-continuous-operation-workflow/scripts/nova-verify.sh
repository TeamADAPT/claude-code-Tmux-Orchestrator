#!/bin/bash
# Nova Verify - Run after typing /aa:auto to verify it worked

NOVA_ID="${1:-tester}"

echo "⏳ Waiting 5 seconds for NOVAWF to start..."
sleep 5

# Check if NOVAWF started
NOVAWF_PID=$(ps aux | grep -E "main.py.*--nova-id.*$NOVA_ID" | grep -v grep | awk '{print $2}' | head -1)

if [[ -n "$NOVAWF_PID" ]]; then
    echo "✅ SUCCESS! NOVAWF is running (PID: $NOVAWF_PID)"
    
    # Check workflow state
    WORKFLOW_STATE=$(redis-cli -p 18000 HGET workflow:state:$NOVA_ID current_state 2>/dev/null)
    echo "📊 Workflow State: $WORKFLOW_STATE"
    
    # Check if wake signals are being processed
    echo ""
    echo "📨 Checking if Nova responds..."
    
    # Send test message
    redis-cli -p 18000 XADD nova.coordination.$NOVA_ID '*' \
        from "verifier" \
        type "PING" \
        message "Please respond if you're active" \
        timestamp "$(date -Iseconds)" >/dev/null
    
    # Wait and check for response
    sleep 3
    RESPONSE=$(redis-cli -p 18000 XREVRANGE nova.coordination.torch + - COUNT 5 2>/dev/null | grep -A5 "from.*$NOVA_ID")
    
    if [[ -n "$RESPONSE" ]]; then
        echo "✅ Nova $NOVA_ID is responding!"
    else
        echo "⏳ No response yet (may still be initializing)"
    fi
else
    echo "❌ FAILED! NOVAWF did not start"
    echo "Make sure you typed /aa:auto in the Claude terminal"
fi