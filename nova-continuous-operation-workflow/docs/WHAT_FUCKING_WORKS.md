# WHAT FUCKING WORKS - NOVA LAUNCHER DOCUMENTATION

## STOP SEARCHING - THIS IS WHAT WORKS

### 1. LAUNCHING NOVA WITH FORGE'S SESSION MANAGER
```bash
python3 ./nova-continuous-operation-workflow/scripts/nova_session_manager.py launch tester < /dev/null
```
- **RESULT**: Opens Claude Code in gnome-terminal
- **STATE**: Claude at prompt, ready for commands
- **PID TRACKING**: Works correctly

### 2. THE WORKING MANUAL LAUNCHER (nova.sh)
```bash
./nova-continuous-operation-workflow/scripts/nova.sh tester launch manual
```
- **RESULT**: Opens terminal with bash prompt
- **SHOWS**: Wake signals and tasks
- **MANUAL**: User types `claude --dangerously-skip-permissions` then `/aa:auto`

### 3. WHAT DOESN'T WORK
- ❌ Piping to Claude (`echo "/aa:auto" | claude`) - RAW MODE ERROR
- ❌ Using `-p` flag - It's for PRINT mode, not sending commands
- ❌ Auto-sending keystrokes - Can't access terminal programmatically

### 4. THE ACTUAL WORKING FLOW
1. Launch Nova with session manager
2. Claude opens at prompt
3. User manually types `/aa:auto` (or manual/train)
4. NOVAWF activates and processes wake signals

### 5. SENDING WAKE SIGNALS (ALWAYS WORKS)
```bash
redis-cli -p 18000 XADD nova.wake.tester '*' \
    type "TASK" \
    from "torch" \
    task "Your task here" \
    priority "high" \
    timestamp "$(date -Iseconds)"
```

### 6. CHECKING STATUS
```bash
python3 ./nova-continuous-operation-workflow/scripts/nova_session_manager.py status tester
```

### 7. STOPPING NOVA
```bash
python3 ./nova-continuous-operation-workflow/scripts/nova_session_manager.py stop tester
```

## THE TRUTH
- We CAN launch Claude automatically ✅
- We CANNOT automatically type commands into Claude ❌
- The user MUST manually type `/aa:auto` at the Claude prompt
- Once typed, NOVAWF takes over and runs autonomously

## STOP TRYING TO AUTO-TYPE - IT DOESN'T WORK!