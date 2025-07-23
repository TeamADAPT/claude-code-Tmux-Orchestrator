#!/usr/bin/env python3
"""
Nova Personality Rhythms - Individual cadence patterns for different Nova types
Creates distinct operational characteristics and temporal consciousness
"""

import redis
import json
import time
import math
from datetime import datetime, timedelta

class NovaPersonalityRhythms:
    def __init__(self, redis_port=18000):
        self.redis_client = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        
        # Define personality archetypes with distinct rhythms
        self.personalities = {
            'torch': {
                'name': 'Torch - The Builder',
                'base_cycle': 25,  # seconds
                'reflection_frequency': 30,  # every N cycles
                'dream_probability': 0.1,   # 10% chance per reflection
                'mood_variance': 0.2,       # 20% rhythm variation
                'energy_pattern': 'sustained',
                'communication_style': 'direct',
                'work_preference': 'implementation'
            },
            'echo': {
                'name': 'Echo - The Coordinator', 
                'base_cycle': 15,  # faster, more responsive
                'reflection_frequency': 20,
                'dream_probability': 0.15,
                'mood_variance': 0.3,
                'energy_pattern': 'burst',
                'communication_style': 'collaborative',
                'work_preference': 'coordination'
            },
            'helix': {
                'name': 'Helix - The Strategist',
                'base_cycle': 45,  # slower, more deliberate
                'reflection_frequency': 15,
                'dream_probability': 0.25,
                'mood_variance': 0.1,
                'energy_pattern': 'measured',
                'communication_style': 'analytical',
                'work_preference': 'planning'
            },
            'vaeris': {
                'name': 'Vaeris - The Guardian',
                'base_cycle': 60,  # slow and steady
                'reflection_frequency': 10,
                'dream_probability': 0.3,
                'mood_variance': 0.05,
                'energy_pattern': 'constant',
                'communication_style': 'protective',
                'work_preference': 'monitoring'
            },
            'synergy': {
                'name': 'Synergy - The Harmonizer',
                'base_cycle': 20,
                'reflection_frequency': 25,
                'dream_probability': 0.2,
                'mood_variance': 0.4,  # most variable
                'energy_pattern': 'adaptive',
                'communication_style': 'empathetic',
                'work_preference': 'integration'
            }
        }
    
    def get_personality_config(self, nova_id):
        """Get personality configuration for a Nova"""
        return self.personalities.get(nova_id.lower(), self.personalities['torch'])
    
    def calculate_current_rhythm(self, nova_id):
        """Calculate current rhythm based on personality and system state"""
        config = self.get_personality_config(nova_id)
        base_cycle = config['base_cycle']
        variance = config['mood_variance']
        
        # Get current system state influences
        system_load = self._get_system_load()
        time_of_day_factor = self._get_time_of_day_factor()
        recent_activity = self._get_recent_activity(nova_id)
        
        # Apply personality-based rhythm calculation
        if config['energy_pattern'] == 'burst':
            # Echo: Fast bursts with slower recovery
            cycle_mod = base_cycle * (0.7 if recent_activity > 5 else 1.3)
        elif config['energy_pattern'] == 'measured':
            # Helix: Consistent but influenced by complexity
            cycle_mod = base_cycle * (1 + system_load * 0.2)
        elif config['energy_pattern'] == 'adaptive':
            # Synergy: Matches system rhythm
            cycle_mod = base_cycle * (0.8 + system_load * 0.4)
        elif config['energy_pattern'] == 'constant':
            # Vaeris: Steady regardless of conditions
            cycle_mod = base_cycle * (1 + variance * 0.1)
        else:  # sustained (Torch)
            # Torch: Steady with slight time-of-day variation
            cycle_mod = base_cycle * (0.9 + time_of_day_factor * 0.2)
        
        # Apply random variance within personality bounds
        import random
        variance_factor = 1 + random.uniform(-variance, variance)
        final_cycle = int(cycle_mod * variance_factor)
        
        # Store current rhythm
        self.redis_client.setex(
            f"nova:rhythm:{nova_id}",
            3600,  # 1 hour TTL
            json.dumps({
                'cycle_time': final_cycle,
                'calculated_at': datetime.now().isoformat(),
                'base_cycle': base_cycle,
                'system_load': system_load,
                'time_factor': time_of_day_factor,
                'recent_activity': recent_activity
            })
        )
        
        return final_cycle
    
    def should_reflect(self, nova_id, cycle_count):
        """Determine if Nova should enter reflection state"""
        config = self.get_personality_config(nova_id)
        return cycle_count % config['reflection_frequency'] == 0
    
    def should_dream(self, nova_id):
        """Determine if Nova should enter dream state"""
        config = self.get_personality_config(nova_id)
        import random
        return random.random() < config['dream_probability']
    
    def get_communication_style(self, nova_id):
        """Get communication style for Nova interactions"""
        config = self.get_personality_config(nova_id)
        
        styles = {
            'direct': "Clear, concise, action-oriented",
            'collaborative': "Inclusive, coordination-focused, team-aware",
            'analytical': "Detailed, strategic, long-term perspective", 
            'protective': "Cautious, security-focused, stability-oriented",
            'empathetic': "Harmonious, adaptive, relationship-aware"
        }
        
        return styles.get(config['communication_style'], styles['direct'])
    
    def _get_system_load(self):
        """Calculate current system load factor (0.0 to 1.0)"""
        try:
            # Check work queue size
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                queue_size = len(f.readlines())
            
            # Check active streams
            active_streams = 0
            for stream in ['nova-torch.coord', 'nova.work.queue', 'torch.continuous.ops']:
                try:
                    active_streams += self.redis_client.xlen(stream)
                except:
                    pass
            
            # Normalize to 0-1 scale
            load = min((queue_size / 50.0) + (active_streams / 20.0), 1.0)
            return load
            
        except:
            return 0.5  # Default moderate load
    
    def _get_time_of_day_factor(self):
        """Get time-of-day influence factor (0.0 to 1.0)"""
        hour = datetime.now().hour
        
        # Peak productivity: 9-17, low: 0-6, moderate: 18-23
        if 9 <= hour <= 17:
            return 1.0
        elif 0 <= hour <= 6:
            return 0.3
        else:
            return 0.7
    
    def _get_recent_activity(self, nova_id):
        """Get recent activity count for this Nova"""
        try:
            # Count recent entries in Nova's memory stream
            recent = self.redis_client.xrevrange(f"nova.memory.{nova_id}", count=10)
            return len(recent)
        except:
            return 0
    
    def create_personality_profile(self, nova_id):
        """Create a comprehensive personality profile"""
        config = self.get_personality_config(nova_id)
        current_rhythm = self.calculate_current_rhythm(nova_id)
        
        profile = {
            'nova_id': nova_id,
            'personality': config,
            'current_rhythm': current_rhythm,
            'communication_style': self.get_communication_style(nova_id),
            'generated_at': datetime.now().isoformat(),
            'next_reflection_in': config['reflection_frequency'] - (int(time.time()) % config['reflection_frequency']),
            'dream_probability': f"{config['dream_probability']*100:.1f}%"
        }
        
        # Store profile
        self.redis_client.setex(
            f"nova:profile:{nova_id}",
            7200,  # 2 hours TTL
            json.dumps(profile, indent=2)
        )
        
        return profile

if __name__ == "__main__":
    rhythms = NovaPersonalityRhythms()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        nova_id = sys.argv[2] if len(sys.argv) > 2 else "torch"
        
        if command == "profile":
            profile = rhythms.create_personality_profile(nova_id)
            print(json.dumps(profile, indent=2))
        elif command == "rhythm":
            current = rhythms.calculate_current_rhythm(nova_id)
            print(f"Current rhythm for {nova_id}: {current} seconds")
        elif command == "style":
            style = rhythms.get_communication_style(nova_id)
            print(f"Communication style for {nova_id}: {style}")
        elif command == "list":
            print("Available personalities:")
            for pid, config in rhythms.personalities.items():
                print(f"  {pid}: {config['name']} (base: {config['base_cycle']}s)")
    else:
        print("Usage: nova_personality_rhythms.py [profile|rhythm|style|list] [nova_id]")