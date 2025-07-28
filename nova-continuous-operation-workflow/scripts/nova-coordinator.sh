#!/bin/bash
# Nova Coordinator - Central management for all Nova agents
# Handles wake-up, monitoring, and coordination

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Nova registry
NOVAS=("torch" "echo" "forge" "bloom" "tester")

# Function to display header
show_header() {
    clear
    echo -e "${PURPLE}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║               🌟 NOVA COORDINATOR SYSTEM 🌟               ║${NC}"
    echo -e "${PURPLE}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to check all Nova statuses
check_all_novas() {
    echo -e "${CYAN}📊 NOVA STATUS REPORT - $(date +%H:%M:%S)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════${NC}"
    
    for nova in "${NOVAS[@]}"; do
        local state=$(redis-cli -p 18000 HGET workflow:state:$nova current_state 2>/dev/null)
        local wake_count=$(redis-cli -p 18000 XLEN nova.wake.$nova 2>/dev/null)
        local task_count=$(redis-cli -p 18000 LLEN nova:tasks:$nova 2>/dev/null)
        
        # Determine status color
        local status_color=$RED
        local status_text="STOPPED"
        if [[ -n "$state" ]]; then
            status_color=$GREEN
            status_text="$state"
            if [[ "$state" == "manual_mode" ]]; then
                status_color=$YELLOW
            fi
        fi
        
        # Display Nova status
        printf "%-10s ${status_color}%-15s${NC} " "🔵 $nova:" "$status_text"
        
        # Show pending indicators
        if [[ -n "$wake_count" && "$wake_count" -gt 0 ]]; then
            printf "${YELLOW}[%d wake]${NC} " "$wake_count"
        fi
        if [[ -n "$task_count" && "$task_count" -gt 0 ]]; then
            printf "${CYAN}[%d tasks]${NC} " "$task_count"
        fi
        
        echo ""
    done
    echo ""
}

# Function to wake all stopped Novas
wake_all_stopped() {
    echo -e "${YELLOW}🔔 Waking all stopped Novas...${NC}"
    
    for nova in "${NOVAS[@]}"; do
        local state=$(redis-cli -p 18000 HGET workflow:state:$nova current_state 2>/dev/null)
        
        if [[ -z "$state" ]]; then
            echo -e "  Waking ${CYAN}$nova${NC}..."
            redis-cli -p 18000 XADD nova.wake.$nova '*' \
                type "WAKE_SIGNAL" \
                from "coordinator" \
                task "Resume autonomous operation" \
                priority "normal" \
                timestamp "$(date -Iseconds)" \
                context "Bulk wake from coordinator" >/dev/null
        fi
    done
    
    echo -e "${GREEN}✅ Wake signals sent${NC}"
}

# Function to broadcast message to all Novas
broadcast_message() {
    local message="$1"
    
    echo -e "${CYAN}📢 Broadcasting to all Novas...${NC}"
    
    # Send to ecosystem coordination
    redis-cli -p 18000 XADD nova.ecosystem.coordination '*' \
        from "coordinator" \
        type "BROADCAST" \
        message "$message" \
        timestamp "$(date -Iseconds)" >/dev/null
    
    # Send to each Nova's coordination stream
    for nova in "${NOVAS[@]}"; do
        redis-cli -p 18000 XADD nova.coordination.$nova '*' \
            from "coordinator" \
            to "$nova" \
            type "BROADCAST" \
            message "$message" \
            timestamp "$(date -Iseconds)" >/dev/null
    done
    
    echo -e "${GREEN}✅ Broadcast sent${NC}"
}

# Function to launch Nova selection menu
launch_nova_menu() {
    echo -e "${CYAN}🚀 SELECT NOVA TO LAUNCH:${NC}"
    echo "========================="
    
    local i=1
    for nova in "${NOVAS[@]}"; do
        echo "$i) $nova"
        ((i++))
    done
    echo "0) Cancel"
    
    read -p "Selection: " choice
    
    if [[ "$choice" -ge 1 && "$choice" -le "${#NOVAS[@]}" ]]; then
        local nova="${NOVAS[$((choice-1))]}"
        
        echo ""
        echo -e "${CYAN}Select launch mode:${NC}"
        echo "1) Auto (autonomous)"
        echo "2) Manual"
        echo "3) Train"
        
        read -p "Mode: " mode_choice
        
        case $mode_choice in
            1) mode="auto" ;;
            2) mode="manual" ;;
            3) mode="train" ;;
            *) mode="auto" ;;
        esac
        
        echo ""
        ./nova-continuous-operation-workflow/scripts/nova-launcher.sh "$nova" launch "$mode"
    fi
}

# Function to show recent activity
show_recent_activity() {
    echo -e "${CYAN}📜 RECENT ECOSYSTEM ACTIVITY:${NC}"
    echo "=============================="
    
    redis-cli -p 18000 XREVRANGE nova.ecosystem.coordination + - COUNT 10 2>/dev/null | \
        grep -E "from|type|message|timestamp" | \
        awk 'NR%4==1 {from=$0} NR%4==2 {type=$0} NR%4==3 {msg=$0} NR%4==0 {time=$0; printf "%-20s %-15s %s\n", from, type, msg}'
}

# Function to monitor real-time activity
monitor_activity() {
    echo -e "${CYAN}📡 MONITORING NOVA ACTIVITY (Press Ctrl+C to stop)${NC}"
    echo "================================================="
    
    while true; do
        clear
        show_header
        check_all_novas
        show_recent_activity
        sleep 5
    done
}

# Function to quick actions menu
quick_actions_menu() {
    while true; do
        show_header
        check_all_novas
        
        echo -e "${YELLOW}🎯 QUICK ACTIONS:${NC}"
        echo "=================="
        echo "1) Wake all stopped Novas"
        echo "2) Launch a Nova"
        echo "3) Broadcast message"
        echo "4) Monitor activity"
        echo "5) Show detailed status"
        echo "6) Emergency stop all"
        echo "0) Exit"
        echo ""
        
        read -p "Select action: " action
        
        case $action in
            1)
                wake_all_stopped
                read -p "Press enter to continue..."
                ;;
            2)
                launch_nova_menu
                read -p "Press enter to continue..."
                ;;
            3)
                read -p "Enter broadcast message: " msg
                broadcast_message "$msg"
                read -p "Press enter to continue..."
                ;;
            4)
                monitor_activity
                ;;
            5)
                for nova in "${NOVAS[@]}"; do
                    echo ""
                    ./nova-continuous-operation-workflow/scripts/nova-launcher.sh "$nova" status
                done
                read -p "Press enter to continue..."
                ;;
            6)
                echo -e "${RED}⚠️  EMERGENCY STOP - Are you sure? (y/N)${NC}"
                read -n 1 confirm
                if [[ "$confirm" == "y" ]]; then
                    for nova in "${NOVAS[@]}"; do
                        redis-cli -p 18000 XADD nova.coordination.$nova '*' \
                            from "coordinator" \
                            type "EMERGENCY_STOP" \
                            message "Emergency stop requested by coordinator" \
                            timestamp "$(date -Iseconds)" >/dev/null
                    done
                    echo -e "${RED}✅ Emergency stop sent to all Novas${NC}"
                fi
                read -p "Press enter to continue..."
                ;;
            0)
                exit 0
                ;;
        esac
    done
}

# Main execution
case "${1:-menu}" in
    status)
        check_all_novas
        ;;
    wake-all)
        wake_all_stopped
        ;;
    monitor)
        monitor_activity
        ;;
    broadcast)
        broadcast_message "${2:-Test broadcast}"
        ;;
    menu|*)
        quick_actions_menu
        ;;
esac