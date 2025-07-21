# CLAUDE.md - Nova-Torch Integration

**Version:** 2.0.0  
**Date:** 2025-01-16  
**Author:** pm-torch  
**Department:** DevOps  
**Project:** Torch  

This file provides guidance to Claude Code (claude.ai/code) when working with the Nova-Torch integration.

## Project Overview

Nova-Torch is the production-ready evolution of the original Tmux Orchestrator, designed for integration with the Nova project ecosystem using DragonflyDB for communication and distributed agent management.

## Relationship to Original System

This project builds upon the original Tmux Orchestrator (`../`) while adding:
- DragonflyDB communication layer replacing tmux send-keys
- Distributed agent registry and management
- Production-ready monitoring and observability
- Scalable multi-node architecture

**Original System Access:**
- Scripts: `../send-claude-message.sh`, `../schedule_with_note.sh`
- Documentation: `../CLAUDE-original-v1.0.0.md`
- Learnings: `../LEARNINGS.md`

## Development Commands

### Environment Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start DragonflyDB locally
docker-compose up -d dragonfly

# Run tests
pytest tests/

# Start development server
python -m nova_torch.main
```

### Key Scripts
```bash
# Original tmux-based communication (fallback)
../send-claude-message.sh <session:window> "message"

# New DragonflyDB communication
python -m nova_torch.communication.send_message <agent_id> "message"

# Agent registry management
python -m nova_torch.orchestration.agent_registry --list
python -m nova_torch.orchestration.agent_registry --spawn <role> <skills>
```

## Architecture

### Communication Layer
```python
# DragonflyDB-based messaging
from nova_torch.communication import NovaOrchestrator

orchestrator = NovaOrchestrator()
orchestrator.send_message('agent_123', 'Task assignment: implement auth')
```

### Agent Management
```python
# Distributed agent registry
from nova_torch.orchestration import AgentRegistry

registry = AgentRegistry()
agents = registry.find_available_agents(role='developer', skills=['python'])
```

### Monitoring
```python
# Observability and metrics
from nova_torch.monitoring import SystemMonitor

monitor = SystemMonitor()
metrics = monitor.get_system_health()
```

## Integration Patterns

### Backward Compatibility
- Original tmux scripts remain functional
- Gradual migration path from tmux to DragonflyDB
- Fallback mechanisms for system failures

### Nova System Integration
- Uses DragonflyDB for inter-service communication
- Integrates with central task management system
- Provides metrics to Nova monitoring stack

## Development Workflow

1. **Reference Original**: Check `../LEARNINGS.md` for battle-tested patterns
2. **Test Locally**: Use docker-compose for local DragonflyDB
3. **Maintain Compatibility**: Ensure original system remains functional
4. **Version Control**: Follow semantic versioning in `VERSION` file
5. **Document Changes**: Update `CHANGELOG.md` with all modifications

## Safety Protocols

### Git Discipline (Inherited from Original)
- Commit every 30 minutes during development
- Use feature branches for new functionality
- Tag stable versions before major changes

### Testing Requirements
- Unit tests for all new components
- Integration tests with DragonflyDB
- Backward compatibility tests with original system
- Performance benchmarks vs. original implementation

## Troubleshooting

### Common Issues
1. **DragonflyDB Connection**: Check docker-compose services
2. **Agent Registration**: Verify Redis connection and keys
3. **Message Delivery**: Check channel subscriptions
4. **Fallback Mode**: Use original tmux scripts if needed

### Debug Commands
```bash
# Check DragonflyDB status
docker-compose ps dragonfly

# Monitor message flow
python -m nova_torch.communication.debug_monitor

# Agent registry status
python -m nova_torch.orchestration.agent_registry --status
```

## Migration Strategy

### Phase 1: Communication Layer
- Replace tmux send-keys with DragonflyDB pubsub
- Maintain original execution environment
- Add message persistence and correlation

### Phase 2: Agent Management
- Implement distributed agent registry
- Add dynamic agent spawning
- Enable cross-node communication

### Phase 3: Production Features
- Add comprehensive monitoring
- Implement fault tolerance
- Enable auto-scaling

## Version History

- **v2.0.0**: Initial Nova integration architecture
- **v1.0.0**: Original Tmux Orchestrator (see `../CLAUDE-original-v1.0.0.md`)

## References

- Original Assessment: `../../.claude/assessment/torch_assessment_initial.md`
- Integration Plan: `../../.claude/Planning/torch_plan_integration.md`
- Operations History: `../../.claude/torch_operations_history.md`