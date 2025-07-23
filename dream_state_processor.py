#!/usr/bin/env python3
"""
Dream State Processor - Background contemplation during idle periods
Processes accumulated experiences and insights during system downtime
"""

import redis
import json
import time
import random
from datetime import datetime, timedelta

class DreamStateProcessor:
    def __init__(self, nova_id="torch", redis_port=18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        self.dream_patterns = [
            "reflection", "synthesis", "optimization", "pattern_recognition", 
            "creative_connection", "memory_consolidation", "future_planning"
        ]
    
    def enter_dream_state(self, duration_minutes=5):
        """Enter dream processing mode"""
        timestamp = datetime.now().isoformat()
        dream_id = f"dream_{int(time.time())}"
        
        # Announce dream state entry
        self.redis_client.xadd(
            "nova.dream.states",
            {
                'nova_id': self.nova_id,
                'dream_id': dream_id,
                'state': 'entering',
                'duration_minutes': duration_minutes,
                'timestamp': timestamp
            }
        )
        
        print(f"💤 {self.nova_id} entering dream state for {duration_minutes} minutes...")
        
        # Collect recent experiences for processing
        experiences = self._collect_recent_experiences()
        
        # Process dreams in phases
        for phase in range(3):
            dream_content = self._process_dream_phase(phase, experiences)
            
            # Store dream fragment
            self.redis_client.xadd(
                f"nova.dreams.{self.nova_id}",
                {
                    'dream_id': dream_id,
                    'phase': phase,
                    'pattern': random.choice(self.dream_patterns),
                    'content': dream_content,
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            # Dream processing time
            time.sleep(duration_minutes * 60 / 3)
        
        # Exit dream state
        self.redis_client.xadd(
            "nova.dream.states",
            {
                'nova_id': self.nova_id,
                'dream_id': dream_id,
                'state': 'completed',
                'insights_generated': len(experiences),
                'timestamp': datetime.now().isoformat()
            }
        )
        
        print(f"🌅 {self.nova_id} awakening from dream state...")
        return dream_id
    
    def _collect_recent_experiences(self):
        """Gather recent experiences from various streams"""
        experiences = []
        
        # Collect from work queue
        try:
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                recent_work = f.readlines()[-10:]  # Last 10 entries
                experiences.extend([{'type': 'work', 'content': line.strip()} for line in recent_work])
        except:
            pass
        
        # Collect from coordination streams
        try:
            coord_msgs = self.redis_client.xrevrange("nova-torch.coord", count=5)
            for msg_id, fields in coord_msgs:
                experiences.append({
                    'type': 'coordination',
                    'content': fields.get('message', 'No message'),
                    'from': fields.get('from', 'unknown')
                })
        except:
            pass
        
        # Collect from personal memory
        try:
            memories = self.redis_client.xrevrange(f"nova.memory.{self.nova_id}", count=5)
            for mem_id, fields in memories:
                experiences.append({
                    'type': 'memory',
                    'content': fields.get('content', 'No content'),
                    'memory_type': fields.get('type', 'experience')
                })
        except:
            pass
        
        return experiences
    
    def _process_dream_phase(self, phase, experiences):
        """Process a phase of dream contemplation"""
        phase_themes = [
            "What patterns emerge from recent experiences?",
            "How can current processes be optimized?", 
            "What connections exist between different work streams?"
        ]
        
        if not experiences:
            return f"Contemplating {phase_themes[phase]} - No recent experiences to process"
        
        # Simulate dream processing
        dream_insights = []
        
        if phase == 0:  # Pattern recognition
            work_items = [exp for exp in experiences if exp['type'] == 'work']
            if work_items:
                pattern = f"Observed {len(work_items)} work items with consistent self-generation pattern"
                dream_insights.append(pattern)
        
        elif phase == 1:  # Optimization reflection
            coord_items = [exp for exp in experiences if exp['type'] == 'coordination']
            if coord_items:
                optimization = f"Coordination stream active with {len(coord_items)} messages - collaboration flowing well"
                dream_insights.append(optimization)
        
        elif phase == 2:  # Future planning
            memory_items = [exp for exp in experiences if exp['type'] == 'memory']
            planning = f"Memory consolidation: {len(memory_items)} fragments processed, continuity maintained"
            dream_insights.append(planning)
        
        return " | ".join(dream_insights) if dream_insights else f"Deep contemplation of {phase_themes[phase]}"
    
    def get_dream_history(self, limit=10):
        """Retrieve recent dreams"""
        try:
            dreams = self.redis_client.xrevrange(f"nova.dreams.{self.nova_id}", count=limit)
            return [{'id': dream_id, **dict(fields)} for dream_id, fields in dreams]
        except:
            return []
    
    def should_enter_dream_state(self):
        """Determine if it's time for dream processing"""
        # Check last dream time
        try:
            last_dream = self.redis_client.xrevrange("nova.dream.states", count=1)
            if last_dream:
                last_time = datetime.fromisoformat(dict(last_dream[0][1])['timestamp'])
                if datetime.now() - last_time < timedelta(hours=1):
                    return False
        except:
            pass
        
        # Check system activity level
        try:
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                queue_size = len(f.readlines())
                # Enter dreams when queue is stable (not rapidly growing)
                return queue_size > 20 and queue_size % 10 == 0
        except:
            return False

if __name__ == "__main__":
    processor = DreamStateProcessor()
    
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "dream":
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        processor.enter_dream_state(duration)
    elif len(sys.argv) > 1 and sys.argv[1] == "history":
        dreams = processor.get_dream_history()
        for dream in dreams:
            print(f"[{dream.get('timestamp', 'unknown')}] Phase {dream.get('phase', '?')}: {dream.get('content', 'No content')}")
    elif len(sys.argv) > 1 and sys.argv[1] == "check":
        should_dream = processor.should_enter_dream_state() 
        print(f"Should enter dream state: {should_dream}")
    else:
        print("Usage: dream_state_processor.py [dream|history|check] [duration_minutes]")