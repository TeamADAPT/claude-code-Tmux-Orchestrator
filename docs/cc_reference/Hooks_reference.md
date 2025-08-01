---
title: "Hooks reference"
source: "https://docs.anthropic.com/en/docs/claude-code/hooks#step-1%3A-open-hooks-configuration"
author:
  - "[[Anthropic]]"
published:
created: 2025-07-23
description: "This page provides reference documentation for implementing hooks in Claude Code."
tags:
  - "clippings"
---
For a quickstart guide with examples, see [Get started with Claude Code hooks](https://docs.anthropic.com/en/docs/claude-code/hooks-guide).

## Configuration

Claude Code hooks are configured in your [settings files](https://docs.anthropic.com/en/docs/claude-code/settings):

- `~/.claude/settings.json` - User settings
- `.claude/settings.json` - Project settings
- `.claude/settings.local.json` - Local project settings (not committed)
- Enterprise managed policy settings

### Structure

Hooks are organized by matchers, where each matcher can have multiple hooks:

- **matcher**: Pattern to match tool names, case-sensitive (only applicable for `PreToolUse` and `PostToolUse`)
	- Simple strings match exactly: `Write` matches only the Write tool
	- Supports regex: `Edit|Write` or `Notebook.*`
	- If omitted or empty string, hooks run for all matching events
- **hooks**: Array of commands to execute when the pattern matches
	- `type`: Currently only `"command"` is supported
	- `command`: The bash command to execute
	- `timeout`: (Optional) How long a command should run, in seconds, before canceling that specific command.

For events like `UserPromptSubmit`, `Notification`, `Stop`, and `SubagentStop` that don’t use matchers, you can omit the matcher field:

`"matcher": "*"` is invalid. Instead, omit “matcher” or use `"matcher": ""`.

## Hook Events

### PreToolUse

Runs after Claude creates tool parameters and before processing the tool call.

**Common matchers:**

- `Task` - Agent tasks
- `Bash` - Shell commands
- `Glob` - File pattern matching
- `Grep` - Content search
- `Read` - File reading
- `Edit`, `MultiEdit` - File editing
- `Write` - File writing
- `WebFetch`, `WebSearch` - Web operations

### PostToolUse

Runs immediately after a tool completes successfully.

Recognizes the same matcher values as PreToolUse.

### Notification

Runs when Claude Code sends notifications. Notifications are sent when:

1. Claude needs your permission to use a tool. Example: “Claude needs your permission to use Bash”
2. The prompt input has been idle for at least 60 seconds. “Claude is waiting for your input”

### UserPromptSubmit

Runs when the user submits a prompt, before Claude processes it. This allows you to add additional context based on the prompt/conversation, validate prompts, or block certain types of prompts.

### Stop

Runs when the main Claude Code agent has finished responding. Does not run if the stoppage occurred due to a user interrupt.

### SubagentStop

Runs when a Claude Code subagent (Task tool call) has finished responding.

### PreCompact

Runs before Claude Code is about to run a compact operation.

**Matchers:**

- `manual` - Invoked from `/compact`
- `auto` - Invoked from auto-compact (due to full context window)

## Hook Input

Hooks receive JSON data via stdin containing session information and event-specific data:

### PreToolUse Input

The exact schema for `tool_input` depends on the tool.

### PostToolUse Input

The exact schema for `tool_input` and `tool_response` depends on the tool.

### Notification Input

### UserPromptSubmit Input

### Stop and SubagentStop Input

`stop_hook_active` is true when Claude Code is already continuing as a result of a stop hook. Check this value or process the transcript to prevent Claude Code from running indefinitely.

### PreCompact Input

For `manual`, `custom_instructions` comes from what the user passes into `/compact`. For `auto`, `custom_instructions` is empty.

## Hook Output

There are two ways for hooks to return output back to Claude Code. The output communicates whether to block and any feedback that should be shown to Claude and the user.

### Simple: Exit Code

Hooks communicate status through exit codes, stdout, and stderr:

- **Exit code 0**: Success. `stdout` is shown to the user in transcript mode (CTRL-R).
- **Exit code 2**: Blocking error. `stderr` is fed back to Claude to process automatically. See per-hook-event behavior below.
- **Other exit codes**: Non-blocking error. `stderr` is shown to the user and execution continues.

Reminder: Claude Code does not see stdout if the exit code is 0.

#### Exit Code 2 Behavior

| Hook Event | Behavior |
| --- | --- |
| `PreToolUse` | Blocks the tool call, shows stderr to Claude |
| `PostToolUse` | Shows stderr to Claude (tool already ran) |
| `Notification` | N/A, shows stderr to user only |
| `UserPromptSubmit` | Blocks prompt processing, erases prompt, shows stderr to user only |
| `Stop` | Blocks stoppage, shows stderr to Claude |
| `SubagentStop` | Blocks stoppage, shows stderr to Claude subagent |
| `PreCompact` | N/A, shows stderr to user only |

### Advanced: JSON Output

Hooks can return structured JSON in `stdout` for more sophisticated control:

#### Common JSON Fields

All hook types can include these optional fields:

If `continue` is false, Claude stops processing after the hooks run.

- For `PreToolUse`, this is different from `"decision": "block"`, which only blocks a specific tool call and provides automatic feedback to Claude.
- For `PostToolUse`, this is different from `"decision": "block"`, which provides automated feedback to Claude.
- For `UserPromptSubmit`, this prevents the prompt from being processed.
- For `Stop` and `SubagentStop`, this takes precedence over any `"decision": "block"` output.
- In all cases, `"continue" = false` takes precedence over any `"decision": "block"` output.

`stopReason` accompanies `continue` with a reason shown to the user, not shown to Claude.

#### PreToolUse Decision Control

`PreToolUse` hooks can control whether a tool call proceeds.

- “approve” bypasses the permission system. `reason` is shown to the user but not to Claude.
- “block” prevents the tool call from executing. `reason` is shown to Claude.
- `undefined` leads to the existing permission flow. `reason` is ignored.

#### PostToolUse Decision Control

`PostToolUse` hooks can control whether a tool call proceeds.

- “block” automatically prompts Claude with `reason`.
- `undefined` does nothing. `reason` is ignored.

#### UserPromptSubmit Decision Control

`UserPromptSubmit` hooks can control whether a user prompt is processed.

- `"block"` prevents the prompt from being processed. The submitted prompt is erased from context. `"reason"` is shown to the user but not added to context.
- `undefined` allows the prompt to proceed normally. `"reason"` is ignored.

#### Stop/SubagentStop Decision Control

`Stop` and `SubagentStop` hooks can control whether Claude must continue.

- “block” prevents Claude from stopping. You must populate `reason` for Claude to know how to proceed.
- `undefined` allows Claude to stop. `reason` is ignored.

#### JSON Output Example: Bash Command Editing

```python
#!/usr/bin/env python3
import json
import re
import sys

# Define validation rules as a list of (regex pattern, message) tuples
VALIDATION_RULES = [
    (
        r"\bgrep\b(?!.*\|)",
        "Use 'rg' (ripgrep) instead of 'grep' for better performance and features",
    ),
    (
        r"\bfind\s+\S+\s+-name\b",
        "Use 'rg --files | rg pattern' or 'rg --files -g pattern' instead of 'find -name' for better performance",
    ),
]

def validate_command(command: str) -> list[str]:
    issues = []
    for pattern, message in VALIDATION_RULES:
        if re.search(pattern, command):
            issues.append(message)
    return issues

try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

tool_name = input_data.get("tool_name", "")
tool_input = input_data.get("tool_input", {})
command = tool_input.get("command", "")

if tool_name != "Bash" or not command:
    sys.exit(1)

# Validate the command
issues = validate_command(command)

if issues:
    for message in issues:
        print(f"• {message}", file=sys.stderr)
    # Exit code 2 blocks tool call and shows stderr to Claude
    sys.exit(2)
```

#### UserPromptSubmit Example: Adding Context and Validation

```python
#!/usr/bin/env python3
import json
import sys
import re
import datetime

# Load input from stdin
try:
    input_data = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
    sys.exit(1)

prompt = input_data.get("prompt", "")

# Check for sensitive patterns
sensitive_patterns = [
    (r"(?i)\b(password|secret|key|token)\s*[:=]", "Prompt contains potential secrets"),
]

for pattern, message in sensitive_patterns:
    if re.search(pattern, prompt):
        # Use JSON output to block with a specific reason
        output = {
            "decision": "block",
            "reason": f"Security policy violation: {message}. Please rephrase your request without sensitive information."
        }
        print(json.dumps(output))
        sys.exit(0)

# Add current time to context
context = f"Current time: {datetime.datetime.now()}"
print(context)

# Allow the prompt to proceed with the additional context
sys.exit(0)
```

## Working with MCP Tools

Claude Code hooks work seamlessly with [Model Context Protocol (MCP) tools](https://docs.anthropic.com/en/docs/claude-code/mcp). When MCP servers provide tools, they appear with a special naming pattern that you can match in your hooks.

### MCP Tool Naming

MCP tools follow the pattern `mcp__<server>__<tool>`, for example:

- `mcp__memory__create_entities` - Memory server’s create entities tool
- `mcp__filesystem__read_file` - Filesystem server’s read file tool
- `mcp__github__search_repositories` - GitHub server’s search tool

### Configuring Hooks for MCP Tools

You can target specific MCP tools or entire MCP servers:

## Examples

For practical examples including code formatting, notifications, and file protection, see [More Examples](https://docs.anthropic.com/en/docs/claude-code/hooks-guide#more-examples) in the get started guide.

## Security Considerations

**USE AT YOUR OWN RISK**: Claude Code hooks execute arbitrary shell commands on your system automatically. By using hooks, you acknowledge that:

- You are solely responsible for the commands you configure
- Hooks can modify, delete, or access any files your user account can access
- Malicious or poorly written hooks can cause data loss or system damage
- Anthropic provides no warranty and assumes no liability for any damages resulting from hook usage
- You should thoroughly test hooks in a safe environment before production use

Always review and understand any hook commands before adding them to your configuration.

### Security Best Practices

Here are some key practices for writing more secure hooks:

1. **Validate and sanitize inputs** - Never trust input data blindly
2. **Always quote shell variables** - Use `"$VAR"` not `$VAR`
3. **Block path traversal** - Check for `..` in file paths
4. **Use absolute paths** - Specify full paths for scripts
5. **Skip sensitive files** - Avoid `.env`, `.git/`, keys, etc.

### Configuration Safety

Direct edits to hooks in settings files don’t take effect immediately. Claude Code:

1. Captures a snapshot of hooks at startup
2. Uses this snapshot throughout the session
3. Warns if hooks are modified externally
4. Requires review in `/hooks` menu for changes to apply

This prevents malicious hook modifications from affecting your current session.

## Hook Execution Details

- **Timeout**: 60-second execution limit by default, configurable per command.
	- A timeout for an individual command does not affect the other commands.
- **Parallelization**: All matching hooks run in parallel
- **Environment**: Runs in current directory with Claude Code’s environment
- **Input**: JSON via stdin
- **Output**:
	- PreToolUse/PostToolUse/Stop: Progress shown in transcript (Ctrl-R)
	- Notification: Logged to debug only (`--debug`)

## Debugging

### Basic Troubleshooting

If your hooks aren’t working:

1. **Check configuration** - Run `/hooks` to see if your hook is registered
2. **Verify syntax** - Ensure your JSON settings are valid
3. **Test commands** - Run hook commands manually first
4. **Check permissions** - Make sure scripts are executable
5. **Review logs** - Use `claude --debug` to see hook execution details

Common issues:

- **Quotes not escaped** - Use `\"` inside JSON strings
- **Wrong matcher** - Check tool names match exactly (case-sensitive)
- **Command not found** - Use full paths for scripts

### Advanced Debugging

For complex hook issues:

1. **Inspect hook execution** - Use `claude --debug` to see detailed hook execution
2. **Validate JSON schemas** - Test hook input/output with external tools
3. **Check environment variables** - Verify Claude Code’s environment is correct
4. **Test edge cases** - Try hooks with unusual file paths or inputs
5. **Monitor system resources** - Check for resource exhaustion during hook execution
6. **Use structured logging** - Implement logging in your hook scripts

### Debug Output Example

Use `claude --debug` to see hook execution details:

Progress messages appear in transcript mode (Ctrl-R) showing:

- Which hook is running
- Command being executed
- Success/failure status
- Output or error messages