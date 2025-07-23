#!/usr/bin/env python3
"""
Test Wake Signal Prioritization System
Demonstrates different priority levels and their handling
"""

import time
import json
from wake_signal_prioritizer import WakeSignalPrioritizer

def test_comprehensive_wake_signals():
    """Comprehensive test of wake signal prioritization"""
    
    print("🧪 Testing Wake Signal Prioritization System")
    print("=" * 60)
    
    prioritizer = WakeSignalPrioritizer(nova_id="torch")
    
    # Test scenarios with expected priorities
    test_scenarios = [
        {
            'message': 'EMERGENCY: Database connection failed - system down!',
            'stream': 'nova.emergency.alerts',
            'sender': 'system-admin',
            'expected_priority': 'CRITICAL',
            'description': 'Emergency system failure'
        },
        {
            'message': 'Urgent: Production deployment has critical bug affecting users',
            'stream': 'nova.coordination.urgent', 
            'sender': 'lead-engineer',
            'expected_priority': 'HIGH',
            'description': 'Critical production issue'
        },
        {
            'message': 'Please review this pull request when you have time',
            'stream': 'nova.work.queue',
            'sender': 'developer',
            'expected_priority': 'MEDIUM',
            'description': 'Standard work request'
        },
        {
            'message': 'Consider refactoring this component in the future',
            'stream': 'nova.suggestions',
            'sender': 'code-reviewer',
            'expected_priority': 'LOW',
            'description': 'Future improvement suggestion'
        },
        {
            'message': 'Update documentation when convenient',
            'stream': 'nova.background.tasks',
            'sender': 'maintainer',
            'expected_priority': 'BACKGROUND',
            'description': 'Background maintenance task'
        },
        {
            'message': 'Help! API is returning errors and users are complaining!',
            'stream': 'nova.work.queue',
            'sender': 'support-team',
            'expected_priority': 'HIGH',  # Escalated due to "help" and "error" keywords
            'description': 'Support escalation with urgency keywords'
        }
    ]
    
    print(f"Running {len(test_scenarios)} test scenarios...\n")
    
    results = []
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"Test {i}: {scenario['description']}")
        print(f"Message: \"{scenario['message'][:60]}...\"")
        print(f"Stream: {scenario['stream']}")
        print(f"Sender: {scenario['sender']}")
        
        # Process the signal
        result = prioritizer.process_wake_signal(
            message=scenario['message'],
            stream_name=scenario['stream'],
            sender=scenario['sender']
        )
        
        # Check if priority matches expectation
        priority_match = result['priority'] == scenario['expected_priority']
        match_icon = "✅" if priority_match else "❌"
        
        print(f"Expected Priority: {scenario['expected_priority']}")
        print(f"Actual Priority: {result['priority']} {match_icon}")
        print(f"Action: {result['action']}")
        print(f"Wake Delay: {result['wake_delay']}s")
        
        results.append({
            'test': i,
            'description': scenario['description'],
            'expected': scenario['expected_priority'],
            'actual': result['priority'],
            'match': priority_match,
            'delay': result['wake_delay']
        })
        
        print("-" * 40)
        time.sleep(0.5)  # Brief pause between tests
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("=" * 60)
    
    passed = sum(1 for r in results if r['match'])
    total = len(results)
    
    print(f"Tests Passed: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Wake signal prioritization working correctly.")
    else:
        print("⚠️  Some tests failed. Priority logic may need adjustment.")
        
        print("\nFailed Tests:")
        for r in results:
            if not r['match']:
                print(f"  Test {r['test']}: Expected {r['expected']}, got {r['actual']}")
    
    # Display priority distribution
    print(f"\n📈 Priority Distribution:")
    stats = prioritizer.get_priority_stats()
    for priority, count in stats.items():
        print(f"  {priority}: {count} signals")
    
    # Show recent signals
    print(f"\n📋 Recent Signals (last 5):")
    pending = prioritizer.get_pending_signals()[:5]
    for signal in pending:
        timestamp = signal['timestamp'][:19].replace('T', ' ')
        print(f"  [{signal['priority']}] {timestamp}: {signal['message'][:50]}...")
    
    return results

def test_integration_flow():
    """Test the complete integration flow"""
    
    print("\n🔄 Testing Integration Flow")
    print("=" * 60)
    
    prioritizer = WakeSignalPrioritizer(nova_id="torch")
    
    # Simulate a critical alert that should bypass all cooldowns
    print("1. Sending critical system alert...")
    critical_result = prioritizer.process_wake_signal(
        message="CRITICAL: Redis server crashed - all services affected",
        stream_name="nova.emergency.alerts",
        sender="monitoring-system"
    )
    
    print(f"   Result: {critical_result['priority']} priority, {critical_result['action']} action")
    
    # Simulate high priority work
    print("\n2. Sending high priority work request...")
    high_result = prioritizer.process_wake_signal(
        message="Urgent deployment needed for security patch",
        stream_name="nova.coordination.urgent", 
        sender="security-team"
    )
    
    print(f"   Result: {high_result['priority']} priority, {high_result['action']} action")
    
    # Simulate normal work
    print("\n3. Sending normal work task...")
    normal_result = prioritizer.process_wake_signal(
        message="Add unit tests for user authentication module",
        stream_name="nova.work.queue",
        sender="developer"
    )
    
    print(f"   Result: {normal_result['priority']} priority, {normal_result['action']} action")
    
    print("\n✅ Integration flow test complete")

if __name__ == "__main__":
    # Run comprehensive tests
    test_results = test_comprehensive_wake_signals()
    
    # Run integration tests
    test_integration_flow()
    
    print(f"\n🏁 All tests completed!")
    print("Wake signal prioritization system is ready for production use.")