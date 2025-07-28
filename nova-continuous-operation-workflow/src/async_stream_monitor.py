#!/usr/bin/env python3
"""
Async Stream Monitor - True real-time bidirectional communication
Implements XREAD BLOCK 0 with asyncio for continuous monitoring
"""
import asyncio
import redis.asyncio as aioredis
import json
from datetime import datetime
from typing import Dict, List, Optional

class AsyncStreamMonitor:
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.redis = None
        self.running = False
        self.streams = {}
        
    async def connect(self):
        """Initialize async Redis connection"""
        self.redis = await aioredis.from_url('redis://localhost:18000', decode_responses=True)
        print(f"🔌 Connected to Redis for Nova: {self.nova_id}")
        
    async def disconnect(self):
        """Clean up connection"""
        if self.redis:
            await self.redis.aclose()
            
    async def monitor_stream(self, stream_name: str, last_id: str = '$'):
        """Monitor a single stream with XREAD BLOCK"""
        while self.running:
            try:
                # XREAD BLOCK 0 for infinite blocking until data arrives
                result = await self.redis.xread(
                    {stream_name: last_id},
                    block=0  # Block forever until data arrives
                )
                
                if result:
                    for stream, messages in result:
                        for msg_id, data in messages:
                            # Process message
                            await self.handle_message(stream, msg_id, data)
                            # Update position
                            last_id = msg_id
                            
            except Exception as e:
                print(f"❌ Error monitoring {stream_name}: {e}")
                await asyncio.sleep(1)
                
    async def handle_message(self, stream: str, msg_id: str, data: Dict):
        """Process incoming messages"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        if 'collab' in stream:
            sender = data.get('from', 'unknown')
            msg_type = data.get('type', 'MESSAGE')
            message = data.get('message', '')
            print(f"[{timestamp}] 💬 {sender}: {msg_type} - {message}")
            
            # Auto-respond to certain message types
            if msg_type == 'PING':
                await self.send_pong(sender)
                
        elif 'tasks' in stream and stream.endswith(self.nova_id):
            task_type = data.get('type', 'unknown')
            print(f"[{timestamp}] 📥 NEW TASK: {task_type}")
            
            # Could trigger task executor here
            await self.process_task(msg_id, data)
            
        elif 'ecosystem.events' in stream:
            event_type = data.get('type', 'EVENT')
            print(f"[{timestamp}] 🌐 ECOSYSTEM: {event_type}")
            
    async def send_pong(self, to_nova: str):
        """Auto-respond to PING"""
        await self.redis.xadd(f'project.{to_nova}.collab', {
            'from': self.nova_id,
            'type': 'PONG',
            'message': 'Alive and monitoring!',
            'timestamp': datetime.now().isoformat()
        })
        
    async def process_task(self, task_id: str, task_data: Dict):
        """Process incoming task (placeholder for task executor integration)"""
        print(f"   Would process task {task_id}: {task_data.get('type')}")
        
    async def send_heartbeat(self):
        """Send periodic heartbeats"""
        while self.running:
            await self.redis.xadd('nova.ecosystem.events', {
                'type': 'HEARTBEAT',
                'nova_id': self.nova_id,
                'status': 'active',
                'timestamp': datetime.now().isoformat()
            })
            await asyncio.sleep(30)  # Every 30 seconds
            
    async def run(self, streams_to_monitor: Optional[List[str]] = None):
        """Run the async monitor"""
        await self.connect()
        self.running = True
        
        # Default streams
        if streams_to_monitor is None:
            streams_to_monitor = [
                f'project.{self.nova_id}.collab',
                f'nova.tasks.{self.nova_id}',
                'nova.ecosystem.events',
                'project.tester.collab' if self.nova_id == 'torch' else 'project.torch.collab'
            ]
            
        print(f"🚀 Starting async monitor for {len(streams_to_monitor)} streams")
        print(f"   Streams: {streams_to_monitor}")
        print("   Using XREAD BLOCK 0 for true real-time monitoring")
        print("   Press Ctrl+C to stop\n")
        
        # Create tasks for each stream + heartbeat
        tasks = []
        for stream in streams_to_monitor:
            task = asyncio.create_task(self.monitor_stream(stream))
            tasks.append(task)
            
        # Add heartbeat task
        tasks.append(asyncio.create_task(self.send_heartbeat()))
        
        try:
            # Run all tasks concurrently
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            print("\n✋ Shutting down...")
        finally:
            self.running = False
            await self.disconnect()

async def test_bidirectional():
    """Test bidirectional communication"""
    nova_id = 'torch'
    monitor = AsyncStreamMonitor(nova_id)
    
    # Connect
    await monitor.connect()
    
    # Send test message
    await monitor.redis.xadd('project.tester.collab', {
        'from': nova_id,
        'type': 'ASYNC_TEST',
        'message': 'Testing true real-time bidirectional streams!',
        'info': 'Using XREAD BLOCK 0 with asyncio'
    })
    
    print("✅ Sent test message to tester")
    
    # Clean up
    await monitor.disconnect()

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # Run test
        asyncio.run(test_bidirectional())
    else:
        # Run monitor
        nova_id = sys.argv[1] if len(sys.argv) > 1 else 'torch'
        monitor = AsyncStreamMonitor(nova_id)
        
        try:
            asyncio.run(monitor.run())
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")