# Nova-Torch Integration

**Version:** 0.1.0  
**Date:** 2025-01-16  
**Author:** pm-torch  
**Department:** DevOps  
**Project:** Torch  

## Overview

Nova-Torch is the production-ready evolution of the original Tmux Orchestrator, designed to integrate seamlessly with the Nova project ecosystem using DragonflyDB for communication and distributed agent management.

## Relationship to Original

This project builds upon the battle-tested patterns from the original Tmux Orchestrator while adding:
- DragonflyDB communication layer
- Distributed agent management
- Production-ready observability
- Scalable architecture patterns

## Directory Structure

```
nova-torch/
├── VERSION                 # Semantic versioning
├── CHANGELOG.md           # Version history
├── README.md              # This file
├── src/
│   ├── communication/     # DragonflyDB messaging
│   ├── orchestration/     # Agent management
│   └── monitoring/        # Observability
├── config/                # Configuration files
├── tests/                 # Test suites
├── docs/                  # Documentation
└── deployment/            # Deployment configs
```

## Original System Access

The original Tmux Orchestrator remains fully functional in the parent directory:
- **Scripts**: `../send-claude-message.sh`, `../schedule_with_note.sh`
- **Utilities**: `../tmux_utils.py`
- **Documentation**: `../CLAUDE-original-v1.0.0.md`
- **Learnings**: `../LEARNINGS.md`

## Development Status

- **Current Version**: 0.1.0 (Planning Phase)
- **Next Version**: 0.2.0 (DragonflyDB Integration)
- **Target Version**: 1.0.0 (Production Ready)

## Integration Benefits

1. **Preserves Original**: Tmux-based system remains operational
2. **Evolutionary Path**: Clear progression from proof-of-concept to production
3. **Shared Knowledge**: Access to original learnings and patterns
4. **Backward Compatibility**: Can fallback to original system if needed
5. **Comparative Development**: Test new features against proven baseline

## Quick Start

Currently in planning phase. See:
- `../.claude/assessment/torch_assessment_initial.md`
- `../.claude/Planning/torch_plan_integration.md`

## Contributing

Follow semantic versioning for all changes:
- **MAJOR**: Breaking changes
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, backward compatible

Update `CHANGELOG.md` with all changes.