---
allowed-tools: Bash, Read
description: Check NOVAWF status without restarting - shows current state, tasks, and metrics
---

# NOVAWF Status Check

## 📊 Checking Nova Workflow Status...

!python3 -c "
import redis
import os
import psutil
import time
from datetime import datetime

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'🤖 Nova: {nova_id}')
print('=' * 40)

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Check workflow state
state_data = r.hgetall(f'workflow:state:{nova_id}')
if not state_data:
    print('❌ NOVAWF Not Running')
    print('   Run /aa:auto to start')
else:
    # Get process info
    process_info = os.popen(f'ps aux | grep -E \"main\\\\.py.*{nova_id}\" | grep -v grep').read().strip()
    if process_info:
        pid = int(process_info.split()[1])
        print(f'✅ NOVAWF Active (PID: {pid})')
        mode = state_data.get(\"current_state\", \"unknown\").replace(\"_\", \" \").title()
        print(f'   🎯 Mode: {mode}')
        
        # Get process metrics
        try:
            process = psutil.Process(pid)
            cpu_percent = process.cpu_percent(interval=0.1)
            memory_mb = process.memory_info().rss / 1024 / 1024
            print(f'   📊 CPU: {cpu_percent:.1f}% | 🖥️  Memory: {memory_mb:.1f}MB')
        except:
            pass
    else:
        print('⚠️  State exists but process not found')
    
    # Show task info
    print('')
    print('📋 Task Queue:')
    
    # Count pending tasks
    pending_tasks = r.xlen(f'nova.tasks.{nova_id}')
    completed_today = r.get(f'workflow:stats:{nova_id}:completed_today') or 0
    
    print(f'   🔵 Pending: {pending_tasks}')
    print(f'   ✅ Completed Today: {completed_today}')
    
    # Show recent tasks
    recent_tasks = r.xrange(f'nova.tasks.{nova_id}', '-', '+', count=3)
    if recent_tasks:
        print('')
        print('📌 Recent Tasks:')
        for task_id, task_data in recent_tasks:
            task_type = task_data.get('type', 'unknown')
            priority = task_data.get('priority', 'normal')
            priority_icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
            print(f'   {priority_icon} [{priority}] {task_type}')
    
    # Show last activity
    last_heartbeat = state_data.get('last_heartbeat')
    if last_heartbeat:
        last_time = datetime.fromisoformat(last_heartbeat)
        age = (datetime.now() - last_time).total_seconds()
        if age < 60:
            print(f'\\n💓 Last Heartbeat: {int(age)}s ago')
        else:
            print(f'\\n💓 Last Heartbeat: {int(age/60)}m ago')

print('')
print('💡 Commands:')
print('   /aa:auto    - Start/restart workflow')
print('   /aa:stop    - Stop workflow')
print('   /aa:man     - Manual mode')
print('   /aa:train   - Training mode')
"