# Nova-Torch Kubernetes Deployment Guide

This directory contains production-ready Kubernetes manifests for deploying Nova-Torch.

## Prerequisites

1. Kubernetes cluster (1.24+)
2. kubectl configured
3. Helm (for cert-manager)
4. Prometheus Operator (optional but recommended)
5. NGINX Ingress Controller

## Quick Start

### 1. Install Prerequisites

```bash
# Install NGINX Ingress Controller
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.8.1/deploy/static/provider/cloud/deploy.yaml

# Install cert-manager for TLS
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.12.0/cert-manager.yaml

# Install Prometheus Operator (optional)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### 2. Configure Secrets

```bash
# Create DragonflyDB password
kubectl create secret generic nova-torch-secrets \
  --from-literal=dragonfly-password=$(openssl rand -base64 32) \
  -n nova-torch --dry-run=client -o yaml > secrets-prod.yaml

# Create Grafana admin password
kubectl create secret generic grafana-secrets \
  --from-literal=admin-password=$(openssl rand -base64 32) \
  -n nova-torch --dry-run=client -o yaml >> secrets-prod.yaml
```

### 3. Deploy Nova-Torch

Using Kustomize:
```bash
# Deploy all resources
kubectl apply -k .

# Or deploy with custom overlays
kubectl apply -k overlays/production/
```

Manual deployment:
```bash
# Create namespace and RBAC
kubectl apply -f namespace.yaml
kubectl apply -f rbac.yaml

# Configure secrets and configs
kubectl apply -f secrets.yaml  # Edit first!
kubectl apply -f configmap.yaml

# Deploy DragonflyDB
kubectl apply -f dragonfly-deployment.yaml

# Deploy Nova-Torch
kubectl apply -f orchestrator-deployment.yaml
kubectl apply -f agent-deployment.yaml

# Setup monitoring
kubectl apply -f monitoring-deployment.yaml

# Configure autoscaling
kubectl apply -f autoscaling.yaml

# Setup ingress
kubectl apply -f ingress.yaml
```

## Architecture

### Components

1. **Orchestrator** (3 replicas)
   - Central coordination
   - Task distribution
   - Agent management
   - gRPC API

2. **Agents** (5-50 replicas, auto-scaled)
   - Task execution
   - Specialized roles (developer, PM, QA)
   - Autonomous operation

3. **DragonflyDB** (3-node cluster)
   - Message streaming
   - State management
   - High-performance cache

4. **Monitoring Stack**
   - Prometheus for metrics
   - Grafana for visualization
   - Custom dashboards

### Networking

- Internal communication via ClusterIP services
- External access via NGINX Ingress
- TLS termination at ingress
- Network policies for security

### Storage

- DragonflyDB: 100Gi SSD per node
- Prometheus: 100Gi for metrics
- Grafana: 10Gi for dashboards
- Agents: 10Gi ephemeral per pod

## Configuration

### Environment Variables

Key environment variables for customization:

```yaml
NOVA_TORCH_ROLE: orchestrator|agent
AGENT_TYPE: developer|project_manager|qa|devops
DRAGONFLY_HOST: dragonfly-service
DRAGONFLY_PORT: 6379
ORCHESTRATOR_HOST: nova-torch-orchestrator
ORCHESTRATOR_PORT: 50051
```

### ConfigMaps

Main configuration in `configmap.yaml`:
- System settings
- DragonflyDB connection
- Orchestrator parameters
- Agent limits
- Monitoring config

### Scaling

Horizontal Pod Autoscaling configured for:
- Orchestrator: 3-10 replicas
- Agents: 5-50 replicas
- Developer agents: 3-20 replicas
- PM agents: 2-10 replicas

Vertical Pod Autoscaling available for resource optimization.

## Monitoring

### Metrics

Access Prometheus metrics:
```bash
kubectl port-forward -n nova-torch svc/prometheus 9090:9090
```

Key metrics:
- `nova_torch_agents_active`: Active agent count
- `nova_torch_tasks_queued`: Queue depth
- `nova_torch_messages_total`: Message throughput
- `nova_torch_system_health_status`: Overall health

### Dashboards

Access Grafana:
```bash
kubectl port-forward -n nova-torch svc/grafana 3000:3000
```

Default credentials: admin / (check secret)

Pre-configured dashboards:
- Nova-Torch Overview
- Agent Performance
- Task Analytics
- System Health

### Alerts

Example alert rules:
```yaml
- High task queue depth (>1000)
- Low agent availability (<3)
- Orchestrator unhealthy
- DragonflyDB connection lost
```

## Security

### RBAC

- Orchestrator: Full pod management
- Agents: Read-only access
- Prometheus: Metrics scraping

### Network Policies

- Restricted pod-to-pod communication
- DragonflyDB isolated
- Monitoring segregated

### TLS/SSL

- Ingress TLS with cert-manager
- Internal TLS optional
- Secrets encrypted at rest

## Troubleshooting

### Check Pod Status
```bash
kubectl get pods -n nova-torch
kubectl describe pod <pod-name> -n nova-torch
kubectl logs <pod-name> -n nova-torch
```

### Common Issues

1. **Pods not starting**
   - Check resource limits
   - Verify secrets exist
   - Check init container logs

2. **Connection errors**
   - Verify services are running
   - Check network policies
   - Test DNS resolution

3. **Performance issues**
   - Review HPA metrics
   - Check resource utilization
   - Analyze Prometheus metrics

### Debug Commands
```bash
# Test DragonflyDB connection
kubectl run -it --rm debug --image=redis:7 --restart=Never -n nova-torch -- redis-cli -h dragonfly-service -a $PASSWORD ping

# Check orchestrator health
kubectl exec -it <orchestrator-pod> -n nova-torch -- curl http://localhost:8001/health

# View agent logs
kubectl logs -f -l app=nova-torch,component=agent -n nova-torch
```

## Maintenance

### Backup

DragonflyDB backups:
```bash
# Trigger manual snapshot
kubectl exec -it dragonfly-0 -n nova-torch -- redis-cli BGSAVE

# Copy snapshot
kubectl cp nova-torch/dragonfly-0:/data/dump.rdb ./backup-$(date +%Y%m%d).rdb
```

### Updates

Rolling updates:
```bash
# Update image
kubectl set image deployment/nova-torch-orchestrator orchestrator=nova-torch/orchestrator:0.3.0 -n nova-torch

# Monitor rollout
kubectl rollout status deployment/nova-torch-orchestrator -n nova-torch
```

### Scaling

Manual scaling:
```bash
# Scale agents
kubectl scale deployment/nova-torch-agent --replicas=10 -n nova-torch

# Scale orchestrator
kubectl scale deployment/nova-torch-orchestrator --replicas=5 -n nova-torch
```

## Production Checklist

- [ ] Replace default passwords
- [ ] Configure proper domain names
- [ ] Setup backup strategy
- [ ] Configure monitoring alerts
- [ ] Test disaster recovery
- [ ] Document runbooks
- [ ] Setup log aggregation
- [ ] Configure resource quotas
- [ ] Enable audit logging
- [ ] Test autoscaling