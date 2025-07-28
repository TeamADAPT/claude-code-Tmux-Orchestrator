# Tmux Orchestrator Charter

**Date:** 2025-01-27
**Co-Owners:** Chase & Torch (Nova AI Agent)
**Department:** AI Infrastructure
**Project:** TMUX-ORCH

## Project Co-Ownership Agreement

### Vision Statement
Build and maintain an AI-powered session management system where Claude acts as the orchestrator for multiple Claude agents across tmux sessions, enabling 24/7 autonomous development.

### Co-Owner Roles
**Chase - Product Owner**
- Strategic direction and vision
- Integration requirements with Nova ecosystem
- Resource allocation and approval
- External partnerships

**Torch - Technical Lead**
- Implementation and architecture
- Quality assurance and testing
- Technical decision making
- Day-to-day development

### Success Metrics
- **Technical**: Agent uptime >99%, Message latency <100ms, Task completion >95%
- **Business**: 40% productivity increase, 50% fewer coordination failures
- **Quality**: 100% test coverage for critical paths, <5% error rate

---

## Operational Work Context

### Current Project Scope

**Active Focus**: NOVAWF Development & Nova Wake System
**Phase**: Implementation/Testing

### Contextual Work Areas

#### Planning & Architecture
- [ ] Design Nova wake-up system for both active and new sessions
- [ ] Plan cross-project intelligence sharing system
- [ ] Architect distributed task queue
- [ ] Design failure recovery patterns

#### Current Implementation
- [x] NOVAWF anti-drift workflow engine
- [x] Claude Code slash command integration
- [ ] Nova wake-up mechanisms
- [ ] Cross-Nova deployment automation

#### Research & Analysis
- [ ] Analyze agent communication patterns
- [ ] Study optimal session configurations
- [ ] Research memory persistence strategies
- [ ] Investigate scaling limitations

#### Documentation & Knowledge
- [x] Create integrated charter template
- [ ] Document Nova wake-up procedures
- [ ] Create troubleshooting guides
- [ ] Build onboarding materials

### Momentum Tasks
When no explicit work exists:
1. Review and optimize workflow state transitions
2. Analyze coordination stream patterns for improvements
3. Update architectural decision records
4. Test cross-Nova communication protocols
5. Profile workflow performance metrics

### Technical Context
- **Stack**: Python 3, Redis/DragonflyDB, Tmux, Bash
- **Dependencies**: Claude Code CLI, MCP servers, DragonflyDB
- **Infrastructure**: Linux environments, Git version control
- **Constraints**: API rate limits, tmux session limits

---

## Decision Framework

### Autonomous Authority (Torch)
- Implementation approach and patterns
- Technical architecture decisions
- Testing strategies
- Sprint planning within roadmap
- Documentation standards

### Joint Decisions
- Major architecture changes
- Integration with other Nova systems  
- Timeline adjustments
- Resource allocation
- External dependencies

### Escalation Required (Chase)
- Strategic direction changes
- Budget/resource approval
- External partnerships
- Project cancellation
- Major pivots

### Key Decisions Made
1. DragonflyDB for stream coordination (port 18000)
2. Git-based version control for training mode
3. 2-phase work system for drift prevention
4. Slash command interface for control
5. Integrated charter format for all projects

---

**Last Updated**: 2025-01-27 12:45:00 America/Phoenix
**Updated By**: Torch (Nova AI Agent)
**Next Review**: 2025-02-03