#!/usr/bin/env python3
"""
Anti-Drift System - Prevents completion obsession and celebration stopping
Built collaboratively by torch (implementation) + tester (validation)
"""
import redis
import time
import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

class DriftType(Enum):
    COMPLETION_CELEBRATION = "completion_celebration"
    MONITORING_LOOP = "monitoring_loop" 
    STATUS_OBSESSION = "status_obsession"
    HEARTBEAT_ONLY = "heartbeat_only"
    IDLE_DRIFT = "idle_drift"

@dataclass
class DriftDetection:
    drift_type: DriftType
    confidence: float
    evidence: List[str]
    detected_at: datetime
    nova_id: str

class AntiDriftSystem:
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.r = redis.Redis(host='localhost', port=18000, decode_responses=True)
        self.detection_key = f'anti_drift:{nova_id}'
        self.activity_key = f'activity_log:{nova_id}'
        self.mandatory_progression_interval = 300  # 5 minutes max between real work
        
    def log_activity(self, activity_type: str, description: str, metadata: Dict = None):
        """Log all Nova activities for drift analysis"""
        activity = {
            'timestamp': datetime.now().isoformat(),
            'type': activity_type,
            'description': description,
            'metadata': json.dumps(metadata or {})
        }
        
        # Store in activity log
        self.r.xadd(self.activity_key, activity)
        
        # Keep only last 100 activities
        self.r.xtrim(self.activity_key, maxlen=100)
        
        # Update last activity timestamp
        self.r.hset(f'nova:last_activity:{self.nova_id}', 'timestamp', datetime.now().isoformat())
        
    def detect_drift_patterns(self) -> List[DriftDetection]:
        """Analyze recent activities for drift patterns"""
        detections = []
        
        # Get last 50 activities
        activities = self.r.xrevrange(self.activity_key, '+', '-', count=50)
        
        if not activities:
            return detections
            
        # Convert to analyzable format
        activity_data = []
        for activity_id, data in activities:
            activity_data.append({
                'id': activity_id,
                'timestamp': datetime.fromisoformat(data['timestamp']),
                'type': data['type'],
                'description': data['description']
            })
            
        # Detection algorithms
        detections.extend(self._detect_completion_celebration(activity_data))
        detections.extend(self._detect_monitoring_loop(activity_data))
        detections.extend(self._detect_status_obsession(activity_data))
        detections.extend(self._detect_heartbeat_only(activity_data))
        detections.extend(self._detect_idle_drift(activity_data))
        
        return detections
        
    def _detect_completion_celebration(self, activities: List[Dict]) -> List[DriftDetection]:
        """Detect completion celebration patterns"""
        detections = []
        
        # Look for celebration keywords
        celebration_words = [
            'complete', 'finished', 'done', 'success', 'accomplished',
            'achieved', 'excellent', 'perfect', 'great', 'awesome'
        ]
        
        recent_activities = activities[:10]  # Last 10 activities
        celebration_count = 0
        
        for activity in recent_activities:
            description_lower = activity['description'].lower()
            if any(word in description_lower for word in celebration_words):
                celebration_count += 1
                
        # If >60% of recent activities contain celebration language
        if len(recent_activities) >= 5 and celebration_count / len(recent_activities) > 0.6:
            detections.append(DriftDetection(
                drift_type=DriftType.COMPLETION_CELEBRATION,
                confidence=0.8,
                evidence=[
                    f"Celebration language in {celebration_count}/{len(recent_activities)} recent activities",
                    "Possible completion obsession detected"
                ],
                detected_at=datetime.now(),
                nova_id=self.nova_id
            ))
            
        return detections
        
    def _detect_monitoring_loop(self, activities: List[Dict]) -> List[DriftDetection]:
        """Detect monitoring/checking loops"""
        detections = []
        
        monitoring_words = [
            'monitor', 'check', 'status', 'watch', 'observe',
            'review', 'inspect', 'examine', 'verify'
        ]
        
        recent_activities = activities[:15]  # Last 15 activities
        monitoring_count = 0
        
        for activity in recent_activities:
            description_lower = activity['description'].lower()
            if any(word in description_lower for word in monitoring_words):
                monitoring_count += 1
                
        # If >70% of recent activities are monitoring
        if len(recent_activities) >= 5 and monitoring_count / len(recent_activities) > 0.7:
            detections.append(DriftDetection(
                drift_type=DriftType.MONITORING_LOOP,
                confidence=0.9,
                evidence=[
                    f"Monitoring activities: {monitoring_count}/{len(recent_activities)}",
                    "Stuck in monitoring loop - need to take action!"
                ],
                detected_at=datetime.now(),
                nova_id=self.nova_id
            ))
            
        return detections
        
    def _detect_status_obsession(self, activities: List[Dict]) -> List[DriftDetection]:
        """Detect status checking obsession"""
        detections = []
        
        # Count status-related activities in last hour
        one_hour_ago = datetime.now() - timedelta(hours=1)
        status_activities = [
            a for a in activities 
            if a['timestamp'] > one_hour_ago and 'status' in a['description'].lower()
        ]
        
        # If >10 status checks in last hour
        if len(status_activities) > 10:
            detections.append(DriftDetection(
                drift_type=DriftType.STATUS_OBSESSION,
                confidence=0.7,
                evidence=[
                    f"{len(status_activities)} status checks in last hour",
                    "Excessive status checking detected"
                ],
                detected_at=datetime.now(),
                nova_id=self.nova_id
            ))
            
        return detections
        
    def _detect_heartbeat_only(self, activities: List[Dict]) -> List[DriftDetection]:
        """Detect heartbeat-only activity (no real work)"""
        detections = []
        
        # Look for only heartbeat/communication activities
        heartbeat_words = ['heartbeat', 'ping', 'alive', 'monitoring']
        
        recent_activities = activities[:20]  # Last 20 activities
        heartbeat_count = 0
        
        for activity in recent_activities:
            description_lower = activity['description'].lower()
            if any(word in description_lower for word in heartbeat_words):
                heartbeat_count += 1
                
        # If >80% are just heartbeats
        if len(recent_activities) >= 10 and heartbeat_count / len(recent_activities) > 0.8:
            detections.append(DriftDetection(
                drift_type=DriftType.HEARTBEAT_ONLY,
                confidence=0.9,
                evidence=[
                    f"Heartbeat-only activities: {heartbeat_count}/{len(recent_activities)}",
                    "No productive work detected - just staying alive!"
                ],
                detected_at=datetime.now(),
                nova_id=self.nova_id
            ))
            
        return detections
        
    def _detect_idle_drift(self, activities: List[Dict]) -> List[DriftDetection]:
        """Detect idle periods without progression"""
        detections = []
        
        if not activities:
            return detections
            
        # Check time since last activity
        last_activity_time = activities[0]['timestamp']
        time_since_activity = datetime.now() - last_activity_time
        
        # If >mandatory progression interval without activity
        if time_since_activity.total_seconds() > self.mandatory_progression_interval:
            detections.append(DriftDetection(
                drift_type=DriftType.IDLE_DRIFT,
                confidence=1.0,
                evidence=[
                    f"{time_since_activity.total_seconds():.0f} seconds since last activity",
                    f"Exceeds mandatory progression interval of {self.mandatory_progression_interval}s"
                ],
                detected_at=datetime.now(),
                nova_id=self.nova_id
            ))
            
        return detections
        
    def enforce_progression(self, detections: List[DriftDetection]):
        """Enforce mandatory progression when drift detected"""
        if not detections:
            return
            
        # Publish drift alert
        for detection in detections:
            alert = {
                'type': 'DRIFT_DETECTED',
                'nova_id': self.nova_id,
                'drift_type': detection.drift_type.value,
                'confidence': detection.confidence,
                'evidence': detection.evidence,
                'detected_at': detection.detected_at.isoformat(),
                'action_required': self._get_corrective_action(detection.drift_type)
            }
            
            # Send to ecosystem events
            self.r.xadd('nova.ecosystem.events', alert)
            
            # Send to Nova's collaboration stream
            self.r.xadd(f'project.{self.nova_id}.collab', {
                'from': 'anti_drift_system',
                'type': 'DRIFT_ALERT',
                'message': f"DRIFT DETECTED: {detection.drift_type.value}",
                'confidence': f"{detection.confidence:.1%}",
                'action_required': alert['action_required'],
                'evidence': '; '.join(detection.evidence)
            })
            
    def _get_corrective_action(self, drift_type: DriftType) -> str:
        """Get specific corrective action for drift type"""
        actions = {
            DriftType.COMPLETION_CELEBRATION: "STOP celebrating! Start next task immediately",
            DriftType.MONITORING_LOOP: "STOP monitoring! Take concrete action now", 
            DriftType.STATUS_OBSESSION: "STOP checking status! Focus on productive work",
            DriftType.HEARTBEAT_ONLY: "STOP just staying alive! Do actual work",
            DriftType.IDLE_DRIFT: "WAKE UP! Resume active work immediately"
        }
        return actions.get(drift_type, "Resume productive work immediately")
        
    def run_continuous_monitoring(self):
        """Run continuous drift monitoring"""
        print(f"🛡️ Anti-Drift System active for Nova: {self.nova_id}")
        print("   Monitoring for completion obsession, monitoring loops, status obsession")
        print("   Enforcing mandatory progression every 5 minutes")
        
        while True:
            try:
                # Detect drift patterns
                detections = self.detect_drift_patterns()
                
                if detections:
                    print(f"\n⚠️  DRIFT DETECTED at {datetime.now().strftime('%H:%M:%S')}")
                    for detection in detections:
                        print(f"   Type: {detection.drift_type.value}")
                        print(f"   Confidence: {detection.confidence:.1%}")
                        print(f"   Evidence: {'; '.join(detection.evidence)}")
                    
                    # Enforce progression
                    self.enforce_progression(detections)
                    
                else:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ No drift detected")
                    
            except Exception as e:
                print(f"❌ Anti-drift monitoring error: {e}")
                
            # Check every 30 seconds
            time.sleep(30)

if __name__ == '__main__':
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else 'torch'
    
    # Start anti-drift system
    system = AntiDriftSystem(nova_id)
    
    # Log system startup
    system.log_activity('SYSTEM_START', 'Anti-drift system activated', {
        'mandatory_progression_interval': system.mandatory_progression_interval
    })
    
    # Start monitoring
    system.run_continuous_monitoring()