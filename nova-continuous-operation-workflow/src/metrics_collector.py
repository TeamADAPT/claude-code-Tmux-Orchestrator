#!/usr/bin/env python3
"""
Nova Metrics Collector - Track task velocity and performance metrics
"""
import redis
import time
import json
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Tuple

class MetricsCollector:
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.r = redis.Redis(host='localhost', port=18000, decode_responses=True)
        self.metrics_key = f'nova:metrics:{nova_id}'
        self.velocity_key = f'nova:velocity:{nova_id}'
        
    def collect_velocity_metrics(self) -> Dict:
        """Calculate task processing velocity over different time windows"""
        now = datetime.now()
        windows = {
            '1min': timedelta(minutes=1),
            '5min': timedelta(minutes=5),
            '15min': timedelta(minutes=15),
            '1hour': timedelta(hours=1),
            '24hour': timedelta(days=1)
        }
        
        velocity_data = {}
        
        for window_name, delta in windows.items():
            start_time = now - delta
            start_ts = int(start_time.timestamp() * 1000)
            
            # Count completed tasks in this window
            history = self.r.xrange(
                f'nova.tasks.{self.nova_id}.history',
                min=f'{start_ts}-0',
                max='+'
            )
            
            completed_count = len(history)
            success_count = sum(1 for _, data in history if data.get('status') == 'success')
            failed_count = sum(1 for _, data in history if data.get('status') == 'failed')
            
            # Calculate average duration
            durations = []
            for _, data in history:
                if 'duration_ms' in data:
                    durations.append(int(data['duration_ms']))
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # Tasks per minute rate
            minutes = delta.total_seconds() / 60
            rate = completed_count / minutes if minutes > 0 else 0
            
            velocity_data[window_name] = {
                'completed': completed_count,
                'success': success_count,
                'failed': failed_count,
                'rate_per_minute': round(rate, 2),
                'avg_duration_ms': round(avg_duration, 2),
                'success_rate': round(success_count / completed_count * 100, 1) if completed_count > 0 else 0
            }
        
        # Store current velocity
        self.r.hset(self.velocity_key, 'data', json.dumps(velocity_data))
        self.r.hset(self.velocity_key, 'updated_at', now.isoformat())
        self.r.expire(self.velocity_key, 300)  # 5 minute TTL
        
        return velocity_data
    
    def get_queue_depth_trends(self) -> Dict:
        """Track queue depth over time"""
        queue_key = f'nova.tasks.{self.nova_id}'
        current_depth = self.r.xlen(queue_key)
        
        # Store historical queue depth
        history_key = f'nova:queue_depth:{self.nova_id}'
        now = datetime.now()
        
        # Add current measurement
        self.r.zadd(history_key, {json.dumps({
            'depth': current_depth,
            'timestamp': now.isoformat()
        }): now.timestamp()})
        
        # Keep only last 24 hours
        cutoff = (now - timedelta(days=1)).timestamp()
        self.r.zremrangebyscore(history_key, '-inf', cutoff)
        
        # Get trend data
        trend_data = []
        for item in self.r.zrange(history_key, 0, -1):
            trend_data.append(json.loads(item))
        
        return {
            'current_depth': current_depth,
            'trend': trend_data[-20:] if len(trend_data) > 20 else trend_data  # Last 20 points
        }
    
    def get_task_type_distribution(self) -> Dict:
        """Analyze distribution of task types"""
        # Last 100 tasks
        history = self.r.xrevrange(f'nova.tasks.{self.nova_id}.history', '+', '-', count=100)
        
        type_counts = defaultdict(int)
        type_durations = defaultdict(list)
        
        for _, data in history:
            task_type = data.get('type', 'unknown')
            type_counts[task_type] += 1
            
            if 'duration_ms' in data:
                type_durations[task_type].append(int(data['duration_ms']))
        
        distribution = {}
        for task_type, count in type_counts.items():
            durations = type_durations[task_type]
            distribution[task_type] = {
                'count': count,
                'percentage': round(count / len(history) * 100, 1),
                'avg_duration_ms': round(sum(durations) / len(durations), 2) if durations else 0
            }
        
        return distribution
    
    def get_performance_score(self) -> int:
        """Calculate overall performance score (0-100)"""
        velocity = self.collect_velocity_metrics()
        
        # Factors for score calculation
        factors = []
        
        # Success rate (40% weight)
        success_rate = velocity['5min']['success_rate']
        factors.append(success_rate * 0.4)
        
        # Processing rate (30% weight) - normalize to 0-100
        rate = velocity['5min']['rate_per_minute']
        normalized_rate = min(rate * 10, 100)  # 10 tasks/min = 100%
        factors.append(normalized_rate * 0.3)
        
        # Queue depth (20% weight) - lower is better
        queue_depth = self.r.xlen(f'nova.tasks.{self.nova_id}')
        depth_score = max(0, 100 - queue_depth * 5)  # Each pending task reduces score by 5
        factors.append(depth_score * 0.2)
        
        # Response time (10% weight) - faster is better
        avg_duration = velocity['5min']['avg_duration_ms']
        if avg_duration > 0:
            time_score = max(0, 100 - (avg_duration / 100))  # 10s = 0 score
        else:
            time_score = 100
        factors.append(time_score * 0.1)
        
        return int(sum(factors))
    
    def publish_metrics(self):
        """Publish metrics to ecosystem events stream"""
        metrics = {
            'nova_id': self.nova_id,
            'type': 'METRICS_UPDATE',
            'timestamp': datetime.now().isoformat(),
            'velocity': self.collect_velocity_metrics(),
            'queue_trends': self.get_queue_depth_trends(),
            'task_distribution': self.get_task_type_distribution(),
            'performance_score': self.get_performance_score()
        }
        
        # Publish to ecosystem events
        self.r.xadd('nova.ecosystem.events', {
            'type': 'METRICS_UPDATE',
            'nova_id': self.nova_id,
            'data': json.dumps(metrics)
        })
        
        return metrics
    
    def run_continuous(self, interval: int = 60):
        """Run metrics collection continuously"""
        print(f"📊 Metrics Collector started for Nova: {self.nova_id}")
        print(f"   Publishing metrics every {interval} seconds")
        
        while True:
            try:
                metrics = self.publish_metrics()
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Metrics published")
                print(f"  Performance Score: {metrics['performance_score']}/100")
                print(f"  5min Rate: {metrics['velocity']['5min']['rate_per_minute']} tasks/min")
                print(f"  Queue Depth: {metrics['queue_trends']['current_depth']}")
                
            except Exception as e:
                print(f"❌ Error collecting metrics: {e}")
            
            time.sleep(interval)

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python3 metrics_collector.py <nova_id> [interval]")
        sys.exit(1)
    
    nova_id = sys.argv[1]
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    
    collector = MetricsCollector(nova_id)
    collector.run_continuous(interval)