#!/bin/bash
# Launch Multiple Novas in External Terminals
# Creates a complete Nova team with proper layout

echo "🚀 LAUNCHING NOVA TEAM"
echo "====================="

# Default team configuration
NOVAS=(
    "torch:/nfs/projects/claude-code-Tmux-Orchestrator:auto"
    "echo:/nfs/projects/webapp:manual"  
    "forge:/nfs/projects/infrastructure:manual"
)

# Parse custom team if provided
if [[ $# -gt 0 ]]; then
    NOVAS=("$@")
fi

echo "📋 Team Configuration:"
for nova_config in "${NOVAS[@]}"; do
    IFS=':' read -r nova_id project_path start_mode <<< "$nova_config"
    echo "  - $nova_id: $project_path ($start_mode mode)"
done
echo ""

# Function to calculate terminal position
calculate_position() {
    local index=$1
    local x=$((($index % 2) * 650))
    local y=$((($index / 2) * 400))
    echo "${x}+${y}"
}

# Launch activity monitor first
echo "📊 Launching Activity Monitor..."
gnome-terminal \
    --title="📊 Nova Team Activity Monitor" \
    --working-directory="$(dirname $0)/.." \
    --geometry=100x20+1300+0 \
    -- bash -c "
    echo '📊 NOVA TEAM ACTIVITY MONITOR'
    echo '============================'
    echo 'Monitoring all Nova streams...'
    echo ''
    
    # Simple activity monitor
    while true; do
        clear
        echo '📊 NOVA TEAM ACTIVITY - '$(date +%H:%M:%S)''
        echo '============================'
        echo ''
        
        # Check each Nova's state
        for nova in torch echo forge bloom; do
            echo -n \"🔵 \$nova: \"
            state=\$(redis-cli -p 18000 HGET workflow:state:\$nova current_state 2>/dev/null)
            if [[ -n \"\$state\" ]]; then
                echo \"\$state\"
            else
                echo \"stopped\"
            fi
        done
        
        echo ''
        echo 'Recent Coordination Messages:'
        echo '----------------------------'
        redis-cli -p 18000 XREVRANGE nova.ecosystem.coordination + - COUNT 5 2>/dev/null | grep -E 'from|message' | head -10
        
        sleep 5
    done
" &

sleep 2

# Launch each Nova
index=0
for nova_config in "${NOVAS[@]}"; do
    IFS=':' read -r nova_id project_path start_mode <<< "$nova_config"
    
    # Set default values if not provided
    project_path="${project_path:-/nfs/projects}"
    start_mode="${start_mode:-manual}"
    
    echo "🔥 Launching $nova_id..."
    
    # Calculate terminal position
    position=$(calculate_position $index)
    
    gnome-terminal \
        --working-directory="$project_path" \
        --title="🔥 Nova $nova_id - $start_mode mode" \
        --geometry="120x30+$position" \
        -- bash -c "
        $(dirname $0)/launch-nova-terminal.sh $nova_id $project_path $start_mode
    " &
    
    sleep 1
    ((index++))
done

# Launch coordination terminal
echo "🎛️ Launching Coordination Terminal..."
gnome-terminal \
    --title="🎛️ Nova Coordination Center" \
    --working-directory="$(dirname $0)/.." \
    --geometry=100x20+1300+450 \
    -- bash -c "
    echo '🎛️ NOVA COORDINATION CENTER'
    echo '=========================='
    echo ''
    echo '📋 USEFUL COMMANDS:'
    echo ''
    echo '1. Send wake signal to Nova:'
    echo '   redis-cli -p 18000 XADD nova.wake.torch '\*' type \"WAKE_SIGNAL\" from \"coordinator\" task \"Resume NOVAWF development\"'
    echo ''
    echo '2. Broadcast to all Novas:'
    echo '   redis-cli -p 18000 XADD nova.ecosystem.coordination '\*' from \"coordinator\" type \"BROADCAST\" message \"Team standup in 5 minutes\"'
    echo ''
    echo '3. Check Nova states:'
    echo '   for n in torch echo forge; do echo -n \"\$n: \"; redis-cli -p 18000 HGET workflow:state:\$n current_state; done'
    echo ''
    echo '4. Send specific task:'
    echo '   redis-cli -p 18000 XADD nova.tasks.echo '\*' type \"TASK\" title \"Update UI components\" priority \"high\"'
    echo ''
    bash
" &

echo ""
echo "✅ Nova Team Launched!"
echo ""
echo "🎯 TERMINAL LAYOUT:"
echo "┌─────────────────────┬─────────────────────┬──────────────────┐"
echo "│ Nova 1 (torch)      │ Nova 2 (echo)       │ Activity Monitor │"
echo "├─────────────────────┼─────────────────────┼──────────────────┤"
echo "│ Nova 3 (forge)      │ Nova 4 (bloom)      │ Coordination Ctr │"
echo "└─────────────────────┴─────────────────────┴──────────────────┘"
echo ""
echo "💡 Each Nova will:"
echo "  - Check for wake signals on startup"
echo "  - Start in specified mode (auto/manual/train)"
echo "  - Connect to DragonflyDB for coordination"
echo "  - Load project context from charter"
echo ""
echo "🔄 Use coordination terminal to:"
echo "  - Send wake signals"
echo "  - Broadcast messages"
echo "  - Monitor team activity"