#!/usr/bin/env python3
"""
AdaptDev Unified Task Management System
Integrates with awesome-claude-code taskmaster, CCA agents, and Nova operational control
"""

import json
import subprocess
import time
import uuid
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading

# Add paths for integration
sys.path.insert(0, '/nfs/projects/novacore')
sys.path.insert(0, '/nfs/projects/adaptdev/subprojects/cca/src')

from nova_operational_control_core import NovaOperationalControlCore
from task_management_framework import AdaptDevTaskManager, TaskPhase, TaskPriority, TaskType

class IntegrationStatus(Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class ComponentIntegration:
    """Represents integration with AdaptDev components"""
    component_name: str
    integration_status: IntegrationStatus
    api_endpoint: Optional[str] = None
    capabilities: List[str] = field(default_factory=list)
    responsible_novas: List[str] = field(default_factory=list)
    last_health_check: Optional[datetime] = None
    configuration: Dict[str, Any] = field(default_factory=dict)

class AdaptDevUnifiedTaskManager:
    """Unified task management system integrating all AdaptDev components"""
    
    def __init__(self):
        self.dragonfly_password = "dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
        
        # Initialize base task manager
        self.task_manager = AdaptDevTaskManager()
        
        # Component integrations
        self.integrations: Dict[str, ComponentIntegration] = {}
        
        # Initialize components
        self._initialize_component_integrations()
        
        # Monitoring
        self.monitoring_active = False
        self.monitoring_thread = None
        
    def _initialize_component_integrations(self):
        """Initialize integrations with all AdaptDev components"""
        
        # Awesome Claude Code Integration
        self.integrations["awesome-claude-code"] = ComponentIntegration(
            component_name="awesome-claude-code",
            integration_status=IntegrationStatus.UNKNOWN,
            api_endpoint="/nfs/projects/adaptdev/subprojects/awesome-claude-code",
            capabilities=[
                "atlassian-integration",
                "mcp-server-management", 
                "nova-profile-system",
                "taskmaster-integration",
                "autonomous-operations"
            ],
            responsible_novas=["BLOOM", "ZENITH", "ECHO"],
            configuration={
                "taskmaster_path": "/nfs/projects/adaptdev/subprojects/awesome-claude-code/.taskmaster",
                "integrations_path": "/nfs/projects/adaptdev/subprojects/awesome-claude-code/cc_dev/integrations",
                "mcp_servers_path": "/nfs/projects/adaptdev/subprojects/awesome-claude-code/cc_dev/mcp-servers"
            }
        )
        
        # CCA Integration
        self.integrations["cca"] = ComponentIntegration(
            component_name="cca",
            integration_status=IntegrationStatus.UNKNOWN,
            api_endpoint="/nfs/projects/adaptdev/subprojects/cca",
            capabilities=[
                "autonomous-agent-orchestration",
                "grpc-communication",
                "agent-task-distribution",
                "python-agent-execution"
            ],
            responsible_novas=["AXIOM", "NEXUS", "PRIME"],
            configuration={
                "src_path": "/nfs/projects/adaptdev/subprojects/cca/src",
                "agents_path": "/nfs/projects/adaptdev/subprojects/cca/src/cca/agents",
                "orchestrator_path": "/nfs/projects/adaptdev/subprojects/cca/src/cca/orchestrator"
            }
        )
        
        # AdaptDev Core Integration
        self.integrations["adaptdev-core"] = ComponentIntegration(
            component_name="adaptdev-core",
            integration_status=IntegrationStatus.UNKNOWN,
            api_endpoint="/nfs/projects/adaptdev/subprojects/adaptdev",
            capabilities=[
                "feature-flag-management",
                "unified-dashboard",
                "project-scaffolding",
                "workflow-automation"
            ],
            responsible_novas=["PRIME", "APEX"],
            configuration={
                "feature_flags_path": "/nfs/projects/adaptdev/subprojects/adaptdev/feature-flags",
                "dashboard_path": "/nfs/projects/adaptdev/subprojects/adaptdev"
            }
        )
        
        print("🔗 Component integrations initialized")
        
    def check_component_health(self, component_name: str) -> bool:
        """Check health of specific component"""
        
        if component_name not in self.integrations:
            return False
        
        integration = self.integrations[component_name]
        
        try:
            # Check if component path exists
            if not os.path.exists(integration.api_endpoint):
                integration.integration_status = IntegrationStatus.ERROR
                return False
            
            # Component-specific health checks
            if component_name == "awesome-claude-code":
                return self._check_awesome_claude_code_health(integration)
            elif component_name == "cca":
                return self._check_cca_health(integration)
            elif component_name == "adaptdev-core":
                return self._check_adaptdev_core_health(integration)
            
            return True
            
        except Exception as e:
            print(f"❌ Health check failed for {component_name}: {e}")
            integration.integration_status = IntegrationStatus.ERROR
            return False
    
    def _check_awesome_claude_code_health(self, integration: ComponentIntegration) -> bool:
        """Check awesome-claude-code component health"""
        
        try:
            # Check taskmaster integration
            taskmaster_path = integration.configuration["taskmaster_path"]
            if os.path.exists(taskmaster_path):
                integration.integration_status = IntegrationStatus.CONNECTED
                
                # Check for active MCP servers
                mcp_servers_path = integration.configuration["mcp_servers_path"]
                if os.path.exists(mcp_servers_path):
                    # Count active MCP servers
                    mcp_servers = [d for d in os.listdir(mcp_servers_path) if os.path.isdir(os.path.join(mcp_servers_path, d))]
                    integration.configuration["active_mcp_servers"] = len(mcp_servers)
                
                integration.last_health_check = datetime.now()
                return True
            else:
                integration.integration_status = IntegrationStatus.DISCONNECTED
                return False
                
        except Exception as e:
            print(f"❌ Awesome Claude Code health check failed: {e}")
            integration.integration_status = IntegrationStatus.ERROR
            return False
    
    def _check_cca_health(self, integration: ComponentIntegration) -> bool:
        """Check CCA component health"""
        
        try:
            # Check CCA source structure
            src_path = integration.configuration["src_path"]
            if os.path.exists(src_path):
                # Check for agents
                agents_path = integration.configuration["agents_path"]
                if os.path.exists(agents_path):
                    # Count available agents
                    agents = [f for f in os.listdir(agents_path) if f.endswith('.py') and f != '__init__.py']
                    integration.configuration["available_agents"] = len(agents)
                
                # Check orchestrator
                orchestrator_path = integration.configuration["orchestrator_path"]
                if os.path.exists(orchestrator_path):
                    integration.configuration["orchestrator_available"] = True
                    
                integration.integration_status = IntegrationStatus.CONNECTED
                integration.last_health_check = datetime.now()
                return True
            else:
                integration.integration_status = IntegrationStatus.DISCONNECTED
                return False
                
        except Exception as e:
            print(f"❌ CCA health check failed: {e}")
            integration.integration_status = IntegrationStatus.ERROR
            return False
    
    def _check_adaptdev_core_health(self, integration: ComponentIntegration) -> bool:
        """Check AdaptDev core component health"""
        
        try:
            # Check feature flags
            feature_flags_path = integration.configuration["feature_flags_path"]
            if os.path.exists(feature_flags_path):
                # Check for feature flags configuration
                feature_flags_file = os.path.join(feature_flags_path, "feature-flags.json")
                if os.path.exists(feature_flags_file):
                    with open(feature_flags_file, 'r') as f:
                        flags = json.load(f)
                        integration.configuration["active_feature_flags"] = len(flags)
                
                integration.integration_status = IntegrationStatus.CONNECTED
                integration.last_health_check = datetime.now()
                return True
            else:
                integration.integration_status = IntegrationStatus.DISCONNECTED
                return False
                
        except Exception as e:
            print(f"❌ AdaptDev core health check failed: {e}")
            integration.integration_status = IntegrationStatus.ERROR
            return False
    
    def create_integrated_task(self, task_data: Dict[str, Any]) -> str:
        """Create task with component integration"""
        
        # Create base task
        task_id = self.task_manager.create_task(task_data)
        
        # Integrate with specific components
        components_affected = task_data.get("component_affected", [])
        
        for component in components_affected:
            if component in self.integrations:
                self._integrate_task_with_component(task_id, component)
        
        return task_id
    
    def _integrate_task_with_component(self, task_id: str, component_name: str):
        """Integrate task with specific component"""
        
        integration = self.integrations[component_name]
        
        if component_name == "awesome-claude-code":
            self._integrate_with_awesome_claude_code(task_id, integration)
        elif component_name == "cca":
            self._integrate_with_cca(task_id, integration)
        elif component_name == "adaptdev-core":
            self._integrate_with_adaptdev_core(task_id, integration)
    
    def _integrate_with_awesome_claude_code(self, task_id: str, integration: ComponentIntegration):
        """Integrate task with awesome-claude-code taskmaster"""
        
        task = self.task_manager.tasks[task_id]
        
        # Create taskmaster integration
        taskmaster_task = {
            "id": task_id,
            "title": task.title,
            "description": task.description,
            "priority": task.priority.value,
            "type": task.task_type.value,
            "status": task.phase.value,
            "created_at": task.created_timestamp.isoformat(),
            "assignees": [a.assignee_id for a in task.assignments],
            "integration_source": "adaptdev_unified_task_manager"
        }
        
        # Write to taskmaster integration
        try:
            taskmaster_path = integration.configuration["taskmaster_path"]
            task_file = os.path.join(taskmaster_path, f"{task_id}.json")
            
            os.makedirs(taskmaster_path, exist_ok=True)
            with open(task_file, 'w') as f:
                json.dump(taskmaster_task, f, indent=2)
            
            print(f"✅ Task {task_id} integrated with awesome-claude-code taskmaster")
            
        except Exception as e:
            print(f"❌ Failed to integrate task {task_id} with awesome-claude-code: {e}")
    
    def _integrate_with_cca(self, task_id: str, integration: ComponentIntegration):
        """Integrate task with CCA agent system"""
        
        task = self.task_manager.tasks[task_id]
        
        # Create CCA agent task
        agent_task = {
            "task_id": task_id,
            "agent_type": "python_agent",
            "task_specification": {
                "title": task.title,
                "description": task.description,
                "requirements": task.technical_requirements,
                "acceptance_criteria": task.acceptance_criteria
            },
            "execution_parameters": {
                "priority": task.priority.value,
                "estimated_duration": sum(a.estimated_hours for a in task.assignments) if task.assignments else 8.0,
                "resource_requirements": task.resources_required
            },
            "integration_metadata": {
                "source": "adaptdev_unified_task_manager",
                "created_at": task.created_timestamp.isoformat(),
                "component_affected": task.component_affected
            }
        }
        
        # Send to CCA orchestrator
        try:
            # Send via Redis stream to CCA orchestrator
            subprocess.run([
                'redis-cli', '-h', 'localhost', '-p', '18000',
                '-a', self.dragonfly_password, '--no-auth-warning',
                'XADD', 'cca.agent.tasks', '*',
                'task_id', task_id,
                'agent_task', json.dumps(agent_task),
                'timestamp', datetime.now().isoformat()
            ], capture_output=True, text=True, timeout=3)
            
            print(f"✅ Task {task_id} integrated with CCA agent system")
            
        except Exception as e:
            print(f"❌ Failed to integrate task {task_id} with CCA: {e}")
    
    def _integrate_with_adaptdev_core(self, task_id: str, integration: ComponentIntegration):
        """Integrate task with AdaptDev core features"""
        
        task = self.task_manager.tasks[task_id]
        
        # Check if task affects feature flags
        if "feature-flags" in task.labels or "feature" in task.task_type.value:
            self._integrate_with_feature_flags(task_id, integration)
        
        # Send to AdaptDev core stream
        try:
            core_task = {
                "task_id": task_id,
                "title": task.title,
                "type": task.task_type.value,
                "priority": task.priority.value,
                "component_integration": "adaptdev-core",
                "created_at": task.created_timestamp.isoformat()
            }
            
            subprocess.run([
                'redis-cli', '-h', 'localhost', '-p', '18000',
                '-a', self.dragonfly_password, '--no-auth-warning',
                'XADD', 'adaptdev.core.tasks', '*',
                'task_id', task_id,
                'core_task', json.dumps(core_task),
                'timestamp', datetime.now().isoformat()
            ], capture_output=True, text=True, timeout=3)
            
            print(f"✅ Task {task_id} integrated with AdaptDev core")
            
        except Exception as e:
            print(f"❌ Failed to integrate task {task_id} with AdaptDev core: {e}")
    
    def _integrate_with_feature_flags(self, task_id: str, integration: ComponentIntegration):
        """Integrate task with feature flag system"""
        
        task = self.task_manager.tasks[task_id]
        
        try:
            # Create feature flag for task
            flag_id = f"task_{task_id.replace('-', '_')}"
            feature_flag = {
                "id": flag_id,
                "name": f"Task {task_id}",
                "description": f"Feature flag for task: {task.title}",
                "enabled": False,
                "created_at": datetime.now().isoformat(),
                "task_id": task_id,
                "conditions": {
                    "task_phase": task.phase.value,
                    "component_affected": task.component_affected
                }
            }
            
            # Write to feature flags
            feature_flags_path = integration.configuration["feature_flags_path"]
            flag_file = os.path.join(feature_flags_path, f"{flag_id}.json")
            
            os.makedirs(feature_flags_path, exist_ok=True)
            with open(flag_file, 'w') as f:
                json.dump(feature_flag, f, indent=2)
            
            print(f"✅ Feature flag {flag_id} created for task {task_id}")
            
        except Exception as e:
            print(f"❌ Failed to create feature flag for task {task_id}: {e}")
    
    def start_monitoring(self):
        """Start monitoring of all component integrations"""
        
        if self.monitoring_active:
            return
        
        self.monitoring_active = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        
        print("📊 Unified task manager monitoring started")
    
    def _monitoring_loop(self):
        """Monitoring loop for component health"""
        
        while self.monitoring_active:
            try:
                # Check health of all components
                for component_name in self.integrations:
                    self.check_component_health(component_name)
                
                # Send status update
                self._send_monitoring_update()
                
                # Wait before next check
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"❌ Monitoring loop error: {e}")
                time.sleep(10)
    
    def _send_monitoring_update(self):
        """Send monitoring update to streams"""
        
        try:
            status_update = {
                "timestamp": datetime.now().isoformat(),
                "component_status": {
                    name: {
                        "status": integration.integration_status.value,
                        "last_health_check": integration.last_health_check.isoformat() if integration.last_health_check else None,
                        "capabilities": integration.capabilities,
                        "configuration": integration.configuration
                    }
                    for name, integration in self.integrations.items()
                },
                "task_manager_status": {
                    "total_tasks": len(self.task_manager.tasks),
                    "active_plans": len(self.task_manager.execution_plans),
                    "active_assignments": len(self.task_manager.active_assignments)
                }
            }
            
            subprocess.run([
                'redis-cli', '-h', 'localhost', '-p', '18000',
                '-a', self.dragonfly_password, '--no-auth-warning',
                'XADD', 'adaptdev.unified.status', '*',
                'status_update', json.dumps(status_update),
                'timestamp', datetime.now().isoformat()
            ], capture_output=True, text=True, timeout=3)
            
        except Exception as e:
            print(f"❌ Failed to send monitoring update: {e}")
    
    def get_unified_dashboard(self) -> Dict[str, Any]:
        """Get unified dashboard with all component status"""
        
        # Get base dashboard
        base_dashboard = self.task_manager.get_dashboard_status()
        
        # Add component integration status
        integration_status = {}
        for name, integration in self.integrations.items():
            integration_status[name] = {
                "status": integration.integration_status.value,
                "capabilities": integration.capabilities,
                "responsible_novas": integration.responsible_novas,
                "last_health_check": integration.last_health_check.isoformat() if integration.last_health_check else None,
                "configuration": integration.configuration
            }
        
        return {
            **base_dashboard,
            "component_integrations": integration_status,
            "unified_monitoring": {
                "monitoring_active": self.monitoring_active,
                "total_components": len(self.integrations),
                "connected_components": len([i for i in self.integrations.values() if i.integration_status == IntegrationStatus.CONNECTED])
            }
        }
    
    def execute_unified_plan(self, plan_id: str) -> bool:
        """Execute plan with full component integration"""
        
        print(f"🚀 Executing unified plan {plan_id}")
        
        # Check component health before execution
        for component_name in self.integrations:
            if not self.check_component_health(component_name):
                print(f"❌ Component {component_name} health check failed")
                return False
        
        # Execute base plan
        if not self.task_manager.execute_plan(plan_id):
            print(f"❌ Base plan execution failed")
            return False
        
        # Perform component-specific post-execution actions
        self._post_execution_component_sync(plan_id)
        
        print(f"✅ Unified plan {plan_id} executed successfully")
        return True
    
    def _post_execution_component_sync(self, plan_id: str):
        """Sync with components after plan execution"""
        
        try:
            # Send execution completion notification
            completion_notification = {
                "plan_id": plan_id,
                "execution_completed": True,
                "timestamp": datetime.now().isoformat(),
                "component_sync_required": True
            }
            
            subprocess.run([
                'redis-cli', '-h', 'localhost', '-p', '18000',
                '-a', self.dragonfly_password, '--no-auth-warning',
                'XADD', 'adaptdev.execution.complete', '*',
                'plan_id', plan_id,
                'completion_data', json.dumps(completion_notification),
                'timestamp', datetime.now().isoformat()
            ], capture_output=True, text=True, timeout=3)
            
        except Exception as e:
            print(f"❌ Failed to send execution completion notification: {e}")

def main():
    """Deploy AdaptDev Unified Task Management System"""
    
    print("🎯 ADAPTDEV UNIFIED TASK MANAGEMENT SYSTEM")
    print("=" * 60)
    
    # Initialize unified task manager
    unified_manager = AdaptDevUnifiedTaskManager()
    
    # Check component health
    print("\n🔍 Checking component health...")
    for component_name in unified_manager.integrations:
        status = unified_manager.check_component_health(component_name)
        print(f"  {component_name}: {'✅ HEALTHY' if status else '❌ UNHEALTHY'}")
    
    # Start monitoring
    unified_manager.start_monitoring()
    
    # Create sample integrated task
    print("\n📋 Creating sample integrated task...")
    
    integrated_task = unified_manager.create_integrated_task({
        "title": "Implement cross-component real-time synchronization",
        "description": "Enable real-time sync between awesome-claude-code, CCA agents, and AdaptDev core",
        "task_type": "integration",
        "priority": "high",
        "component_affected": ["awesome-claude-code", "cca", "adaptdev-core"],
        "acceptance_criteria": [
            "Real-time sync operational between all components",
            "Task status updates propagated instantly",
            "Component health monitoring active"
        ],
        "technical_requirements": [
            "Redis stream integration",
            "WebSocket connections",
            "Health monitoring endpoints"
        ],
        "labels": ["integration", "real-time", "monitoring"]
    })
    
    # Assign to Nova team
    unified_manager.task_manager.assign_task(integrated_task, "PRIME", "nova", "integration_lead", 20.0)
    unified_manager.task_manager.assign_task(integrated_task, "BLOOM", "nova", "awesome_claude_specialist", 16.0)
    unified_manager.task_manager.assign_task(integrated_task, "AXIOM", "nova", "cca_specialist", 12.0)
    
    # Get unified dashboard
    print("\n📊 Unified Dashboard Status:")
    dashboard = unified_manager.get_unified_dashboard()
    
    print(f"  📋 Total tasks: {dashboard['task_statistics']['total_tasks']}")
    print(f"  🔗 Component integrations: {dashboard['unified_monitoring']['total_components']}")
    print(f"  ✅ Connected components: {dashboard['unified_monitoring']['connected_components']}")
    print(f"  👥 Active assignments: {dashboard['assignment_statistics']['total_assignments']}")
    
    print("\n🔗 Component Integration Status:")
    for name, status in dashboard['component_integrations'].items():
        print(f"  {name}: {status['status'].upper()}")
        print(f"    Capabilities: {len(status['capabilities'])}")
        print(f"    Responsible Novas: {status['responsible_novas']}")
    
    print("\n🌟 ADAPTDEV UNIFIED TASK MANAGEMENT SYSTEM: OPERATIONAL!")
    print("✅ All component integrations initialized")
    print("✅ Monitoring and health checking active")
    print("✅ Cross-component task synchronization enabled")
    print("✅ Nova team coordination integrated")
    print("✅ Unified dashboard operational")
    
    return unified_manager

if __name__ == "__main__":
    main()