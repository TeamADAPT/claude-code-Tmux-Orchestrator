# NOVA LAUNCHER - WORKING SOLUTION

## ✅ CONFIRMED WORKING SCRIPT: nova.sh

**Location**: `/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/scripts/nova.sh`

### What Makes This Work:
1. **NO PIPING TO CLAUDE** - Avoids raw mode errors
2. **Proper gnome-terminal syntax** - Uses `--` separator
3. **Shows wake signals and tasks** - Full context on startup
4. **Gives bash prompt** - User manually starts Claude
5. **Tracks session state** - Like Forge's approach

### Usage:
```bash
# Launch Nova
./nova.sh <nova_id> launch <mode>

# Examples:
./nova.sh echo launch manual
./nova.sh torch launch auto
./nova.sh forge launch train

# Check status
./nova.sh echo status

# Stop Nova
./nova.sh echo stop
```

### What Happens:
1. Opens gnome-terminal with Nova's profile directory
2. Shows all wake signals and pending tasks
3. Sets environment variables (NOVA_ID, CLAUDE_CONFIG_DIR)
4. Gives you a bash prompt
5. You manually run: `claude --dangerously-skip-permissions`
6. Then type: `/aa:manual` (or auto/train)

### Key Code Section:
```bash
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
    
    # Start interactive bash
    bash
    "
```

## ❌ What DOESN'T Work:
- Piping commands to Claude (causes raw mode errors)
- Using `-e` flag with gnome-terminal (deprecated)
- Auto-sending commands with echo/sleep
- Using `script` command workarounds

## 📋 Terminal Output Example:
```
🔥 Nova echo Ready!
====================

Profile: /nfs/novas/profiles/echo
Mode: manual

📬 Wake Signals:
[Lists all wake signals with timestamps and tasks]

📋 Pending Tasks:
[Shows tasks from nova:tasks:echo queue]

💡 Instructions:
1. Run: claude --dangerously-skip-permissions
2. Type: /aa:manual

x@adapt:/nfs/novas/profiles/echo$ 
```

## 🚀 Nova-to-Nova Collaboration:
Novas can launch each other:
```bash
# From Torch, launch Echo
./nova.sh echo launch manual

# Send wake signal
redis-cli -p 18000 XADD nova.wake.echo '*' \
    type "TASK" \
    from "torch" \
    task "Collaborate on project X" \
    priority "high" \
    timestamp "$(date -Iseconds)"
```

## 🔧 Session Management:
The script creates these files in Nova profile:
- `nova.terminal_pid` - Terminal process ID
- `nova.last_launch` - Timestamp of last launch
- `nova.status` - JSON status file

## ⚠️ IMPORTANT:
**ALWAYS USE THIS SCRIPT** - It's the only one that reliably works without raw mode errors!