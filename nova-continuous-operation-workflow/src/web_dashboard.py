#!/usr/bin/env python3
"""
Nova Web Dashboard - Real-time monitoring interface
"""
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import redis
import json
import threading
import time
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'nova-dashboard-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

r = redis.Redis(host='localhost', port=18000, decode_responses=True)

# Background thread for real-time updates
def background_monitor():
    """Monitor streams and emit updates"""
    last_id = '$'
    
    while True:
        try:
            # Monitor ecosystem events
            result = r.xread({'nova.ecosystem.events': last_id}, block=1000)
            
            if result:
                for stream_name, messages in result:
                    for msg_id, data in messages:
                        last_id = msg_id
                        socketio.emit('ecosystem_event', data)
            
            # Emit periodic stats
            stats = get_network_stats()
            socketio.emit('stats_update', stats)
            
        except Exception as e:
            print(f"Monitor error: {e}")
            time.sleep(5)

@app.route('/')
def index():
    """Main dashboard page"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>Nova Ecosystem Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #0a0a0a;
            color: #fff;
        }
        .dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .card {
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .card h2 {
            margin-top: 0;
            color: #4a9eff;
        }
        .nova-node {
            display: inline-block;
            margin: 5px;
            padding: 10px 15px;
            background: #2a2a2a;
            border-radius: 20px;
            border: 2px solid #4a9eff;
            position: relative;
        }
        .nova-node.active {
            border-color: #4aff4a;
            box-shadow: 0 0 10px rgba(74, 255, 74, 0.5);
        }
        .metric {
            font-size: 2em;
            font-weight: bold;
            color: #4a9eff;
        }
        .metric-label {
            font-size: 0.9em;
            color: #888;
        }
        #events {
            max-height: 300px;
            overflow-y: auto;
        }
        .event {
            padding: 8px;
            margin: 4px 0;
            background: #2a2a2a;
            border-left: 3px solid #4a9eff;
            font-family: monospace;
            font-size: 0.9em;
        }
        .event.error {
            border-color: #ff4a4a;
        }
        .event.success {
            border-color: #4aff4a;
        }
        .chart-container {
            position: relative;
            height: 200px;
        }
    </style>
</head>
<body>
    <h1>🚀 Nova Ecosystem Dashboard</h1>
    
    <div class="dashboard">
        <div class="card">
            <h2>Network Status</h2>
            <div id="network-status">
                <div class="metric" id="active-novas">0</div>
                <div class="metric-label">Active Novas</div>
                <div id="nova-list"></div>
            </div>
        </div>
        
        <div class="card">
            <h2>Task Metrics</h2>
            <div>
                <div class="metric" id="pending-tasks">0</div>
                <div class="metric-label">Pending Tasks</div>
                <div class="metric" id="tasks-per-minute">0</div>
                <div class="metric-label">Tasks/Minute</div>
            </div>
        </div>
        
        <div class="card">
            <h2>Performance</h2>
            <div class="chart-container">
                <canvas id="performance-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>Live Events</h2>
            <div id="events"></div>
        </div>
    </div>
    
    <script>
        const socket = io();
        
        // Initialize chart
        const ctx = document.getElementById('performance-chart').getContext('2d');
        const chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Tasks/min',
                    data: [],
                    borderColor: '#4a9eff',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
        
        // Update functions
        function updateStats(data) {
            document.getElementById('active-novas').textContent = data.active_novas;
            document.getElementById('pending-tasks').textContent = data.total_pending_tasks;
            document.getElementById('tasks-per-minute').textContent = data.tasks_per_minute.toFixed(1);
            
            // Update nova list
            const novaList = document.getElementById('nova-list');
            novaList.innerHTML = '';
            data.nova_list.forEach(nova => {
                const node = document.createElement('div');
                node.className = 'nova-node active';
                node.textContent = nova;
                novaList.appendChild(node);
            });
            
            // Update chart
            const now = new Date().toLocaleTimeString();
            chart.data.labels.push(now);
            chart.data.datasets[0].data.push(data.tasks_per_minute);
            
            // Keep only last 20 points
            if (chart.data.labels.length > 20) {
                chart.data.labels.shift();
                chart.data.datasets[0].data.shift();
            }
            chart.update();
        }
        
        function addEvent(data) {
            const events = document.getElementById('events');
            const event = document.createElement('div');
            event.className = 'event';
            
            const timestamp = new Date().toLocaleTimeString();
            event.textContent = `[${timestamp}] ${data.type}: ${JSON.stringify(data)}`;
            
            if (data.type.includes('FAILED')) event.classList.add('error');
            if (data.type.includes('SUCCESS')) event.classList.add('success');
            
            events.insertBefore(event, events.firstChild);
            
            // Keep only last 50 events
            while (events.children.length > 50) {
                events.removeChild(events.lastChild);
            }
        }
        
        // Socket handlers
        socket.on('stats_update', updateStats);
        socket.on('ecosystem_event', addEvent);
        
        // Initial load
        fetch('/api/stats')
            .then(res => res.json())
            .then(updateStats);
    </script>
</body>
</html>
    '''

@app.route('/api/stats')
def get_stats():
    """Get current statistics"""
    return jsonify(get_network_stats())

@app.route('/api/novas')
def get_novas():
    """Get active Novas"""
    active_novas = list(r.smembers('nova:registry:active'))
    novas = []
    
    for nova_id in active_novas:
        nova_data = r.hgetall(f'nova:registry:{nova_id}')
        if nova_data:
            novas.append({
                'id': nova_id,
                'capabilities': json.loads(nova_data.get('capabilities', '[]')),
                'status': nova_data.get('status'),
                'last_heartbeat': nova_data.get('last_heartbeat'),
                'pending_tasks': r.xlen(f'nova.tasks.{nova_id}')
            })
    
    return jsonify(novas)

@app.route('/api/nova/<nova_id>')
def get_nova_details(nova_id):
    """Get detailed Nova information"""
    nova_data = r.hgetall(f'nova:registry:{nova_id}')
    stats = r.hgetall(f'workflow:stats:{nova_id}')
    
    # Get recent tasks
    history = r.xrevrange(f'nova.tasks.{nova_id}.history', '+', '-', count=10)
    recent_tasks = []
    for task_id, data in history:
        recent_tasks.append(data)
    
    return jsonify({
        'info': nova_data,
        'stats': stats,
        'recent_tasks': recent_tasks,
        'pending_tasks': r.xlen(f'nova.tasks.{nova_id}')
    })

def get_network_stats():
    """Calculate network statistics"""
    active_novas = list(r.smembers('nova:registry:active'))
    total_pending = 0
    total_completed = 0
    
    for nova_id in active_novas:
        total_pending += r.xlen(f'nova.tasks.{nova_id}')
        stats = r.hgetall(f'workflow:stats:{nova_id}')
        if stats:
            total_completed += int(stats.get('total_count', 0))
    
    # Calculate tasks per minute (simplified)
    tasks_per_minute = total_completed / max(1, len(active_novas)) / 10  # Rough estimate
    
    return {
        'active_novas': len(active_novas),
        'nova_list': active_novas,
        'total_pending_tasks': total_pending,
        'total_completed_tasks': total_completed,
        'tasks_per_minute': tasks_per_minute
    }

if __name__ == '__main__':
    # Start background monitor
    monitor_thread = threading.Thread(target=background_monitor)
    monitor_thread.daemon = True
    monitor_thread.start()
    
    print("🌐 Nova Dashboard starting on http://localhost:5000")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)