#!/usr/bin/env python3
"""
Nova Continuous Operation Workflow - API Guardian
Critical safety component to prevent API hammering and quota exhaustion

Owner: Nova Torch
Project: NOVAWF - Nova Continuous Operation Workflow
Phase: 2 - Safety Implementation (CRITICAL)
"""

import time
import redis
import logging
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger('novawf.safety.api_guardian')

class RateLimitType(Enum):
    """Types of rate limits enforced"""
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    REQUESTS_PER_DAY = "requests_per_day"
    CONCURRENT_REQUESTS = "concurrent_requests"
    BURST_THRESHOLD = "burst_threshold"

@dataclass
class SafetyValidation:
    """Result of safety validation check"""
    is_safe: bool
    violation_type: Optional[str] = None
    mandatory_action: Optional[str] = None
    cooldown_required: bool = False
    cooldown_duration: int = 300  # 5 minutes default
    details: Optional[Dict] = None

class APIGuardian:
    """
    Critical safety component preventing API hammering and quota exhaustion.
    This is the last line of defense against runaway API calls.
    """
    
    # HARD LIMITS - These are conservative to ensure safety
    HARD_LIMITS = {
        RateLimitType.REQUESTS_PER_MINUTE: 25,      # Hard limit: 25 req/min
        RateLimitType.REQUESTS_PER_HOUR: 400,       # Hard limit: 400 req/hour  
        RateLimitType.REQUESTS_PER_DAY: 8000,       # Hard limit: 8000 req/day
        RateLimitType.CONCURRENT_REQUESTS: 3,       # Hard limit: 3 concurrent
        RateLimitType.BURST_THRESHOLD: 10,          # Max 10 requests in 30 seconds
    }
    
    # Cooldown durations for different violations
    COOLDOWN_DURATIONS = {
        RateLimitType.REQUESTS_PER_MINUTE: 300,     # 5 minutes
        RateLimitType.REQUESTS_PER_HOUR: 900,       # 15 minutes
        RateLimitType.REQUESTS_PER_DAY: 3600,       # 1 hour
        RateLimitType.CONCURRENT_REQUESTS: 180,     # 3 minutes
        RateLimitType.BURST_THRESHOLD: 600,         # 10 minutes
    }
    
    def __init__(self, nova_id: str, redis_port: int = 18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(
            host='localhost', 
            port=redis_port, 
            decode_responses=True, 
            password='adapt123'
        )
        
        # In-memory tracking for fast access
        self.request_history = deque(maxlen=1000)
        self.concurrent_requests = 0
        self.last_violation_time = None
        self.cooldown_active = False
        self.cooldown_end_time = None
        
        # Initialize from Redis if available
        self._load_state_from_redis()
        
        logger.info(f"API Guardian initialized for {nova_id} with conservative limits")
    
    def validate_request_safety(self) -> SafetyValidation:
        """
        MANDATORY validation before any API request.
        This is the critical safety check that must pass.
        """
        # First check if we're in cooldown
        if self._is_in_cooldown():
            remaining_cooldown = int((self.cooldown_end_time - datetime.now()).total_seconds())
            return SafetyValidation(
                is_safe=False,
                violation_type="COOLDOWN_ACTIVE",
                mandatory_action="WAIT",
                cooldown_required=True,
                cooldown_duration=remaining_cooldown,
                details={"reason": "Previous violation cooldown still active"}
            )
        
        # Clean old requests from history
        self._clean_request_history()
        
        # Check all rate limits
        for limit_type, threshold in self.HARD_LIMITS.items():
            current_usage = self._get_current_usage(limit_type)
            
            if current_usage >= threshold:
                logger.critical(f"API RATE LIMIT EXCEEDED: {limit_type.value} - {current_usage}/{threshold}")
                
                # Activate cooldown
                cooldown_duration = self.COOLDOWN_DURATIONS[limit_type]
                self._activate_cooldown(limit_type, cooldown_duration)
                
                # Post safety alert
                self._post_safety_alert(limit_type, current_usage, threshold)
                
                return SafetyValidation(
                    is_safe=False,
                    violation_type=f"API_RATE_LIMIT_EXCEEDED_{limit_type.value.upper()}",
                    mandatory_action="IMMEDIATE_SHUTDOWN",
                    cooldown_required=True,
                    cooldown_duration=cooldown_duration,
                    details={
                        "limit_type": limit_type.value,
                        "current_usage": current_usage,
                        "threshold": threshold,
                        "timestamp": datetime.now().isoformat()
                    }
                )
        
        # All checks passed
        return SafetyValidation(is_safe=True)
    
    def record_api_request(self, request_type: str = "general"):
        """Record an API request for rate limiting"""
        timestamp = datetime.now()
        
        # Add to history
        self.request_history.append({
            'timestamp': timestamp,
            'type': request_type,
            'nova_id': self.nova_id
        })
        
        # Persist to Redis
        self._persist_request_to_redis(timestamp, request_type)
        
        logger.debug(f"Recorded API request: {request_type}")
    
    def increment_concurrent_requests(self) -> bool:
        """Increment concurrent request counter, return False if limit exceeded"""
        if self.concurrent_requests >= self.HARD_LIMITS[RateLimitType.CONCURRENT_REQUESTS]:
            logger.warning(f"Concurrent request limit reached: {self.concurrent_requests}")
            return False
        
        self.concurrent_requests += 1
        self._update_concurrent_count_redis()
        return True
    
    def decrement_concurrent_requests(self):
        """Decrement concurrent request counter"""
        if self.concurrent_requests > 0:
            self.concurrent_requests -= 1
            self._update_concurrent_count_redis()
    
    def _get_current_usage(self, limit_type: RateLimitType) -> int:
        """Get current usage for a specific limit type"""
        now = datetime.now()
        
        if limit_type == RateLimitType.REQUESTS_PER_MINUTE:
            cutoff = now - timedelta(minutes=1)
            return len([r for r in self.request_history if r['timestamp'] > cutoff])
        
        elif limit_type == RateLimitType.REQUESTS_PER_HOUR:
            cutoff = now - timedelta(hours=1)
            return len([r for r in self.request_history if r['timestamp'] > cutoff])
        
        elif limit_type == RateLimitType.REQUESTS_PER_DAY:
            cutoff = now - timedelta(days=1)
            return len([r for r in self.request_history if r['timestamp'] > cutoff])
        
        elif limit_type == RateLimitType.CONCURRENT_REQUESTS:
            return self.concurrent_requests
        
        elif limit_type == RateLimitType.BURST_THRESHOLD:
            cutoff = now - timedelta(seconds=30)
            return len([r for r in self.request_history if r['timestamp'] > cutoff])
        
        return 0
    
    def _clean_request_history(self):
        """Remove old requests from history"""
        cutoff = datetime.now() - timedelta(days=1)
        self.request_history = deque(
            [r for r in self.request_history if r['timestamp'] > cutoff],
            maxlen=1000
        )
    
    def _is_in_cooldown(self) -> bool:
        """Check if currently in cooldown period"""
        if not self.cooldown_active:
            return False
        
        if self.cooldown_end_time and datetime.now() < self.cooldown_end_time:
            return True
        
        # Cooldown expired
        self.cooldown_active = False
        self.cooldown_end_time = None
        self._clear_cooldown_redis()
        return False
    
    def _activate_cooldown(self, limit_type: RateLimitType, duration: int):
        """Activate cooldown period"""
        self.cooldown_active = True
        self.cooldown_end_time = datetime.now() + timedelta(seconds=duration)
        self.last_violation_time = datetime.now()
        
        # Persist to Redis
        self._persist_cooldown_redis(limit_type, duration)
        
        logger.critical(f"COOLDOWN ACTIVATED: {duration} seconds for {limit_type.value}")
    
    def _post_safety_alert(self, limit_type: RateLimitType, current: int, threshold: int):
        """Post safety alert to monitoring streams"""
        try:
            alert_data = {
                'type': 'API_SAFETY_VIOLATION',
                'nova_id': self.nova_id,
                'violation_type': limit_type.value,
                'current_usage': current,
                'threshold': threshold,
                'timestamp': datetime.now().isoformat(),
                'severity': 'CRITICAL',
                'action_taken': 'COOLDOWN_ACTIVATED'
            }
            
            # Post to safety alerts stream
            self.redis_client.xadd(
                f'nova.safety.{self.nova_id}',
                alert_data
            )
            
            # Also post to priority alerts
            self.redis_client.xadd(
                'nova.priority.alerts',
                alert_data
            )
            
        except Exception as e:
            logger.error(f"Failed to post safety alert: {e}")
    
    def _persist_request_to_redis(self, timestamp: datetime, request_type: str):
        """Persist request to Redis for distributed tracking"""
        try:
            key = f"api_guardian:{self.nova_id}:requests"
            self.redis_client.zadd(
                key,
                {f"{timestamp.isoformat()}:{request_type}": timestamp.timestamp()}
            )
            # Expire old entries
            cutoff = (datetime.now() - timedelta(days=1)).timestamp()
            self.redis_client.zremrangebyscore(key, 0, cutoff)
            
        except Exception as e:
            logger.error(f"Failed to persist request to Redis: {e}")
    
    def _update_concurrent_count_redis(self):
        """Update concurrent request count in Redis"""
        try:
            key = f"api_guardian:{self.nova_id}:concurrent"
            self.redis_client.set(key, self.concurrent_requests, ex=60)  # 1 minute expiry
        except Exception as e:
            logger.error(f"Failed to update concurrent count: {e}")
    
    def _persist_cooldown_redis(self, limit_type: RateLimitType, duration: int):
        """Persist cooldown state to Redis"""
        try:
            key = f"api_guardian:{self.nova_id}:cooldown"
            cooldown_data = {
                'active': 'true',
                'limit_type': limit_type.value,
                'end_time': self.cooldown_end_time.isoformat(),
                'duration': duration
            }
            self.redis_client.hset(key, mapping=cooldown_data)
            self.redis_client.expire(key, duration)
            
        except Exception as e:
            logger.error(f"Failed to persist cooldown: {e}")
    
    def _clear_cooldown_redis(self):
        """Clear cooldown state from Redis"""
        try:
            key = f"api_guardian:{self.nova_id}:cooldown"
            self.redis_client.delete(key)
        except Exception as e:
            logger.error(f"Failed to clear cooldown: {e}")
    
    def _load_state_from_redis(self):
        """Load state from Redis on initialization"""
        try:
            # Load cooldown state
            cooldown_key = f"api_guardian:{self.nova_id}:cooldown"
            cooldown_data = self.redis_client.hgetall(cooldown_key)
            
            if cooldown_data and cooldown_data.get('active') == 'true':
                end_time = datetime.fromisoformat(cooldown_data['end_time'])
                if end_time > datetime.now():
                    self.cooldown_active = True
                    self.cooldown_end_time = end_time
                    logger.info(f"Loaded active cooldown, expires: {end_time}")
            
            # Load concurrent count
            concurrent_key = f"api_guardian:{self.nova_id}:concurrent"
            concurrent_count = self.redis_client.get(concurrent_key)
            if concurrent_count:
                self.concurrent_requests = int(concurrent_count)
            
        except Exception as e:
            logger.error(f"Failed to load state from Redis: {e}")
    
    def get_safety_status(self) -> Dict:
        """Get comprehensive safety status for monitoring"""
        return {
            'nova_id': self.nova_id,
            'is_safe': not self._is_in_cooldown(),
            'cooldown_active': self.cooldown_active,
            'cooldown_remaining': int((self.cooldown_end_time - datetime.now()).total_seconds()) if self.cooldown_end_time and self.cooldown_active else 0,
            'current_usage': {
                'requests_per_minute': self._get_current_usage(RateLimitType.REQUESTS_PER_MINUTE),
                'requests_per_hour': self._get_current_usage(RateLimitType.REQUESTS_PER_HOUR),
                'requests_per_day': self._get_current_usage(RateLimitType.REQUESTS_PER_DAY),
                'concurrent_requests': self.concurrent_requests,
                'burst_count': self._get_current_usage(RateLimitType.BURST_THRESHOLD)
            },
            'limits': {k.value: v for k, v in self.HARD_LIMITS.items()},
            'last_violation_time': self.last_violation_time.isoformat() if self.last_violation_time else None,
            'generated_at': datetime.now().isoformat()
        }
    
    def emergency_shutdown(self):
        """Emergency shutdown - activate maximum cooldown"""
        logger.critical("EMERGENCY SHUTDOWN ACTIVATED")
        self._activate_cooldown(RateLimitType.REQUESTS_PER_DAY, 3600)  # 1 hour emergency cooldown
        
        # Clear all counters
        self.request_history.clear()
        self.concurrent_requests = 0
        
        # Alert all systems
        self._post_safety_alert(
            RateLimitType.REQUESTS_PER_DAY,
            9999,  # Indicate emergency
            0
        )

if __name__ == "__main__":
    # Test the API Guardian
    import sys
    
    nova_id = sys.argv[1] if len(sys.argv) > 1 else "torch"
    
    logger.info(f"Testing API Guardian for {nova_id}")
    
    guardian = APIGuardian(nova_id)
    
    # Test validation
    validation = guardian.validate_request_safety()
    print(f"Initial validation: {validation}")
    
    # Simulate some requests
    for i in range(5):
        guardian.record_api_request("test_request")
        time.sleep(0.1)
    
    # Check status
    status = guardian.get_safety_status()
    print(f"\nSafety Status: {json.dumps(status, indent=2)}")