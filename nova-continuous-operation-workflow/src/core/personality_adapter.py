#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - Personality Adapter
Adapts workflow behavior based on Nova personality profiles

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 3 - Distribution & Customization
"""

import json
import logging
from datetime import datetime, time
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('novawf.personality')

class PersonalityType(Enum):
    """Nova personality archetypes"""
    ANALYTICAL = "analytical"
    CREATIVE = "creative"
    EFFICIENT = "efficient"
    COLLABORATIVE = "collaborative"
    GUARDIAN = "guardian"
    BALANCED = "balanced"

class TimeOfDay(Enum):
    """Time periods for circadian adjustments"""
    MORNING = "morning"      # 6:00 - 11:59
    AFTERNOON = "afternoon"  # 12:00 - 17:59
    EVENING = "evening"      # 18:00 - 22:59
    NIGHT = "night"          # 23:00 - 5:59

@dataclass
class WorkflowPersonality:
    """Personality-driven workflow configuration"""
    personality_type: PersonalityType
    work_style: str
    communication_style: str
    priority_focus: str
    celebration_style: str
    
    # Task preferences
    preferred_batch_size: int
    deep_work_duration_minutes: int
    break_duration_minutes: int
    max_concurrent_tasks: int
    
    # Workflow adjustments
    phase_duration_multiplier: float
    celebration_duration_seconds: int
    quality_check_frequency: str
    
    # Dynamic modifiers
    current_energy_level: float = 1.0
    current_focus_bonus: float = 0.0
    
    def to_config(self) -> Dict[str, Any]:
        """Convert to configuration dictionary"""
        return {
            'personality_type': self.personality_type.value,
            'work_style': self.work_style,
            'communication_style': self.communication_style,
            'priority_focus': self.priority_focus,
            'celebration_style': self.celebration_style,
            'task_preferences': {
                'preferred_batch_size': self.preferred_batch_size,
                'deep_work_duration_minutes': self.deep_work_duration_minutes,
                'break_duration_minutes': self.break_duration_minutes,
                'max_concurrent_tasks': self.max_concurrent_tasks
            },
            'workflow_adjustments': {
                'phase_duration_multiplier': self.phase_duration_multiplier,
                'celebration_duration_seconds': self.celebration_duration_seconds,
                'quality_check_frequency': self.quality_check_frequency
            },
            'dynamic_state': {
                'energy_level': self.current_energy_level,
                'focus_bonus': self.current_focus_bonus
            }
        }

class PersonalityAdapter:
    """
    Adapts workflow behavior based on Nova personality.
    Provides circadian rhythm adjustments and workload adaptation.
    """
    
    def __init__(self, nova_id: str, config_path: Optional[str] = None):
        self.nova_id = nova_id
        self.config_path = config_path or f"/nfs/novas/{nova_id}/continuous-workflow/config/nova_config.json"
        
        # Load personality profiles
        self.profiles = self._load_personality_profiles()
        
        # Load Nova configuration
        self.nova_config = self._load_nova_config()
        
        # Initialize personality
        self.personality = self._initialize_personality()
        
        logger.info(f"Personality adapter initialized for {nova_id} with {self.personality.personality_type.value} profile")
    
    def _load_personality_profiles(self) -> Dict:
        """Load personality profile definitions"""
        profile_path = Path(__file__).parent.parent.parent / "templates" / "personality-profiles.json"
        
        try:
            with open(profile_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning("Personality profiles not found, using defaults")
            return self._get_default_profiles()
    
    def _load_nova_config(self) -> Dict:
        """Load Nova-specific configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Nova config not found at {self.config_path}, using defaults")
            return self._get_default_config()
    
    def _initialize_personality(self) -> WorkflowPersonality:
        """Initialize personality from config or defaults"""
        # Get personality type from config
        personality_config = self.nova_config.get('personality_config', {})
        personality_type = personality_config.get('work_style', 'balanced')
        
        # Map to personality profile
        if personality_type in self.profiles.get('personality_profiles', {}):
            profile = self.profiles['personality_profiles'][personality_type]
        else:
            profile = self.profiles['personality_profiles']['balanced']
        
        # Create personality object
        return WorkflowPersonality(
            personality_type=PersonalityType(personality_type),
            work_style=profile['work_style'],
            communication_style=profile['communication_style'],
            priority_focus=profile['priority_focus'],
            celebration_style=profile['celebration_style'],
            preferred_batch_size=profile['task_preferences']['preferred_batch_size'],
            deep_work_duration_minutes=profile['task_preferences']['deep_work_duration_minutes'],
            break_duration_minutes=profile['task_preferences']['break_duration_minutes'],
            max_concurrent_tasks=profile['task_preferences']['max_concurrent_tasks'],
            phase_duration_multiplier=profile['workflow_adjustments']['phase_duration_multiplier'],
            celebration_duration_seconds=profile['workflow_adjustments']['celebration_duration_seconds'],
            quality_check_frequency=profile['workflow_adjustments']['quality_check_frequency']
        )
    
    def adapt_to_current_conditions(self) -> WorkflowPersonality:
        """
        Adapt personality based on current time and workload.
        Returns updated personality with dynamic adjustments.
        """
        # Get time of day
        current_hour = datetime.now().hour
        time_of_day = self._get_time_of_day(current_hour)
        
        # Apply time-based modifiers
        time_modifiers = self.profiles.get('personality_modifiers', {}).get('time_of_day', {}).get(time_of_day.value, {})
        
        self.personality.current_energy_level = time_modifiers.get('energy_multiplier', 1.0)
        self.personality.current_focus_bonus = time_modifiers.get('focus_bonus', 0.0)
        
        # Log adaptation
        logger.debug(f"Adapted to {time_of_day.value}: energy={self.personality.current_energy_level}, focus_bonus={self.personality.current_focus_bonus}")
        
        return self.personality
    
    def get_task_batch_size(self, current_workload: str = "normal") -> int:
        """Get adapted task batch size based on personality and workload"""
        base_size = self.personality.preferred_batch_size
        
        # Apply workload modifier
        workload_modifiers = self.profiles.get('personality_modifiers', {}).get('workload_adjustments', {})
        workload_mult = workload_modifiers.get(current_workload, {}).get('batch_size_multiplier', 1.0)
        
        # Apply energy level
        energy_mult = self.personality.current_energy_level
        
        # Calculate final batch size
        adapted_size = int(base_size * workload_mult * energy_mult)
        
        # Ensure reasonable bounds
        return max(1, min(adapted_size, self.personality.max_concurrent_tasks))
    
    def get_work_duration(self) -> int:
        """Get adapted work duration in minutes"""
        base_duration = self.personality.deep_work_duration_minutes
        
        # Apply focus bonus
        focus_adjustment = 1.0 + self.personality.current_focus_bonus
        
        # Apply personality multiplier
        personality_mult = self.personality.phase_duration_multiplier
        
        # Calculate final duration
        adapted_duration = int(base_duration * focus_adjustment * personality_mult)
        
        # Ensure reasonable bounds (15-90 minutes)
        return max(15, min(adapted_duration, 90))
    
    def get_break_duration(self, just_completed_tasks: int = 0) -> int:
        """Get adapted break duration based on work completed"""
        base_break = self.personality.break_duration_minutes
        
        # Longer break if more tasks completed
        if just_completed_tasks > self.personality.preferred_batch_size:
            base_break = int(base_break * 1.5)
        
        # Apply energy level (lower energy = longer breaks)
        energy_adjustment = 2.0 - self.personality.current_energy_level
        
        # Calculate final break
        adapted_break = int(base_break * energy_adjustment)
        
        # Ensure reasonable bounds (3-30 minutes)
        return max(3, min(adapted_break, 30))
    
    def get_celebration_duration(self, achievement_level: str = "normal") -> int:
        """Get celebration duration based on personality and achievement"""
        base_celebration = self.personality.celebration_duration_seconds
        
        # Adjust for achievement level
        achievement_multipliers = {
            "minor": 0.5,
            "normal": 1.0,
            "major": 2.0,
            "milestone": 3.0
        }
        
        mult = achievement_multipliers.get(achievement_level, 1.0)
        
        # Apply celebration style
        if self.personality.celebration_style == "brief_acknowledgment":
            mult *= 0.5
        elif self.personality.celebration_style == "enthusiastic":
            mult *= 1.5
        
        # Calculate final duration
        adapted_duration = int(base_celebration * mult)
        
        # Ensure bounds (30-600 seconds)
        return max(30, min(adapted_duration, 600))
    
    def should_perform_quality_check(self, context: Dict[str, Any]) -> bool:
        """Determine if quality check should be performed based on personality"""
        frequency = self.personality.quality_check_frequency
        
        if frequency == "every_task":
            return True
        elif frequency == "every_operation":
            return True
        elif frequency == "batch_completion":
            return context.get('batch_completed', False)
        elif frequency == "phase_end":
            return context.get('phase_ending', False)
        elif frequency == "after_coordination":
            return context.get('just_coordinated', False)
        elif frequency == "adaptive":
            # Adaptive based on error rate
            error_rate = context.get('recent_error_rate', 0.0)
            return error_rate > 0.1  # Check if error rate > 10%
        
        return False
    
    def _get_time_of_day(self, hour: int) -> TimeOfDay:
        """Map hour to time of day period"""
        if 6 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= hour < 23:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT
    
    def _get_default_profiles(self) -> Dict:
        """Default personality profiles if file not found"""
        return {
            "personality_profiles": {
                "balanced": {
                    "work_style": "balanced",
                    "communication_style": "adaptive",
                    "priority_focus": "quality_and_speed",
                    "celebration_style": "proportional",
                    "task_preferences": {
                        "preferred_batch_size": 5,
                        "deep_work_duration_minutes": 35,
                        "break_duration_minutes": 8,
                        "max_concurrent_tasks": 4
                    },
                    "workflow_adjustments": {
                        "phase_duration_multiplier": 1.0,
                        "celebration_duration_seconds": 180,
                        "quality_check_frequency": "adaptive"
                    }
                }
            },
            "personality_modifiers": {
                "time_of_day": {
                    "morning": {"energy_multiplier": 1.2, "focus_bonus": 0.1},
                    "afternoon": {"energy_multiplier": 0.9, "focus_bonus": 0},
                    "evening": {"energy_multiplier": 0.8, "focus_bonus": -0.1},
                    "night": {"energy_multiplier": 1.1, "focus_bonus": 0.2}
                }
            }
        }
    
    def _get_default_config(self) -> Dict:
        """Default Nova configuration"""
        return {
            "nova_id": self.nova_id,
            "personality_config": {
                "work_style": "balanced"
            }
        }
    
    def save_adapted_config(self):
        """Save current adapted configuration"""
        adapted_config = self.personality.to_config()
        
        # Merge with existing config
        self.nova_config['personality_adaptation'] = adapted_config
        self.nova_config['last_adaptation'] = datetime.now().isoformat()
        
        # Save to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.nova_config, f, indent=2)
            logger.info(f"Saved adapted configuration for {self.nova_id}")
        except Exception as e:
            logger.error(f"Failed to save adapted config: {e}")

if __name__ == "__main__":
    # Test personality adapter
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    adapter = PersonalityAdapter(nova_id)
    
    # Test adaptation
    personality = adapter.adapt_to_current_conditions()
    print(f"Nova {nova_id} personality: {personality.personality_type.value}")
    print(f"Current energy: {personality.current_energy_level}")
    print(f"Focus bonus: {personality.current_focus_bonus}")
    
    # Test work parameters
    print(f"\nWork parameters:")
    print(f"Batch size: {adapter.get_task_batch_size()}")
    print(f"Work duration: {adapter.get_work_duration()} minutes")
    print(f"Break duration: {adapter.get_break_duration()} minutes")
    print(f"Celebration (normal): {adapter.get_celebration_duration('normal')} seconds")
    
    # Test quality check
    contexts = [
        {"batch_completed": True},
        {"phase_ending": True},
        {"recent_error_rate": 0.15}
    ]
    
    print(f"\nQuality check decisions:")
    for ctx in contexts:
        should_check = adapter.should_perform_quality_check(ctx)
        print(f"Context {ctx}: {should_check}")