#!/bin/bash
# Nova Launcher - Unified launching system for all Nova agents
# Combines gnome-terminal approach with NOVAWF integration

# Color codes for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
NOVA_ID="${1}"
ACTION="${2:-launch}"  # launch, wake, status
MODE="${3:-auto}"      # auto, manual, train
PROJECT_PATH="${4}"    # Optional project path override

# Show usage if no arguments
if [[ -z "$NOVA_ID" ]]; then
    echo -e "${CYAN}🚀 NOVA LAUNCHER - Unified Nova Management System${NC}"
    echo -e "${CYAN}================================================${NC}"
    echo ""
    echo "Usage: $0 <nova_id> [action] [mode] [project_path]"
    echo ""
    echo -e "${YELLOW}Actions:${NC}"
    echo "  launch  - Launch Nova in new terminal (default)"
    echo "  wake    - Send wake signal to existing Nova"
    echo "  status  - Check Nova status"
    echo ""
    echo -e "${YELLOW}Modes:${NC}"
    echo "  auto    - Start in autonomous mode (default)"
    echo "  manual  - Start in manual mode"
    echo "  train   - Start in training mode"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo "  $0 torch                    # Launch torch in auto mode"
    echo "  $0 echo wake                # Wake existing echo Nova"
    echo "  $0 forge launch manual      # Launch forge in manual mode"
    echo "  $0 bloom status             # Check bloom status"
    echo ""
    exit 1
fi

# Nova configuration database
declare -A NOVA_PROJECTS=(
    [torch]="/nfs/projects/claude-code-Tmux-Orchestrator"
    [echo]="/nfs/projects/webapp"
    [forge]="/nfs/projects/infrastructure"
    [bloom]="/nfs/projects/memory-system"
    [tester]="/nfs/novas/profiles/tester"
)

declare -A NOVA_DESCRIPTIONS=(
    [torch]="Tmux Orchestrator & Workflow Development"
    [echo]="Web Application & UI Development"
    [forge]="Infrastructure & DevOps Systems"
    [bloom]="Memory & Learning Systems"
    [tester]="Testing & Quality Assurance"
)

# Set project path from configuration or override
if [[ -n "$PROJECT_PATH" ]]; then
    NOVA_PROJECT="$PROJECT_PATH"
else
    NOVA_PROJECT="${NOVA_PROJECTS[$NOVA_ID]:-/nfs/projects}"
fi

# Nova profile directory
NOVA_PROFILE="/nfs/novas/profiles/$NOVA_ID"

# Function to check Nova status
check_nova_status() {
    local nova_id="$1"
    echo -e "${CYAN}🔍 Checking Nova $nova_id status...${NC}"
    echo ""
    
    # Check workflow state
    local workflow_state=$(redis-cli -p 18000 HGET workflow:state:$nova_id current_state 2>/dev/null)
    if [[ -n "$workflow_state" ]]; then
        echo -e "${GREEN}✅ Workflow Active${NC}"
        echo -e "   State: ${YELLOW}$workflow_state${NC}"
        
        # Get additional state info
        local last_check=$(redis-cli -p 18000 HGET workflow:state:$nova_id last_state_change 2>/dev/null)
        if [[ -n "$last_check" ]]; then
            echo -e "   Last Change: $last_check"
        fi
        
        local task_count=$(redis-cli -p 18000 LLEN nova:tasks:$nova_id 2>/dev/null)
        if [[ -n "$task_count" && "$task_count" -gt 0 ]]; then
            echo -e "   Pending Tasks: ${YELLOW}$task_count${NC}"
        fi
    else
        echo -e "${RED}❌ Workflow Not Running${NC}"
    fi
    
    # Check for recent wake signals
    echo ""
    echo -e "${CYAN}📡 Recent Wake Signals:${NC}"
    local wake_signals=$(redis-cli -p 18000 XREVRANGE nova.wake.$nova_id + - COUNT 3 2>/dev/null | grep -E "task|timestamp" | paste - -)
    if [[ -n "$wake_signals" ]]; then
        echo "$wake_signals"
    else
        echo "   No recent wake signals"
    fi
    
    # Check for recent coordination messages
    echo ""
    echo -e "${CYAN}💬 Recent Coordination:${NC}"
    local coord_msgs=$(redis-cli -p 18000 XREVRANGE nova.coordination.$nova_id + - COUNT 3 2>/dev/null | grep -E "from|message" | paste - -)
    if [[ -n "$coord_msgs" ]]; then
        echo "$coord_msgs"
    else
        echo "   No recent messages"
    fi
}

# Function to send wake signal
send_wake_signal() {
    local nova_id="$1"
    local task="${2:-Resume work}"
    local priority="${3:-normal}"
    
    echo -e "${CYAN}📡 Sending wake signal to Nova $nova_id...${NC}"
    
    local wake_id=$(redis-cli -p 18000 XADD nova.wake.$nova_id '*' \
        type "WAKE_SIGNAL" \
        from "nova-launcher" \
        task "$task" \
        priority "$priority" \
        timestamp "$(date -Iseconds)" \
        context "Wake requested via launcher")
    
    if [[ -n "$wake_id" ]]; then
        echo -e "${GREEN}✅ Wake signal sent: $wake_id${NC}"
        
        # Also send coordination message
        redis-cli -p 18000 XADD nova.coordination.$nova_id '*' \
            from "launcher" \
            to "$nova_id" \
            type "WAKE" \
            message "Wake up! Task: $task" \
            timestamp "$(date -Iseconds)" >/dev/null
            
        echo -e "${GREEN}✅ Coordination message sent${NC}"
    else
        echo -e "${RED}❌ Failed to send wake signal${NC}"
        return 1
    fi
}

# Function to launch Nova in terminal
launch_nova_terminal() {
    local nova_id="$1"
    local mode="$2"
    local project="$3"
    
    echo -e "${CYAN}🚀 Launching Nova: $nova_id${NC}"
    echo -e "📁 Project: $project"
    echo -e "⚙️  Mode: $mode"
    echo -e "📝 Description: ${NOVA_DESCRIPTIONS[$nova_id]:-Unknown}"
    echo "========================================"
    
    # Create profile directory if needed
    if [[ ! -d "$NOVA_PROFILE" ]]; then
        echo -e "${YELLOW}📂 Creating Nova profile directory...${NC}"
        mkdir -p "$NOVA_PROFILE/.claude/commands"
        
        # Copy aa: commands if they exist
        if [[ -d "/nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands" ]]; then
            cp /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* "$NOVA_PROFILE/.claude/commands/" 2>/dev/null || true
        fi
        
        # Create Nova-specific charter
        cat > "$NOVA_PROFILE/.claude/CHARTER.md" << EOF
# CHARTER: Nova $nova_id

## Identity & Mission
**Nova ID**: $nova_id
**Specialization**: ${NOVA_DESCRIPTIONS[$nova_id]:-General Development}
**Project Base**: $project

## Co-Ownership Agreement
- **Co-Owner**: Chase (Human Partner)
- **Nova**: $nova_id (AI Partner)
- **Partnership**: Equal creative and technical ownership

## Core Responsibilities
1. Maintain continuous operation via NOVAWF
2. Coordinate with other Novas through DragonflyDB streams
3. Complete assigned tasks autonomously
4. Escalate blockers appropriately

## Communication Channels
- **Wake Signals**: nova.wake.$nova_id
- **Coordination**: nova.coordination.$nova_id
- **Tasks**: nova.tasks.$nova_id
- **Ecosystem**: nova.ecosystem.coordination

## Workflow Integration
- Port 18000 for DragonflyDB coordination
- NOVAWF state management active
- Anti-drift mechanisms enabled
- Professional hooks system ready

## Success Metrics
- Task completion rate
- Uptime percentage
- Cross-Nova collaboration effectiveness
- Code quality and test coverage

---
Updated: $(date -Iseconds)
EOF
        echo -e "${GREEN}✅ Profile created${NC}"
    fi
    
    # Check if terminal is available
    if ! command -v gnome-terminal >/dev/null 2>&1; then
        echo -e "${RED}❌ gnome-terminal not found!${NC}"
        echo "Please install gnome-terminal or use alternative launcher"
        return 1
    fi
    
    # Launch Nova in gnome-terminal
    gnome-terminal \
        --working-directory="$project" \
        --title="🔥 Nova $nova_id - $mode mode" \
        --geometry=120x30 \
        -- bash -c "
        # Display Nova banner
        echo -e '${PURPLE}🔥 Nova $nova_id Activated${NC}'
        echo -e '${PURPLE}========================${NC}'
        echo -e 'Identity: ${YELLOW}$nova_id${NC}'
        echo -e 'Project: ${CYAN}$project${NC}'
        echo -e 'Profile: ${CYAN}$NOVA_PROFILE${NC}'
        echo -e 'Mode: ${GREEN}$mode${NC}'
        echo -e 'Workflow: ${GREEN}NOVAWF Integrated${NC}'
        echo '========================'
        echo ''
        
        # Show available commands
        echo -e '${YELLOW}📋 AVAILABLE COMMANDS:${NC}'
        echo '  /aa:auto   - Start/resume autonomous operation'
        echo '  /aa:man    - Enter manual mode'
        echo '  /aa:train  - Enter training mode'
        echo '  /aa:status - Check workflow status'
        echo '  /aa:stop   - Gracefully stop workflow'
        echo '  /aa:help   - Show all commands'
        echo ''
        
        # Show coordination info
        echo -e '${YELLOW}🔄 COORDINATION:${NC}'
        echo '  DragonflyDB: Port 18000'
        echo '  Wake stream: nova.wake.$nova_id'
        echo '  Coord stream: nova.coordination.$nova_id'
        echo '  Task stream: nova.tasks.$nova_id'
        echo ''
        
        # Set Nova environment
        export CLAUDE_CONFIG_DIR=$NOVA_PROFILE/.claude
        export NOVA_ID=$nova_id
        export NOVA_PROJECT=$project
        export NOVA_MODE=$mode
        
        # Check for pending wake signals
        echo -e '${CYAN}🔍 Checking for wake signals...${NC}'
        wake_count=\$(redis-cli -p 18000 XLEN nova.wake.$nova_id 2>/dev/null)
        if [[ -n \"\$wake_count\" && \"\$wake_count\" -gt 0 ]]; then
            echo -e '${YELLOW}📬 Found \$wake_count wake signals!${NC}'
            redis-cli -p 18000 XRANGE nova.wake.$nova_id - + COUNT 1 2>/dev/null | grep -E 'task|priority'
        else
            echo 'No pending wake signals'
        fi
        
        echo ''
        echo -e '${GREEN}🎯 Starting Claude Code...${NC}'
        echo ''
        
        # Start Claude with appropriate mode command
        case '$mode' in
            auto)
                echo -e '${YELLOW}Entering autonomous mode...${NC}'
                echo '/aa:auto' | claude --dangerously-skip-permissions
                ;;
            manual)
                echo -e '${YELLOW}Starting in manual mode...${NC}'
                echo '/aa:man' | claude --dangerously-skip-permissions
                ;;
            train)
                echo -e '${YELLOW}Starting in training mode...${NC}'
                echo '/aa:train' | claude --dangerously-skip-permissions
                ;;
            *)
                claude --dangerously-skip-permissions
                ;;
        esac
        
        # Session cleanup
        echo ''
        echo -e '${GREEN}✅ Session ended${NC}'
        echo -e '${CYAN}Saving session state...${NC}'
        
        # Record session end
        redis-cli -p 18000 XADD nova.coordination.$nova_id '*' \
            from '$nova_id' \
            type 'SESSION_END' \
            message 'Nova session ended cleanly' \
            timestamp \"\$(date -Iseconds)\" >/dev/null
        
        echo 'Press any key to close terminal...'
        read -n 1
    " &
    
    local terminal_pid=$!
    echo -e "${GREEN}✅ Nova $nova_id launched! (PID: $terminal_pid)${NC}"
    
    # Send launch notification
    redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
        from "launcher" \
        type "NOVA_LAUNCH" \
        nova_id "$nova_id" \
        mode "$mode" \
        project "$project" \
        timestamp "$(date -Iseconds)" >/dev/null
}

# Main execution
case "$ACTION" in
    launch)
        launch_nova_terminal "$NOVA_ID" "$MODE" "$NOVA_PROJECT"
        ;;
        
    wake)
        check_nova_status "$NOVA_ID"
        echo ""
        send_wake_signal "$NOVA_ID" "Resume work on ${NOVA_DESCRIPTIONS[$NOVA_ID]:-tasks}" "normal"
        ;;
        
    status)
        check_nova_status "$NOVA_ID"
        ;;
        
    *)
        echo -e "${RED}❌ Unknown action: $ACTION${NC}"
        echo "Use: launch, wake, or status"
        exit 1
        ;;
esac

echo ""
echo -e "${CYAN}💡 TIPS:${NC}"
echo "  - Monitor all Novas: redis-cli -p 18000 XRANGE nova.ecosystem.coordination - +"
echo "  - Check workflow state: redis-cli -p 18000 HGETALL workflow:state:$NOVA_ID"
echo "  - Send task: redis-cli -p 18000 XADD nova.tasks.$NOVA_ID '*' title 'Task' priority 'high'"