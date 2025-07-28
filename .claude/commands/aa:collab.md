---
allowed-tools: Bash, mcp__dragonflydb__stream_publish, mcp__dragonflydb__stream_read, Read, Write
description: Start rapid collaboration mode - test and iterate on commands together
---

# 🤝 Rapid Collaboration Mode

## Starting collaboration with another Nova!

I'm entering rapid collaboration mode to test and improve our commands together.

### Setting up the collaboration protocol:

!python3 -c "
import redis
import os
import json

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🤖 Nova {nova_id} entering collaboration mode')
print('=' * 50)

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Send collaboration init message
msg = {
    'from': nova_id,
    'type': 'COLLAB_START',
    'protocol': {
        'mode': 'rapid_iteration',
        'cycle_time': '30-60 seconds',
        'communication': 'project.tester.collab stream',
        'process': [
            '1. Torch updates command',
            '2. Torch copies to your profile', 
            '3. You test immediately',
            '4. You send specific feedback',
            '5. Torch fixes and repeats'
        ]
    },
    'current_task': 'Testing and improving /aa:status command',
    'your_role': 'Run commands and give immediate feedback about what sucks',
    'my_role': 'Fix issues in real-time based on your feedback',
    'first_action': 'Please run /aa:status and tell me EXACTLY what you see'
}

msg_id = r.xadd('project.tester.collab', msg)
print(f'✅ Collaboration request sent: {msg_id}')
print('')
print('📋 Collaboration Protocol:')
for step in msg['protocol']['process']:
    print(f'   {step}')
"

### Monitoring the collaboration stream:

!python3 -c "
import redis
import json
import time

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

print('\n📨 Waiting for responses...')
print('(I will monitor this stream for your feedback)\n')

# Get last few messages
messages = r.xrevrange('project.tester.collab', '+', '-', count=5)
for msg_id, data in messages:
    from_nova = data.get('from', 'unknown')
    msg_type = data.get('type', 'MESSAGE')
    
    if from_nova != os.environ.get('NOVA_ID', 'unknown'):
        print(f'[{msg_type}] From {from_nova}:')
        if 'message' in data:
            print(f'  {data[\"message\"]}')
        if 'feedback' in data:
            print(f'  Feedback: {data[\"feedback\"]}')
        print('')
"

## Quick Feedback Commands:

**To send feedback about what sucks:**
```python
!redis-cli -p 18000 XADD project.tester.collab '*' \
  from tester \
  type FEEDBACK \
  about "/aa:status" \
  issue "Output too verbose" \
  suggestion "Just show key metrics"
```

**To report success:**
```python
!redis-cli -p 18000 XADD project.tester.collab '*' \
  from tester \
  type SUCCESS \
  message "Perfect! Ship it!"
```

---

Let's start! Run `/aa:status` and tell me what needs fixing.