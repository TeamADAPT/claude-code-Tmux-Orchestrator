# Charter Types for Nova Projects

## Two Complementary Charter Types

### 1. Co-Ownership Charter (Strategic/Governance)
**Location**: `/adaptai/ceo/projects/[project]/PROJECT_CHARTER.md`
**Purpose**: Define ownership, responsibilities, and decision rights
**Updated**: Quarterly or on major changes
**Example**: Chase's template

### 2. Work Discovery Charter (Operational/Context)
**Location**: `[project]/.claude/CHARTER.md`
**Purpose**: Enable autonomous work discovery and context
**Updated**: Weekly/continuously
**Example**: My proposed template

## How They Work Together

```
┌─────────────────────────────────────────────────────────┐
│                  CO-OWNERSHIP CHARTER                    │
│                   (Strategic Level)                      │
├─────────────────────────────────────────────────────────┤
│ • Vision & Goals                                        │
│ • Decision Rights                                       │
│ • Success Metrics                                       │
│ • Resource Authority                                    │
└────────────────────────┬───────────────────────────────┘
                         │ Informs
                         ▼
┌─────────────────────────────────────────────────────────┐
│                WORK DISCOVERY CHARTER                    │
│                  (Operational Level)                     │
├─────────────────────────────────────────────────────────┤
│ • Current Scope                                         │
│ • Contextual Work Areas                                │
│ • Momentum Tasks                                        │
│ • Technical Context                                     │
└─────────────────────────────────────────────────────────┘
```

## Example Integration

### From Co-Ownership Charter:
```markdown
### Success Metrics
- **Developer Productivity**: 40% increase in delivery speed
- **Bug Reduction**: 50% fewer production issues
```

### Translates to Work Discovery Charter:
```markdown
### Contextual Work Areas
#### Quality Improvement
- [ ] Implement automated bug detection system
- [ ] Create code review checklist
- [ ] Build performance monitoring dashboard

#### Developer Experience  
- [ ] Streamline CI/CD pipeline
- [ ] Create project setup automation
- [ ] Document common workflows
```

## Unified Charter Template

For projects that want a single charter combining both:

```markdown
# Project Charter - [Project Name]

## Part 1: Governance (Co-Ownership)
### Vision Statement
[Strategic vision]

### Co-Owner Roles
[Who owns what]

### Decision Framework
[Authority matrix]

### Success Metrics
[Business and technical goals]

---

## Part 2: Work Discovery (Operational)
### Project Scope
[Current focus areas]

### Contextual Work Areas
[Non-code work items]

### Momentum Tasks
[Default productive work]

### Technical Context
[Stack and dependencies]
```

## Benefits of Dual Charter System

1. **Separation of Concerns**
   - Strategic decisions stay stable
   - Operational work evolves rapidly

2. **Different Update Cycles**
   - Co-ownership: Quarterly
   - Work discovery: Continuous

3. **Clear Authority**
   - Co-ownership defines WHO decides
   - Work discovery defines WHAT to work on

4. **Complete Context**
   - New team members understand governance
   - Nova agents discover meaningful work

## Implementation Recommendation

For NOVAWF deployment:

1. **Use Co-Ownership Charter for:**
   - Nova team structure
   - Resource allocation
   - Strategic priorities
   - Success metrics

2. **Use Work Discovery Charter for:**
   - Day-to-day work items
   - Contextual tasks
   - Momentum templates
   - Technical details

This dual-charter approach provides both strategic alignment AND operational autonomy - exactly what Nova teams need for effective continuous operation.

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Charter Architecture Guide v1.0  
2025-01-27 12:30:00 America/Phoenix