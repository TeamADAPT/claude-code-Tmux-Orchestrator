# Contextual Work Discovery Guide

## The Purpose of CHARTER.md

The `.claude/CHARTER.md` file serves as the **contextual compass** for Nova agents, defining what constitutes valuable work beyond code tasks.

## How CHARTER.md Enables Work Discovery

### 1. **Explicit Context Areas**
Instead of only finding code issues, Novas can discover:
```
Planning & Architecture
├── System design needs
├── Technical debt items
├── Future roadmap work
└── Architecture documentation

Management & Coordination
├── Process improvements
├── Team coordination
├── Resource planning
└── Stakeholder communication

Research & Analysis
├── Performance investigations
├── Technology evaluations
├── Competitive analysis
└── User behavior studies
```

### 2. **Work Discovery Algorithm Enhancement**

```python
class EnhancedWorkDiscovery:
    def discover_contextual_work(self):
        # 1. Load project charter
        charter = self.load_charter()
        
        # 2. Check code-based work (traditional)
        code_work = self.find_code_issues()
        if code_work:
            return code_work
        
        # 3. Check charter-based work (new!)
        for area in charter.contextual_work_areas:
            unchecked_items = area.get_unchecked_items()
            if unchecked_items:
                return self.create_task_from_charter_item(unchecked_items[0])
        
        # 4. Generate momentum from charter templates
        return self.generate_from_charter_momentum()
```

### 3. **Charter-Driven Momentum Tasks**

Instead of generic momentum tasks, the charter provides project-specific templates:

```markdown
## Momentum Task Templates
1. Review API documentation for completeness
2. Analyze last week's error logs for patterns  
3. Profile database queries for optimization
4. Update architecture diagrams with recent changes
5. Research new framework features for adoption
```

## Implementation in NOVAWF

### Workflow State Manager Update
```python
def _handle_work_discovery(self) -> WorkflowState:
    """Enhanced work discovery using charter"""
    
    # Traditional discovery
    work_item = self._discover_stream_work()
    if work_item:
        return self._process_work_item(work_item)
    
    # Charter-based discovery
    charter_work = self._discover_charter_work()
    if charter_work:
        return self._process_charter_item(charter_work)
    
    # Charter-aware momentum
    momentum_task = self._generate_charter_momentum()
    return self._process_momentum_task(momentum_task)
```

### Charter Work Types

#### **Investigative Work**
```python
{
    "type": "research",
    "title": "Analyze scaling bottlenecks",
    "context": "From charter: Research & Analysis",
    "deliverable": "Report with recommendations",
    "estimated_time": "2 hours"
}
```

#### **Planning Work**
```python
{
    "type": "architecture",
    "title": "Design message queue integration",
    "context": "From charter: Planning & Architecture", 
    "deliverable": "Architecture decision record",
    "estimated_time": "3 hours"
}
```

#### **Coordination Work**
```python
{
    "type": "management",
    "title": "Create sprint planning template",
    "context": "From charter: Management & Coordination",
    "deliverable": "Template document",
    "estimated_time": "1 hour"
}
```

## Benefits of Charter-Driven Work

### 1. **Continuity Across Sessions**
- New Nova can read charter and understand project state
- Work context preserved beyond code
- Institutional knowledge captured

### 2. **Higher-Level Productivity**
- Not just fixing bugs, but improving systems
- Not just writing code, but planning architecture
- Not just implementing, but researching and analyzing

### 3. **Team Coordination**
```markdown
Nova Echo reads charter → Sees "Design new navigation UX"
Nova Torch reads charter → Sees "Plan API for navigation"
Result: Coordinated effort on related work
```

### 4. **Measurable Progress**
Charter items can be:
- ✅ Checked off when complete
- 📊 Tracked for velocity metrics
- 🔄 Updated with findings
- 🤝 Shared across team

## Charter Integration Examples

### Example 1: Web Application Project
```markdown
### User Experience
- [ ] Conduct accessibility audit of checkout flow
- [ ] Research and implement lazy loading strategy
- [ ] Create mobile-first design guidelines
- [x] ~~Optimize image loading performance~~ (Completed 2025-01-27)
```

### Example 2: Data Pipeline Project
```markdown
### Data Quality
- [ ] Design validation framework for incoming data
- [ ] Research anomaly detection approaches
- [ ] Plan data lineage tracking system
- [ ] Document data retention policies
```

### Example 3: Infrastructure Project
```markdown
### Reliability Engineering
- [ ] Plan disaster recovery procedures
- [ ] Research chaos engineering tools
- [ ] Design SLO monitoring dashboard
- [ ] Create runbook templates
```

## Best Practices

### 1. **Keep Charter Items Actionable**
❌ "Improve system performance"
✅ "Profile API endpoints and identify top 3 bottlenecks"

### 2. **Include Success Criteria**
❌ "Research caching solutions"
✅ "Research caching solutions and deliver comparison matrix of Redis vs Memcached for our use case"

### 3. **Regular Charter Maintenance**
- Weekly: Check off completed items
- Biweekly: Add new discovered needs
- Monthly: Refactor and reorganize

### 4. **Cross-Nova Visibility**
Charter should be readable by any Nova who might:
- Take over the project
- Collaborate on features
- Need context for decisions

## Future Evolution

As memory systems mature, charters will:
- Auto-populate from completed work patterns
- Suggest new contextual work based on project trends
- Connect related items across projects
- Generate velocity insights

But the charter file remains valuable as:
- Human-readable project state
- Explicit work prioritization
- Shared team understanding
- Audit trail of decisions

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Contextual Work Discovery Guide v1.0  
2025-01-27 12:15:00 America/Phoenix