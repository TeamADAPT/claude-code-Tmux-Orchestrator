#!/usr/bin/env python3
"""
Torch Personal Memory System - Storage Layer
Persistent storage with cross-session continuity using bloom-memory

Project: TORCHX-2 - Build Personal Memory & Learning System
Owner: Nova Torch
Created: 2025-07-24
"""

import os
import json
import redis
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Any, Set, Tuple
import logging

from memory_schema import (
    LearningInsight, MemoryType, MemoryStrength, 
    LearningDomain, MemoryConnection, LearningPathway,
    ReflectionProtocol, MemoryMetrics
)

logger = logging.getLogger('torch.memory')

class MemoryStorage:
    """
    Persistent storage layer for Torch's personal memory system.
    Uses SQLite for structured data and Redis for fast access.
    """
    
    def __init__(self, storage_path: str = "/nfs/projects/claude-code-Tmux-Orchestrator/torch-memory-system/data"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # SQLite for persistent storage
        self.db_path = self.storage_path / "torch_memories.db"
        self.conn = sqlite3.connect(str(self.db_path))
        self._initialize_database()
        
        # Redis for fast access and caching
        self.redis_client = redis.Redis(
            host='localhost',
            port=18000,
            decode_responses=True,
            password='adapt123'
        )
        
        # Bloom filter integration path
        self.bloom_path = Path("/nfs/projects/claude-code-Tmux-Orchestrator/bloom-memory")
        
        logger.info(f"Memory storage initialized at {self.storage_path}")
    
    def _initialize_database(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Memories table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            memory_id TEXT PRIMARY KEY,
            memory_type TEXT NOT NULL,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            context TEXT,
            tags TEXT,
            created_at TIMESTAMP NOT NULL,
            accessed_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            modified_at TIMESTAMP,
            strength INTEGER NOT NULL,
            confidence REAL NOT NULL,
            utility_score REAL NOT NULL,
            parent_memory_id TEXT,
            session_id TEXT,
            project_context TEXT,
            reflection_notes TEXT,
            action_items TEXT
        )
        """)
        
        # Connections table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_memory_id TEXT NOT NULL,
            target_memory_id TEXT NOT NULL,
            connection_type TEXT NOT NULL,
            strength REAL NOT NULL,
            context TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (source_memory_id) REFERENCES memories (memory_id),
            FOREIGN KEY (target_memory_id) REFERENCES memories (memory_id)
        )
        """)
        
        # Learning pathways table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS learning_pathways (
            pathway_id TEXT PRIMARY KEY,
            domain TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            milestones TEXT,
            current_milestone INTEGER DEFAULT 0,
            memory_ids TEXT,
            started_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            progress_percentage REAL DEFAULT 0.0,
            learning_velocity REAL DEFAULT 0.0,
            retention_rate REAL DEFAULT 0.0
        )
        """)
        
        # Reflection history table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reflections (
            reflection_id INTEGER PRIMARY KEY AUTOINCREMENT,
            protocol_name TEXT NOT NULL,
            trigger TEXT NOT NULL,
            reflection_content TEXT NOT NULL,
            patterns_identified TEXT,
            action_items TEXT,
            created_at TIMESTAMP NOT NULL
        )
        """)
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_memory_type ON memories (memory_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_domain ON memories (domain)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories (created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_project ON memories (project_context)")
        
        self.conn.commit()
    
    def store_memory(self, memory: LearningInsight) -> bool:
        """Store a memory persistently"""
        try:
            cursor = self.conn.cursor()
            
            # Store main memory
            cursor.execute("""
            INSERT OR REPLACE INTO memories (
                memory_id, memory_type, domain, title, content, context, tags,
                created_at, accessed_count, last_accessed, modified_at,
                strength, confidence, utility_score, parent_memory_id,
                session_id, project_context, reflection_notes, action_items
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.memory_id,
                memory.memory_type.value,
                memory.domain.value,
                memory.title,
                memory.content,
                json.dumps(memory.context),
                json.dumps(list(memory.tags)),
                memory.created_at,
                memory.accessed_count,
                memory.last_accessed,
                memory.modified_at,
                memory.strength.value,
                memory.confidence,
                memory.utility_score,
                memory.parent_memory_id,
                memory.session_id,
                memory.project_context,
                json.dumps(memory.reflection_notes),
                json.dumps(memory.action_items)
            ))
            
            # Store connections
            for conn in memory.connections:
                cursor.execute("""
                INSERT INTO memory_connections (
                    source_memory_id, target_memory_id, connection_type,
                    strength, context, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    memory.memory_id,
                    conn.target_memory_id,
                    conn.connection_type,
                    conn.strength,
                    conn.context,
                    conn.created_at
                ))
            
            self.conn.commit()
            
            # Cache in Redis for fast access
            self._cache_memory(memory)
            
            # Post to memory stream for real-time monitoring
            self._post_to_memory_stream(memory)
            
            logger.info(f"Stored memory: {memory.memory_id} - {memory.title}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store memory: {e}")
            self.conn.rollback()
            return False
    
    def retrieve_memory(self, memory_id: str) -> Optional[LearningInsight]:
        """Retrieve a specific memory"""
        # Check Redis cache first
        cached = self._get_cached_memory(memory_id)
        if cached:
            return cached
        
        # Fetch from database
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE memory_id = ?", (memory_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        # Reconstruct memory object
        memory = self._row_to_memory(row)
        
        # Update access count and timestamp
        self._update_access_stats(memory_id)
        
        # Cache for future access
        self._cache_memory(memory)
        
        return memory
    
    def search_memories(self, 
                       query: Optional[str] = None,
                       memory_type: Optional[MemoryType] = None,
                       domain: Optional[LearningDomain] = None,
                       tags: Optional[Set[str]] = None,
                       project_context: Optional[str] = None,
                       min_strength: Optional[MemoryStrength] = None,
                       limit: int = 50) -> List[LearningInsight]:
        """Search memories with various filters"""
        cursor = self.conn.cursor()
        
        # Build query
        conditions = []
        params = []
        
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type.value)
        
        if domain:
            conditions.append("domain = ?")
            params.append(domain.value)
        
        if project_context:
            conditions.append("project_context = ?")
            params.append(project_context)
        
        if min_strength:
            conditions.append("strength >= ?")
            params.append(min_strength.value)
        
        if query:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        
        # Construct SQL
        sql = "SELECT * FROM memories"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        memories = []
        for row in rows:
            memory = self._row_to_memory(row)
            
            # Filter by tags if specified
            if tags and not tags.intersection(memory.tags):
                continue
                
            memories.append(memory)
        
        return memories
    
    def find_connected_memories(self, memory_id: str, 
                              connection_type: Optional[str] = None,
                              max_depth: int = 2) -> List[Tuple[LearningInsight, float]]:
        """Find memories connected to a given memory"""
        visited = set()
        connections = []
        
        def traverse(current_id: str, depth: int, path_strength: float):
            if depth > max_depth or current_id in visited:
                return
            
            visited.add(current_id)
            
            cursor = self.conn.cursor()
            
            # Find connections
            if connection_type:
                cursor.execute("""
                SELECT target_memory_id, strength FROM memory_connections 
                WHERE source_memory_id = ? AND connection_type = ?
                """, (current_id, connection_type))
            else:
                cursor.execute("""
                SELECT target_memory_id, strength FROM memory_connections 
                WHERE source_memory_id = ?
                """, (current_id,))
            
            for target_id, strength in cursor.fetchall():
                memory = self.retrieve_memory(target_id)
                if memory:
                    combined_strength = path_strength * strength
                    connections.append((memory, combined_strength))
                    
                    # Recursive traversal
                    traverse(target_id, depth + 1, combined_strength)
        
        traverse(memory_id, 0, 1.0)
        
        # Sort by connection strength
        connections.sort(key=lambda x: x[1], reverse=True)
        
        return connections
    
    def create_connection(self, source_id: str, target_id: str,
                         connection_type: str, strength: float = 0.5,
                         context: str = "") -> bool:
        """Create a connection between two memories"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO memory_connections (
                source_memory_id, target_memory_id, connection_type,
                strength, context, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (source_id, target_id, connection_type, strength, context, datetime.now()))
            
            self.conn.commit()
            
            # Update source memory's connections
            source_memory = self.retrieve_memory(source_id)
            if source_memory:
                source_memory.connections.append(MemoryConnection(
                    target_memory_id=target_id,
                    connection_type=connection_type,
                    strength=strength,
                    context=context
                ))
                self._cache_memory(source_memory)
            
            logger.info(f"Created connection: {source_id} -> {target_id} ({connection_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create connection: {e}")
            return False
    
    def store_learning_pathway(self, pathway: LearningPathway) -> bool:
        """Store a learning pathway"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT OR REPLACE INTO learning_pathways (
                pathway_id, domain, title, description, milestones,
                current_milestone, memory_ids, started_at, completed_at,
                progress_percentage, learning_velocity, retention_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pathway.pathway_id,
                pathway.domain.value,
                pathway.title,
                pathway.description,
                json.dumps(pathway.milestones),
                pathway.current_milestone,
                json.dumps(pathway.memory_ids),
                pathway.started_at,
                pathway.completed_at,
                pathway.progress_percentage,
                pathway.learning_velocity,
                pathway.retention_rate
            ))
            
            self.conn.commit()
            logger.info(f"Stored learning pathway: {pathway.pathway_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store pathway: {e}")
            return False
    
    def store_reflection(self, protocol: ReflectionProtocol, 
                        content: str, patterns: List[str], 
                        actions: List[str]) -> bool:
        """Store a reflection session"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
            INSERT INTO reflections (
                protocol_name, trigger, reflection_content,
                patterns_identified, action_items, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                protocol.name,
                protocol.trigger,
                content,
                json.dumps(patterns),
                json.dumps(actions),
                datetime.now()
            ))
            
            self.conn.commit()
            
            # Post to reflection stream
            self.redis_client.xadd(
                'torch.reflections',
                {
                    'protocol': protocol.name,
                    'trigger': protocol.trigger,
                    'patterns_count': str(len(patterns)),
                    'actions_count': str(len(actions)),
                    'timestamp': datetime.now().isoformat()
                }
            )
            
            logger.info(f"Stored reflection: {protocol.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store reflection: {e}")
            return False
    
    def get_memory_metrics(self, time_window_days: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive memory metrics"""
        # Get recent memories
        cursor = self.conn.cursor()
        cutoff = datetime.now() - timedelta(days=time_window_days)
        
        cursor.execute("""
        SELECT * FROM memories WHERE created_at > ?
        """, (cutoff,))
        
        recent_memories = [self._row_to_memory(row) for row in cursor.fetchall()]
        
        # Calculate metrics
        metrics = {
            'total_memories': len(recent_memories),
            'learning_velocity': MemoryMetrics.calculate_learning_velocity(recent_memories, time_window_days),
            'retention_rate': MemoryMetrics.calculate_retention_rate(recent_memories),
            'connection_density': MemoryMetrics.calculate_connection_density(recent_memories),
            'knowledge_clusters': MemoryMetrics.identify_knowledge_clusters(recent_memories),
            'memories_by_type': {},
            'memories_by_domain': {},
            'strongest_memories': [],
            'most_connected': []
        }
        
        # Group by type and domain
        for memory in recent_memories:
            type_key = memory.memory_type.value
            domain_key = memory.domain.value
            
            metrics['memories_by_type'][type_key] = metrics['memories_by_type'].get(type_key, 0) + 1
            metrics['memories_by_domain'][domain_key] = metrics['memories_by_domain'].get(domain_key, 0) + 1
        
        # Find strongest memories
        strongest = sorted(recent_memories, key=lambda m: m.strength.value, reverse=True)[:5]
        metrics['strongest_memories'] = [
            {'id': m.memory_id, 'title': m.title, 'strength': m.strength.value}
            for m in strongest
        ]
        
        # Find most connected
        most_connected = sorted(recent_memories, key=lambda m: len(m.connections), reverse=True)[:5]
        metrics['most_connected'] = [
            {'id': m.memory_id, 'title': m.title, 'connections': len(m.connections)}
            for m in most_connected
        ]
        
        return metrics
    
    def _row_to_memory(self, row: tuple) -> LearningInsight:
        """Convert database row to memory object"""
        # Unpack row (assuming column order matches table definition)
        (memory_id, memory_type, domain, title, content, context_json, tags_json,
         created_at, accessed_count, last_accessed, modified_at,
         strength, confidence, utility_score, parent_memory_id,
         session_id, project_context, reflection_notes_json, action_items_json) = row
        
        # Load connections
        cursor = self.conn.cursor()
        cursor.execute("""
        SELECT target_memory_id, connection_type, strength, context, created_at
        FROM memory_connections WHERE source_memory_id = ?
        """, (memory_id,))
        
        connections = []
        for conn_row in cursor.fetchall():
            connections.append(MemoryConnection(
                target_memory_id=conn_row[0],
                connection_type=conn_row[1],
                strength=conn_row[2],
                context=conn_row[3],
                created_at=datetime.fromisoformat(conn_row[4])
            ))
        
        return LearningInsight(
            memory_id=memory_id,
            memory_type=MemoryType(memory_type),
            domain=LearningDomain(domain),
            title=title,
            content=content,
            context=json.loads(context_json) if context_json else {},
            tags=set(json.loads(tags_json)) if tags_json else set(),
            created_at=datetime.fromisoformat(created_at),
            accessed_count=accessed_count,
            last_accessed=datetime.fromisoformat(last_accessed) if last_accessed else None,
            modified_at=datetime.fromisoformat(modified_at) if modified_at else None,
            strength=MemoryStrength(strength),
            confidence=confidence,
            utility_score=utility_score,
            connections=connections,
            parent_memory_id=parent_memory_id,
            session_id=session_id,
            project_context=project_context,
            reflection_notes=json.loads(reflection_notes_json) if reflection_notes_json else [],
            action_items=json.loads(action_items_json) if action_items_json else []
        )
    
    def _cache_memory(self, memory: LearningInsight):
        """Cache memory in Redis"""
        key = f"torch:memory:{memory.memory_id}"
        self.redis_client.setex(
            key,
            3600,  # 1 hour TTL
            memory.to_json()
        )
    
    def _get_cached_memory(self, memory_id: str) -> Optional[LearningInsight]:
        """Get memory from Redis cache"""
        key = f"torch:memory:{memory_id}"
        data = self.redis_client.get(key)
        
        if data:
            return LearningInsight.from_json(data)
        return None
    
    def _update_access_stats(self, memory_id: str):
        """Update access statistics for a memory"""
        cursor = self.conn.cursor()
        cursor.execute("""
        UPDATE memories 
        SET accessed_count = accessed_count + 1,
            last_accessed = ?
        WHERE memory_id = ?
        """, (datetime.now(), memory_id))
        self.conn.commit()
    
    def _post_to_memory_stream(self, memory: LearningInsight):
        """Post memory creation to stream for monitoring"""
        self.redis_client.xadd(
            'torch.memory.created',
            {
                'memory_id': memory.memory_id,
                'type': memory.memory_type.value,
                'domain': memory.domain.value,
                'title': memory.title,
                'strength': str(memory.strength.value),
                'project': memory.project_context or 'none',
                'timestamp': datetime.now().isoformat()
            }
        )

if __name__ == "__main__":
    # Test memory storage
    storage = MemoryStorage()
    
    # Create test memory
    test_memory = LearningInsight(
        memory_type=MemoryType.TECHNICAL,
        domain=LearningDomain.SOFTWARE_ENGINEERING,
        title="Memory system architecture complete",
        content="Built persistent memory storage with SQLite and Redis caching for cross-session continuity.",
        tags={"memory-system", "persistence", "architecture"},
        strength=MemoryStrength.STRONG,
        confidence=0.9,
        project_context="TORCHX-2"
    )
    
    # Store it
    success = storage.store_memory(test_memory)
    print(f"Storage successful: {success}")
    
    # Retrieve it
    retrieved = storage.retrieve_memory(test_memory.memory_id)
    if retrieved:
        print(f"Retrieved memory: {retrieved.title}")
    
    # Get metrics
    metrics = storage.get_memory_metrics(30)
    print(f"\nMemory metrics: {json.dumps(metrics, indent=2)}")