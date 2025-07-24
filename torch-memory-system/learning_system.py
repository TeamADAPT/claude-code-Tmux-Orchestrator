#!/usr/bin/env python3
"""
Torch Personal Memory System - Learning & Reflection Engine
Accelerated learning through pattern recognition and reflection

Project: TORCHX-2 - Build Personal Memory & Learning System
Owner: Nova Torch
Created: 2025-07-24
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Set, Tuple
from collections import defaultdict, Counter

from memory_schema import (
    LearningInsight, MemoryType, MemoryStrength,
    LearningDomain, MemoryConnection, LearningPathway,
    ReflectionProtocol, DEFAULT_REFLECTION_PROTOCOLS
)
from memory_storage import MemoryStorage

logger = logging.getLogger('torch.learning')

class PatternRecognizer:
    """Identifies patterns across memories for accelerated learning"""
    
    def __init__(self, storage: MemoryStorage):
        self.storage = storage
    
    def find_recurring_patterns(self, memories: List[LearningInsight]) -> Dict[str, List[Dict]]:
        """Identify recurring patterns in memories"""
        patterns = {
            'technical_patterns': [],
            'problem_solving_patterns': [],
            'collaboration_patterns': [],
            'growth_patterns': []
        }
        
        # Analyze technical patterns
        tech_memories = [m for m in memories if m.memory_type == MemoryType.TECHNICAL]
        if tech_memories:
            # Find common tags
            tag_counter = Counter()
            for memory in tech_memories:
                tag_counter.update(memory.tags)
            
            common_tags = tag_counter.most_common(5)
            for tag, count in common_tags:
                if count >= 3:  # Pattern threshold
                    patterns['technical_patterns'].append({
                        'pattern': f"Recurring technical theme: {tag}",
                        'frequency': count,
                        'examples': [m.title for m in tech_memories if tag in m.tags][:3]
                    })
        
        # Analyze problem-solving patterns
        procedural_memories = [m for m in memories if m.memory_type == MemoryType.PROCEDURAL]
        if procedural_memories:
            # Look for solution approaches
            solution_keywords = ['solved', 'fixed', 'resolved', 'overcame', 'implemented']
            for keyword in solution_keywords:
                matching = [m for m in procedural_memories if keyword in m.content.lower()]
                if len(matching) >= 2:
                    patterns['problem_solving_patterns'].append({
                        'pattern': f"Solution approach using '{keyword}'",
                        'frequency': len(matching),
                        'examples': [m.title for m in matching][:3]
                    })
        
        # Analyze collaboration patterns
        collab_memories = [m for m in memories if m.memory_type == MemoryType.COLLABORATIVE]
        if collab_memories:
            # Find successful collaboration indicators
            success_indicators = ['successful', 'effective', 'productive', 'synergy']
            for indicator in success_indicators:
                matching = [m for m in collab_memories if indicator in m.content.lower()]
                if matching:
                    patterns['collaboration_patterns'].append({
                        'pattern': f"Successful collaboration through {indicator}",
                        'frequency': len(matching),
                        'examples': [m.title for m in matching][:2]
                    })
        
        # Analyze growth patterns
        strong_memories = [m for m in memories if m.strength.value >= MemoryStrength.STRONG.value]
        if strong_memories:
            # Group by domain to see growth areas
            domain_growth = defaultdict(list)
            for memory in strong_memories:
                domain_growth[memory.domain.value].append(memory)
            
            for domain, domain_memories in domain_growth.items():
                if len(domain_memories) >= 2:
                    patterns['growth_patterns'].append({
                        'pattern': f"Strong growth in {domain}",
                        'frequency': len(domain_memories),
                        'examples': [m.title for m in domain_memories][:3]
                    })
        
        return patterns
    
    def identify_knowledge_gaps(self, memories: List[LearningInsight]) -> List[Dict]:
        """Identify areas where knowledge might be lacking"""
        gaps = []
        
        # Check domain coverage
        domain_coverage = defaultdict(int)
        for memory in memories:
            domain_coverage[memory.domain.value] += 1
        
        # Identify underrepresented domains
        all_domains = [d.value for d in LearningDomain]
        for domain in all_domains:
            if domain_coverage[domain] < 3:  # Threshold for adequate coverage
                gaps.append({
                    'gap_type': 'domain_coverage',
                    'domain': domain,
                    'current_memories': domain_coverage[domain],
                    'recommendation': f"Explore more in {domain} domain"
                })
        
        # Check for disconnected memories (knowledge islands)
        disconnected = []
        for memory in memories:
            if len(memory.connections) == 0:
                disconnected.append(memory)
        
        if len(disconnected) > 5:
            gaps.append({
                'gap_type': 'knowledge_integration',
                'count': len(disconnected),
                'recommendation': "Connect isolated insights to build knowledge network"
            })
        
        # Check for low-confidence areas
        low_confidence = [m for m in memories if m.confidence < 0.6]
        if low_confidence:
            topics = Counter(m.domain.value for m in low_confidence)
            for domain, count in topics.most_common(3):
                gaps.append({
                    'gap_type': 'confidence_gap',
                    'domain': domain,
                    'count': count,
                    'recommendation': f"Strengthen understanding in {domain}"
                })
        
        return gaps
    
    def suggest_connections(self, memory: LearningInsight, 
                          all_memories: List[LearningInsight]) -> List[Tuple[str, str, float]]:
        """Suggest potential connections for a memory"""
        suggestions = []
        
        # Don't suggest connections to self
        candidates = [m for m in all_memories if m.memory_id != memory.memory_id]
        
        for candidate in candidates:
            # Skip if already connected
            if any(c.target_memory_id == candidate.memory_id for c in memory.connections):
                continue
            
            # Calculate similarity score
            score = 0.0
            
            # Same domain bonus
            if memory.domain == candidate.domain:
                score += 0.3
            
            # Same type bonus
            if memory.memory_type == candidate.memory_type:
                score += 0.2
            
            # Tag overlap
            tag_overlap = len(memory.tags.intersection(candidate.tags))
            if tag_overlap > 0:
                score += 0.1 * tag_overlap
            
            # Project context match
            if memory.project_context and memory.project_context == candidate.project_context:
                score += 0.3
            
            # Temporal proximity (memories created close in time)
            time_diff = abs((memory.created_at - candidate.created_at).total_seconds())
            if time_diff < 3600:  # Within an hour
                score += 0.2
            elif time_diff < 86400:  # Within a day
                score += 0.1
            
            if score >= 0.4:  # Threshold for suggestion
                # Determine connection type
                if memory.domain == candidate.domain:
                    connection_type = 'similar'
                elif any(tag in candidate.tags for tag in memory.tags):
                    connection_type = 'related'
                else:
                    connection_type = 'cross_domain'
                
                suggestions.append((candidate.memory_id, connection_type, score))
        
        # Sort by score
        suggestions.sort(key=lambda x: x[2], reverse=True)
        
        return suggestions[:5]  # Top 5 suggestions

class LearningEngine:
    """Main learning system orchestrating memory, patterns, and reflection"""
    
    def __init__(self, nova_id: str = "torch"):
        self.nova_id = nova_id
        self.storage = MemoryStorage()
        self.pattern_recognizer = PatternRecognizer(self.storage)
        self.reflection_protocols = DEFAULT_REFLECTION_PROTOCOLS
        
        logger.info(f"Learning engine initialized for {nova_id}")
    
    def record_insight(self, 
                      title: str,
                      content: str,
                      memory_type: MemoryType = MemoryType.TECHNICAL,
                      domain: LearningDomain = LearningDomain.SOFTWARE_ENGINEERING,
                      tags: Optional[Set[str]] = None,
                      strength: MemoryStrength = MemoryStrength.MODERATE,
                      project_context: Optional[str] = None,
                      parent_memory_id: Optional[str] = None) -> str:
        """Record a new learning insight"""
        # Create memory
        memory = LearningInsight(
            memory_type=memory_type,
            domain=domain,
            title=title,
            content=content,
            tags=tags or set(),
            strength=strength,
            confidence=0.8,  # Default confidence
            project_context=project_context,
            parent_memory_id=parent_memory_id,
            session_id=f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        )
        
        # Store it
        success = self.storage.store_memory(memory)
        
        if success:
            # Check for pattern connections
            recent_memories = self.storage.search_memories(limit=50)
            suggestions = self.pattern_recognizer.suggest_connections(memory, recent_memories)
            
            # Auto-create strong connections
            for target_id, connection_type, score in suggestions:
                if score >= 0.6:  # Strong similarity
                    self.storage.create_connection(
                        memory.memory_id, target_id, connection_type, score,
                        f"Auto-connected based on similarity score {score:.2f}"
                    )
            
            logger.info(f"Recorded insight: {memory.memory_id} with {len(suggestions)} potential connections")
            
            # Check if reflection is needed
            self._check_reflection_triggers()
            
            return memory.memory_id
        
        return ""
    
    def reflect(self, trigger: str = "manual") -> Dict[str, Any]:
        """Perform reflection based on trigger"""
        # Find appropriate protocol
        protocol = next((p for p in self.reflection_protocols if p.trigger == trigger), None)
        if not protocol:
            protocol = self.reflection_protocols[0]  # Default to daily review
        
        # Get relevant memories for reflection
        if trigger == "daily":
            memories = self.storage.search_memories(limit=100)
            time_window = "today"
        elif trigger == "project_complete":
            # Would filter by project context
            memories = self.storage.search_memories(limit=200)
            time_window = "this project"
        else:
            memories = self.storage.search_memories(limit=50)
            time_window = "recent"
        
        # Run pattern recognition
        patterns = self.pattern_recognizer.find_recurring_patterns(memories)
        gaps = self.pattern_recognizer.identify_knowledge_gaps(memories)
        
        # Generate insights
        insights = []
        
        # Technical insights
        for pattern in patterns['technical_patterns']:
            insights.append(f"Technical pattern: {pattern['pattern']} (seen {pattern['frequency']} times)")
        
        # Problem-solving insights
        for pattern in patterns['problem_solving_patterns']:
            insights.append(f"Effective approach: {pattern['pattern']}")
        
        # Growth insights
        for pattern in patterns['growth_patterns']:
            insights.append(f"Growth area: {pattern['pattern']}")
        
        # Action items from gaps
        action_items = []
        for gap in gaps[:5]:  # Top 5 gaps
            action_items.append(gap['recommendation'])
        
        # Store reflection
        reflection_content = f"""
        Reflection for {time_window}:
        
        Patterns identified: {len(patterns['technical_patterns']) + len(patterns['problem_solving_patterns'])}
        Knowledge gaps found: {len(gaps)}
        Total memories analyzed: {len(memories)}
        """
        
        self.storage.store_reflection(
            protocol, reflection_content, 
            [str(p) for p in patterns.values()], 
            action_items
        )
        
        return {
            'trigger': trigger,
            'protocol': protocol.name,
            'memories_analyzed': len(memories),
            'insights': insights,
            'patterns': patterns,
            'gaps': gaps,
            'action_items': action_items,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_learning_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get a summary of learning progress"""
        # Get metrics
        metrics = self.storage.get_memory_metrics(days)
        
        # Get recent strong memories
        strong_memories = self.storage.search_memories(
            min_strength=MemoryStrength.STRONG,
            limit=10
        )
        
        # Calculate progress
        if days > 7:
            prev_metrics = self.storage.get_memory_metrics(days * 2)
            velocity_change = metrics['learning_velocity'] - prev_metrics.get('learning_velocity', 0)
        else:
            velocity_change = 0
        
        summary = {
            'period_days': days,
            'total_insights': metrics['total_memories'],
            'learning_velocity': f"{metrics['learning_velocity']:.2f} insights/day",
            'velocity_trend': 'increasing' if velocity_change > 0 else 'stable',
            'retention_rate': f"{metrics['retention_rate']:.1%}",
            'connection_density': f"{metrics['connection_density']:.2%}",
            'strongest_insights': [
                {'title': m.title, 'strength': m.strength.value}
                for m in strong_memories
            ],
            'knowledge_distribution': metrics['memories_by_domain'],
            'recommended_focus': self._get_learning_recommendations(metrics)
        }
        
        return summary
    
    def create_learning_pathway(self, 
                              title: str,
                              domain: LearningDomain,
                              milestones: List[Dict[str, Any]]) -> str:
        """Create a structured learning pathway"""
        pathway = LearningPathway(
            domain=domain,
            title=title,
            description=f"Learning pathway for {title}",
            milestones=milestones
        )
        
        success = self.storage.store_learning_pathway(pathway)
        
        if success:
            logger.info(f"Created learning pathway: {pathway.pathway_id}")
            return pathway.pathway_id
        
        return ""
    
    def _check_reflection_triggers(self):
        """Check if any reflection triggers are met"""
        # Check for daily reflection
        last_daily = self.storage.conn.execute("""
        SELECT MAX(created_at) FROM reflections WHERE trigger = 'daily'
        """).fetchone()[0]
        
        if last_daily:
            last_daily_time = datetime.fromisoformat(last_daily)
            if datetime.now() - last_daily_time > timedelta(hours=24):
                logger.info("Daily reflection trigger activated")
                # Could auto-trigger or notify
    
    def _get_learning_recommendations(self, metrics: Dict) -> List[str]:
        """Generate learning recommendations based on metrics"""
        recommendations = []
        
        # Check velocity
        if metrics['learning_velocity'] < 2.0:
            recommendations.append("Increase learning velocity by exploring new topics daily")
        
        # Check retention
        if metrics['retention_rate'] < 0.7:
            recommendations.append("Review and reinforce existing knowledge more frequently")
        
        # Check connections
        if metrics['connection_density'] < 0.1:
            recommendations.append("Build more connections between insights for better integration")
        
        # Check domain balance
        domains = metrics['memories_by_domain']
        if domains:
            max_domain = max(domains.values())
            min_domain = min(domains.values())
            if max_domain > min_domain * 3:
                recommendations.append("Balance learning across different domains")
        
        return recommendations

if __name__ == "__main__":
    # Test learning system
    engine = LearningEngine("torch")
    
    # Record some insights
    memory_id = engine.record_insight(
        title="Learning system architecture complete",
        content="Built a sophisticated learning system with pattern recognition, reflection protocols, and pathway tracking.",
        memory_type=MemoryType.TECHNICAL,
        domain=LearningDomain.SOFTWARE_ENGINEERING,
        tags={"learning-system", "memory", "architecture", "TORCHX-2"},
        strength=MemoryStrength.CORE,
        project_context="TORCHX-2"
    )
    
    print(f"Recorded insight: {memory_id}")
    
    # Perform reflection
    reflection = engine.reflect("manual")
    print(f"\nReflection insights: {len(reflection['insights'])}")
    for insight in reflection['insights']:
        print(f"  - {insight}")
    
    # Get learning summary
    summary = engine.get_learning_summary(7)
    print(f"\nLearning Summary:")
    print(json.dumps(summary, indent=2))