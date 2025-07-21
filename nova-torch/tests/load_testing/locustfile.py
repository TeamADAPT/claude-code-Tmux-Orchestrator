"""
Load Testing Suite for Nova-Torch
Author: Torch
Department: QA/DevOps
Project: Nova-Torch
Date: 2025-01-21

Comprehensive load testing using Locust for Nova-Torch orchestration system
"""

import asyncio
import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from locust import User, task, between, events
from locust.clients import ResponseContextManager
from locust.exception import LocustError

import grpc
import grpc.aio
from google.protobuf import empty_pb2

# Mock imports for testing - in real implementation these would be actual modules
from communication.dragonfly_client import DragonflyClient, NovaMessage
from communication.proto import nova_torch_pb2, nova_torch_pb2_grpc
from orchestration.nova_orchestrator import NovaOrchestrator
from registry.agent_registry import AgentRegistry, AgentInfo


class NovaMessageGenerator:
    """Generates realistic Nova messages for load testing"""
    
    MESSAGE_TYPES = [
        "task_assignment", "task_completion", "task_status", 
        "agent_heartbeat", "agent_request", "agent_response",
        "collaboration_request", "collaboration_response",
        "broadcast", "system_status"
    ]
    
    AGENT_TYPES = ["developer", "project_manager", "qa", "devops", "analyst"]
    
    TASK_TYPES = [
        "code_generation", "bug_fix", "testing", "deployment",
        "code_review", "documentation", "analysis", "optimization"
    ]
    
    @classmethod
    def generate_message(cls, message_type: Optional[str] = None) -> NovaMessage:
        """Generate a realistic Nova message"""
        if not message_type:
            message_type = random.choice(cls.MESSAGE_TYPES)
            
        sender_id = f"agent_{random.randint(1000, 9999)}"
        
        # Generate realistic payloads based on message type
        payload = cls._generate_payload(message_type)
        
        return NovaMessage(
            message_id=f"msg_{int(time.time() * 1000)}_{random.randint(100, 999)}",
            message_type=message_type,
            sender_id=sender_id,
            recipient_id="orchestrator" if message_type != "broadcast" else None,
            payload=payload,
            timestamp=time.time(),
            ttl=300,  # 5 minutes
            priority=random.randint(1, 10)
        )
    
    @classmethod
    def _generate_payload(cls, message_type: str) -> Dict[str, Any]:
        """Generate message-specific payload"""
        base_payload = {
            "version": "0.2.0",
            "source": "load_test",
            "test_id": f"load_test_{int(time.time())}"
        }
        
        if message_type == "task_assignment":
            return {
                **base_payload,
                "task_id": f"task_{random.randint(10000, 99999)}",
                "task_type": random.choice(cls.TASK_TYPES),
                "priority": random.randint(1, 10),
                "estimated_duration": random.randint(60, 3600),
                "requirements": {
                    "skills": random.sample(["python", "javascript", "react", "docker", "kubernetes"], 
                                          random.randint(1, 3)),
                    "resources": {
                        "cpu": random.uniform(0.5, 2.0),
                        "memory": random.randint(512, 4096)
                    }
                },
                "description": "Load test task assignment"
            }
        
        elif message_type == "task_completion":
            return {
                **base_payload,
                "task_id": f"task_{random.randint(10000, 99999)}",
                "status": "completed",
                "result": {
                    "success": random.choice([True, True, True, False]),  # 75% success rate
                    "output": "Task completed successfully" if random.random() > 0.25 else "Task failed",
                    "duration": random.randint(30, 1800),
                    "resources_used": {
                        "cpu_time": random.uniform(10, 300),
                        "memory_peak": random.randint(256, 2048)
                    }
                }
            }
        
        elif message_type == "agent_heartbeat":
            return {
                **base_payload,
                "agent_type": random.choice(cls.AGENT_TYPES),
                "status": "active",
                "current_load": random.uniform(0.1, 0.9),
                "tasks_in_progress": random.randint(0, 5),
                "capabilities": random.sample(cls.TASK_TYPES, random.randint(2, 4)),
                "health": {
                    "cpu_usage": random.uniform(10, 80),
                    "memory_usage": random.uniform(20, 90),
                    "uptime": random.randint(3600, 86400)
                }
            }
        
        elif message_type == "collaboration_request":
            return {
                **base_payload,
                "collaboration_id": f"collab_{random.randint(1000, 9999)}",
                "project_id": f"proj_{random.randint(100, 999)}",
                "requested_skills": random.sample(cls.TASK_TYPES, random.randint(1, 3)),
                "estimated_duration": random.randint(300, 7200),
                "urgency": random.choice(["low", "medium", "high", "critical"])
            }
        
        return base_payload


class DragonflyLoadTestClient:
    """Custom client for DragonflyDB load testing"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, password: str = None):
        self.host = host
        self.port = port
        self.password = password
        self.client: Optional[DragonflyClient] = None
        self.connected = False
    
    async def connect(self):
        """Connect to DragonflyDB"""
        try:
            self.client = DragonflyClient(
                host=self.host,
                port=self.port,
                password=self.password
            )
            await self.client.connect()
            self.connected = True
        except Exception as e:
            raise LocustError(f"Failed to connect to DragonflyDB: {e}")
    
    async def disconnect(self):
        """Disconnect from DragonflyDB"""
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
    
    async def send_message(self, stream: str, message: NovaMessage) -> ResponseContextManager:
        """Send message to stream"""
        start_time = time.time()
        
        try:
            message_id = await self.client.send_message(stream, message)
            
            response_time = int((time.time() - start_time) * 1000)
            
            # Create mock response for Locust
            response = ResponseContextManager(
                request_type="STREAM_SEND",
                name=f"send_message/{stream}",
                url=f"dragonfly://{self.host}:{self.port}/{stream}",
                response_time=response_time,
                response_length=len(json.dumps(asdict(message))),
                response=None,
                context={},
                exception=None
            )
            
            return response
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            
            response = ResponseContextManager(
                request_type="STREAM_SEND",
                name=f"send_message/{stream}",
                url=f"dragonfly://{self.host}:{self.port}/{stream}",
                response_time=response_time,
                response_length=0,
                response=None,
                context={},
                exception=e
            )
            
            return response


class GrpcLoadTestClient:
    """Custom client for gRPC load testing"""
    
    def __init__(self, host: str = "localhost", port: int = 50051):
        self.host = host
        self.port = port
        self.channel: Optional[grpc.aio.Channel] = None
        self.stub: Optional[nova_torch_pb2_grpc.NovaOrchestratorStub] = None
    
    async def connect(self):
        """Connect to gRPC service"""
        try:
            self.channel = grpc.aio.insecure_channel(f"{self.host}:{self.port}")
            self.stub = nova_torch_pb2_grpc.NovaOrchestratorStub(self.channel)
        except Exception as e:
            raise LocustError(f"Failed to connect to gRPC service: {e}")
    
    async def disconnect(self):
        """Disconnect from gRPC service"""
        if self.channel:
            await self.channel.close()
    
    async def register_agent(self, agent_info: AgentInfo) -> ResponseContextManager:
        """Register agent via gRPC"""
        start_time = time.time()
        
        try:
            request = nova_torch_pb2.RegisterAgentRequest(
                agent_id=agent_info.agent_id,
                agent_type=agent_info.agent_type,
                capabilities=agent_info.capabilities,
                host=agent_info.host,
                port=agent_info.port
            )
            
            response = await self.stub.RegisterAgent(request)
            
            response_time = int((time.time() - start_time) * 1000)
            
            return ResponseContextManager(
                request_type="GRPC",
                name="register_agent",
                url=f"grpc://{self.host}:{self.port}/RegisterAgent",
                response_time=response_time,
                response_length=len(response.SerializeToString()),
                response=response,
                context={},
                exception=None
            )
            
        except Exception as e:
            response_time = int((time.time() - start_time) * 1000)
            
            return ResponseContextManager(
                request_type="GRPC",
                name="register_agent",
                url=f"grpc://{self.host}:{self.port}/RegisterAgent",
                response_time=response_time,
                response_length=0,
                response=None,
                context={},
                exception=e
            )


class NovaOrchestratorUser(User):
    """Locust user simulating orchestrator interactions"""
    
    wait_time = between(1, 5)
    weight = 3
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dragonfly_client = None
        self.grpc_client = None
        self.agent_id = f"load_test_agent_{random.randint(1000, 9999)}"
    
    async def on_start(self):
        """Initialize connections"""
        # Initialize DragonflyDB client
        dragonfly_host = self.environment.host or "localhost"
        dragonfly_port = getattr(self.environment, 'dragonfly_port', 6379)
        
        self.dragonfly_client = DragonflyLoadTestClient(
            host=dragonfly_host, 
            port=dragonfly_port
        )
        await self.dragonfly_client.connect()
        
        # Initialize gRPC client
        grpc_host = self.environment.host or "localhost"
        grpc_port = getattr(self.environment, 'grpc_port', 50051)
        
        self.grpc_client = GrpcLoadTestClient(
            host=grpc_host, 
            port=grpc_port
        )
        await self.grpc_client.connect()
    
    async def on_stop(self):
        """Cleanup connections"""
        if self.dragonfly_client:
            await self.dragonfly_client.disconnect()
        
        if self.grpc_client:
            await self.grpc_client.disconnect()
    
    @task(5)
    def send_task_assignment(self):
        """Send task assignment message"""
        message = NovaMessageGenerator.generate_message("task_assignment")
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.tasks.assignments", message
            )
            
            # Report to Locust
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(8)
    def send_heartbeat(self):
        """Send agent heartbeat"""
        message = NovaMessageGenerator.generate_message("agent_heartbeat")
        message.sender_id = self.agent_id
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.agents.heartbeat", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(3)
    def send_task_completion(self):
        """Send task completion message"""
        message = NovaMessageGenerator.generate_message("task_completion")
        message.sender_id = self.agent_id
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.tasks.completions", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(2)
    def request_collaboration(self):
        """Send collaboration request"""
        message = NovaMessageGenerator.generate_message("collaboration_request")
        message.sender_id = self.agent_id
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.collaboration.requests", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(1)
    def register_agent_grpc(self):
        """Register agent via gRPC"""
        agent_info = AgentInfo(
            agent_id=self.agent_id,
            agent_type=random.choice(NovaMessageGenerator.AGENT_TYPES),
            capabilities=random.sample(NovaMessageGenerator.TASK_TYPES, 3),
            host="load_test_host",
            port=random.randint(8000, 9000),
            status="active"
        )
        
        async def _register():
            response = await self.grpc_client.register_agent(agent_info)
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_register())


class NovaAgentUser(User):
    """Locust user simulating agent behavior"""
    
    wait_time = between(2, 10)
    weight = 10
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dragonfly_client = None
        self.agent_id = f"load_test_agent_{random.randint(1000, 9999)}"
        self.agent_type = random.choice(NovaMessageGenerator.AGENT_TYPES)
        self.tasks_completed = 0
    
    async def on_start(self):
        """Initialize agent"""
        dragonfly_host = self.environment.host or "localhost"
        dragonfly_port = getattr(self.environment, 'dragonfly_port', 6379)
        
        self.dragonfly_client = DragonflyLoadTestClient(
            host=dragonfly_host, 
            port=dragonfly_port
        )
        await self.dragonfly_client.connect()
    
    async def on_stop(self):
        """Cleanup agent"""
        if self.dragonfly_client:
            await self.dragonfly_client.disconnect()
    
    @task(10)
    def send_heartbeat(self):
        """Send periodic heartbeat"""
        message = NovaMessageGenerator.generate_message("agent_heartbeat")
        message.sender_id = self.agent_id
        message.payload.update({
            "agent_type": self.agent_type,
            "tasks_completed": self.tasks_completed
        })
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.agents.heartbeat", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(5)
    def complete_task(self):
        """Simulate task completion"""
        message = NovaMessageGenerator.generate_message("task_completion")
        message.sender_id = self.agent_id
        
        self.tasks_completed += 1
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.tasks.completions", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())
    
    @task(2)
    def request_help(self):
        """Request collaboration help"""
        message = NovaMessageGenerator.generate_message("collaboration_request")
        message.sender_id = self.agent_id
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.collaboration.requests", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())


class NovaSystemStressUser(User):
    """High-intensity user for stress testing"""
    
    wait_time = between(0.1, 1)
    weight = 1
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dragonfly_client = None
        self.message_count = 0
    
    async def on_start(self):
        """Initialize stress client"""
        dragonfly_host = self.environment.host or "localhost"
        dragonfly_port = getattr(self.environment, 'dragonfly_port', 6379)
        
        self.dragonfly_client = DragonflyLoadTestClient(
            host=dragonfly_host, 
            port=dragonfly_port
        )
        await self.dragonfly_client.connect()
    
    async def on_stop(self):
        """Cleanup stress client"""
        if self.dragonfly_client:
            await self.dragonfly_client.disconnect()
    
    @task
    def flood_messages(self):
        """Send rapid message bursts"""
        message_types = ["agent_heartbeat", "task_status", "system_status"]
        message = NovaMessageGenerator.generate_message(random.choice(message_types))
        
        self.message_count += 1
        message.sender_id = f"stress_test_{self.message_count}"
        
        async def _send():
            response = await self.dragonfly_client.send_message(
                "nova.torch.stress.test", message
            )
            
            events.request.fire(
                request_type=response.request_type,
                name=response.name,
                response_time=response.response_time,
                response_length=response.response_length,
                exception=response.exception
            )
        
        asyncio.create_task(_send())


# Load test event handlers for custom metrics
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize load test"""
    print("🚀 Nova-Torch Load Test Starting...")
    print(f"Target Host: {environment.host}")
    print(f"Expected Users: {environment.runner.target_user_count}")


@events.test_stop.add_listener  
def on_test_stop(environment, **kwargs):
    """Cleanup load test"""
    print("🏁 Nova-Torch Load Test Complete!")
    
    if environment.runner.stats.total.num_requests > 0:
        print(f"Total Requests: {environment.runner.stats.total.num_requests}")
        print(f"Failure Rate: {environment.runner.stats.total.fail_ratio:.2%}")
        print(f"Average Response Time: {environment.runner.stats.total.avg_response_time:.2f}ms")


if __name__ == "__main__":
    # Example usage for development testing
    import subprocess
    import sys
    
    print("Starting Nova-Torch Load Test...")
    print("Use Ctrl+C to stop the test")
    
    # Default Locust command
    cmd = [
        sys.executable, "-m", "locust",
        "-f", __file__,
        "--host", "localhost",
        "--users", "50",
        "--spawn-rate", "5",
        "--run-time", "5m",
        "--html", "load_test_report.html"
    ]
    
    subprocess.run(cmd)