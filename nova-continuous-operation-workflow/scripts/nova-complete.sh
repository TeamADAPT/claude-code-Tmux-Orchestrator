#!/bin/bash
# Nova Complete Launcher - Combines session manager + command sending
# This is the FINAL integrated solution

NOVA_ID="${1:-torch}"
ACTION="${2:-launch}"  # launch, status, stop, command
PARAM3="${3}"         # mode for launch, or command text for command action

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

# Base paths
SCRIPT_DIR="$(dirname "$0")"
SESSION_MGR="$SCRIPT_DIR/nova_session_manager.py"

case "$ACTION" in
    launch)
        MODE="${PARAM3:-auto}"
        echo -e "${CYAN}🚀 Launching Nova $NOVA_ID in $MODE mode${NC}"
        
        # First, ensure profile exists and has commands
        NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
        mkdir -p "$NOVA_PROFILE/.claude/commands"
        cp -r /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true
        
        # Launch with session manager
        RESULT=$(python3 "$SESSION_MGR" launch "$NOVA_ID" < /dev/null)
        echo "$RESULT"
        
        # Extract PID from result
        if [[ "$RESULT" =~ PID:\ ([0-9]+) ]]; then
            PID="${BASH_REMATCH[1]}"
            
            # Wait for Claude to be ready
            echo -e "${YELLOW}⏳ Waiting for Claude to initialize...${NC}"
            sleep 3
            
            # Create command file for Nova to execute on startup
            COMMAND_FILE="$NOVA_PROFILE/.startup_command"
            echo "/aa:$MODE" > "$COMMAND_FILE"
            
            echo -e "${GREEN}✅ Nova $NOVA_ID launched!${NC}"
            echo -e "${YELLOW}📝 Startup command prepared: /aa:$MODE${NC}"
            echo ""
            echo "Nova should execute the command from: $COMMAND_FILE"
            
            # Send notification
            redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
                from "nova-complete-launcher" \
                type "NOVA_LAUNCHED" \
                nova_id "$NOVA_ID" \
                mode "$MODE" \
                pid "$PID" \
                command_file "$COMMAND_FILE" \
                timestamp "$(date -Iseconds)" >/dev/null
        fi
        ;;
        
    status)
        echo -e "${CYAN}📊 Nova $NOVA_ID Status${NC}"
        python3 "$SESSION_MGR" status "$NOVA_ID"
        ;;
        
    stop)
        echo -e "${RED}🛑 Stopping Nova $NOVA_ID${NC}"
        python3 "$SESSION_MGR" stop "$NOVA_ID"
        ;;
        
    command)
        COMMAND="${PARAM3}"
        if [[ -z "$COMMAND" ]]; then
            echo "❌ Usage: $0 $NOVA_ID command '<command>'"
            exit 1
        fi
        
        echo -e "${CYAN}📤 Sending command to Nova $NOVA_ID: $COMMAND${NC}"
        
        # Check if Nova is running
        STATUS=$(python3 "$SESSION_MGR" status "$NOVA_ID" | grep '"status"' | grep -o '"[^"]*"$' | tr -d '"')
        
        if [[ "$STATUS" != "running" ]]; then
            echo -e "${RED}❌ Nova $NOVA_ID is not running (status: $STATUS)${NC}"
            exit 1
        fi
        
        # Create command file
        NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"
        COMMAND_FILE="$NOVA_PROFILE/.next_command"
        echo "$COMMAND" > "$COMMAND_FILE"
        
        # Send coordination message
        redis-cli -p 18000 XADD nova.coordination.$NOVA_ID '*' \
            from "nova-complete-launcher" \
            type "COMMAND_REQUEST" \
            command "$COMMAND" \
            file "$COMMAND_FILE" \
            message "Please execute command from $COMMAND_FILE" \
            timestamp "$(date -Iseconds)" >/dev/null
            
        echo -e "${GREEN}✅ Command sent via file: $COMMAND_FILE${NC}"
        ;;
        
    list)
        echo -e "${CYAN}📋 All Nova Status:${NC}"
        python3 "$SESSION_MGR" list
        ;;
        
    *)
        echo "Usage: $0 <nova_id> [launch|status|stop|command|list] [mode|command_text]"
        echo ""
        echo "Examples:"
        echo "  $0 tester launch auto      # Launch tester in auto mode"
        echo "  $0 echo status             # Check echo status"
        echo "  $0 forge stop              # Stop forge"
        echo "  $0 bloom command '/aa:status'  # Send command to bloom"
        echo "  $0 x list                  # List all Novas"
        exit 1
        ;;
esac