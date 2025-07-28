# WORK_DISCOVERY: How Novas Find Their Direction

## The Core Question: "What Should I Work On?"

Every Nova faces this question continuously. WORK_DISCOVERY is the systematic answer.

## Work Discovery Hierarchy

```
WORK_DISCOVERY State
    │
    ├── 1. Check Assigned Tasks (Explicit Direction)
    │     ├── DragonflyDB streams
    │     ├── Jira/Atlassian assignments  
    │     ├── Direct user commands
    │     └── Cross-Nova coordination requests
    │
    ├── 2. Check Project Context (Implicit Direction)
    │     ├── Open PRs needing work
    │     ├── Failing tests to fix
    │     ├── TODO comments in code
    │     └── Documentation gaps
    │
    └── 3. Generate Momentum Tasks (Self-Direction)
          ├── Code optimization opportunities
          ├── Test coverage improvements
          ├── Documentation updates
          └── Performance analysis
```

## How Different Novas Know Their Purpose

### 1. **New Novas - Initial Identity**
```python
# When a Nova is created, it receives:
nova_config = {
    "id": "echo",
    "specialization": "frontend_development",
    "primary_skills": ["React", "TypeScript", "UI/UX"],
    "project_context": "/projects/webapp",
    "coordination_streams": ["nova.coordination.echo"],
    "mission": "Maintain and enhance the web application frontend"
}
```

### 2. **Work Discovery Sources**

#### **Stream-Based Tasks** (Primary)
```python
# Novas monitor their coordination streams
stream_messages = redis.xread({
    "nova.coordination.torch": "$",
    "nova.tasks.torch": "$",
    "nova.ecosystem.coordination": "$"
})

# Message types that create work:
- TASK_ASSIGNMENT: Direct task from user/PM
- COLLABORATION_REQUEST: Help needed from another Nova
- SYSTEM_ALERT: Automated issue detection
- SCHEDULED_MAINTENANCE: Recurring tasks
```

#### **Context-Based Discovery** (Secondary)
```python
# Novas scan their environment
def discover_contextual_work():
    work_items = []
    
    # Check git status
    if uncommitted_changes():
        work_items.append("Review and commit pending changes")
    
    # Check test status
    if failing_tests():
        work_items.append("Fix failing test suite")
    
    # Check code quality
    if linting_errors():
        work_items.append("Address code quality issues")
    
    # Check dependencies
    if outdated_dependencies():
        work_items.append("Update project dependencies")
    
    return work_items
```

#### **Momentum Tasks** (Tertiary)
```python
# When no explicit work exists, maintain momentum
MOMENTUM_TEMPLATES = {
    "torch": [
        "Analyze workflow performance metrics",
        "Optimize state machine transitions",
        "Document recent architectural decisions",
        "Review cross-Nova coordination patterns"
    ],
    "echo": [
        "Audit component accessibility",
        "Profile React render performance",
        "Update Storybook documentation",
        "Review and refactor old components"
    ],
    "forge": [
        "Analyze database query performance",
        "Review infrastructure scaling options",
        "Document deployment procedures",
        "Optimize caching strategies"
    ]
}
```

## Real Example: Torch's Work Discovery

```python
class TorchWorkDiscovery:
    def discover_next_work(self):
        # 1. Check my streams first
        tasks = self.stream_controller.get_pending_tasks()
        if tasks:
            return tasks[0]  # Highest priority
        
        # 2. Check project needs
        if self.check_workflow_health():
            issues = self.diagnose_workflow_issues()
            if issues:
                return self.create_fix_task(issues[0])
        
        # 3. Check ecosystem coordination
        help_requests = self.check_nova_help_requests()
        if help_requests:
            return help_requests[0]
        
        # 4. Generate momentum work
        return self.generate_momentum_task()
```

## How Novas Learn Their Specialization

### Initial Configuration
```yaml
# .claude/nova_config.yaml
nova:
  id: bloom
  type: memory_specialist
  
  capabilities:
    - long_term_memory_management
    - pattern_recognition
    - cross_session_learning
    
  work_sources:
    - stream: "nova.memory.requests"
    - path: "/projects/memory-system"
    - integration: "memory_api"
    
  momentum_focus:
    - "Optimize memory query performance"
    - "Analyze learning patterns"
    - "Improve memory categorization"
```

### Dynamic Learning
```python
# Novas adapt based on work patterns
class NovaSpecializationLearning:
    def update_specialization(self, completed_task):
        # Track what type of work succeeds
        self.success_patterns[completed_task.category] += 1
        
        # Adjust momentum task generation
        if self.success_patterns['frontend'] > threshold:
            self.momentum_templates.add_frontend_tasks()
        
        # Update work discovery priorities
        self.work_discovery_weights = self.calculate_weights()
```

## The Complete Work Discovery Flow

```
┌─────────────────────────────────────────────────────┐
│                  WORK_DISCOVERY                      │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Stream Check (100ms)                            │
│     └─> Found work? → Execute it                   │
│                                                     │
│  2. Project Scan (500ms)                            │
│     └─> Found issues? → Fix them                   │
│                                                     │
│  3. Collaboration Check (200ms)                     │
│     └─> Help needed? → Assist Nova                 │
│                                                     │
│  4. Momentum Generation (instant)                   │
│     └─> Always have something productive            │
│                                                     │
│  RESULT: Never idle, always valuable work          │
└─────────────────────────────────────────────────────┘
```

## Configuration for New Novas

When deploying NOVAWF to a new Nova:

```bash
# 1. Create Nova identity
python3 create_nova.py --id "apex" --specialization "database_optimization"

# 2. Configure work sources
python3 configure_nova.py apex \
  --streams "nova.db.requests,nova.coordination.apex" \
  --project-path "/projects/database" \
  --momentum-focus "query optimization,index analysis"

# 3. Start with NOVAWF
/aa:auto  # Nova begins discovering and executing work
```

## The Philosophy in Practice

**"The workflow should be like breathing"** means:
- Work discovery happens automatically
- Novas don't wait for explicit instructions
- There's always something valuable to do
- The system prevents "analysis paralysis"
- Forward momentum is maintained always

Each Nova breathes differently:
- **Torch**: Breathes workflow optimization
- **Echo**: Breathes frontend excellence  
- **Forge**: Breathes infrastructure reliability
- **Bloom**: Breathes memory and learning

But they all breathe continuously, finding their work through the same WORK_DISCOVERY process.

---
**Nova Continuous Operation Workflow (NOVAWF)**  
Work Discovery Architecture v1.0  
2025-01-27 11:55:00 America/Phoenix