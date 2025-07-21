"""
Load Testing Configuration for Nova-Torch
Author: Torch
Department: QA/DevOps
Project: Nova-Torch
Date: 2025-01-21

Configuration profiles for different load testing scenarios
"""

from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import os


@dataclass
class LoadTestProfile:
    """Load test configuration profile"""
    name: str
    description: str
    users: int
    spawn_rate: int
    run_time: str
    host: str
    dragonfly_port: int = 6379
    grpc_port: int = 50051
    additional_args: List[str] = None
    environment_vars: Dict[str, str] = None
    
    def __post_init__(self):
        if self.additional_args is None:
            self.additional_args = []
        if self.environment_vars is None:
            self.environment_vars = {}


class LoadTestProfiles:
    """Predefined load testing profiles"""
    
    SMOKE_TEST = LoadTestProfile(
        name="smoke",
        description="Quick smoke test to verify basic functionality",
        users=5,
        spawn_rate=1,
        run_time="2m",
        host="localhost",
        additional_args=["--headless"]
    )
    
    DEVELOPMENT_TEST = LoadTestProfile(
        name="development",
        description="Development environment testing",
        users=20,
        spawn_rate=2,
        run_time="5m",
        host="localhost",
        additional_args=["--html", "dev_load_test_report.html"]
    )
    
    STAGING_TEST = LoadTestProfile(
        name="staging", 
        description="Staging environment load test",
        users=100,
        spawn_rate=10,
        run_time="15m",
        host="staging.nova-torch.internal",
        additional_args=[
            "--html", "staging_load_test_report.html",
            "--csv", "staging_results"
        ]
    )
    
    PRODUCTION_TEST = LoadTestProfile(
        name="production",
        description="Production load test with realistic traffic",
        users=500,
        spawn_rate=25,
        run_time="30m", 
        host="nova-torch.production.internal",
        additional_args=[
            "--html", "production_load_test_report.html",
            "--csv", "production_results",
            "--logfile", "production_load_test.log"
        ],
        environment_vars={
            "DRAGONFLY_PASSWORD": "production_password_from_env"
        }
    )
    
    STRESS_TEST = LoadTestProfile(
        name="stress",
        description="High-intensity stress test to find breaking points",
        users=1000,
        spawn_rate=50,
        run_time="1h",
        host="stress-test.nova-torch.internal",
        additional_args=[
            "--html", "stress_test_report.html",
            "--csv", "stress_results",
            "--logfile", "stress_test.log",
            "--expect-workers", "4"
        ]
    )
    
    SOAK_TEST = LoadTestProfile(
        name="soak",
        description="Long-running soak test for stability",
        users=200,
        spawn_rate=5,
        run_time="4h",
        host="soak-test.nova-torch.internal", 
        additional_args=[
            "--html", "soak_test_report.html",
            "--csv", "soak_results",
            "--logfile", "soak_test.log"
        ]
    )
    
    SPIKE_TEST = LoadTestProfile(
        name="spike",
        description="Spike test with sudden traffic increases",
        users=2000,
        spawn_rate=200,
        run_time="10m",
        host="spike-test.nova-torch.internal",
        additional_args=[
            "--html", "spike_test_report.html", 
            "--csv", "spike_results",
            "--logfile", "spike_test.log"
        ]
    )
    
    @classmethod
    def get_profile(cls, name: str) -> Optional[LoadTestProfile]:
        """Get a profile by name"""
        profiles = {
            "smoke": cls.SMOKE_TEST,
            "development": cls.DEVELOPMENT_TEST,
            "staging": cls.STAGING_TEST,
            "production": cls.PRODUCTION_TEST,
            "stress": cls.STRESS_TEST,
            "soak": cls.SOAK_TEST,
            "spike": cls.SPIKE_TEST
        }
        return profiles.get(name.lower())
    
    @classmethod
    def list_profiles(cls) -> List[str]:
        """List all available profile names"""
        return [
            "smoke", "development", "staging", 
            "production", "stress", "soak", "spike"
        ]


class LoadTestScenarios:
    """Specific testing scenarios with custom configurations"""
    
    @staticmethod
    def agent_scaling_test() -> Dict[str, Any]:
        """Test agent auto-scaling behavior"""
        return {
            "name": "agent_scaling",
            "description": "Test agent auto-scaling under load",
            "custom_users": [
                {"class": "NovaOrchestratorUser", "weight": 1, "count": 5},
                {"class": "NovaAgentUser", "weight": 20, "count": 100},
                {"class": "NovaSystemStressUser", "weight": 1, "count": 10}
            ],
            "phases": [
                {"duration": "2m", "users": 10, "spawn_rate": 2},
                {"duration": "5m", "users": 50, "spawn_rate": 8},
                {"duration": "3m", "users": 100, "spawn_rate": 15},
                {"duration": "5m", "users": 50, "spawn_rate": 10}
            ]
        }
    
    @staticmethod
    def collaboration_stress_test() -> Dict[str, Any]:
        """Test collaboration system under heavy load"""
        return {
            "name": "collaboration_stress",
            "description": "Heavy collaboration request load",
            "focus_tasks": [
                "request_collaboration",
                "send_collaboration_response", 
                "broadcast_collaboration"
            ],
            "custom_message_distribution": {
                "collaboration_request": 40,
                "collaboration_response": 30,
                "task_assignment": 20,
                "agent_heartbeat": 10
            }
        }
    
    @staticmethod
    def message_throughput_test() -> Dict[str, Any]:
        """Test maximum message throughput"""
        return {
            "name": "message_throughput",
            "description": "Maximum DragonflyDB message throughput test",
            "target_metrics": {
                "messages_per_second": 10000,
                "max_latency_ms": 100,
                "error_rate_threshold": 0.01
            },
            "streams_to_test": [
                "nova.torch.tasks.assignments",
                "nova.torch.tasks.completions",
                "nova.torch.agents.heartbeat",
                "nova.torch.collaboration.requests"
            ]
        }
    
    @staticmethod
    def failover_recovery_test() -> Dict[str, Any]:
        """Test system resilience during failover"""
        return {
            "name": "failover_recovery",
            "description": "Test system behavior during component failures",
            "failure_scenarios": [
                {"component": "orchestrator", "failure_duration": "30s"},
                {"component": "dragonfly_node", "failure_duration": "60s"},
                {"component": "agent_pool", "failure_percentage": 0.5}
            ],
            "recovery_metrics": {
                "max_recovery_time": "120s",
                "message_loss_threshold": 0.001,
                "service_availability": 0.999
            }
        }


class LoadTestMetrics:
    """Metrics and thresholds for load test validation"""
    
    PERFORMANCE_THRESHOLDS = {
        "smoke": {
            "avg_response_time": 100,  # ms
            "95th_percentile": 500,
            "error_rate": 0.01,
            "throughput_rps": 50
        },
        "development": {
            "avg_response_time": 200,
            "95th_percentile": 1000,
            "error_rate": 0.02,
            "throughput_rps": 100
        },
        "staging": {
            "avg_response_time": 150,
            "95th_percentile": 800,
            "error_rate": 0.01,
            "throughput_rps": 500
        },
        "production": {
            "avg_response_time": 100,
            "95th_percentile": 500,
            "error_rate": 0.005,
            "throughput_rps": 2000
        },
        "stress": {
            "avg_response_time": 300,
            "95th_percentile": 2000,
            "error_rate": 0.05,
            "throughput_rps": 5000
        }
    }
    
    RESOURCE_THRESHOLDS = {
        "cpu_usage": 0.8,
        "memory_usage": 0.85,
        "disk_io_wait": 0.1,
        "network_utilization": 0.7
    }
    
    SYSTEM_HEALTH_CHECKS = [
        "dragonfly_connection_status",
        "orchestrator_response_time",
        "agent_registry_health",
        "task_queue_depth",
        "message_processing_rate"
    ]


class LoadTestEnvironment:
    """Environment-specific configurations"""
    
    ENVIRONMENTS = {
        "local": {
            "host": "localhost",
            "dragonfly_port": 6379,
            "grpc_port": 50051,
            "web_ui": "http://localhost:8089",
            "max_users": 100
        },
        "docker": {
            "host": "nova-torch-orchestrator",
            "dragonfly_port": 6379,
            "grpc_port": 50051,
            "web_ui": "http://localhost:8089",
            "max_users": 500
        },
        "k8s-dev": {
            "host": "nova-torch-orchestrator.nova-torch.svc.cluster.local",
            "dragonfly_port": 6379,
            "grpc_port": 50051,
            "web_ui": "http://localhost:8089",
            "max_users": 1000
        },
        "k8s-staging": {
            "host": "api.staging.nova-torch.example.com",
            "dragonfly_port": 6379,
            "grpc_port": 443,
            "web_ui": "http://localhost:8089",
            "max_users": 2000,
            "tls": True
        },
        "k8s-production": {
            "host": "api.nova-torch.example.com", 
            "dragonfly_port": 6379,
            "grpc_port": 443,
            "web_ui": "http://localhost:8089",
            "max_users": 5000,
            "tls": True,
            "auth_required": True
        }
    }
    
    @classmethod
    def get_environment(cls, env_name: str) -> Dict[str, Any]:
        """Get environment configuration"""
        return cls.ENVIRONMENTS.get(env_name, cls.ENVIRONMENTS["local"])
    
    @classmethod
    def get_connection_string(cls, env_name: str) -> str:
        """Get connection string for environment"""
        env = cls.get_environment(env_name)
        protocol = "https" if env.get("tls") else "http"
        return f"{protocol}://{env['host']}:{env['grpc_port']}"


def create_test_command(profile_name: str, env_name: str = "local") -> List[str]:
    """Create Locust command for given profile and environment"""
    profile = LoadTestProfiles.get_profile(profile_name)
    env_config = LoadTestEnvironment.get_environment(env_name)
    
    if not profile:
        raise ValueError(f"Unknown profile: {profile_name}")
    
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--host", env_config["host"],
        "--users", str(profile.users),
        "--spawn-rate", str(profile.spawn_rate),
        "--run-time", profile.run_time
    ]
    
    # Add profile-specific arguments
    cmd.extend(profile.additional_args)
    
    # Add environment variables
    env_vars = {}
    env_vars.update(profile.environment_vars)
    env_vars.update({
        "DRAGONFLY_PORT": str(env_config["dragonfly_port"]),
        "GRPC_PORT": str(env_config["grpc_port"])
    })
    
    return cmd, env_vars


if __name__ == "__main__":
    # Example usage
    print("Available Load Test Profiles:")
    for profile_name in LoadTestProfiles.list_profiles():
        profile = LoadTestProfiles.get_profile(profile_name)
        print(f"  {profile.name}: {profile.description}")
    
    print("\nExample Commands:")
    cmd, env_vars = create_test_command("development", "local")
    print(f"Development test: {' '.join(cmd)}")
    
    cmd, env_vars = create_test_command("production", "k8s-production")
    print(f"Production test: {' '.join(cmd)}")