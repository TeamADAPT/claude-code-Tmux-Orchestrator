---
allowed-tools: Bash, Read
description: Show task execution history with timing and results
---

# 📜 Task Execution History

## Displaying recent task activity...

!python3 -c "
import redis
import os
from datetime import datetime, timedelta

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'📜 Task History for Nova: {nova_id}')
print('=' * 60)

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Get completed tasks from history stream
history_key = f'nova.tasks.{nova_id}.history'
history = r.xrevrange(history_key, '+', '-', count=10)

if not history:
    print('\\n❌ No task history found')
    print('   Tasks will appear here after execution')
else:
    print(f'\\n📊 Last {len(history)} completed tasks:\\n')
    
    success_count = 0
    total_duration = 0
    
    for task_id, data in history:
        # Parse task data
        task_type = data.get('type', 'unknown')
        status = data.get('status', 'unknown')
        priority = data.get('priority', 'normal')
        started = data.get('started_at', '')
        completed = data.get('completed_at', '')
        duration = float(data.get('duration_ms', 0))
        
        # Status emoji
        status_icon = '✅' if status == 'success' else '❌' if status == 'failed' else '⚠️'
        
        # Priority icon
        priority_icon = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
        
        # Calculate timing
        if duration > 0:
            total_duration += duration
            if status == 'success':
                success_count += 1
                
        duration_str = f'{duration:.0f}ms' if duration < 1000 else f'{duration/1000:.1f}s'
        
        # Format output
        print(f'{status_icon} {priority_icon} {task_type}')
        print(f'   Duration: {duration_str} | Status: {status}')
        
        if completed:
            comp_time = datetime.fromisoformat(completed.replace('Z', '+00:00'))
            age = datetime.now() - comp_time.replace(tzinfo=None)
            if age.total_seconds() < 60:
                age_str = f'{int(age.total_seconds())}s ago'
            elif age.total_seconds() < 3600:
                age_str = f'{int(age.total_seconds()/60)}m ago'
            else:
                age_str = f'{int(age.total_seconds()/3600)}h ago'
            print(f'   Completed: {age_str}')
        
        # Show error if failed
        if status == 'failed' and 'error' in data:
            print(f'   Error: {data[\"error\"][:50]}...')
        
        print()
    
    # Show statistics
    print('\\n📈 Statistics:')
    print(f'   Success Rate: {success_count}/{len(history)} ({success_count/len(history)*100:.0f}%)')
    if total_duration > 0:
        avg_duration = total_duration / len(history)
        avg_str = f'{avg_duration:.0f}ms' if avg_duration < 1000 else f'{avg_duration/1000:.1f}s'
        print(f'   Avg Duration: {avg_str}')

# Check pending tasks
pending = r.xlen(f'nova.tasks.{nova_id}')
if pending > 0:
    print(f'\\n⏳ {pending} tasks pending in queue')
"

## 💡 Tips:
- History is stored in `nova.tasks.<nova_id>.history` stream
- Includes timing, status, and error information
- Use with `/aa:status` for complete task overview