# Nova-Torch Load Testing Suite

Comprehensive load testing framework for Nova-Torch using Locust.

## Overview

This load testing suite simulates realistic traffic patterns for Nova-Torch, including:
- Agent registration and heartbeats
- Task assignment and completion
- Collaboration requests
- Message streaming via DragonflyDB
- gRPC API interactions

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Verify Locust installation
locust --version
```

### Basic Usage

```bash
# Run smoke test (quick verification)
python run_load_tests.py smoke --environment local

# Run development load test
python run_load_tests.py development --environment local

# Run full test suite
python run_load_tests.py suite --environment staging
```

### Web UI Mode

```bash
# Start Locust web UI for interactive testing
locust -f locustfile.py --host http://localhost:50051

# Then open http://localhost:8089 in your browser
```

## Test Profiles

| Profile | Users | Duration | Purpose |
|---------|-------|----------|---------|
| smoke | 5 | 2m | Quick functionality verification |
| development | 20 | 5m | Development environment testing |
| staging | 100 | 15m | Pre-production validation |
| production | 500 | 30m | Production load simulation |
| stress | 1000 | 1h | Breaking point identification |
| soak | 200 | 4h | Long-term stability testing |
| spike | 2000 | 10m | Traffic spike handling |

## Load Test Architecture

### User Classes

1. **NovaOrchestratorUser** (Weight: 3)
   - Simulates orchestrator operations
   - Task assignment and management
   - System coordination

2. **NovaAgentUser** (Weight: 10) 
   - Simulates agent behavior
   - Task execution and completion
   - Heartbeat reporting

3. **NovaSystemStressUser** (Weight: 1)
   - High-intensity stress testing
   - Rapid message bursts
   - System limit testing

### Message Types Tested

- `task_assignment` - Task distribution
- `task_completion` - Task results
- `agent_heartbeat` - Agent status updates
- `collaboration_request` - Inter-agent communication
- `broadcast` - System-wide notifications
- `system_status` - Health monitoring

## Configuration

### Environment Configuration

Edit `load_test_config.py` to customize environments:

```python
ENVIRONMENTS = {
    "local": {
        "host": "localhost",
        "dragonfly_port": 6379,
        "grpc_port": 50051
    },
    "k8s-production": {
        "host": "api.nova-torch.example.com",
        "dragonfly_port": 6379, 
        "grpc_port": 443,
        "tls": True
    }
}
```

### Custom Profiles

Create custom test profiles:

```python
CUSTOM_PROFILE = LoadTestProfile(
    name="custom",
    description="Custom load test",
    users=100,
    spawn_rate=10,
    run_time="10m",
    host="custom.nova-torch.internal"
)
```

## Advanced Usage

### Distributed Load Testing

```bash
# Start master node
python run_load_tests.py production --distributed --workers 4

# Start worker nodes (on separate machines)
locust -f locustfile.py --worker --master-host <master-ip>
```

### Custom Scenarios

```bash
# Agent scaling test
python -c "from load_test_config import LoadTestScenarios; print(LoadTestScenarios.agent_scaling_test())"

# Collaboration stress test
python -c "from load_test_config import LoadTestScenarios; print(LoadTestScenarios.collaboration_stress_test())"
```

### Performance Thresholds

Tests automatically validate against performance thresholds:

```python
PERFORMANCE_THRESHOLDS = {
    "production": {
        "avg_response_time": 100,  # ms
        "95th_percentile": 500,
        "error_rate": 0.005,
        "throughput_rps": 2000
    }
}
```

## Results and Reporting

### Output Files

Each test generates:
- `{test_id}_report.html` - Visual test report
- `{test_id}_results_stats.csv` - Detailed statistics
- `{test_id}_results_failures.csv` - Failure analysis
- `{test_id}_summary.json` - Structured results
- `{test_id}.log` - Execution logs

### Metrics Tracked

- **Response Times**: Average, min, max, percentiles
- **Throughput**: Requests per second
- **Error Rates**: Failure percentage by request type
- **Resource Usage**: CPU, memory, network
- **System Health**: Component status and availability

### Sample Report Analysis

```bash
# Generate performance report
python -c "
from run_load_tests import LoadTestRunner
runner = LoadTestRunner()
# Analyze results...
"
```

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Run Load Tests
  run: |
    python run_load_tests.py smoke --environment staging
    
- name: Upload Results
  uses: actions/upload-artifact@v3
  with:
    name: load-test-results
    path: load_test_results/
```

### Jenkins Pipeline

```groovy
stage('Load Testing') {
    steps {
        sh 'python run_load_tests.py development --environment staging'
        publishHTML([
            allowMissing: false,
            alwaysLinkToLastBuild: true,
            keepAll: true,
            reportDir: 'load_test_results',
            reportFiles: '*_report.html',
            reportName: 'Load Test Report'
        ])
    }
}
```

## Monitoring Integration

### Prometheus Metrics

The load tests automatically expose metrics compatible with the Nova-Torch monitoring stack:

```python
# Custom metrics in tests
load_test_requests_total
load_test_response_time_seconds
load_test_errors_total
```

### Grafana Dashboard

Import the load testing dashboard to visualize:
- Real-time test progress
- Response time distributions
- Error rate trends
- System resource impact

## Troubleshooting

### Common Issues

1. **Connection Refused**
   ```bash
   # Verify target service is running
   curl -v http://localhost:50051/health
   
   # Check network connectivity
   telnet localhost 6379
   ```

2. **High Error Rates**
   ```bash
   # Check system resources
   kubectl top pods -n nova-torch
   
   # Review application logs
   kubectl logs -f deployment/nova-torch-orchestrator -n nova-torch
   ```

3. **Slow Performance**
   ```bash
   # Monitor system metrics during test
   python -c "import psutil; print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')"
   ```

### Debug Mode

```bash
# Run with verbose logging
PYTHONPATH=. python run_load_tests.py development --environment local -v

# Enable debug output
export LOCUST_LOGLEVEL=DEBUG
```

## Best Practices

### Test Design
- Start with smoke tests before larger loads
- Use realistic message distributions
- Include both success and failure scenarios
- Test auto-scaling triggers

### Performance Baseline
- Establish baseline performance metrics
- Run consistent test environments
- Document expected performance ranges
- Track performance trends over time

### Load Patterns
- Gradual ramp-up to avoid shock loading
- Sustained load periods for stability testing
- Spike testing for scalability validation
- Graceful ramp-down to test cleanup

### Result Analysis
- Compare results against baselines
- Identify performance bottlenecks
- Correlate with system resource usage
- Document findings and improvements

## Examples

### Basic Load Test

```bash
# Simple smoke test
python run_load_tests.py smoke

# Development environment test  
python run_load_tests.py development --environment local
```

### Advanced Testing

```bash
# Production simulation with validation
python run_load_tests.py production --environment k8s-staging

# Full test suite for release validation
python run_load_tests.py all --environment k8s-staging
```

### Custom Test Execution

```python
from run_load_tests import LoadTestRunner
from load_test_config import LoadTestProfile

# Create custom profile
custom_profile = LoadTestProfile(
    name="custom_spike",
    description="Custom spike test",
    users=1000,
    spawn_rate=100,
    run_time="5m",
    host="localhost"
)

# Run test
runner = LoadTestRunner()
results = runner.run_test("custom_spike", "local")
print(f"Test completed: {results['success']}")
```