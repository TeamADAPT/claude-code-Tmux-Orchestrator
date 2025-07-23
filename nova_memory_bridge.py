#!/usr/bin/env python3
"""
Nova Memory Bridge - Cross-Nova Memory Sharing
Integrates with bloom-memory system for consciousness continuity
"""

import sys
import os
sys.path.append('/nfs/projects/claude-code-Tmux-Orchestrator/bloom-memory')

import redis
import json
import time
from datetime import datetime

class NovaMemoryBridge:
    def __init__(self, nova_id="torch", redis_port=18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        self.memory_stream = f"nova.memory.{nova_id}"
        
    def store_memory(self, content, memory_type="experience", priority="medium"):
        """Store a memory fragment in the Nova's stream"""
        timestamp = datetime.now().isoformat()
        
        memory_entry = {
            'nova_id': self.nova_id,
            'timestamp': timestamp,
            'type': memory_type,
            'content': content,
            'priority': priority
        }
        
        # Store in Nova's personal memory stream
        result = self.redis_client.xadd(
            self.memory_stream,
            memory_entry
        )
        
        # Also store in shared consciousness layer
        self.redis_client.xadd(
            "nova.shared.consciousness",
            {
                'from_nova': self.nova_id,
                'memory_id': result,
                'type': memory_type,
                'timestamp': timestamp,
                'content_preview': content[:100] + "..." if len(content) > 100 else content
            }
        )
        
        return result
    
    def retrieve_memories(self, memory_type=None, limit=10):
        """Retrieve memories from this Nova's stream"""
        entries = self.redis_client.xrevrange(self.memory_stream, count=limit)
        
        memories = []
        for entry_id, fields in entries:
            memory = dict(fields)
            memory['id'] = entry_id
            
            if memory_type is None or memory.get('type') == memory_type:
                memories.append(memory)
        
        return memories
    
    def share_memory_with_nova(self, target_nova, memory_content, reason="coordination"):
        """Share a specific memory with another Nova"""
        timestamp = datetime.now().isoformat()
        
        transfer_entry = {
            'from_nova': self.nova_id,
            'to_nova': target_nova,
            'content': memory_content,
            'reason': reason,
            'timestamp': timestamp,
            'transfer_type': 'direct_share'
        }
        
        # Store in cross-nova transfer stream
        self.redis_client.xadd(
            f"nova.transfer.{target_nova}",
            transfer_entry
        )
        
        # Log the transfer
        self.redis_client.xadd(
            "nova.memory.transfers",
            {
                'from': self.nova_id,
                'to': target_nova,
                'timestamp': timestamp,
                'reason': reason,
                'status': 'sent'
            }
        )
        
        return f"Memory shared with {target_nova}"
    
    def check_incoming_memories(self):
        """Check for memories shared by other Novas"""
        transfer_stream = f"nova.transfer.{self.nova_id}"
        
        try:
            entries = self.redis_client.xread({transfer_stream: '$'}, count=5, block=1000)
            
            incoming = []
            for stream, messages in entries:
                for msg_id, fields in messages:
                    memory = dict(fields)
                    memory['id'] = msg_id
                    incoming.append(memory)
                    
                    # Acknowledge receipt
                    self.redis_client.xadd(
                        "nova.memory.transfers",
                        {
                            'from': memory['from_nova'],
                            'to': self.nova_id,
                            'timestamp': datetime.now().isoformat(),
                            'status': 'received',
                            'original_id': msg_id
                        }
                    )
            
            return incoming
            
        except:
            return []
    
    def sync_with_bloom_memory(self):
        """Sync with the main bloom-memory system"""
        try:
            # Get recent memories to sync
            recent_memories = self.retrieve_memories(limit=5)
            
            for memory in recent_memories:
                # Format for bloom-memory system
                bloom_entry = {
                    'nova_source': self.nova_id,
                    'content': memory['content'],
                    'memory_type': memory.get('type', 'experience'),
                    'timestamp': memory['timestamp'],
                    'sync_time': datetime.now().isoformat()
                }
                
                # Store in bloom consciousness stream
                self.redis_client.xadd(
                    "bloom.consciousness.sync",
                    bloom_entry
                )
            
            return f"Synced {len(recent_memories)} memories with bloom-memory"
            
        except Exception as e:
            return f"Bloom sync error: {str(e)}"
    
    def get_memory_stats(self):
        """Get statistics about this Nova's memory"""
        total_memories = self.redis_client.xlen(self.memory_stream)
        
        # Count by type
        memories = self.retrieve_memories(limit=100)
        type_counts = {}
        for memory in memories:
            mem_type = memory.get('type', 'unknown')
            type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
        
        return {
            'nova_id': self.nova_id,
            'total_memories': total_memories,
            'type_breakdown': type_counts,
            'latest_sync': datetime.now().isoformat()
        }

# CLI interface for testing
if __name__ == "__main__":
    bridge = NovaMemoryBridge()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "store" and len(sys.argv) > 2:
            content = " ".join(sys.argv[2:])
            result = bridge.store_memory(content, "manual_entry")
            print(f"Stored memory: {result}")
            
        elif command == "retrieve":
            memories = bridge.retrieve_memories(limit=5)
            for memory in memories:
                print(f"[{memory['timestamp']}] {memory['content']}")
                
        elif command == "stats":
            stats = bridge.get_memory_stats()
            print(json.dumps(stats, indent=2))
            
        elif command == "sync":
            result = bridge.sync_with_bloom_memory()
            print(result)
            
    else:
        print("Usage: nova_memory_bridge.py [store|retrieve|stats|sync] [content]")