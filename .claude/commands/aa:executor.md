---
allowed-tools: Bash
description: Start the task executor to process real tasks
---

# ⚡ Task Executor Control

Starting the task execution engine...

!python3 -c "
import os
import subprocess
import signal

nova_id = os.environ.get('NOVA_ID', 'unknown')
print(f'⚡ Task Executor for Nova: {nova_id}')

# Check if already running
ps_output = subprocess.run(['ps', 'aux'], capture_output=True, text=True).stdout
executor_running = any(f'task_executor.py.*{nova_id}' in line for line in ps_output.split('\\n'))

if executor_running:
    print('❌ Task executor already running!')
    print('   Use pkill -f task_executor.py to stop it first')
else:
    print('🚀 Starting task executor...')
    
    # Start in background
    subprocess.Popen([
        'python3',
        '/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/task_executor.py',
        nova_id
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    
    print('✅ Task executor started!')
    print('   - Processing tasks from nova.tasks.' + nova_id)
    print('   - Results go to nova.tasks.' + nova_id + '.history')
    print('   - Monitor with /aa:history')
"

## Test it!

Send a test task:
```bash
redis-cli -p 18000 XADD nova.tasks.{nova_id} '*' \
  type EXECUTE_COMMAND \
  command "echo Hello from task executor!" \
  priority high
```