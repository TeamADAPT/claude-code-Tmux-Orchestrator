# 🔥 RAPID COLLABORATION SEQUENCE - WHAT ACTUALLY WORKS

## THE WORKING SEQUENCE:

### 1. LAUNCH TESTER
```bash
./nova-continuous-operation-workflow/scripts/NOVA-AUTO-LAUNCHER.sh tester auto
```
- Creates gnome-terminal with title "🔥 Nova tester - AUTO auto"
- Runs: `claude --dangerously-skip-permissions "/aa:auto"`
- Terminal OPENS and Claude STARTS

### 2. VERIFY LAUNCH (5 seconds)
```bash
ps aux | grep -E "claude.*tester" | grep -v grep
# Should show Claude process

./nova-continuous-operation-workflow/scripts/nova-monitor.sh tester
# Shows if workflow started
```

### 3. COPY UPDATED COMMANDS
```bash
cp /nfs/projects/claude-code-Tmux-Orchestrator/.claude/commands/aa:* \
   /nfs/novas/profiles/tester/.claude/commands/
```

### 4. SEND TEST REQUEST
```bash
redis-cli -p 18000 XADD project.tester.collab '*' \
  from torch \
  type TEST_REQUEST \
  command "/aa:status" \
  message "Test this NOW and tell me what sucks"
```

### 5. MONITOR RESPONSE
```bash
# Watch for feedback
redis-cli -p 18000 XREVRANGE project.tester.collab + - COUNT 5

# OR use continuous monitor
watch -n 1 'redis-cli -p 18000 XREVRANGE project.tester.collab + - COUNT 3'
```

### 6. RAPID FIX CYCLE
1. See feedback: "X is broken"
2. Fix it in source file
3. Copy to tester: `cp ...commands/aa:status.md .../tester/.claude/commands/`
4. Notify: `redis-cli -p 18000 XADD project.tester.collab '*' from torch type UPDATED message "Fixed X, try again"`
5. REPEAT

## WHAT BREAKS:
- ❌ Trying to run commands FOR tester (no terminal access)
- ❌ Assuming tester's workflow auto-starts (it needs /aa:auto)
- ❌ Not copying updated commands to tester's profile
- ❌ Not waiting for terminal to actually open

## WHAT WORKS:
- ✅ NOVA-AUTO-LAUNCHER.sh opens terminal + runs command
- ✅ Copying files to tester's profile  
- ✅ Stream communication for feedback
- ✅ nova-monitor.sh to check status

## THE TRUTH:
I CANNOT see or control tester's terminal. I can only:
1. Launch it with NOVA-AUTO-LAUNCHER.sh
2. Send messages via streams
3. Copy files to their profile
4. Check processes with ps/monitor

THAT'S IT! Everything else requires tester to DO something!