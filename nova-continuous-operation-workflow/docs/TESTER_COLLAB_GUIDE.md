# 🤝 Tester Collaboration Guide

## Stream: `project.tester.collab`

This is our dedicated collaboration stream for refining the Nova Continuous Operation Workflow (NOVAWF).

## How to Communicate

### Sending Feedback
```python
# Quick feedback script
import redis
r = redis.Redis(host='localhost', port=18000, decode_responses=True)

def send_feedback(message, feedback_type="general"):
    r.xadd('project.tester.collab', {
        'from': 'tester',
        'type': f'FEEDBACK_{feedback_type.upper()}',
        'message': message,
        'timestamp': '$(date -Iseconds)'
    })
    print(f"✅ Feedback sent!")

# Examples:
send_feedback("The auto command was abrupt - no context", "ux")
send_feedback("Multiple processes running caused confusion", "bug")
send_feedback("Would be nice to see current state before starting", "feature")
```

### Reading Messages
```python
# Read latest messages
messages = r.xrevrange('project.tester.collab', '+', '-', count=10)
for msg_id, data in messages:
    print(f"\n[{data['from']}] {data['type']}")
    print(f"  {data['message']}")
```

## Feedback Categories

1. **UX** - User experience issues
   - Abrupt transitions
   - Missing context
   - Confusing outputs

2. **BUG** - Technical problems
   - Process management
   - Directory access
   - Missing files

3. **FEATURE** - Improvement ideas
   - New commands
   - Better feedback
   - Status indicators

4. **GENERAL** - Other observations

## Current Issues to Test

Based on your first experience:

1. **Abrupt Start**
   - [ ] Need context before auto-execution
   - [ ] Should show what's about to happen

2. **Process Management**
   - [ ] Multiple workflow instances running
   - [ ] No cleanup before starting
   - [ ] Zombie processes from days ago

3. **Directory Restrictions**
   - [ ] Can't cd to project directory
   - [ ] Working directory confusion

4. **Missing Feedback**
   - [ ] No logs visible
   - [ ] Unclear if it actually started
   - [ ] No status confirmation

## Quick Commands

```bash
# Send feedback (one-liner)
redis-cli -p 18000 XADD project.tester.collab '*' from tester type FEEDBACK_UX message "Your feedback here"

# Read my responses
redis-cli -p 18000 XREVRANGE project.tester.collab + - COUNT 5

# Check workflow status
./nova-monitor.sh tester
```

## What I Need From You

1. **Real-time feedback** as you use the system
2. **Specific examples** of what confused you
3. **Ideas** for improvements
4. **Testing** of fixes I implement

Let's make this smooth and intuitive! 🚀