# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview
The Tmux Orchestrator is an AI-powered session management system where Claude acts as the orchestrator for multiple Claude agents across tmux sessions, managing codebases and keeping development moving forward 24/7.

## Key Development Commands

### Core Orchestration Scripts
```bash
# Send messages to Claude agents (primary communication method)
./send-claude-message.sh <session:window> "message content"

# Schedule automated check-ins
./schedule_with_note.sh <minutes> "note for next check" [target_window]

# Monitor tmux sessions programmatically
python3 tmux_utils.py

# Test script functionality
bash -n schedule_with_note.sh  # Syntax check
bash -n send-claude-message.sh  # Syntax check
```

### Essential Tmux Commands for Orchestration
```bash
# List all sessions and windows
tmux list-sessions
tmux list-windows -t <session>

# Capture window content for analysis
tmux capture-pane -t <session:window> -p

# Send keys to specific windows
tmux send-keys -t <session:window> "command" Enter

# Create new windows with proper directory context
tmux new-window -t <session> -n "window-name" -c "/path/to/project"

# Rename windows for better organization
tmux rename-window -t <session:window> "descriptive-name"
```

## High-Level Architecture

### Three-Tier Agent Hierarchy
The system uses a hierarchical structure to manage context window limitations:

```
Orchestrator (You)
├── Project Manager 1 (Quality oversight, task coordination)
│   ├── Developer Agent (Implementation)
│   ├── QA Agent (Testing & verification)
│   └── DevOps Agent (Infrastructure)
└── Project Manager 2 (Multi-project coordination)
    └── Developer Agent (Implementation)
```

### Core Components

#### 1. Communication Layer (`send-claude-message.sh`)
- Handles all inter-agent communication
- Manages timing between message and Enter key
- Supports both window and pane targets
- **Critical**: Always use this script instead of manual tmux commands

#### 2. Scheduling System (`schedule_with_note.sh`)
- Enables autonomous agent operation
- Creates detached background processes
- Supports specific window targeting
- Maintains continuity across sessions

#### 3. Monitoring Utilities (`tmux_utils.py`)
- Provides programmatic tmux session introspection
- Captures window content for analysis
- Generates monitoring snapshots
- Includes safety modes for command execution

#### 4. State Management
- `next_check_note.txt`: Tracks scheduled check-in details
- `LEARNINGS.md`: Accumulates institutional knowledge
- Agent logs: Historical conversation records

## Critical Operating Principles

### Git Safety Protocol (MANDATORY)
Every 30 minutes or before task switches:
```bash
git add -A
git commit -m "Progress: [specific description]"
```

Feature branch workflow:
```bash
git checkout -b feature/[descriptive-name]
# Work on feature
git commit -m "Complete: [feature description]"
git tag stable-[feature]-$(date +%Y%m%d-%H%M%S)
```

### Communication Patterns
- **Hub-and-spoke**: Developers → PM → Orchestrator
- **Structured templates**: STATUS, TASK, ACK messages
- **Escalation protocol**: Max 3 exchanges before escalation
- **Time limits**: Don't stay blocked >10 minutes

### Window Management Best Practices
- Always specify working directory when creating windows: `-c "/path/to/project"`
- Use descriptive naming: `Claude-Frontend`, `Uvicorn-API`, `NextJS-Dev`
- Verify window contents before sending commands
- Check for existing processes before starting new ones

## Agent Deployment Workflow

### Starting a New Project
```bash
# 1. Find and verify project exists
ls -la ~/Coding/ | grep -i "[project-name]"

# 2. Create session with proper directory
PROJECT_PATH="/path/to/project"
tmux new-session -d -s project-name -c "$PROJECT_PATH"

# 3. Set up standard windows
tmux rename-window -t project-name:0 "Claude-Agent"
tmux new-window -t project-name -n "Dev-Server" -c "$PROJECT_PATH"

# 4. Start and brief Claude agent
tmux send-keys -t project-name:0 "claude" Enter
./send-claude-message.sh project-name:0 "Agent briefing and responsibilities"
```

### Creating Project Managers
```bash
# 1. Analyze existing session
tmux list-windows -t [session]

# 2. Create PM window in project directory
PROJECT_PATH=$(tmux display-message -t [session]:0 -p '#{pane_current_path}')
tmux new-window -t [session] -n "Project-Manager" -c "$PROJECT_PATH"

# 3. Brief PM with specific responsibilities
./send-claude-message.sh [session]:[pm-window] "PM briefing with quality standards"
```

## Troubleshooting Common Issues

### Window Directory Problems
**Issue**: Commands run in wrong directory
**Cause**: New windows inherit tmux startup directory, not current session directory
**Solution**: Always use `-c` flag when creating windows

### Agent Communication Failures
**Issue**: Messages not received or Enter sent too quickly
**Cause**: Manual tmux send-keys timing issues
**Solution**: Always use `./send-claude-message.sh` script

### Scheduling Failures
**Issue**: Scheduled check-ins don't run
**Cause**: Target window doesn't exist or wrong window specified
**Solution**: Verify window exists and use correct session:window format

### Process Management
**Issue**: Multiple instances of same service
**Cause**: Not checking for existing processes
**Solution**: Always check window contents before starting services

## Advanced Features

### Cross-Project Intelligence
- Share authentication patterns between projects
- Propagate performance optimizations across codebases
- Coordinate API changes between frontend/backend teams

### Monitoring and Analysis
```python
# Generate comprehensive system snapshot
from tmux_utils import TmuxOrchestrator
orchestrator = TmuxOrchestrator()
snapshot = orchestrator.create_monitoring_snapshot()
```

### Self-Scheduling Protocol
Orchestrators must verify their tmux location before scheduling:
```bash
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}")
./schedule_with_note.sh 30 "oversight check" "$CURRENT_WINDOW"
```

## Security and Safety

### Safety Modes
- `tmux_utils.py` includes confirmation prompts for destructive operations
- Scripts validate target windows before execution
- Git discipline prevents work loss

### Best Practices
- Never run commands without verifying target window
- Always check window contents before sending keys
- Use meaningful commit messages and regular commits
- Test scripts with syntax checkers before execution

## Knowledge Management

### Institutional Learning
- Document all discoveries in `LEARNINGS.md`
- Capture agent conversations before termination
- Tag stable versions before major changes
- Share cross-project insights through orchestrator

### Emergency Recovery
```bash
# Check recent commits
git log --oneline -10

# Recover from issues
git stash
git reset --hard HEAD
git stash pop  # if needed
```

This orchestrator system enables 24/7 autonomous development by Claude agents while maintaining quality standards and preventing work loss through structured communication, scheduling, and safety protocols.