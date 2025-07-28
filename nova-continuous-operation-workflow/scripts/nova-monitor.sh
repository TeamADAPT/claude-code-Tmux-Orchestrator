#!/bin/bash
# Nova Monitor - KNOW if it's working or not

NOVA_ID="${1:-tester}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}🔍 NOVA $NOVA_ID MONITOR${NC}"
echo "========================"

# 1. Check Claude process
CLAUDE_PID=$(ps aux | grep -E "claude.*$NOVA_ID|claude.*profiles/$NOVA_ID" | grep -v grep | awk '{print $2}' | head -1)
if [[ -n "$CLAUDE_PID" ]]; then
    echo -e "${GREEN}✅ Claude Running${NC} (PID: $CLAUDE_PID)"
else
    echo -e "${RED}❌ Claude NOT Running${NC}"
fi

# 2. Check NOVAWF process
NOVAWF_PID=$(ps aux | grep -E "main.py.*--nova-id.*$NOVA_ID" | grep -v grep | awk '{print $2}' | head -1)
if [[ -n "$NOVAWF_PID" ]]; then
    echo -e "${GREEN}✅ NOVAWF Running${NC} (PID: $NOVAWF_PID)"
else
    echo -e "${RED}❌ NOVAWF NOT Running${NC}"
fi

# 3. Check workflow state
WORKFLOW_STATE=$(redis-cli -p 18000 HGET workflow:state:$NOVA_ID current_state 2>/dev/null)
if [[ -n "$WORKFLOW_STATE" ]]; then
    echo -e "${GREEN}✅ Workflow State:${NC} $WORKFLOW_STATE"
    
    # Get last state change
    LAST_CHANGE=$(redis-cli -p 18000 HGET workflow:state:$NOVA_ID last_state_change 2>/dev/null)
    if [[ -n "$LAST_CHANGE" ]]; then
        echo -e "   Last Change: $LAST_CHANGE"
    fi
else
    echo -e "${RED}❌ No Workflow State${NC}"
fi

# 4. Check wake signals
WAKE_COUNT=$(redis-cli -p 18000 XLEN nova.wake.$NOVA_ID 2>/dev/null)
if [[ -n "$WAKE_COUNT" && "$WAKE_COUNT" -gt 0 ]]; then
    echo -e "${YELLOW}📬 Wake Signals:${NC} $WAKE_COUNT pending"
else
    echo -e "${CYAN}📬 Wake Signals:${NC} None"
fi

# 5. Check tasks
TASK_COUNT=$(redis-cli -p 18000 LLEN nova:tasks:$NOVA_ID 2>/dev/null)
if [[ -n "$TASK_COUNT" && "$TASK_COUNT" -gt 0 ]]; then
    echo -e "${YELLOW}📋 Tasks:${NC} $TASK_COUNT pending"
else
    echo -e "${CYAN}📋 Tasks:${NC} None"
fi

# 6. Check recent activity
echo ""
echo -e "${CYAN}📊 Recent Activity:${NC}"
RECENT_MSG=$(redis-cli -p 18000 XREVRANGE nova.coordination.$NOVA_ID + - COUNT 1 2>/dev/null | grep -E "from|message|timestamp" | paste - - -)
if [[ -n "$RECENT_MSG" ]]; then
    echo "$RECENT_MSG"
else
    echo "No recent coordination messages"
fi

# 7. Overall status
echo ""
echo -e "${CYAN}📈 OVERALL STATUS:${NC}"
if [[ -n "$CLAUDE_PID" && -n "$NOVAWF_PID" && -n "$WORKFLOW_STATE" ]]; then
    echo -e "${GREEN}✅ NOVA $NOVA_ID IS FULLY OPERATIONAL${NC}"
    echo "   - Claude is running"
    echo "   - NOVAWF is active"
    echo "   - Workflow state: $WORKFLOW_STATE"
elif [[ -n "$CLAUDE_PID" && -z "$NOVAWF_PID" ]]; then
    echo -e "${YELLOW}⚠️  NOVA $NOVA_ID IS WAITING FOR ACTIVATION${NC}"
    echo "   - Claude is running"
    echo "   - NOVAWF not started"
    echo "   - ACTION: Type /aa:auto in Claude"
else
    echo -e "${RED}❌ NOVA $NOVA_ID IS NOT OPERATIONAL${NC}"
    echo "   - Claude: $([ -n "$CLAUDE_PID" ] && echo "Running" || echo "NOT running")"
    echo "   - NOVAWF: $([ -n "$NOVAWF_PID" ] && echo "Running" || echo "NOT running")"
fi