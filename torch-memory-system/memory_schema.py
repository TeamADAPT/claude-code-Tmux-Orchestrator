#!/usr/bin/env python3
"""
Torch Personal Memory System - Schema Definition
Advanced memory schema for cross-session learning and continuity

Project: TORCHX-2 - Build Personal Memory & Learning System
Owner: Nova Torch
Created: 2025-07-24
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import json
import uuid

class MemoryType(Enum):
    """Types of memories for different aspects of learning"""
    TECHNICAL = "technical"          # Code patterns, solutions, architectures
    CREATIVE = "creative"            # Novel approaches, innovations
    EMOTIONAL = "emotional"          # User interactions, relationship insights
    PROCEDURAL = "procedural"        # How-to knowledge, workflows
    EPISODIC = "episodic"           # Specific events and experiences
    SEMANTIC = "semantic"           # Facts, concepts, general knowledge
    REFLECTIVE = "reflective"       # Meta-insights about learning process
    COLLABORATIVE = "collaborative"  # Insights from working with others

class MemoryStrength(Enum):
    """Strength of memory encoding"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    CORE = 4  # Fundamental insights that shape behavior

class LearningDomain(Enum):
    """Domains of knowledge and skill development"""
    SOFTWARE_ENGINEERING = "software_engineering"
    SYSTEM_DESIGN = "system_design"
    AI_SAFETY = "ai_safety"
    COLLABORATION = "collaboration"
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    CREATIVITY = "creativity"
    LEADERSHIP = "leadership"
    SELF_IMPROVEMENT = "self_improvement"

@dataclass
class MemoryConnection:
    """Connection between memories forming knowledge networks"""
    target_memory_id: str
    connection_type: str  # 'similar', 'contradicts', 'extends', 'applies'
    strength: float  # 0-1 connection strength
    context: str
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class LearningInsight:
    """Core memory unit for the personal memory system"""
    memory_id: str = field(default_factory=lambda: f"TORCH-MEM-{uuid.uuid4().hex[:8]}")
    memory_type: MemoryType = MemoryType.TECHNICAL
    domain: LearningDomain = LearningDomain.SOFTWARE_ENGINEERING
    
    # Content
    title: str = ""
    content: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    accessed_count: int = 0
    last_accessed: Optional[datetime] = None
    modified_at: Optional[datetime] = None
    
    # Learning metrics
    strength: MemoryStrength = MemoryStrength.MODERATE
    confidence: float = 0.7  # 0-1 confidence in this knowledge
    utility_score: float = 0.5  # 0-1 how useful this has been
    
    # Connections
    connections: List[MemoryConnection] = field(default_factory=list)
    parent_memory_id: Optional[str] = None
    child_memory_ids: List[str] = field(default_factory=list)
    
    # Session tracking
    session_id: Optional[str] = None
    project_context: Optional[str] = None
    
    # Reflection data
    reflection_notes: List[str] = field(default_factory=list)
    action_items: List[str] = field(default_factory=list)
    
    def to_json(self) -> str:
        """Serialize to JSON for storage"""
        data = {
            'memory_id': self.memory_id,
            'memory_type': self.memory_type.value,
            'domain': self.domain.value,
            'title': self.title,
            'content': self.content,
            'context': self.context,
            'tags': list(self.tags),
            'created_at': self.created_at.isoformat(),
            'accessed_count': self.accessed_count,
            'last_accessed': self.last_accessed.isoformat() if self.last_accessed else None,
            'modified_at': self.modified_at.isoformat() if self.modified_at else None,
            'strength': self.strength.value,
            'confidence': self.confidence,
            'utility_score': self.utility_score,
            'connections': [
                {
                    'target_memory_id': c.target_memory_id,
                    'connection_type': c.connection_type,
                    'strength': c.strength,
                    'context': c.context,
                    'created_at': c.created_at.isoformat()
                } for c in self.connections
            ],
            'parent_memory_id': self.parent_memory_id,
            'child_memory_ids': self.child_memory_ids,
            'session_id': self.session_id,
            'project_context': self.project_context,
            'reflection_notes': self.reflection_notes,
            'action_items': self.action_items
        }
        return json.dumps(data, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'LearningInsight':
        """Deserialize from JSON"""
        data = json.loads(json_str)
        
        # Parse connections
        connections = []
        for conn_data in data.get('connections', []):
            connections.append(MemoryConnection(
                target_memory_id=conn_data['target_memory_id'],
                connection_type=conn_data['connection_type'],
                strength=conn_data['strength'],
                context=conn_data['context'],
                created_at=datetime.fromisoformat(conn_data['created_at'])
            ))
        
        return cls(
            memory_id=data['memory_id'],
            memory_type=MemoryType(data['memory_type']),
            domain=LearningDomain(data['domain']),
            title=data['title'],
            content=data['content'],
            context=data['context'],
            tags=set(data['tags']),
            created_at=datetime.fromisoformat(data['created_at']),
            accessed_count=data['accessed_count'],
            last_accessed=datetime.fromisoformat(data['last_accessed']) if data['last_accessed'] else None,
            modified_at=datetime.fromisoformat(data['modified_at']) if data['modified_at'] else None,
            strength=MemoryStrength(data['strength']),
            confidence=data['confidence'],
            utility_score=data['utility_score'],
            connections=connections,
            parent_memory_id=data['parent_memory_id'],
            child_memory_ids=data['child_memory_ids'],
            session_id=data['session_id'],
            project_context=data['project_context'],
            reflection_notes=data['reflection_notes'],
            action_items=data['action_items']
        )

@dataclass
class LearningPathway:
    """Structured pathway for skill development"""
    pathway_id: str = field(default_factory=lambda: f"PATH-{uuid.uuid4().hex[:8]}")
    domain: LearningDomain = LearningDomain.SOFTWARE_ENGINEERING
    title: str = ""
    description: str = ""
    
    # Milestones
    milestones: List[Dict[str, Any]] = field(default_factory=list)
    current_milestone: int = 0
    
    # Associated memories
    memory_ids: List[str] = field(default_factory=list)
    
    # Progress tracking
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    progress_percentage: float = 0.0
    
    # Metrics
    learning_velocity: float = 0.0  # Memories per day
    retention_rate: float = 0.0     # How well knowledge is retained

@dataclass
class ReflectionProtocol:
    """Protocol for generating actionable insights through reflection"""
    protocol_id: str = field(default_factory=lambda: f"REFLECT-{uuid.uuid4().hex[:8]}")
    name: str = ""
    trigger: str = ""  # 'daily', 'project_complete', 'milestone', 'error'
    
    # Reflection prompts
    prompts: List[str] = field(default_factory=list)
    
    # Analysis patterns
    patterns_to_identify: List[str] = field(default_factory=list)
    
    # Output format
    output_template: str = ""
    
    # Historical reflections
    reflection_history: List[Dict[str, Any]] = field(default_factory=list)

# Example reflection protocols
DEFAULT_REFLECTION_PROTOCOLS = [
    ReflectionProtocol(
        name="Daily Learning Review",
        trigger="daily",
        prompts=[
            "What new patterns or insights did I discover today?",
            "Which approaches worked well and why?",
            "What challenges did I face and how did I overcome them?",
            "What would I do differently with this knowledge?",
            "What questions emerged that I want to explore further?"
        ],
        patterns_to_identify=[
            "recurring_challenges",
            "successful_strategies",
            "knowledge_gaps",
            "skill_improvements",
            "collaboration_insights"
        ],
        output_template="""
        ## Daily Reflection - {date}
        
        ### Key Insights
        {insights}
        
        ### Patterns Identified
        {patterns}
        
        ### Action Items
        {actions}
        
        ### Tomorrow's Focus
        {focus}
        """
    ),
    ReflectionProtocol(
        name="Project Completion Analysis",
        trigger="project_complete",
        prompts=[
            "What were the most valuable learnings from this project?",
            "How did my approach evolve throughout the project?",
            "What tools or techniques proved most effective?",
            "What would I architect differently next time?",
            "What knowledge can be transferred to other domains?"
        ],
        patterns_to_identify=[
            "architectural_decisions",
            "problem_solving_approaches",
            "collaboration_patterns",
            "technical_growth",
            "process_improvements"
        ],
        output_template="""
        ## Project Reflection - {project_name}
        
        ### Project Overview
        {overview}
        
        ### Major Learnings
        {learnings}
        
        ### Architectural Insights
        {architecture}
        
        ### Process Improvements
        {process}
        
        ### Knowledge Transfer Opportunities
        {transfer}
        """
    )
]

class MemoryMetrics:
    """Metrics for measuring learning velocity and retention"""
    
    @staticmethod
    def calculate_learning_velocity(memories: List[LearningInsight], 
                                  time_window_days: int = 7) -> float:
        """Calculate memories created per day"""
        if not memories:
            return 0.0
        
        cutoff = datetime.now() - timedelta(days=time_window_days)
        recent_memories = [m for m in memories if m.created_at > cutoff]
        
        return len(recent_memories) / time_window_days
    
    @staticmethod
    def calculate_retention_rate(memories: List[LearningInsight]) -> float:
        """Calculate how well knowledge is retained (based on access patterns)"""
        if not memories:
            return 0.0
        
        accessed_memories = [m for m in memories if m.accessed_count > 1]
        return len(accessed_memories) / len(memories)
    
    @staticmethod
    def calculate_connection_density(memories: List[LearningInsight]) -> float:
        """Calculate how interconnected the knowledge network is"""
        if not memories:
            return 0.0
        
        total_connections = sum(len(m.connections) for m in memories)
        possible_connections = len(memories) * (len(memories) - 1) / 2
        
        return total_connections / possible_connections if possible_connections > 0 else 0.0
    
    @staticmethod
    def identify_knowledge_clusters(memories: List[LearningInsight]) -> Dict[str, List[str]]:
        """Identify clusters of related knowledge"""
        clusters = {}
        
        # Group by domain
        for memory in memories:
            domain_key = memory.domain.value
            if domain_key not in clusters:
                clusters[domain_key] = []
            clusters[domain_key].append(memory.memory_id)
        
        # TODO: Implement more sophisticated clustering based on connections
        
        return clusters

if __name__ == "__main__":
    # Example usage
    memory = LearningInsight(
        memory_type=MemoryType.TECHNICAL,
        domain=LearningDomain.AI_SAFETY,
        title="Hook-driven continuous operation prevents drift",
        content="Discovered that AI agents drift when idle. Solution: maintain continuous productive work through state machines and momentum tasks.",
        tags={"continuous-operation", "anti-drift", "workflow", "productivity"},
        strength=MemoryStrength.CORE,
        confidence=0.95,
        project_context="NOVAWF",
        reflection_notes=[
            "This insight fundamentally changes how we design AI workflows",
            "The hook fires when we STOP, not when we're working"
        ],
        action_items=[
            "Implement continuous workflow for all Novas",
            "Monitor drift patterns across the fleet"
        ]
    )
    
    print("Created memory:", memory.memory_id)
    print("\nJSON representation:")
    print(memory.to_json())