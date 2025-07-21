# Nova-Torch Deployment Guide - Bare Metal with systemd

**Date:** 2025-01-16 16:00:00 UTC  
**Author:** pm-torch  
**Department:** DevOps  
**Project:** Nova-Torch  
**Document Type:** Deployment Guide  

## Overview

This guide covers deploying Nova-Torch on bare metal servers using systemd for service management. We DO NOT use Docker containers - all services run directly on the host with systemd supervision.

## Prerequisites

### System Requirements
- Ubuntu 22.04 LTS or newer (or compatible systemd-based distribution)
- Python 3.10+
- systemd 249+
- Redis CLI tools (for DragonflyDB interaction)
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

### Access Requirements
- Read access to `/adaptai/ceo/secrets/`
- sudo privileges for systemd service management
- DragonflyDB connection credentials

## Installation Steps

### 1. Create System User
```bash
# Create dedicated user for nova-torch
sudo useradd -r -s /bin/bash -d /var/lib/nova-torch -m nova-torch

# Add to necessary groups
sudo usermod -a -G systemd-journal nova-torch
```

### 2. Directory Structure
```bash
# Create required directories
sudo mkdir -p /opt/nova-torch
sudo mkdir -p /etc/nova-torch/agents
sudo mkdir -p /var/log/nova-torch
sudo mkdir -p /var/lib/nova-torch

# Set ownership
sudo chown -R nova-torch:nova-torch /opt/nova-torch
sudo chown -R nova-torch:nova-torch /etc/nova-torch
sudo chown -R nova-torch:nova-torch /var/log/nova-torch
sudo chown -R nova-torch:nova-torch /var/lib/nova-torch
```

### 3. Install Application
```bash
# Clone repository
cd /opt
sudo -u nova-torch git clone https://github.com/TeamADAPT/nova-torch.git

# Install Python dependencies
cd /opt/nova-torch
sudo -u nova-torch python3 -m venv venv
sudo -u nova-torch ./venv/bin/pip install -r requirements.txt
```

### 4. Configure DragonflyDB Access
```bash
# Create password file (secure read from secrets)
sudo touch /etc/nova-torch/dragonfly-password
sudo chmod 600 /etc/nova-torch/dragonfly-password
sudo chown nova-torch:nova-torch /etc/nova-torch/dragonfly-password

# Copy password from secrets (manual step for security)
# sudo -u nova-torch cat /adaptai/ceo/secrets/DRAGONFLY_ACCESS_AND_NAMING_GUIDE.md | grep "Password:" | cut -d' ' -f2 > /etc/nova-torch/dragonfly-password
```

### 5. Main Configuration
```bash
# Create main config
sudo -u nova-torch cat > /etc/nova-torch/config.yaml << 'EOF'
# Nova-Torch Configuration
dragonfly:
  host: localhost
  port: 18000
  password_file: /etc/nova-torch/dragonfly-password
  
streams:
  prefix: "nova.torch"
  orchestrator: "nova.torch.orchestrator"
  agents: "nova.torch.agents"
  registry: "nova.torch.registry"
  tasks: "nova.torch.tasks"
  monitoring: "nova.torch.monitoring"

orchestrator:
  heartbeat_interval: 30
  agent_timeout: 120
  max_agents: 50
  
logging:
  level: INFO
  format: json
  output: /var/log/nova-torch/orchestrator.log
  
monitoring:
  metrics_port: 9090
  health_check_port: 8080
EOF
```

### 6. Install systemd Services
```bash
# Copy service files
sudo cp deployment/systemd/*.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload
```

### 7. Start Services
```bash
# Enable and start orchestrator
sudo systemctl enable nova-torch-orchestrator.service
sudo systemctl start nova-torch-orchestrator.service

# Check status
sudo systemctl status nova-torch-orchestrator.service
```

## Agent Management

### Starting Agents
```bash
# Start a specific agent (e.g., developer-1)
sudo systemctl start nova-torch-agent@developer-1.service

# Enable agent to start on boot
sudo systemctl enable nova-torch-agent@developer-1.service
```

### Agent Configuration
Create configuration for each agent:
```bash
sudo -u nova-torch cat > /etc/nova-torch/agents/developer-1.yaml << 'EOF'
agent:
  id: developer-1
  role: developer
  skills:
    - python
    - javascript
    - testing
  max_concurrent_tasks: 3
  
tmux_fallback:
  enabled: true
  session: "legacy-developer-1"
  window: 0
EOF
```

### Managing Multiple Agents
```bash
# Start multiple agents
for i in {1..5}; do
  sudo systemctl start nova-torch-agent@developer-$i.service
done

# Check all agent statuses
sudo systemctl status 'nova-torch-agent@*.service'
```

## Monitoring

### Logs
```bash
# View orchestrator logs
sudo journalctl -u nova-torch-orchestrator -f

# View specific agent logs
sudo journalctl -u nova-torch-agent@developer-1 -f

# View all nova-torch logs
sudo journalctl -t nova-torch-orchestrator -t nova-torch-agent-* -f
```

### Health Checks
```bash
# Check orchestrator health
curl http://localhost:8080/health

# Check metrics
curl http://localhost:9090/metrics
```

### DragonflyDB Monitoring
```bash
# Monitor nova-torch streams
redis-cli -h localhost -p 18000 -a "$(cat /etc/nova-torch/dragonfly-password)" --no-auth-warning \
  XREAD BLOCK 0 STREAMS nova.torch.monitoring $
```

## Maintenance

### Service Control
```bash
# Restart orchestrator
sudo systemctl restart nova-torch-orchestrator

# Stop all agents
sudo systemctl stop 'nova-torch-agent@*.service'

# Reload configuration
sudo systemctl reload nova-torch-orchestrator
```

### Updates
```bash
# Update code
cd /opt/nova-torch
sudo -u nova-torch git pull
sudo -u nova-torch ./venv/bin/pip install -r requirements.txt

# Restart services
sudo systemctl restart nova-torch-orchestrator
sudo systemctl restart 'nova-torch-agent@*.service'
```

### Backup
```bash
# Backup configuration
sudo tar -czf /backup/nova-torch-config-$(date +%Y%m%d).tar.gz /etc/nova-torch/

# Backup data
sudo tar -czf /backup/nova-torch-data-$(date +%Y%m%d).tar.gz /var/lib/nova-torch/
```

## Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u nova-torch-orchestrator -n 50

# Verify permissions
ls -la /etc/nova-torch/
ls -la /var/log/nova-torch/

# Test configuration
sudo -u nova-torch python3 -m nova_torch.config_test
```

### DragonflyDB Connection Issues
```bash
# Test connection
redis-cli -h localhost -p 18000 -a "$(cat /etc/nova-torch/dragonfly-password)" --no-auth-warning PING

# Check firewall
sudo iptables -L -n | grep 18000
```

### Agent Registration Failures
```bash
# Check agent preflight
sudo -u nova-torch python3 -m nova_torch.agent.preflight --agent-id developer-1

# Verify agent config
sudo -u nova-torch python3 -m nova_torch.agent.validate_config /etc/nova-torch/agents/developer-1.yaml
```

## Security Considerations

### File Permissions
- Config files: 640 (nova-torch:nova-torch)
- Password files: 600 (nova-torch:nova-torch)
- Log files: 640 (nova-torch:nova-torch)
- Application code: 755 (nova-torch:nova-torch)

### systemd Hardening
- NoNewPrivileges: Prevents privilege escalation
- ProtectSystem: Read-only system directories
- PrivateTmp: Isolated temporary files
- Resource limits: Memory and CPU quotas

### Network Security
- DragonflyDB: Bind to localhost only
- Metrics: Internal network only
- Health checks: Behind reverse proxy

## Integration with Original Tmux System

The nova-torch system maintains backward compatibility:

1. **Fallback Mode**: Agents can fall back to tmux communication
2. **Hybrid Operation**: Some agents on DragonflyDB, others on tmux
3. **Migration Path**: Gradual agent migration without downtime

```bash
# Enable tmux fallback for specific agent
sudo -u nova-torch sed -i 's/enabled: false/enabled: true/' /etc/nova-torch/agents/developer-1.yaml
sudo systemctl restart nova-torch-agent@developer-1
```

---

**Document Maintained By:** pm-torch  
**Department:** DevOps  
**Project:** Nova-Torch  
**Classification:** Internal Deployment Guide  
**Last Updated:** 2025-01-16