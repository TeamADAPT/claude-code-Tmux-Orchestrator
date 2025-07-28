#!/usr/bin/env python3
"""
Nova Registry - Discovery and capability management
"""
import redis
import json
import time
import socket
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class NovaRegistry:
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.redis = redis.Redis(host='localhost', port=18000, decode_responses=True)
        self.capabilities = []
        self.heartbeat_thread = None
        self.running = False
        
    def register(self, capabilities: List[str], metadata: Dict = None):
        """Register this Nova with the ecosystem"""
        registration = {
            'nova_id': self.nova_id,
            'capabilities': json.dumps(capabilities),
            'status': 'active',
            'registered_at': datetime.now().isoformat(),
            'last_heartbeat': datetime.now().isoformat(),
            'hostname': socket.gethostname(),
            'metadata': json.dumps(metadata or {})
        }
        
        # Store in registry
        self.redis.hset(f'nova:registry:{self.nova_id}', mapping=registration)
        
        # Add to active set
        self.redis.sadd('nova:registry:active', self.nova_id)
        
        # Announce registration
        self.redis.xadd('nova.ecosystem.events', {
            'type': 'NOVA_REGISTERED',
            'nova_id': self.nova_id,
            'capabilities': json.dumps(capabilities),
            'timestamp': datetime.now().isoformat()
        })
        
        self.capabilities = capabilities
        self._start_heartbeat()
        
        return True
    
    def _start_heartbeat(self):
        """Start heartbeat thread"""
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
    
    def _heartbeat_loop(self):
        """Send regular heartbeats"""
        while self.running:
            try:
                # Update heartbeat
                self.redis.hset(
                    f'nova:registry:{self.nova_id}', 
                    'last_heartbeat', 
                    datetime.now().isoformat()
                )
                
                # Check for dead Novas
                self._cleanup_dead_novas()
                
                time.sleep(30)  # Heartbeat every 30 seconds
                
            except Exception as e:
                print(f"Heartbeat error: {e}")
                time.sleep(60)
    
    def _cleanup_dead_novas(self):
        """Remove Novas that haven't sent heartbeat in 5 minutes"""
        active_novas = self.redis.smembers('nova:registry:active')
        
        for nova_id in active_novas:
            nova_data = self.redis.hgetall(f'nova:registry:{nova_id}')
            if nova_data:
                last_heartbeat = nova_data.get('last_heartbeat')
                if last_heartbeat:
                    last_time = datetime.fromisoformat(last_heartbeat)
                    if datetime.now() - last_time > timedelta(minutes=5):
                        # Mark as inactive
                        self.redis.srem('nova:registry:active', nova_id)
                        self.redis.hset(f'nova:registry:{nova_id}', 'status', 'inactive')
                        
                        # Announce death
                        self.redis.xadd('nova.ecosystem.events', {
                            'type': 'NOVA_INACTIVE',
                            'nova_id': nova_id,
                            'last_seen': last_heartbeat,
                            'timestamp': datetime.now().isoformat()
                        })
    
    def discover(self, capability: Optional[str] = None) -> List[Dict]:
        """Discover other active Novas"""
        active_novas = self.redis.smembers('nova:registry:active')
        discovered = []
        
        for nova_id in active_novas:
            if nova_id == self.nova_id:
                continue  # Skip self
                
            nova_data = self.redis.hgetall(f'nova:registry:{nova_id}')
            if nova_data:
                capabilities = json.loads(nova_data.get('capabilities', '[]'))
                
                # Filter by capability if specified
                if capability and capability not in capabilities:
                    continue
                
                discovered.append({
                    'nova_id': nova_id,
                    'capabilities': capabilities,
                    'status': nova_data.get('status'),
                    'last_heartbeat': nova_data.get('last_heartbeat'),
                    'metadata': json.loads(nova_data.get('metadata', '{}'))
                })
        
        return discovered
    
    def find_nova_for_task(self, task_type: str) -> Optional[str]:
        """Find best Nova for a specific task type"""
        candidates = self.discover()
        
        # Score Novas based on capabilities and load
        best_nova = None
        best_score = -1
        
        for nova in candidates:
            score = 0
            
            # Check if Nova has the capability
            if task_type in nova['capabilities']:
                score += 10
            
            # Check load (pending tasks)
            queue_size = self.redis.xlen(f"nova.tasks.{nova['nova_id']}")
            score -= queue_size  # Lower queue size is better
            
            # Check recent success rate
            stats = self.redis.hgetall(f"workflow:stats:{nova['nova_id']}")
            if stats:
                success = int(stats.get('success_count', 0))
                total = int(stats.get('total_count', 1))
                success_rate = success / total if total > 0 else 0
                score += success_rate * 5
            
            if score > best_score:
                best_score = score
                best_nova = nova['nova_id']
        
        return best_nova
    
    def broadcast(self, message_type: str, data: Dict):
        """Broadcast message to all active Novas"""
        active_novas = self.redis.smembers('nova:registry:active')
        
        for nova_id in active_novas:
            if nova_id == self.nova_id:
                continue
                
            self.redis.xadd(f'nova.coordination.{nova_id}', {
                'from': self.nova_id,
                'type': message_type,
                'data': json.dumps(data),
                'timestamp': datetime.now().isoformat()
            })
    
    def get_network_status(self) -> Dict:
        """Get overall network status"""
        active_novas = list(self.redis.smembers('nova:registry:active'))
        total_tasks = 0
        total_completed = 0
        
        for nova_id in active_novas:
            total_tasks += self.redis.xlen(f"nova.tasks.{nova_id}")
            stats = self.redis.hgetall(f"workflow:stats:{nova_id}")
            if stats:
                total_completed += int(stats.get('total_count', 0))
        
        return {
            'active_novas': len(active_novas),
            'nova_list': active_novas,
            'total_pending_tasks': total_tasks,
            'total_completed_tasks': total_completed,
            'network_health': 'healthy' if len(active_novas) > 0 else 'degraded'
        }
    
    def unregister(self):
        """Unregister this Nova from the ecosystem"""
        self.running = False
        
        # Remove from active set
        self.redis.srem('nova:registry:active', self.nova_id)
        
        # Update status
        self.redis.hset(f'nova:registry:{self.nova_id}', 'status', 'offline')
        
        # Announce departure
        self.redis.xadd('nova.ecosystem.events', {
            'type': 'NOVA_UNREGISTERED',
            'nova_id': self.nova_id,
            'timestamp': datetime.now().isoformat()
        })

# CLI for testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: nova_registry.py <command> [args]")
        print("Commands: register, discover, status")
        sys.exit(1)
    
    command = sys.argv[1]
    nova_id = sys.argv[2] if len(sys.argv) > 2 else 'test'
    
    registry = NovaRegistry(nova_id)
    
    if command == "register":
        capabilities = sys.argv[3:] if len(sys.argv) > 3 else ['general']
        registry.register(capabilities)
        print(f"✅ Nova {nova_id} registered with capabilities: {capabilities}")
        
    elif command == "discover":
        novas = registry.discover()
        print(f"🔍 Discovered {len(novas)} active Novas:")
        for nova in novas:
            print(f"  - {nova['nova_id']}: {nova['capabilities']}")
            
    elif command == "status":
        status = registry.get_network_status()
        print(f"🌐 Nova Network Status:")
        print(f"  Active Novas: {status['active_novas']}")
        print(f"  Pending Tasks: {status['total_pending_tasks']}")
        print(f"  Completed Tasks: {status['total_completed_tasks']}")
        print(f"  Health: {status['network_health']}")