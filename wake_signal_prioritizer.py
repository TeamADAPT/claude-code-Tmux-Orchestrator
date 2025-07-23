#!/usr/bin/env python3
"""
Wake-up Signal Prioritization System
Handles different types of coordination messages and work requests with appropriate urgency levels
"""

import redis
import json
import time
import re
from datetime import datetime, timedelta
from enum import Enum

class SignalPriority(Enum):
    CRITICAL = 1    # Immediate wake-up required
    HIGH = 2        # Wake within 30 seconds
    MEDIUM = 3      # Wake within 5 minutes
    LOW = 4         # Wake within 30 minutes
    BACKGROUND = 5  # Process during next natural cycle

class WakeSignalPrioritizer:
    def __init__(self, nova_id="torch", redis_port=18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        
        # Priority keyword patterns (more precise matching)
        self.priority_patterns = {
            SignalPriority.CRITICAL: [
                r'\b(emergency|critical.*bug|system.*crash|server.*down)\b',
                r'\b(production.*down|database.*crashed|api.*failing)\b',
                r'(alert|emergency).*immediate',
                r'\b(critical.*failure|system.*failure)\b'
            ],
            SignalPriority.HIGH: [
                r'\b(urgent|high.*priority|important.*bug)\b',
                r'\b(production.*bug|security.*patch|deployment.*issue)\b',
                r'\b(blocked|deadline.*today|asap)\b',
                r'\b(critical.*review|urgent.*attention)\b'
            ],
            SignalPriority.MEDIUM: [
                r'\b(review|task|work|todo|update)\b',
                r'\b(bug|issue|problem|improvement)\b',
                r'\b(coordinate|sync|meeting|optimize)\b'
            ],
            SignalPriority.LOW: [
                r'\b(suggestion|idea|consider|maybe)\b',
                r'\b(documentation|cleanup|refactor)\b',
                r'\b(future|later|when.*time|convenient)\b'
            ]
        }
        
        # Stream importance weights
        self.stream_weights = {
            'nova.emergency.alerts': SignalPriority.CRITICAL,
            'nova.coordination.urgent': SignalPriority.HIGH,
            'nova.work.queue': SignalPriority.MEDIUM,
            'nova.coordination.messages': SignalPriority.MEDIUM,
            'nova.tasks.torch.todo': SignalPriority.MEDIUM,
            'nova.suggestions': SignalPriority.LOW,
            'nova.background.tasks': SignalPriority.BACKGROUND
        }
    
    def analyze_signal_priority(self, message, stream_name=None, sender=None):
        """Analyze a message and determine its wake-up priority"""
        
        # Start with stream-based priority
        base_priority = self.stream_weights.get(stream_name, SignalPriority.MEDIUM)
        
        # Analyze message content
        message_text = str(message).lower()
        content_priority = self._analyze_content_priority(message_text)
        
        # Apply sender-based adjustments
        sender_priority = self._analyze_sender_priority(sender)
        
        # Take the highest priority (lowest enum value)
        priorities = [base_priority.value, content_priority.value, sender_priority.value]
        final_priority_value = min(priorities)
        final_priority = SignalPriority(final_priority_value)
        
        # Context-based escalations
        final_priority = self._apply_context_escalations(final_priority, message_text, stream_name)
        
        return final_priority
    
    def _analyze_content_priority(self, message_text):
        """Analyze message content for priority keywords"""
        for priority, patterns in self.priority_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message_text, re.IGNORECASE):
                    return priority
        return SignalPriority.BACKGROUND
    
    def _analyze_sender_priority(self, sender):
        """Adjust priority based on message sender"""
        if not sender:
            return SignalPriority.BACKGROUND
            
        sender = sender.lower()
        
        # Critical system senders
        if any(role in sender for role in ['emergency', 'alert', 'monitoring-system']):
            return SignalPriority.CRITICAL
        
        # High-priority senders
        if any(role in sender for role in ['admin', 'manager', 'lead', 'orchestrator', 'security']):
            return SignalPriority.HIGH
        
        # Medium priority senders
        if any(sys in sender for sys in ['system', 'monitor', 'hook', 'nova', 'developer']):
            return SignalPriority.MEDIUM
            
        return SignalPriority.BACKGROUND
    
    def _apply_context_escalations(self, priority, message_text, stream_name):
        """Apply context-based priority escalations"""
        
        # Time-based escalations (only for off-hours critical issues)
        hour = datetime.now().hour
        if (0 <= hour <= 6 or 22 <= hour <= 23):  # Night/late hours
            if priority == SignalPriority.HIGH and any(word in message_text for word in ['critical', 'urgent', 'emergency']):
                priority = SignalPriority.CRITICAL
        
        # Load-based escalations (only escalate if system is really overwhelmed)
        if self._is_system_under_load():
            work_queue_size = self._get_work_queue_size()
            if work_queue_size > 50 and priority == SignalPriority.MEDIUM:
                priority = SignalPriority.HIGH
        
        # Sequence-based escalations (only for truly repeated signals)
        if self._is_repeated_signal(message_text):
            # Only escalate if it's been repeated multiple times
            repeat_count = self._get_repeat_count(message_text)
            if repeat_count >= 3 and priority.value > 1:
                priority = SignalPriority(priority.value - 1)
        
        return priority
    
    def _is_system_under_load(self):
        """Check if system is currently under heavy load"""
        try:
            # Check work queue size
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                queue_size = len(f.readlines())
            
            # Check active coordination streams
            active_messages = 0
            for stream in ['nova.coordination.messages', 'nova.work.queue']:
                try:
                    active_messages += self.redis_client.xlen(stream)
                except:
                    pass
            
            return queue_size > 30 or active_messages > 10
        except:
            return False
    
    def _is_repeated_signal(self, message_text):
        """Check if this is a repeated/escalated signal"""
        try:
            # Look for recent similar messages
            recent_signals = self.redis_client.xrevrange("nova.wake.signals", count=5)
            for signal_id, fields in recent_signals:
                if fields.get('message', '').lower() in message_text:
                    return True
            return False
        except:
            return False
    
    def _get_work_queue_size(self):
        """Get current work queue size"""
        try:
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                return len(f.readlines())
        except:
            return 0
    
    def _get_repeat_count(self, message_text):
        """Count how many times this message has been repeated"""
        try:
            recent_signals = self.redis_client.xrevrange("nova.wake.signals", count=10)
            count = 0
            for signal_id, fields in recent_signals:
                if message_text.lower() in fields.get('message', '').lower():
                    count += 1
            return count
        except:
            return 0
    
    def process_wake_signal(self, message, stream_name=None, sender=None, metadata=None):
        """Process an incoming wake signal and determine action"""
        
        priority = self.analyze_signal_priority(message, stream_name, sender)
        timestamp = datetime.now().isoformat()
        
        # Create wake signal record
        signal_data = {
            'nova_id': self.nova_id,
            'message': str(message),
            'stream': stream_name or 'unknown',
            'sender': sender or 'unknown',
            'priority': priority.name,
            'priority_value': priority.value,
            'timestamp': timestamp,
            'action_required': self._determine_action(priority)
        }
        
        # Add metadata if provided
        if metadata:
            signal_data.update(metadata)
        
        # Store signal
        signal_id = self.redis_client.xadd("nova.wake.signals", signal_data)
        
        # Take immediate action based on priority
        self._execute_wake_action(priority, signal_data, signal_id)
        
        return {
            'signal_id': signal_id,
            'priority': priority.name,
            'action': signal_data['action_required'],
            'wake_delay': self._get_wake_delay(priority)
        }
    
    def _determine_action(self, priority):
        """Determine what action to take for this priority level"""
        actions = {
            SignalPriority.CRITICAL: "immediate_wake",
            SignalPriority.HIGH: "priority_wake", 
            SignalPriority.MEDIUM: "scheduled_wake",
            SignalPriority.LOW: "deferred_wake",
            SignalPriority.BACKGROUND: "next_cycle_wake"
        }
        return actions[priority]
    
    def _get_wake_delay(self, priority):
        """Get appropriate wake delay for priority level"""
        delays = {
            SignalPriority.CRITICAL: 0,      # Immediate
            SignalPriority.HIGH: 30,         # 30 seconds
            SignalPriority.MEDIUM: 300,      # 5 minutes
            SignalPriority.LOW: 1800,        # 30 minutes
            SignalPriority.BACKGROUND: 3600  # 1 hour
        }
        return delays[priority]
    
    def _execute_wake_action(self, priority, signal_data, signal_id):
        """Execute the appropriate wake action"""
        
        if priority == SignalPriority.CRITICAL:
            # Immediate wake - bypass all cooldowns
            self._send_immediate_wake_signal(signal_data)
            
        elif priority == SignalPriority.HIGH:
            # Priority wake - short delay
            self._schedule_priority_wake(signal_data, 30)
            
        elif priority == SignalPriority.MEDIUM:
            # Normal scheduling
            self._schedule_normal_wake(signal_data, 300)
            
        else:  # LOW or BACKGROUND
            # Add to deferred queue
            self._add_to_deferred_queue(signal_data)
    
    def _send_immediate_wake_signal(self, signal_data):
        """Send immediate wake signal bypassing cooldowns"""
        
        # Clear any active cooldowns for critical signals
        self.redis_client.delete(f"frosty:claude:{self.nova_id}")
        self.redis_client.delete("claude_restart_cooldown")
        
        # Send wake signal to coordination stream
        self.redis_client.xadd(
            "nova.immediate.wake",
            {
                'target': self.nova_id,
                'reason': 'critical_signal',
                'message': signal_data['message'][:200],  # Truncate long messages
                'timestamp': datetime.now().isoformat()
            }
        )
        
        print(f"🚨 CRITICAL WAKE SIGNAL: {signal_data['message'][:100]}")
    
    def _schedule_priority_wake(self, signal_data, delay_seconds):
        """Schedule a priority wake with short delay"""
        
        # Add to priority queue
        self.redis_client.xadd(
            "nova.priority.wake.queue",
            {
                'target': self.nova_id,
                'message': signal_data['message'],
                'scheduled_for': (datetime.now() + timedelta(seconds=delay_seconds)).isoformat(),
                'priority': 'HIGH'
            }
        )
        
        print(f"⚡ Priority wake scheduled in {delay_seconds}s: {signal_data['message'][:100]}")
    
    def _schedule_normal_wake(self, signal_data, delay_seconds):
        """Schedule normal wake with standard delay"""
        
        self.redis_client.xadd(
            "nova.scheduled.wake.queue", 
            {
                'target': self.nova_id,
                'message': signal_data['message'],
                'scheduled_for': (datetime.now() + timedelta(seconds=delay_seconds)).isoformat(),
                'priority': 'MEDIUM'
            }
        )
        
        print(f"📅 Wake scheduled in {delay_seconds//60}m: {signal_data['message'][:100]}")
    
    def _add_to_deferred_queue(self, signal_data):
        """Add signal to deferred processing queue"""
        
        self.redis_client.xadd(
            "nova.deferred.signals",
            {
                'target': self.nova_id,
                'message': signal_data['message'],
                'priority': signal_data['priority'],
                'deferred_at': datetime.now().isoformat()
            }
        )
        
        print(f"📝 Signal deferred for next cycle: {signal_data['message'][:100]}")
    
    def get_pending_signals(self, max_age_hours=24):
        """Get all pending wake signals"""
        try:
            cutoff = datetime.now() - timedelta(hours=max_age_hours)
            signals = self.redis_client.xrevrange("nova.wake.signals", count=50)
            
            pending = []
            for signal_id, fields in signals:
                try:
                    signal_time = datetime.fromisoformat(fields.get('timestamp', ''))
                    if signal_time > cutoff:
                        pending.append({
                            'id': signal_id,
                            'priority': fields.get('priority', 'UNKNOWN'),
                            'message': fields.get('message', 'No message'),
                            'timestamp': fields.get('timestamp', 'Unknown time'),
                            'action': fields.get('action_required', 'unknown')
                        })
                except:
                    continue
            
            return pending
        except:
            return []
    
    def get_priority_stats(self):
        """Get statistics on signal priorities"""
        try:
            recent_signals = self.redis_client.xrevrange("nova.wake.signals", count=100)
            stats = {priority.name: 0 for priority in SignalPriority}
            
            for signal_id, fields in recent_signals:
                priority_name = fields.get('priority', 'BACKGROUND')
                if priority_name in stats:
                    stats[priority_name] += 1
            
            return stats
        except:
            return {priority.name: 0 for priority in SignalPriority}

if __name__ == "__main__":
    prioritizer = WakeSignalPrioritizer()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "test":
            # Test different priority messages
            test_messages = [
                ("System crash detected - immediate attention required", "nova.emergency.alerts", "system-monitor"),
                ("High priority bug in production deployment", "nova.coordination.urgent", "lead-dev"),
                ("New task added to work queue", "nova.work.queue", "task-manager"), 
                ("Consider optimizing this component later", "nova.suggestions", "developer"),
                ("Documentation needs updating", "nova.background.tasks", "maintainer")
            ]
            
            for message, stream, sender in test_messages:
                result = prioritizer.process_wake_signal(message, stream, sender)
                print(f"Message: {message[:50]}...")
                print(f"Priority: {result['priority']}, Action: {result['action']}, Delay: {result['wake_delay']}s")
                print("---")
        
        elif command == "pending":
            pending = prioritizer.get_pending_signals()
            print(f"Pending signals: {len(pending)}")
            for signal in pending[:10]:  # Show last 10
                print(f"[{signal['priority']}] {signal['message'][:80]}...")
        
        elif command == "stats":
            stats = prioritizer.get_priority_stats()
            print("Priority distribution:")
            for priority, count in stats.items():
                print(f"  {priority}: {count}")
        
        elif command == "process":
            if len(sys.argv) > 2:
                message = " ".join(sys.argv[2:])
                result = prioritizer.process_wake_signal(message)
                print(f"Processed: {result}")
            else:
                print("Usage: wake_signal_prioritizer.py process <message>")
    else:
        print("Usage: wake_signal_prioritizer.py [test|pending|stats|process]")