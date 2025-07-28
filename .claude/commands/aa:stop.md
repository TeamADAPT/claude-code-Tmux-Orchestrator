---
allowed-tools: Bash, mcp__dragonflydb__stream_publish
description: Stop the NOVAWF workflow completely
---

# Stop Workflow

I'll stop the NOVAWF workflow process.

!python3 -c "
import redis
import os
import signal
import psutil

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Send stop signal via stream
r.xadd('nova.coordination.torch', {
    'type': 'CONTROL_STOP',
    'command': '/stop',
    'from': 'chase',
    'reason': 'USER_REQUESTED_STOP'
})

print('📨 Stop signal sent to workflow')

# Find and kill the process
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    try:
        if proc.info['cmdline'] and 'main.py' in ' '.join(proc.info['cmdline']) and 'torch' in ' '.join(proc.info['cmdline']):
            print(f'🛑 Stopping workflow process PID: {proc.info[\"pid\"]}')
            proc.terminate()
            proc.wait(timeout=5)
            print('✅ Workflow stopped successfully')
            break
    except:
        pass
else:
    print('⚠️  No running workflow process found')

# Clear workflow state
r.delete('workflow:state:torch')
print('🗑️  Workflow state cleared')
"

The workflow has been stopped. Use `/aa:auto` to restart it.