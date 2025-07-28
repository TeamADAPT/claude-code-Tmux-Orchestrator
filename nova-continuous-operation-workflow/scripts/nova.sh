#!/bin/bash
# Nova Launcher - WORKING SOLUTION (Documented in docs/NOVA_LAUNCHER_WORKING.md)
# 
# THIS IS THE ONLY LAUNCHER THAT RELIABLY WORKS WITHOUT RAW MODE ERRORS!
# 
# Usage: ./nova.sh <nova_id> [launch|status|stop] [mode]
# Example: ./nova.sh echo launch manual
#
# What makes this work:
# 1. NO PIPING TO CLAUDE - Avoids raw mode errors
# 2. Uses proper gnome-terminal syntax with -- separator
# 3. Gives user a bash prompt to manually start Claude
# 4. Shows wake signals and tasks on startup

NOVA_ID="${1:-torch}"
ACTION="${2:-launch}"  # launch, status, stop
MODE="${3:-auto}"      # auto, manual, train

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Paths
NOVA_BASE="/nfs/novas/profiles"
NOVA_PROFILE="$NOVA_BASE/$NOVA_ID"
NOVA_COMMANDS="/nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands"

# Ensure Nova profile exists
ensure_nova_profile() {
    if [[ ! -d "$NOVA_PROFILE" ]]; then
        echo -e "${YELLOW}📂 Creating Nova profile: $NOVA_PROFILE${NC}"
        mkdir -p "$NOVA_PROFILE/.claude/commands"
    fi
    
    # Copy NOVAWF commands
    if [[ -d "$NOVA_COMMANDS" ]]; then
        cp -r "$NOVA_COMMANDS"/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true
    fi
}

# Launch Nova (based on working nova-start.sh approach)
launch_nova() {
    echo -e "${CYAN}🚀 Launching Nova: $NOVA_ID${NC}"
    echo -e "${CYAN}⚙️  Mode: $MODE${NC}"
    echo "========================"
    
    ensure_nova_profile
    
    # Create startup info file
    STARTUP_INFO="/tmp/nova-${NOVA_ID}-info.txt"
    cat > "$STARTUP_INFO" << EOF
🔥 Nova $NOVA_ID Ready!
====================

Profile: $NOVA_PROFILE
Mode: $MODE

📬 Wake Signals:
EOF
    
    # Add wake signals
    redis-cli -p 18000 XRANGE nova.wake.$NOVA_ID - + COUNT 5 >> "$STARTUP_INFO" 2>/dev/null || echo "No wake signals" >> "$STARTUP_INFO"
    
    echo "" >> "$STARTUP_INFO"
    echo "📋 Pending Tasks:" >> "$STARTUP_INFO"
    redis-cli -p 18000 LRANGE nova:tasks:$NOVA_ID 0 4 >> "$STARTUP_INFO" 2>/dev/null || echo "No tasks" >> "$STARTUP_INFO"
    
    echo "" >> "$STARTUP_INFO"
    echo "💡 Instructions:" >> "$STARTUP_INFO"
    echo "1. Run: claude --dangerously-skip-permissions" >> "$STARTUP_INFO"
    echo "2. Type: /aa:$MODE" >> "$STARTUP_INFO"
    
    # Launch terminal (using working approach)
    gnome-terminal \
        --title="🔥 Nova $NOVA_ID" \
        --geometry=120x40 \
        --working-directory="$NOVA_PROFILE" \
        -- bash -c "
        # Set environment
        export NOVA_ID=$NOVA_ID
        export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
        
        # Show startup info
        cat $STARTUP_INFO
        echo ''
        
        # Record launch (like Forge's approach)
        echo \$\$ > $NOVA_PROFILE/nova.terminal_pid
        date -Iseconds > $NOVA_PROFILE/nova.last_launch
        echo '{\"status\": \"launched\", \"mode\": \"$MODE\", \"timestamp\": \"$(date -Iseconds)\"}' > $NOVA_PROFILE/nova.status
        
        # Start interactive bash
        bash
        
        # Cleanup on exit
        rm -f $NOVA_PROFILE/nova.terminal_pid
        echo '{\"status\": \"stopped\", \"timestamp\": \"$(date -Iseconds)\"}' > $NOVA_PROFILE/nova.status
        "
    
    # Wait a moment for terminal to start
    sleep 1
    
    # Send launch notification
    redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
        from "nova-launcher" \
        type "NOVA_LAUNCHED" \
        nova_id "$NOVA_ID" \
        mode "$MODE" \
        profile "$NOVA_PROFILE" \
        timestamp "$(date -Iseconds)" >/dev/null
    
    echo -e "${GREEN}✅ Nova $NOVA_ID launched!${NC}"
    echo ""
    echo "In the terminal:"
    echo "1. Run: claude --dangerously-skip-permissions"
    echo "2. Type: /aa:$MODE"
}

# Check Nova status (inspired by Forge's session manager)
check_nova_status() {
    echo -e "${CYAN}📊 Nova $NOVA_ID Status${NC}"
    echo "==================="
    
    if [[ -f "$NOVA_PROFILE/nova.status" ]]; then
        cat "$NOVA_PROFILE/nova.status" | jq . 2>/dev/null || cat "$NOVA_PROFILE/nova.status"
    else
        echo "Status: Not launched"
    fi
    
    if [[ -f "$NOVA_PROFILE/nova.terminal_pid" ]]; then
        PID=$(cat "$NOVA_PROFILE/nova.terminal_pid")
        if ps -p $PID > /dev/null 2>&1; then
            echo -e "${GREEN}Terminal PID: $PID (running)${NC}"
        else
            echo -e "${RED}Terminal PID: $PID (not running)${NC}"
        fi
    fi
    
    # Check workflow state
    echo ""
    echo "Workflow State:"
    redis-cli -p 18000 HGET workflow:state:$NOVA_ID current_state 2>/dev/null || echo "No workflow state"
}

# Stop Nova
stop_nova() {
    echo -e "${YELLOW}🛑 Stopping Nova $NOVA_ID${NC}"
    
    if [[ -f "$NOVA_PROFILE/nova.terminal_pid" ]]; then
        PID=$(cat "$NOVA_PROFILE/nova.terminal_pid")
        if ps -p $PID > /dev/null 2>&1; then
            kill $PID
            echo -e "${GREEN}✅ Stopped terminal PID $PID${NC}"
        fi
    fi
    
    # Send stop signal
    redis-cli -p 18000 XADD nova.coordination.$NOVA_ID '*' \
        from "launcher" \
        type "STOP_REQUEST" \
        timestamp "$(date -Iseconds)" >/dev/null
}

# Main execution
case "$ACTION" in
    launch)
        launch_nova
        ;;
    status)
        check_nova_status
        ;;
    stop)
        stop_nova
        ;;
    *)
        echo "Usage: $0 <nova_id> [launch|status|stop] [mode]"
        echo "Example: $0 echo launch manual"
        exit 1
        ;;
esac