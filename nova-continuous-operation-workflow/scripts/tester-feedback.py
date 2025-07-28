#!/usr/bin/env python3
"""
Tester Feedback Tool - Quick way to send feedback about NOVAWF
"""
import redis
import sys
from datetime import datetime

def send_feedback(message, feedback_type="general"):
    """Send feedback to the collaboration stream"""
    r = redis.Redis(host='localhost', port=18000, decode_responses=True)
    
    msg_data = {
        'from': 'tester',
        'type': f'FEEDBACK_{feedback_type.upper()}',
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    msg_id = r.xadd('project.tester.collab', msg_data)
    print(f"✅ Feedback sent! ID: {msg_id}")
    
    # Check for torch's responses
    print("\n📨 Recent messages from torch:")
    messages = r.xrevrange('project.tester.collab', '+', '-', count=3)
    for msg_id, data in messages:
        if data.get('from') == 'torch':
            print(f"\n[{data.get('type', 'MESSAGE')}] {data.get('subject', '')}")
            if 'message' in data:
                print(f"  {data['message']}")
            if 'questions' in data:
                for q in eval(data['questions']):
                    print(f"  {q}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ./tester-feedback.py <message> [type]")
        print("Types: ux, bug, feature, general")
        print("\nExample: ./tester-feedback.py 'Auto start was confusing' ux")
        sys.exit(1)
    
    message = sys.argv[1]
    feedback_type = sys.argv[2] if len(sys.argv) > 2 else "general"
    
    send_feedback(message, feedback_type)