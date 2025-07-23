#!/usr/bin/env python3
"""
Continuous Operation Metrics and Analytics
Provides comprehensive monitoring and insights for Nova autonomous operation
"""

import redis
import json
import time
import statistics
from datetime import datetime, timedelta
from collections import defaultdict, Counter

class ContinuousMetricsAnalytics:
    def __init__(self, nova_id="torch", redis_port=18000):
        self.nova_id = nova_id
        self.redis_client = redis.Redis(host='localhost', port=redis_port, decode_responses=True)
        self.metric_streams = [
            'nova.wake.signals',
            'nova.wake.metrics', 
            'torch.continuous.ops',
            'nova.hook.metrics',
            'nova.hook.health',
            'nova.dream.states',
            'nova.coordination.messages'
        ]
    
    def collect_operational_metrics(self, time_window_hours=24):
        """Collect comprehensive operational metrics"""
        
        cutoff_time = datetime.now() - timedelta(hours=time_window_hours)
        metrics = {
            'collection_time': datetime.now().isoformat(),
            'time_window_hours': time_window_hours,
            'nova_id': self.nova_id,
            'system_uptime': {},
            'work_processing': {},
            'wake_signals': {},
            'hook_health': {},
            'coordination': {},
            'dream_analysis': {},
            'rhythm_patterns': {},
            'error_analysis': {}
        }
        
        # System uptime and activity
        metrics['system_uptime'] = self._analyze_system_uptime(cutoff_time)
        
        # Work processing efficiency
        metrics['work_processing'] = self._analyze_work_processing(cutoff_time)
        
        # Wake signal analysis
        metrics['wake_signals'] = self._analyze_wake_signals(cutoff_time)
        
        # Hook health metrics
        metrics['hook_health'] = self._analyze_hook_health(cutoff_time)
        
        # Coordination effectiveness
        metrics['coordination'] = self._analyze_coordination(cutoff_time)
        
        # Dream state analysis
        metrics['dream_analysis'] = self._analyze_dream_states(cutoff_time)
        
        # Rhythm pattern efficiency
        metrics['rhythm_patterns'] = self._analyze_rhythm_patterns(cutoff_time)
        
        # Error and recovery analysis
        metrics['error_analysis'] = self._analyze_error_recovery(cutoff_time)
        
        # Store metrics
        self.redis_client.xadd(
            "nova.metrics.analytics",
            {
                'nova_id': self.nova_id,
                'metrics_json': json.dumps(metrics, indent=2),
                'timestamp': datetime.now().isoformat(),
                'window_hours': time_window_hours
            }
        )
        
        return metrics
    
    def _analyze_system_uptime(self, cutoff_time):
        """Analyze system uptime and continuous operation"""
        
        try:
            # Get continuous ops data
            ops_data = self.redis_client.xrevrange("torch.continuous.ops", count=100)
            
            active_periods = []
            status_counts = Counter()
            restart_intervals = []
            
            last_restart_time = None
            
            for entry_id, fields in ops_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                        
                    status = fields.get('status', 'unknown')
                    status_counts[status] += 1
                    
                    if status == 'RESTARTING' and last_restart_time:
                        interval = (timestamp - last_restart_time).total_seconds()
                        restart_intervals.append(interval)
                    
                    if status == 'RESTARTING':
                        last_restart_time = timestamp
                        
                except:
                    continue
            
            return {
                'total_operations': len(ops_data),
                'status_distribution': dict(status_counts),
                'average_restart_interval': statistics.mean(restart_intervals) if restart_intervals else 0,
                'median_restart_interval': statistics.median(restart_intervals) if restart_intervals else 0,
                'uptime_stability': len([i for i in restart_intervals if i > 300]) / max(len(restart_intervals), 1) * 100,  # % intervals >5min
                'restart_frequency_per_hour': len(restart_intervals) / 24 if restart_intervals else 0
            }
            
        except Exception as e:
            return {'error': str(e), 'data_available': False}
    
    def _analyze_work_processing(self, cutoff_time):
        """Analyze work processing efficiency and throughput"""
        
        try:
            # Get work queue data
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                queue_entries = f.readlines()
            
            # Categorize work types
            work_types = Counter()
            self_generated = 0
            external_work = 0
            
            for entry in queue_entries:
                entry = entry.strip()
                if 'SELF_GENERATED' in entry:
                    self_generated += 1
                    work_types['self_generated'] += 1
                elif 'WORK_FOUND' in entry:
                    external_work += 1
                    work_types['external_work'] += 1
                elif 'TODO_FOUND' in entry:
                    work_types['todo_work'] += 1
                elif 'COORD_MSG' in entry:
                    work_types['coordination'] += 1
                else:
                    work_types['other'] += 1
            
            # Get work queue stream data
            work_stream_data = self.redis_client.xrevrange("nova.work.queue", count=50)
            
            return {
                'total_queue_entries': len(queue_entries),
                'self_generated_work_ratio': self_generated / max(len(queue_entries), 1) * 100,
                'external_work_ratio': external_work / max(len(queue_entries), 1) * 100,
                'work_type_distribution': dict(work_types),
                'work_stream_messages': len(work_stream_data),
                'work_generation_rate': len(queue_entries) / 24,  # per hour over 24h
                'processing_efficiency': self._calculate_processing_efficiency()
            }
            
        except Exception as e:
            return {'error': str(e), 'queue_accessible': False}
    
    def _calculate_processing_efficiency(self):
        """Calculate work processing efficiency metrics"""
        try:
            # Simple efficiency calculation based on queue growth vs processing
            with open('/tmp/torch_work_queue.txt', 'r') as f:
                queue_size = len(f.readlines())
            
            # Check recent ops to see if system is keeping up
            recent_ops = self.redis_client.xrevrange("torch.continuous.ops", count=10)
            active_processing = 0
            
            for entry_id, fields in recent_ops:
                if fields.get('status') in ['RESTARTING', 'PROCESSING_WORK']:
                    active_processing += 1
            
            # Efficiency is ratio of active processing to queue buildup
            efficiency = min(100, (active_processing / max(queue_size / 10, 1)) * 100)
            
            return {
                'current_queue_size': queue_size,
                'active_processing_indicators': active_processing,
                'efficiency_percentage': round(efficiency, 2),
                'queue_status': 'healthy' if queue_size < 50 else 'growing' if queue_size < 100 else 'backlogged'
            }
            
        except:
            return {'efficiency_percentage': 0, 'status': 'unknown'}
    
    def _analyze_wake_signals(self, cutoff_time):
        """Analyze wake signal patterns and responsiveness"""
        
        try:
            signals = self.redis_client.xrevrange("nova.wake.signals", count=100)
            
            priority_counts = Counter()
            action_counts = Counter()
            response_times = []
            
            for signal_id, fields in signals:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    priority = fields.get('priority', 'unknown')
                    action = fields.get('action_required', 'unknown')
                    
                    priority_counts[priority] += 1
                    action_counts[action] += 1
                    
                except:
                    continue
            
            return {
                'total_signals': sum(priority_counts.values()),
                'priority_distribution': dict(priority_counts),
                'action_distribution': dict(action_counts),
                'critical_signal_ratio': priority_counts.get('CRITICAL', 0) / max(sum(priority_counts.values()), 1) * 100,
                'average_signals_per_hour': sum(priority_counts.values()) / 24,
                'responsiveness_score': self._calculate_responsiveness_score(priority_counts, action_counts)
            }
            
        except Exception as e:
            return {'error': str(e), 'signals_available': False}
    
    def _calculate_responsiveness_score(self, priority_counts, action_counts):
        """Calculate system responsiveness score based on signal handling"""
        
        # Weight different priorities and actions
        priority_weights = {'CRITICAL': 5, 'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'BACKGROUND': 0.5}
        action_weights = {'immediate_wake': 5, 'priority_wake': 4, 'scheduled_wake': 3, 'deferred_wake': 2}
        
        weighted_priority_score = sum(priority_counts.get(p, 0) * w for p, w in priority_weights.items())
        weighted_action_score = sum(action_counts.get(a, 0) * w for a, w in action_weights.items())
        
        total_signals = sum(priority_counts.values()) or 1
        
        # Normalize to 0-100 scale
        responsiveness = min(100, (weighted_priority_score + weighted_action_score) / total_signals / 5 * 100)
        
        return round(responsiveness, 2)
    
    def _analyze_hook_health(self, cutoff_time):
        """Analyze hook system health and reliability"""
        
        try:
            health_data = self.redis_client.xrevrange("nova.hook.health", count=50)
            metrics_data = self.redis_client.xrevrange("nova.hook.metrics", count=50)
            
            health_status_counts = Counter()
            execution_counts = []
            
            for entry_id, fields in health_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    status = fields.get('health_status', 'unknown')
                    health_status_counts[status] += 1
                    
                except:
                    continue
            
            for entry_id, fields in metrics_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    exec_count = int(fields.get('execution_count', 0))
                    execution_counts.append(exec_count)
                    
                except:
                    continue
            
            return {
                'health_checks_performed': len(health_data),
                'health_status_distribution': dict(health_status_counts),
                'average_executions_per_check': statistics.mean(execution_counts) if execution_counts else 0,
                'hook_stability_score': health_status_counts.get('healthy', 0) / max(sum(health_status_counts.values()), 1) * 100,
                'monitoring_active': sum(health_status_counts.values()) > 0
            }
            
        except Exception as e:
            return {'error': str(e), 'hook_data_available': False}
    
    def _analyze_coordination(self, cutoff_time):
        """Analyze coordination effectiveness between Nova agents"""
        
        try:
            coord_data = self.redis_client.xrevrange("nova.coordination.messages", count=50)
            
            message_counts = Counter()
            sender_activity = Counter()
            
            for entry_id, fields in coord_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    sender = fields.get('from', 'unknown')
                    message_type = fields.get('type', 'general')
                    
                    sender_activity[sender] += 1
                    message_counts[message_type] += 1
                    
                except:
                    continue
            
            return {
                'total_coordination_messages': sum(message_counts.values()),
                'active_coordinators': len(sender_activity),
                'message_type_distribution': dict(message_counts),
                'most_active_coordinator': sender_activity.most_common(1)[0] if sender_activity else ('none', 0),
                'coordination_frequency_per_hour': sum(message_counts.values()) / 24,
                'collaboration_score': min(100, len(sender_activity) * 10 + sum(message_counts.values()))
            }
            
        except Exception as e:
            return {'error': str(e), 'coordination_data_available': False}
    
    def _analyze_dream_states(self, cutoff_time):
        """Analyze dream state patterns and effectiveness"""
        
        try:
            dream_data = self.redis_client.xrevrange("nova.dream.states", count=30)
            
            dream_counts = Counter()
            dream_durations = []
            insights_generated = []
            
            for entry_id, fields in dream_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    state = fields.get('state', 'unknown')
                    dream_counts[state] += 1
                    
                    if state == 'completed':
                        insights = int(fields.get('insights_generated', 0))
                        insights_generated.append(insights)
                        
                        duration = int(fields.get('duration_minutes', 5))
                        dream_durations.append(duration)
                    
                except:
                    continue
            
            return {
                'total_dream_sessions': dream_counts.get('completed', 0),
                'dream_state_distribution': dict(dream_counts),
                'average_dream_duration': statistics.mean(dream_durations) if dream_durations else 0,
                'average_insights_per_dream': statistics.mean(insights_generated) if insights_generated else 0,
                'dream_frequency_per_day': dream_counts.get('completed', 0),
                'contemplation_effectiveness': sum(insights_generated) / max(len(insights_generated), 1)
            }
            
        except Exception as e:
            return {'error': str(e), 'dream_data_available': False}
    
    def _analyze_rhythm_patterns(self, cutoff_time):
        """Analyze Nova personality rhythm effectiveness"""
        
        try:
            # Get rhythm data from Nova personality system
            rhythm_data = self.redis_client.get(f"nova:rhythm:{self.nova_id}")
            profile_data = self.redis_client.get(f"nova:profile:{self.nova_id}")
            
            analysis = {
                'rhythm_system_active': rhythm_data is not None,
                'profile_system_active': profile_data is not None
            }
            
            if rhythm_data:
                rhythm_info = json.loads(rhythm_data)
                analysis.update({
                    'current_cycle_time': rhythm_info.get('cycle_time', 0),
                    'base_cycle_time': rhythm_info.get('base_cycle', 0),
                    'system_load_factor': rhythm_info.get('system_load', 0),
                    'time_adaptation_factor': rhythm_info.get('time_factor', 0),
                    'recent_activity_level': rhythm_info.get('recent_activity', 0)
                })
            
            if profile_data:
                profile_info = json.loads(profile_data)
                analysis.update({
                    'personality_type': profile_info.get('nova_id', 'unknown'),
                    'communication_style': profile_info.get('communication_style', 'unknown'),
                    'dream_probability': profile_info.get('dream_probability', '0%'),
                    'profile_last_updated': profile_info.get('generated_at', 'unknown')
                })
            
            return analysis
            
        except Exception as e:
            return {'error': str(e), 'rhythm_data_available': False}
    
    def _analyze_error_recovery(self, cutoff_time):
        """Analyze error patterns and recovery effectiveness"""
        
        try:
            # Check hook emergencies
            emergency_data = self.redis_client.xrevrange("nova.hook.emergencies", count=20)
            
            emergency_counts = Counter()
            recovery_actions = Counter()
            
            for entry_id, fields in emergency_data:
                try:
                    timestamp = datetime.fromisoformat(fields.get('timestamp', ''))
                    if timestamp < cutoff_time:
                        continue
                    
                    action = fields.get('action', 'unknown')
                    hook_name = fields.get('hook_name', 'unknown')
                    
                    emergency_counts[hook_name] += 1
                    recovery_actions[action] += 1
                    
                except:
                    continue
            
            # Check for cooldown activations (Frosty interventions)
            cooldown_active = bool(self.redis_client.get("claude_restart_cooldown"))
            frosty_count = int(self.redis_client.get("frosty:cooldown:count") or 0)
            
            return {
                'total_emergencies': sum(emergency_counts.values()),
                'problematic_hooks': dict(emergency_counts),
                'recovery_actions_taken': dict(recovery_actions),
                'current_cooldown_active': cooldown_active,
                'frosty_interventions': frosty_count,
                'system_stability_score': max(0, 100 - sum(emergency_counts.values()) * 10),
                'recovery_system_health': 'good' if sum(emergency_counts.values()) < 3 else 'concerning'
            }
            
        except Exception as e:
            return {'error': str(e), 'error_data_available': False}
    
    def generate_analytics_report(self, metrics=None):
        """Generate a comprehensive analytics report"""
        
        if not metrics:
            metrics = self.collect_operational_metrics()
        
        report = {
            'report_generated': datetime.now().isoformat(),
            'nova_id': self.nova_id,
            'summary': {},
            'recommendations': [],
            'alerts': [],
            'performance_scores': {}
        }
        
        # Calculate overall performance scores
        uptime_score = metrics['system_uptime'].get('uptime_stability', 0)
        processing_score = metrics['work_processing'].get('processing_efficiency', {}).get('efficiency_percentage', 0)
        responsiveness_score = metrics['wake_signals'].get('responsiveness_score', 0)
        stability_score = metrics['error_analysis'].get('system_stability_score', 0)
        
        report['performance_scores'] = {
            'uptime_stability': uptime_score,
            'processing_efficiency': processing_score,
            'signal_responsiveness': responsiveness_score,
            'system_stability': stability_score,
            'overall_score': statistics.mean([uptime_score, processing_score, responsiveness_score, stability_score])
        }
        
        # Generate summary
        report['summary'] = {
            'operational_status': 'healthy' if report['performance_scores']['overall_score'] > 70 else 'needs_attention',
            'total_operations': metrics['system_uptime'].get('total_operations', 0),
            'work_processed': metrics['work_processing'].get('total_queue_entries', 0),
            'signals_handled': metrics['wake_signals'].get('total_signals', 0),
            'dream_sessions': metrics['dream_analysis'].get('total_dream_sessions', 0),
            'coordination_messages': metrics['coordination'].get('total_coordination_messages', 0)
        }
        
        # Generate recommendations
        if processing_score < 50:
            report['recommendations'].append("Consider optimizing work processing - efficiency below 50%")
        
        if metrics['error_analysis'].get('total_emergencies', 0) > 5:
            report['recommendations'].append("High number of emergencies detected - review hook stability")
        
        if metrics['wake_signals'].get('critical_signal_ratio', 0) > 30:
            report['recommendations'].append("High critical signal ratio - review prioritization logic")
        
        if uptime_score < 70:
            report['recommendations'].append("System restarts frequent - investigate stability issues")
        
        # Generate alerts
        if metrics['error_analysis'].get('current_cooldown_active', False):
            report['alerts'].append("System currently in cooldown mode")
        
        if metrics['work_processing'].get('work_generation_rate', 0) > 10:
            report['alerts'].append("High work generation rate - monitor for backlog")
        
        # Store report
        self.redis_client.xadd(
            "nova.analytics.reports",
            {
                'nova_id': self.nova_id,
                'report_json': json.dumps(report, indent=2),
                'timestamp': datetime.now().isoformat(),
                'overall_score': report['performance_scores']['overall_score']
            }
        )
        
        return report
    
    def get_recent_reports(self, count=5):
        """Get recent analytics reports"""
        try:
            reports = self.redis_client.xrevrange("nova.analytics.reports", count=count)
            return [{'id': report_id, **dict(fields)} for report_id, fields in reports]
        except:
            return []

if __name__ == "__main__":
    analytics = ContinuousMetricsAnalytics()
    
    import sys
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "collect":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            metrics = analytics.collect_operational_metrics(hours)
            print(json.dumps(metrics, indent=2))
        
        elif command == "report":
            report = analytics.generate_analytics_report()
            print(json.dumps(report, indent=2))
        
        elif command == "summary":
            report = analytics.generate_analytics_report()
            print(f"\n🔍 Nova {analytics.nova_id} Analytics Summary")
            print("=" * 50)
            print(f"Overall Score: {report['performance_scores']['overall_score']:.1f}/100")
            print(f"Status: {report['summary']['operational_status'].upper()}")
            print(f"Operations: {report['summary']['total_operations']}")
            print(f"Work Processed: {report['summary']['work_processed']}")
            print(f"Signals Handled: {report['summary']['signals_handled']}")
            print(f"Dream Sessions: {report['summary']['dream_sessions']}")
            
            if report['alerts']:
                print(f"\n⚠️  Alerts ({len(report['alerts'])}):")
                for alert in report['alerts']:
                    print(f"  • {alert}")
            
            if report['recommendations']:
                print(f"\n💡 Recommendations ({len(report['recommendations'])}):")
                for rec in report['recommendations']:
                    print(f"  • {rec}")
        
        elif command == "history":
            reports = analytics.get_recent_reports()
            print(f"\n📊 Recent Analytics Reports ({len(reports)})")
            print("=" * 50)
            for report in reports:
                timestamp = report.get('timestamp', 'unknown')[:19].replace('T', ' ')
                score = float(report.get('overall_score', 0))
                print(f"[{timestamp}] Score: {score:.1f}/100")
        
    else:
        print("Usage: continuous_metrics_analytics.py [collect|report|summary|history] [hours]")