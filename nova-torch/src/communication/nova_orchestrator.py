"""
Nova Orchestrator - Main orchestration logic for Nova-Torch
Author: Torch (pm-torch)
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16
"""

import asyncio
import uuid
import time
import logging
import json
from typing import Dict, List, Optional, Callable, Any
from concurrent.futures import ThreadPoolExecutor
import threading
from dataclasses import dataclass, field

from .dragonfly_client import DragonflyClient, NovaMessage

logger = logging.getLogger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for NovaOrchestrator"""
    dragonfly_host: str = 'localhost'
    dragonfly_port: int = 18000
    password_file: Optional[str] = '/etc/nova-torch/dragonfly-password'
    
    # Stream names following nova.torch.* convention
    orchestrator_stream: str = 'nova.torch.orchestrator'
    agent_prefix: str = 'nova.torch.agents'
    registry_stream: str = 'nova.torch.registry'
    task_stream: str = 'nova.torch.tasks'
    monitoring_stream: str = 'nova.torch.monitoring'
    
    # Timing configurations
    heartbeat_interval: int = 30  # seconds
    agent_timeout: int = 120  # seconds
    message_retry_count: int = 3
    message_retry_delay: int = 1  # seconds
    
    # Operational limits
    max_agents: int = 50
    max_concurrent_tasks: int = 100
    stream_max_length: int = 10000
    
    # Identity
    orchestrator_id: str = field(default_factory=lambda: f"torch-orchestrator-{uuid.uuid4().hex[:8]}")
    orchestrator_name: str = "Torch"


class NovaOrchestrator:
    """
    Main orchestrator for Nova-Torch system
    Manages agent communication, task distribution, and system health
    """
    
    def __init__(self, config: Optional[OrchestratorConfig] = None):
        """Initialize the Nova Orchestrator"""
        self.config = config or OrchestratorConfig()
        self.client = DragonflyClient(
            host=self.config.dragonfly_host,
            port=self.config.dragonfly_port,
            password_file=self.config.password_file
        )
        
        # Message handlers
        self._handlers: Dict[str, List[Callable]] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="nova-torch")
        
        # Correlation tracking
        self._pending_responses: Dict[str, asyncio.Future] = {}
        self._correlation_timeout = 60  # seconds
        
        # Consumer groups for coordinated reading
        self._consumer_group = f"nova-torch-{self.config.orchestrator_id}"
        
    async def start(self) -> bool:
        """Start the orchestrator"""
        logger.info(f"Starting Nova Orchestrator: {self.config.orchestrator_name} ({self.config.orchestrator_id})")
        
        # Connect to DragonflyDB
        if not self.client.connect():
            logger.error("Failed to connect to DragonflyDB")
            return False
        
        # Create consumer groups
        self._setup_consumer_groups()
        
        # Start background tasks
        self._running = True
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._message_reader()),
            asyncio.create_task(self._monitoring_loop()),
            asyncio.create_task(self._correlation_cleanup())
        ]
        
        # Send startup message
        await self.broadcast("orchestrator_online", {
            "name": self.config.orchestrator_name,
            "version": "0.1.0",
            "capabilities": ["dragonfly", "agent_management", "task_routing"]
        })
        
        logger.info("Nova Orchestrator started successfully")
        return True
    
    async def stop(self):
        """Stop the orchestrator gracefully"""
        logger.info("Stopping Nova Orchestrator...")
        
        # Send shutdown message
        await self.broadcast("orchestrator_offline", {
            "reason": "graceful_shutdown",
            "timestamp": time.time()
        })
        
        # Stop background tasks
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Cleanup
        self._executor.shutdown(wait=True)
        self.client.disconnect()
        
        logger.info("Nova Orchestrator stopped")
    
    def _setup_consumer_groups(self):
        """Create consumer groups for all relevant streams"""
        streams = [
            self.config.orchestrator_stream,
            self.config.registry_stream,
            self.config.task_stream,
            self.config.monitoring_stream
        ]
        
        for stream in streams:
            self.client.create_consumer_group(stream, self._consumer_group)
    
    async def send_message(self, target: str, message_type: str, 
                          payload: Dict[str, Any], priority: str = "normal",
                          correlation_id: Optional[str] = None) -> Optional[str]:
        """
        Send a message to a specific target
        
        Args:
            target: Target agent or role
            message_type: Type of message
            payload: Message payload
            priority: Message priority (low, normal, high, urgent)
            correlation_id: Optional correlation ID for request/response
            
        Returns:
            Message ID if successful
        """
        message = NovaMessage(
            id=uuid.uuid4().hex,
            timestamp=time.time(),
            sender=self.config.orchestrator_id,
            target=target,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id,
            priority=priority
        )
        
        # Determine target stream
        if target.startswith("role:"):
            # Role-based routing
            role = target.split(":", 1)[1]
            stream = f"{self.config.agent_prefix}.{role}"
        elif target == "broadcast":
            stream = self.config.orchestrator_stream
        else:
            # Direct agent targeting
            stream = f"{self.config.agent_prefix}.direct.{target}"
        
        # Send with retry
        for attempt in range(self.config.message_retry_count):
            msg_id = self.client.add_to_stream(stream, message)
            if msg_id:
                logger.debug(f"Sent message {msg_id} to {target} via {stream}")
                return msg_id
            
            if attempt < self.config.message_retry_count - 1:
                await asyncio.sleep(self.config.message_retry_delay)
        
        logger.error(f"Failed to send message to {target} after {self.config.message_retry_count} attempts")
        return None
    
    async def broadcast(self, message_type: str, payload: Dict[str, Any], 
                       priority: str = "normal") -> Optional[str]:
        """Broadcast a message to all agents"""
        return await self.send_message("broadcast", message_type, payload, priority)
    
    async def request(self, target: str, message_type: str, 
                     payload: Dict[str, Any], timeout: float = 30) -> Optional[Dict[str, Any]]:
        """
        Send a request and wait for response
        
        Args:
            target: Target agent
            message_type: Request type
            payload: Request payload
            timeout: Response timeout in seconds
            
        Returns:
            Response payload if received, None if timeout
        """
        correlation_id = uuid.uuid4().hex
        future = asyncio.Future()
        self._pending_responses[correlation_id] = future
        
        # Send request
        msg_id = await self.send_message(
            target, message_type, payload,
            correlation_id=correlation_id
        )
        
        if not msg_id:
            del self._pending_responses[correlation_id]
            return None
        
        try:
            # Wait for response
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            logger.warning(f"Request to {target} timed out (correlation_id: {correlation_id})")
            return None
        finally:
            self._pending_responses.pop(correlation_id, None)
    
    def register_handler(self, message_type: str, handler: Callable):
        """Register a message handler"""
        if message_type not in self._handlers:
            self._handlers[message_type] = []
        self._handlers[message_type].append(handler)
        logger.debug(f"Registered handler for message type: {message_type}")
    
    async def _message_reader(self):
        """Background task to read and process messages"""
        streams = {
            self.config.orchestrator_stream: '>',
            self.config.registry_stream: '>',
            self.config.task_stream: '>',
            self.config.monitoring_stream: '>'
        }
        
        while self._running:
            try:
                # Read as consumer with 1 second timeout
                messages = self.client.read_as_consumer(
                    streams, self._consumer_group, self.config.orchestrator_id,
                    count=10, block=1000
                )
                
                for stream, msg_id, nova_msg in messages:
                    # Process message
                    asyncio.create_task(self._process_message(stream, msg_id, nova_msg))
                    
                    # Acknowledge message
                    self.client.acknowledge_message(stream, self._consumer_group, msg_id)
                    
            except Exception as e:
                logger.error(f"Error in message reader: {e}")
                await asyncio.sleep(1)
    
    async def _process_message(self, stream: str, msg_id: str, message: NovaMessage):
        """Process a single message"""
        logger.debug(f"Processing message {msg_id} from {stream}: {message.message_type}")
        
        # Check for correlation (response to our request)
        if message.correlation_id and message.correlation_id in self._pending_responses:
            future = self._pending_responses.get(message.correlation_id)
            if future and not future.done():
                future.set_result(message.payload)
            return
        
        # Call registered handlers
        handlers = self._handlers.get(message.message_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    await asyncio.get_event_loop().run_in_executor(
                        self._executor, handler, message
                    )
            except Exception as e:
                logger.error(f"Handler error for {message.message_type}: {e}")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat messages"""
        while self._running:
            try:
                await self.broadcast("heartbeat", {
                    "timestamp": time.time(),
                    "uptime": time.time() - self._startup_time if hasattr(self, '_startup_time') else 0,
                    "active_agents": 0,  # TODO: Get from registry
                    "pending_tasks": len(self._pending_responses)
                }, priority="low")
                
                await asyncio.sleep(self.config.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in heartbeat loop: {e}")
                await asyncio.sleep(5)
    
    async def _monitoring_loop(self):
        """Monitor system health and trim streams"""
        while self._running:
            try:
                # Trim streams to prevent unbounded growth
                streams = [
                    self.config.orchestrator_stream,
                    self.config.registry_stream,
                    self.config.task_stream,
                    self.config.monitoring_stream
                ]
                
                for stream in streams:
                    self.client.trim_stream(stream, self.config.stream_max_length)
                
                # TODO: Collect and publish system metrics
                
                await asyncio.sleep(60)  # Run every minute
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)
    
    async def _correlation_cleanup(self):
        """Clean up old correlation IDs"""
        while self._running:
            try:
                now = time.time()
                expired = []
                
                for corr_id, future in self._pending_responses.items():
                    if future.done():
                        expired.append(corr_id)
                
                for corr_id in expired:
                    self._pending_responses.pop(corr_id, None)
                
                await asyncio.sleep(30)  # Run every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in correlation cleanup: {e}")
                await asyncio.sleep(5)
    
    # Convenience methods for common operations
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific agent"""
        return await self.request(agent_id, "status_request", {}, timeout=5)
    
    async def assign_task(self, agent_id: str, task: Dict[str, Any]) -> bool:
        """Assign a task to a specific agent"""
        response = await self.request(
            agent_id, "task_assignment", task, timeout=10
        )
        return response and response.get("accepted", False)
    
    async def ping_agent(self, agent_id: str) -> bool:
        """Ping an agent to check if it's alive"""
        response = await self.request(
            agent_id, "ping", {}, timeout=3
        )
        return response is not None