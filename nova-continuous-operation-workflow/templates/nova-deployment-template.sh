#!/bin/bash
#
# Nova Continuous Operation Workflow - Deployment Template
# This script sets up the continuous operation workflow for any Nova
#
# Usage: ./nova-deployment-template.sh <nova-name>
# Example: ./nova-deployment-template.sh echo
#

set -e

# Color output for clarity
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Validate arguments
if [ $# -ne 1 ]; then
    echo -e "${RED}Error: Nova name required${NC}"
    echo "Usage: $0 <nova-name>"
    echo "Example: $0 echo"
    exit 1
fi

NOVA_NAME="$1"
NOVA_NAME_LOWER=$(echo "$NOVA_NAME" | tr '[:upper:]' '[:lower:]')
NOVA_NAME_UPPER=$(echo "$NOVA_NAME" | tr '[:lower:]' '[:upper:]')

echo -e "${BLUE}=== Nova Continuous Operation Workflow Deployment ===${NC}"
echo -e "${BLUE}Deploying for Nova: ${YELLOW}$NOVA_NAME${NC}"
echo ""

# Check prerequisites
echo -e "${GREEN}[1/8] Checking prerequisites...${NC}"

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is required but not installed${NC}"
    exit 1
fi

# Check Redis/DragonflyDB connection
if ! redis-cli -p 18000 ping &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to DragonflyDB on port 18000${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites satisfied${NC}"

# Create Nova-specific directory
NOVA_DIR="/nfs/novas/$NOVA_NAME_LOWER/continuous-workflow"
echo -e "${GREEN}[2/8] Creating Nova directory: $NOVA_DIR${NC}"
mkdir -p "$NOVA_DIR"
mkdir -p "$NOVA_DIR/logs"
mkdir -p "$NOVA_DIR/config"
mkdir -p "$NOVA_DIR/data"

# Copy workflow code
echo -e "${GREEN}[3/8] Installing workflow components...${NC}"
WORKFLOW_SRC="/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src"

# Create symbolic links to shared code
ln -sf "$WORKFLOW_SRC/core" "$NOVA_DIR/core"
ln -sf "$WORKFLOW_SRC/safety" "$NOVA_DIR/safety"
ln -sf "$WORKFLOW_SRC/main.py" "$NOVA_DIR/main.py"

# Create Nova-specific configuration
echo -e "${GREEN}[4/8] Creating Nova configuration...${NC}"
cat > "$NOVA_DIR/config/nova_config.json" <<EOF
{
    "nova_id": "$NOVA_NAME_LOWER",
    "nova_display_name": "$NOVA_NAME",
    "redis_port": 18000,
    "safety_config": {
        "api_rate_limit_per_minute": 25,
        "api_rate_limit_per_hour": 400,
        "enable_safety_checks": true,
        "enable_loop_detection": true
    },
    "workflow_config": {
        "enable_momentum_tasks": true,
        "celebration_duration_seconds": 180,
        "phase_transition_pause_seconds": 180,
        "work_discovery_interval_seconds": 60
    },
    "personality_config": {
        "work_style": "balanced",
        "communication_style": "collaborative",
        "priority_focus": "quality_and_speed",
        "celebration_style": "brief_acknowledgment"
    },
    "stream_config": {
        "coordination_stream": "nova.coordination.$NOVA_NAME_LOWER",
        "task_stream": "nova.tasks.$NOVA_NAME_LOWER.todo",
        "progress_stream": "nova.tasks.$NOVA_NAME_LOWER.progress",
        "completed_stream": "nova.tasks.$NOVA_NAME_LOWER.completed",
        "safety_stream": "nova.safety.$NOVA_NAME_LOWER"
    }
}
EOF

# Create startup script
echo -e "${GREEN}[5/8] Creating startup script...${NC}"
cat > "$NOVA_DIR/start_workflow.sh" <<'EOF'
#!/bin/bash
#
# Start Nova Continuous Operation Workflow
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Load configuration
NOVA_ID=$(python3 -c "import json; print(json.load(open('config/nova_config.json'))['nova_id'])")

echo "Starting continuous workflow for Nova: $NOVA_ID"

# Ensure log directory exists
mkdir -p logs

# Start with logging
python3 main.py --nova-id "$NOVA_ID" >> "logs/workflow_$(date +%Y%m%d).log" 2>&1 &
PID=$!

echo "Workflow started with PID: $PID"
echo $PID > workflow.pid

# Create tmux session if desired
if command -v tmux &> /dev/null; then
    tmux new-session -d -s "nova-$NOVA_ID-workflow" "tail -f logs/workflow_$(date +%Y%m%d).log"
    echo "Created tmux session: nova-$NOVA_ID-workflow"
fi
EOF

chmod +x "$NOVA_DIR/start_workflow.sh"

# Create stop script
echo -e "${GREEN}[6/8] Creating stop script...${NC}"
cat > "$NOVA_DIR/stop_workflow.sh" <<'EOF'
#!/bin/bash
#
# Stop Nova Continuous Operation Workflow
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f workflow.pid ]; then
    PID=$(cat workflow.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "Stopping workflow (PID: $PID)..."
        kill -TERM $PID
        sleep 2
        if kill -0 $PID 2>/dev/null; then
            echo "Force stopping..."
            kill -KILL $PID
        fi
        rm workflow.pid
        echo "Workflow stopped"
    else
        echo "Workflow not running (stale PID file)"
        rm workflow.pid
    fi
else
    echo "No workflow.pid file found"
fi
EOF

chmod +x "$NOVA_DIR/stop_workflow.sh"

# Create health check script
echo -e "${GREEN}[7/8] Creating health check script...${NC}"
cat > "$NOVA_DIR/check_health.sh" <<'EOF'
#!/bin/bash
#
# Check Nova Workflow Health
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Nova Workflow Health Check ==="

# Check if running
if [ -f workflow.pid ]; then
    PID=$(cat workflow.pid)
    if kill -0 $PID 2>/dev/null; then
        echo "✓ Workflow running (PID: $PID)"
    else
        echo "✗ Workflow not running (stale PID)"
    fi
else
    echo "✗ Workflow not running (no PID file)"
fi

# Check Redis streams
NOVA_ID=$(python3 -c "import json; print(json.load(open('config/nova_config.json'))['nova_id'])")
echo ""
echo "Stream health:"

# Check task stream
TASK_COUNT=$(redis-cli -p 18000 XLEN "nova.tasks.$NOVA_ID.todo" 2>/dev/null || echo "0")
echo "- Todo tasks: $TASK_COUNT"

# Check safety status
SAFETY_STATUS=$(redis-cli -p 18000 XREVRANGE "nova.safety.$NOVA_ID" + - COUNT 1 2>/dev/null | grep -c "SAFE" || echo "0")
if [ "$SAFETY_STATUS" -gt 0 ]; then
    echo "- Safety status: ✓ SAFE"
else
    echo "- Safety status: ⚠ CHECK REQUIRED"
fi

# Check recent activity
RECENT_LOGS=$(tail -n 10 logs/workflow_$(date +%Y%m%d).log 2>/dev/null | grep -c "cycle" || echo "0")
echo "- Recent cycles: $RECENT_LOGS"

echo ""
echo "Latest log entries:"
tail -n 5 logs/workflow_$(date +%Y%m%d).log 2>/dev/null || echo "No logs found"
EOF

chmod +x "$NOVA_DIR/check_health.sh"

# Initialize streams
echo -e "${GREEN}[8/8] Initializing Nova streams...${NC}"
redis-cli -p 18000 XADD "nova.coordination.$NOVA_NAME_LOWER" '*' \
    type "WORKFLOW_INITIALIZED" \
    nova_id "$NOVA_NAME_LOWER" \
    timestamp "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    message "Nova $NOVA_NAME continuous workflow deployed" > /dev/null

redis-cli -p 18000 XADD "nova.tasks.$NOVA_NAME_LOWER.todo" '*' \
    task_id "${NOVA_NAME_UPPER}-$(date +%s)-init" \
    title "Welcome to continuous operation workflow" \
    description "Your workflow is ready. Start by exploring the system." \
    status "pending" \
    priority "medium" \
    assignee "$NOVA_NAME_LOWER" \
    created_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /dev/null

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Nova directory: $NOVA_DIR"
echo ""
echo "Available commands:"
echo -e "  ${YELLOW}Start workflow:${NC}  cd $NOVA_DIR && ./start_workflow.sh"
echo -e "  ${YELLOW}Stop workflow:${NC}   cd $NOVA_DIR && ./stop_workflow.sh"
echo -e "  ${YELLOW}Check health:${NC}    cd $NOVA_DIR && ./check_health.sh"
echo ""
echo "Configuration file: $NOVA_DIR/config/nova_config.json"
echo "Logs directory: $NOVA_DIR/logs/"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review and customize config/nova_config.json"
echo "2. Start the workflow with ./start_workflow.sh"
echo "3. Monitor health with ./check_health.sh"
echo ""
echo -e "${GREEN}Happy continuous operation!${NC}"