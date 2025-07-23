#!/bin/bash
# Metrics Dashboard Updater - Periodic analytics collection and reporting
# Integrates with continuous operation monitoring

TIMESTAMP=$(date -u +%Y%m%d_%H%M%S)
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}" 2>/dev/null || echo "standalone")

# Configuration
METRICS_INTERVAL_MINUTES=15
REPORT_INTERVAL_HOURS=6
ANALYTICS_LOG="/tmp/nova_analytics.log"

echo "📊 Starting metrics dashboard update - $TIMESTAMP" | tee -a "$ANALYTICS_LOG"

# Check if it's time for detailed analytics report
last_report_time=$(redis-cli -p 18000 GET "nova:last_analytics_report" 2>/dev/null || echo "0")
current_time=$(date +%s)
time_since_report=$((current_time - last_report_time))
report_interval_seconds=$((REPORT_INTERVAL_HOURS * 3600))

if [ $time_since_report -gt $report_interval_seconds ] || [ "$1" = "force" ]; then
    echo "📈 Generating comprehensive analytics report..." | tee -a "$ANALYTICS_LOG"
    
    # Generate full analytics report
    if python3 /nfs/projects/claude-code-Tmux-Orchestrator/continuous_metrics_analytics.py report > /tmp/analytics_report_$TIMESTAMP.json; then
        echo "✅ Analytics report generated successfully" | tee -a "$ANALYTICS_LOG"
        
        # Extract key metrics for quick reference
        overall_score=$(jq -r '.performance_scores.overall_score // 0' /tmp/analytics_report_$TIMESTAMP.json 2>/dev/null)
        operational_status=$(jq -r '.summary.operational_status // "unknown"' /tmp/analytics_report_$TIMESTAMP.json 2>/dev/null)
        total_operations=$(jq -r '.summary.total_operations // 0' /tmp/analytics_report_$TIMESTAMP.json 2>/dev/null)
        
        # Update Redis with key metrics
        redis-cli -p 18000 SET "nova:analytics:overall_score" "$overall_score" EX 86400 >/dev/null
        redis-cli -p 18000 SET "nova:analytics:status" "$operational_status" EX 86400 >/dev/null
        redis-cli -p 18000 SET "nova:analytics:operations" "$total_operations" EX 86400 >/dev/null
        redis-cli -p 18000 SET "nova:last_analytics_report" "$current_time" EX 604800 >/dev/null  # 1 week
        
        # Send report to coordination stream
        redis-cli -p 18000 XADD nova.analytics.updates '*' \
            timestamp "$TIMESTAMP" \
            nova_id "torch" \
            overall_score "$overall_score" \
            status "$operational_status" \
            operations "$total_operations" \
            report_file "/tmp/analytics_report_$TIMESTAMP.json" >/dev/null
        
        echo "📊 Analytics: Score=$overall_score/100, Status=$operational_status, Ops=$total_operations" | tee -a "$ANALYTICS_LOG"
        
        # Check for alerts and recommendations
        alert_count=$(jq -r '.alerts | length' /tmp/analytics_report_$TIMESTAMP.json 2>/dev/null || echo "0")
        rec_count=$(jq -r '.recommendations | length' /tmp/analytics_report_$TIMESTAMP.json 2>/dev/null || echo "0")
        
        if [ "$alert_count" -gt 0 ]; then
            echo "⚠️  $alert_count alerts detected - check report for details" | tee -a "$ANALYTICS_LOG"
            
            # Send alert to priority stream
            redis-cli -p 18000 XADD nova.priority.alerts '*' \
                timestamp "$TIMESTAMP" \
                nova_id "torch" \
                alert_count "$alert_count" \
                recommendation_count "$rec_count" \
                report_location "/tmp/analytics_report_$TIMESTAMP.json" >/dev/null
        fi
        
        if [ "$rec_count" -gt 0 ]; then
            echo "💡 $rec_count recommendations available - optimizations suggested" | tee -a "$ANALYTICS_LOG"
        fi
        
    else
        echo "❌ Failed to generate analytics report" | tee -a "$ANALYTICS_LOG"
    fi
else
    echo "⏳ Next full report in $(((report_interval_seconds - time_since_report) / 60)) minutes" | tee -a "$ANALYTICS_LOG"
fi

# Always collect basic metrics for continuous monitoring
echo "📊 Collecting basic operational metrics..." | tee -a "$ANALYTICS_LOG"

# Quick metrics collection
queue_size=$(wc -l < /tmp/torch_work_queue.txt 2>/dev/null || echo "0")
redis_ops_count=$(redis-cli -p 18000 XLEN torch.continuous.ops 2>/dev/null || echo "0")
wake_signals_count=$(redis-cli -p 18000 XLEN nova.wake.signals 2>/dev/null || echo "0")
cooldown_active=$(redis-cli -p 18000 GET claude_restart_cooldown 2>/dev/null || echo "0")

# Store quick metrics
redis-cli -p 18000 XADD nova.metrics.quick '*' \
    timestamp "$TIMESTAMP" \
    window "$CURRENT_WINDOW" \
    queue_size "$queue_size" \
    ops_count "$redis_ops_count" \
    signals_count "$wake_signals_count" \
    cooldown_active "$cooldown_active" \
    collection_interval "$METRICS_INTERVAL_MINUTES" >/dev/null

# System health check
health_status="healthy"
if [ "$cooldown_active" = "1" ]; then
    health_status="cooldown"
elif [ "$queue_size" -gt 100 ]; then
    health_status="backlogged"
elif [ "$queue_size" -gt 50 ]; then
    health_status="busy"
fi

echo "🏥 System Health: $health_status (Queue: $queue_size, Ops: $redis_ops_count, Signals: $wake_signals_count)" | tee -a "$ANALYTICS_LOG"

# Update health in Redis
redis-cli -p 18000 SET "nova:health:status" "$health_status" EX 1800 >/dev/null  # 30 min TTL
redis-cli -p 18000 SET "nova:health:last_check" "$TIMESTAMP" EX 3600 >/dev/null  # 1 hour TTL

# Performance trend analysis (compare with previous metrics)
previous_score=$(redis-cli -p 18000 GET "nova:analytics:overall_score" 2>/dev/null || echo "0")
if [ "$previous_score" != "0" ] && command -v bc >/dev/null; then
    current_score=$(redis-cli -p 18000 GET "nova:analytics:overall_score" 2>/dev/null || echo "0")
    if [ "$current_score" != "0" ]; then
        trend=$(echo "scale=1; $current_score - $previous_score" | bc 2>/dev/null || echo "0")
        if (( $(echo "$trend > 5" | bc -l 2>/dev/null) )); then
            echo "📈 Performance trending up (+$trend points)" | tee -a "$ANALYTICS_LOG"
        elif (( $(echo "$trend < -5" | bc -l 2>/dev/null) )); then
            echo "📉 Performance trending down ($trend points)" | tee -a "$ANALYTICS_LOG"
        else
            echo "📊 Performance stable ($trend point change)" | tee -a "$ANALYTICS_LOG"
        fi
    fi
fi

# Clean up old analytics files (keep last 10)
find /tmp -name "analytics_report_*.json" -type f | sort | head -n -10 | xargs rm -f 2>/dev/null

# Log completion
echo "✅ Metrics dashboard update complete - $TIMESTAMP" | tee -a "$ANALYTICS_LOG"

# Send completion signal to coordination
redis-cli -p 18000 XADD nova.metrics.dashboard '*' \
    timestamp "$TIMESTAMP" \
    window "$CURRENT_WINDOW" \
    update_type "periodic" \
    health_status "$health_status" \
    queue_size "$queue_size" \
    completion_status "success" >/dev/null

exit 0