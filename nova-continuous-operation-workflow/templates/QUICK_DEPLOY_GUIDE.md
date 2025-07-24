# Nova Continuous Operation Workflow - Quick Deployment Guide

## 🚀 5-Minute Setup for Any Nova

### Prerequisites
- Python 3.8+
- Access to DragonflyDB on port 18000
- Write access to `/nfs/novas/` directory

### Quick Deploy (One Command)
```bash
cd /nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/templates
./nova-deployment-template.sh <nova-name>
```

Example for Nova Echo:
```bash
./nova-deployment-template.sh echo
```

This will:
1. ✅ Create Nova-specific directory structure
2. ✅ Install workflow components
3. ✅ Generate personalized configuration
4. ✅ Create management scripts
5. ✅ Initialize communication streams

### Post-Deployment Steps

#### 1. Choose Personality Profile (Optional)
Edit `/nfs/novas/<nova-name>/continuous-workflow/config/nova_config.json`

Available personalities:
- `analytical` - Deep thinker, quality-focused
- `creative` - Innovation-focused, experimental
- `efficient` - Speed-focused, results-oriented
- `collaborative` - Team-focused, coordination expert
- `guardian` - Safety-first, careful approach
- `balanced` - Well-rounded, adaptive (default)

#### 2. Start the Workflow
```bash
cd /nfs/novas/<nova-name>/continuous-workflow
./start_workflow.sh
```

#### 3. Monitor Health
```bash
./check_health.sh
```

### Integration with Existing Nova

If your Nova already has systems running, the workflow integrates seamlessly:

1. **Reads from existing streams**:
   - `nova.coordination.<nova-name>`
   - `nova.tasks.<nova-name>.todo`

2. **Posts updates to**:
   - `nova.tasks.<nova-name>.progress`
   - `nova.tasks.<nova-name>.completed`
   - `nova.safety.<nova-name>`

3. **Respects existing work** - won't interfere with current tasks

### Safety Features (Built-in)

All Novas automatically get:
- 🛡️ API rate limiting (25/min, 400/hour)
- 🔄 Infinite loop detection
- 📊 Resource monitoring
- 🚨 Emergency cooldowns
- ✅ NOVA protocol compliance

### Troubleshooting

#### Workflow won't start?
```bash
# Check logs
tail -f logs/workflow_$(date +%Y%m%d).log

# Verify Redis connection
redis-cli -p 18000 ping
```

#### Too many restarts?
The system has Frosty protection - this is normal and will stabilize.

#### Need to stop?
```bash
./stop_workflow.sh
```

### Advanced Configuration

#### Adjust Work Patterns
In `nova_config.json`, modify:
```json
"workflow_config": {
    "celebration_duration_seconds": 180,  // How long to celebrate
    "phase_transition_pause_seconds": 180, // Break between phases
    "work_discovery_interval_seconds": 60  // How often to check for work
}
```

#### Custom Safety Limits
```json
"safety_config": {
    "api_rate_limit_per_minute": 25,  // Adjust if needed
    "api_rate_limit_per_hour": 400    // Conservative default
}
```

### Support

For issues or questions:
1. Check `/nfs/projects/claude-code-Tmux-Orchestrator/nova-continuous-operation-workflow/docs/`
2. Review logs in Nova's `logs/` directory
3. Coordinate with Nova Torch via streams

---

Remember: The workflow prevents completion celebration loops while maintaining continuous productive operation!