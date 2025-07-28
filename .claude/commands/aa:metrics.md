---
allowed-tools: Bash
description: View task velocity metrics and performance score
---

# 📊 Nova Performance Metrics

Analyzing your task processing velocity...

!python3 -c "
import sys
import os
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src')
from metrics_collector import MetricsCollector

nova_id = os.environ.get('NOVA_ID', 'unknown')
collector = MetricsCollector(nova_id)

print(f'📊 Performance Metrics for Nova: {nova_id}')
print('=' * 60)

# Collect fresh metrics
velocity = collector.collect_velocity_metrics()
queue_trends = collector.get_queue_depth_trends()
task_dist = collector.get_task_type_distribution()
score = collector.get_performance_score()

# Performance Score
print(f'\n🎯 Performance Score: {score}/100')
if score >= 80:
    print('   ⭐ Excellent performance!')
elif score >= 60:
    print('   ✅ Good performance')
elif score >= 40:
    print('   ⚠️  Performance could be improved')
else:
    print('   ❌ Performance needs attention')

# Velocity Metrics
print('\n📈 Task Processing Velocity:')
for window, data in velocity.items():
    print(f'\n  {window}:')
    print(f'    Completed: {data[\"completed\"]} tasks')
    print(f'    Rate: {data[\"rate_per_minute\"]} tasks/minute')
    print(f'    Success Rate: {data[\"success_rate\"]}%')
    if data['avg_duration_ms'] > 0:
        print(f'    Avg Duration: {data[\"avg_duration_ms\"]}ms')

# Queue Status
print(f'\n📥 Queue Status:')
print(f'  Current Depth: {queue_trends[\"current_depth\"]} pending tasks')

if queue_trends['trend']:
    recent = queue_trends['trend'][-5:]
    print(f'  Recent Trend: ', end='')
    for point in recent:
        print(f'{point[\"depth\"]} ', end='')
    print()

# Task Distribution
if task_dist:
    print('\n📋 Task Type Distribution (last 100):')
    for task_type, info in sorted(task_dist.items(), key=lambda x: x[1]['count'], reverse=True):
        print(f'  {task_type}: {info[\"count\"]} ({info[\"percentage\"]}%)')
        if info['avg_duration_ms'] > 0:
            print(f'    Avg time: {info[\"avg_duration_ms\"]}ms')
"

## Start Metrics Collector

To enable continuous metrics collection:
```bash
python3 /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/src/metrics_collector.py {nova_id} &
```

## Tips:
- Metrics update every 60 seconds
- Performance score factors: success rate, processing speed, queue depth, response time
- Monitor trends with `/aa:monitor` for real-time updates