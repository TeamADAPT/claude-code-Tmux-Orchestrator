# Claude Code Slash Commands for NOVAWF

## Overview
This document provides comprehensive documentation on Claude Code slash commands and how to implement NOVAWF control commands (`/man`, `/auto`, `/train`) as native Claude Code commands.

## Claude Code Slash Command System

### How Slash Commands Work
- Slash commands control Claude's behavior during interactive sessions
- Executed by typing `/commandname` in the Claude Code interface
- Can accept arguments: `/commandname argument1 argument2`
- Built-in commands: `/clear`, `/help`, `/review`, `/model`, `/exit`

### Custom Slash Command Locations

1. **Project-Level Commands** (shared with team)
   ```
   .claude/commands/
   ├── man.md          # /man command
   ├── auto.md         # /auto command
   └── train.md        # /train command
   ```

2. **Personal Commands** (available across all projects)
   ```
   ~/.claude/commands/
   └── workflow/
       ├── man.md
       ├── auto.md
       └── train.md
   ```

### Command File Structure

#### Basic Format
```markdown
---
allowed-tools: Bash, Read, Write
description: Brief description of the command
---

# Command prompt content
What Claude should do when this command is executed
```

#### Advanced Features
- **YAML Frontmatter**: Configure metadata and permissions
- **Bash Commands**: Execute with `!` prefix
- **File References**: Include with `@` prefix  
- **Dynamic Arguments**: Access via `$ARGUMENTS`
- **Tool Restrictions**: Specify allowed tools in frontmatter

## NOVAWF Slash Command Implementations

### /man - Enter Manual Mode
Create `.claude/commands/man.md`:

```markdown
---
allowed-tools: Bash, Read, Write, mcp__dragonflydb__stream_publish
description: Enter manual mode - pause NOVAWF autonomous operation
---

# Enter Manual Mode

I'll pause the NOVAWF autonomous operation and enter manual mode.

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /man

The workflow is now in manual mode. I'll wait for your direct instructions.
To resume autonomous operation, use `/auto`.
```

### /auto - Enter Autonomous Mode
Create `.claude/commands/auto.md`:

```markdown
---
allowed-tools: Bash, Read, Write, mcp__dragonflydb__stream_publish
description: Resume autonomous operation - exit manual/training mode
---

# Resume Autonomous Operation

I'll resume the NOVAWF autonomous operation.

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /auto

The workflow has resumed autonomous operation. I'll continue working on tasks automatically.
```

### /train - Enter Training Mode
Create `.claude/commands/train.md`:

```markdown
---
allowed-tools: Bash, Read, Write, Edit, mcp__dragonflydb__stream_publish
description: Enter training mode for adaptive parameter tuning (torch only)
---

# Enter Training Mode

I'll enter training mode for adaptive parameter tuning.

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/control_workflow.py torch /train

Training mode is now active. I can now modify workflow parameters in real-time:
- Use `/train:timing <param> <value>` to adjust timing parameters
- Use `/train:safety <param> <value>` to adjust safety parameters
- Use `/train:workflow <param> <value>` to adjust workflow parameters
- Use `/train:list` to see all tunable parameters
- Use `/auto` to exit training mode
```

### /train:list - List Tunable Parameters
Create `.claude/commands/train/list.md`:

```markdown
---
allowed-tools: Bash
description: List all tunable workflow parameters
---

# List Tunable Parameters

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/training_control.py --list
```

### /train:timing - Adjust Timing Parameters
Create `.claude/commands/train/timing.md`:

```markdown
---
allowed-tools: Bash, Read, Write, Edit
description: Adjust timing parameters (e.g., /train:timing stream_check_interval 30)
---

# Adjust Timing Parameter

Modifying timing parameter: $ARGUMENTS

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/training_control.py torch timing $ARGUMENTS
```

### /train:safety - Adjust Safety Parameters
Create `.claude/commands/train/safety.md`:

```markdown
---
allowed-tools: Bash, Read, Write, Edit
description: Adjust safety parameters (e.g., /train:safety api_rate_limit 50)
---

# Adjust Safety Parameter

Modifying safety parameter: $ARGUMENTS

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/training_control.py torch safety $ARGUMENTS
```

### /train:workflow - Adjust Workflow Parameters
Create `.claude/commands/train/workflow.md`:

```markdown
---
allowed-tools: Bash, Read, Write, Edit
description: Adjust workflow parameters (e.g., /train:workflow momentum_task_threshold 3)
---

# Adjust Workflow Parameter

Modifying workflow parameter: $ARGUMENTS

!python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/training_control.py torch workflow $ARGUMENTS
```

## Advanced Slash Commands

### /workflow:status - Check Workflow Status
Create `.claude/commands/workflow/status.md`:

```markdown
---
allowed-tools: Bash, mcp__dragonflydb__stream_read
description: Check current NOVAWF status and state
---

# Check Workflow Status

I'll check the current workflow status from the coordination stream.

Let me read the latest status from the DragonflyDB stream:

```python
# Read status from nova.coordination.torch stream
# Display current state, phase, metrics
```

@/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/core/workflow_state_manager.py
```

### /workflow:metrics - View Performance Metrics
Create `.claude/commands/workflow/metrics.md`:

```markdown
---
allowed-tools: Bash, mcp__dragonflydb__stream_read
description: View current workflow performance metrics
---

# View Workflow Metrics

I'll retrieve and display the current performance metrics.

```python
# Read from nova.enterprise.metrics.torch
# Display tasks/hour, cycle times, safety status
```
```

## Implementation Steps

1. **Create Command Directory Structure**
   ```bash
   mkdir -p .claude/commands/train
   mkdir -p .claude/commands/workflow
   ```

2. **Implement Base Commands**
   - Create `/man`, `/auto`, `/train` commands
   - Test each command individually

3. **Add Sub-Commands**
   - Implement training sub-commands for parameter tuning
   - Add workflow status and metrics commands

4. **Configure Permissions**
   - Set appropriate `allowed-tools` for each command
   - Consider security implications

5. **Test Integration**
   - Verify commands work within Claude Code sessions
   - Test parameter modifications persist
   - Ensure stream communication works

## Best Practices

### Command Design
- Keep commands focused on single actions
- Use descriptive names and descriptions
- Provide clear feedback to users
- Include usage examples in prompts

### Tool Permissions
- Only allow necessary tools
- Be specific with Bash command patterns
- Consider security implications

### Error Handling
- Check command success/failure
- Provide meaningful error messages
- Include fallback options

### Documentation
- Document all custom commands
- Include examples in command descriptions
- Maintain command changelog

## Integration with NOVAWF

### Stream-Based Control
All NOVAWF commands communicate via DragonflyDB streams:
- Control messages: `nova.coordination.{nova_id}`
- Training parameters: `nova.training.{nova_id}`
- Performance metrics: `nova.enterprise.metrics.{nova_id}`

### State Synchronization
- Commands update workflow state immediately
- Changes persist across sessions
- Git integration for training mode versioning

### Safety Considerations
- Manual mode preserves safety systems
- Training mode includes rollback mechanisms
- All mode changes are logged

## Future Enhancements

### Dynamic Command Generation
- Auto-generate commands from workflow states
- Create task-specific command sets
- Build context-aware command suggestions

### Cross-Nova Commands
- `/nova:echo <message>` - Send to Echo
- `/nova:forge <command>` - Coordinate with Forge
- `/nova:broadcast <message>` - Message all Novas

### Workflow Templates
- `/workflow:template <name>` - Load workflow template
- `/workflow:save <name>` - Save current configuration
- `/workflow:share <nova>` - Share with another Nova

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Claude Code Integration v1.0