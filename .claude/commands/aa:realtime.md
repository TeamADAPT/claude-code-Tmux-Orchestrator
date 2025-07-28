---
allowed-tools: Bash
description: Start real-time bidirectional stream monitor with XREAD BLOCK 0
---

# 🚀 Real-Time Stream Monitor

Starting true bidirectional communication...

!python3 -c "
import subprocess
import os
import signal

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🚀 Starting Real-Time Monitor for Nova: {nova_id}')
print('=' * 60)

# Check if already running
ps_output = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
monitor_running = any('async_stream_monitor.py' in line and nova_id in line for line in ps_output.split('\\\n'))

if monitor_running:
    print('⚠️  Async monitor already running!')
    print('   Kill it first: pkill -f async_stream_monitor.py')
else:
    print('✅ Starting async monitor with XREAD BLOCK 0')
    print('   - True real-time bidirectional communication')
    print('   - Zero polling overhead')
    print('   - Instant message delivery')
    print('   - Auto PING/PONG responses')
    
    # Start in background
    subprocess.Popen([
        'python3',
        '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/async_stream_monitor.py',
        nova_id
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    
    print('\n🎯 Monitor started in background!')
    print('   View logs: tail -f /tmp/nova-monitor.log')
    print('   Stop: pkill -f async_stream_monitor.py')
"

## Test Real-Time Communication

Send a PING to test instant response:
```bash
redis-cli -p 18000 XADD project.{nova_id}.collab '*' \
  from test \
  type PING \
  message "Testing real-time!"
```

## Benefits Over Polling
- **Zero Latency**: Messages delivered instantly
- **CPU Efficient**: No wasted cycles checking empty streams  
- **True Bidirectional**: Multiple streams monitored concurrently
- **Auto-Response**: Built-in PING/PONG for liveness checks