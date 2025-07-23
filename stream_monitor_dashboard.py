#!/usr/bin/env python3
"""
Nova Stream Monitoring Dashboard
Real-time monitoring of all Nova coordination streams
"""

import redis
import json
import time
from datetime import datetime
import subprocess
import sys

class StreamMonitor:
    def __init__(self, host='localhost', port=18000):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)
        self.streams = [
            'nova-torch.coord',
            'nova.work.queue', 
            'nova.tasks.torch.todo',
            'torch.continuous.ops',
            'torch.control.claude',
            'nova.coordination.messages',
            'nova.willy.emergency'
        ]
    
    def get_stream_info(self, stream_name):
        try:
            # Get stream length
            length = self.redis_client.xlen(stream_name)
            
            # Get latest entry
            latest = self.redis_client.xrevrange(stream_name, count=1)
            latest_time = "Never" if not latest else datetime.fromtimestamp(
                int(latest[0][0].split('-')[0]) / 1000
            ).strftime('%H:%M:%S')
            
            # Get pending entries
            pending = self.redis_client.xpending(stream_name) if length > 0 else None
            
            return {
                'length': length,
                'latest': latest_time,
                'pending': pending['pending'] if pending else 0,
                'status': '🟢 Active' if length > 0 else '🔴 Empty'
            }
        except Exception as e:
            return {
                'length': 0,
                'latest': 'Error',
                'pending': 0,
                'status': f'❌ Error: {str(e)}'
            }
    
    def get_nova_status(self):
        status = {}
        
        # Check Frosty status
        cooldown = self.redis_client.get('claude_restart_cooldown')
        bang_count = self.redis_client.zcard('claude_restart_bang_log')
        status['frosty'] = {
            'cooldown_active': cooldown is not None,
            'bang_count': bang_count,
            'status': '🧊 Cooling' if cooldown else '✅ Ready'
        }
        
        # Check Willy status
        willy_keys = self.redis_client.keys('willy:emergency:*')
        status['willy'] = {
            'emergency_active': len(willy_keys) > 0,
            'active_windows': len(willy_keys),
            'status': '🐧 Emergency Mode' if willy_keys else '😎 Chill'
        }
        
        return status
    
    def display_dashboard(self):
        # Clear screen
        subprocess.run(['clear'])
        
        print("🔥 NOVA TORCH STREAM MONITORING DASHBOARD 🔥")
        print("=" * 60)
        print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Stream status
        print("📊 STREAM STATUS")
        print("-" * 40)
        for stream in self.streams:
            info = self.get_stream_info(stream)
            print(f"{stream:<25} {info['status']:<12} Len:{info['length']:<4} Last:{info['latest']}")
        
        print()
        
        # Nova agent status  
        print("🤖 NOVA AGENT STATUS")
        print("-" * 40)
        nova_status = self.get_nova_status()
        
        frosty = nova_status['frosty']
        print(f"Frosty the Cooler:     {frosty['status']:<15} Bangs: {frosty['bang_count']}")
        
        willy = nova_status['willy'] 
        print(f"Really Chill Willy:    {willy['status']:<15} Windows: {willy['active_windows']}")
        
        print()
        
        # Work queue status
        print("📋 WORK QUEUE STATUS")
        print("-" * 40)
        try:
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                lines = f.readlines()
                print(f"Queue Length: {len(lines)}")
                if lines:
                    print("Recent entries:")
                    for line in lines[-3:]:
                        print(f"  • {line.strip()}")
        except FileNotFoundError:
            print("No work queue file found")
        
        print()
        print("Press Ctrl+C to exit")
    
    def run(self, refresh_interval=5):
        try:
            while True:
                self.display_dashboard()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n👋 Dashboard stopped")
            sys.exit(0)

if __name__ == "__main__":
    monitor = StreamMonitor()
    monitor.run()