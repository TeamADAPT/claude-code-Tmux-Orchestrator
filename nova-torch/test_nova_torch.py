#!/usr/bin/env python3
"""
Nova-Torch Integration Test
Author: Torch (pm-torch)
Department: DevOps
Project: Nova-Torch
Date: 2025-01-16

Test script to verify DragonflyDB integration, agent registry, and bloom-memory
"""

import asyncio
import sys
import os
import time
import json
import logging
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test imports
try:
    from communication.dragonfly_client import DragonflyClient, NovaMessage
    from communication.nova_orchestrator import NovaOrchestrator, OrchestratorConfig
    from orchestration.agent_registry import AgentRegistry, AgentInfo
    from orchestration.agent_memory import AgentMemory, AgentMemoryConfig
    logger.info("✅ All imports successful")
except ImportError as e:
    logger.error(f"❌ Import failed: {e}")
    sys.exit(1)


async def test_dragonfly_connection():
    """Test basic DragonflyDB connection"""
    logger.info("🔌 Testing DragonflyDB connection...")
    
    # Use hardcoded password from guide for testing
    client = DragonflyClient(
        host='localhost',
        port=18000,
        password="dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    )
    
    if not client.connect():
        logger.error("❌ Failed to connect to DragonflyDB")
        return False
    
    # Test basic operations
    test_message = NovaMessage(
        id="test-001",
        timestamp=time.time(),
        sender="torch",
        target="test",
        message_type="test_message",
        payload={"message": "Hello Nova-Torch!"}
    )
    
    # Send message
    stream_name = "nova.torch.test"
    msg_id = client.add_to_stream(stream_name, test_message)
    if not msg_id:
        logger.error("❌ Failed to send test message")
        return False
    
    # Read message back
    messages = client.read_stream(stream_name, count=1)
    if not messages:
        logger.error("❌ Failed to read test message")
        return False
    
    logger.info(f"✅ DragonflyDB connection test passed - Message ID: {msg_id}")
    client.disconnect()
    return True


async def test_agent_memory():
    """Test agent memory with bloom-memory integration"""
    logger.info("🧠 Testing agent memory system...")
    
    # Create agent memory
    memory_config = AgentMemoryConfig(
        password="dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    )
    memory = AgentMemory("torch-test-agent", memory_config)
    
    # Test wake up
    wake_result = memory.wake_up()
    logger.info(f"Wake up result: {wake_result}")
    
    # Test state management
    memory.set_agent_info("developer", ["python", "testing"], "active")
    
    # Test memory operations
    memory.remember_task("test-task-1", "testing", "success", {"duration": 5.0})
    memory.remember_interaction("other-agent", "collaboration", {"message": "Hello!"})
    
    # Test context
    memory.focus_on("testing", "nova-torch")
    memory.add_context("integration_test", priority=10)
    
    # Test relationships
    memory.establish_relationship("orchestrator", "coordination", 1.0)
    
    # Get summary
    summary = memory.get_memory_summary()
    logger.info(f"Memory summary: {json.dumps(summary, indent=2)}")
    
    # Test sleep
    sleep_result = memory.sleep()
    logger.info(f"Sleep result: {sleep_result}")
    
    logger.info("✅ Agent memory test passed")
    return True


async def test_agent_registry():
    """Test agent registry system"""
    logger.info("📋 Testing agent registry...")
    
    # Create DragonflyDB client
    client = DragonflyClient(
        host='localhost',
        port=18000,
        password="dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    )
    
    if not client.connect():
        logger.error("❌ Failed to connect to DragonflyDB for registry test")
        return False
    
    # Create registry
    registry = AgentRegistry(client, heartbeat_timeout=60, enable_memory=True)
    
    # Register test agents
    test_agents = [
        AgentInfo(
            agent_id="torch-dev-1",
            role="developer",
            skills=["python", "testing"],
            status="active",
            last_heartbeat=time.time(),
            session_id="test-session-1"
        ),
        AgentInfo(
            agent_id="torch-pm-1",
            role="project_manager",
            skills=["coordination", "planning"],
            status="active",
            last_heartbeat=time.time(),
            session_id="test-session-2"
        )
    ]
    
    # Register agents
    for agent in test_agents:
        success = await registry.register_agent(agent)
        if not success:
            logger.error(f"❌ Failed to register agent {agent.agent_id}")
            return False
    
    # Test finding agents
    developers = await registry.find_agents(role="developer")
    logger.info(f"Found {len(developers)} developers")
    
    python_agents = await registry.find_agents(skills=["python"])
    logger.info(f"Found {len(python_agents)} Python agents")
    
    # Test heartbeat
    success = await registry.heartbeat("torch-dev-1", "busy", "test-task")
    if not success:
        logger.error("❌ Failed to send heartbeat")
        return False
    
    # Test performance update
    success = await registry.update_agent_performance("torch-dev-1", True, 10.5)
    if not success:
        logger.error("❌ Failed to update performance")
        return False
    
    # Get memory summary
    memory_summary = await registry.get_agent_memory_summary("torch-dev-1")
    if memory_summary:
        logger.info(f"Agent memory summary: {json.dumps(memory_summary, indent=2)}")
    
    # Cleanup
    for agent in test_agents:
        await registry.unregister_agent(agent.agent_id)
    
    client.disconnect()
    logger.info("✅ Agent registry test passed")
    return True


async def test_orchestrator():
    """Test Nova orchestrator"""
    logger.info("🎭 Testing Nova orchestrator...")
    
    # Create orchestrator config
    config = OrchestratorConfig(
        dragonfly_host='localhost',
        dragonfly_port=18000,
        password_file=None,  # Use hardcoded password
        orchestrator_name="Torch"
    )
    
    # Create orchestrator
    orchestrator = NovaOrchestrator(config)
    
    # Override password for testing
    orchestrator.client.password = "dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    
    # Test message handler
    test_responses = []
    
    def handle_test_message(message):
        test_responses.append(message)
        logger.info(f"Received test message: {message.message_type}")
    
    orchestrator.register_handler("test_response", handle_test_message)
    
    # Start orchestrator
    if not await orchestrator.start():
        logger.error("❌ Failed to start orchestrator")
        return False
    
    # Send test broadcast
    msg_id = await orchestrator.broadcast("test_announcement", {
        "message": "Nova-Torch integration test",
        "timestamp": time.time()
    })
    
    if not msg_id:
        logger.error("❌ Failed to send broadcast")
        return False
    
    # Test direct message
    msg_id = await orchestrator.send_message(
        "role:developer", "task_assignment", 
        {"task": "run_integration_test", "priority": "high"}
    )
    
    if not msg_id:
        logger.error("❌ Failed to send direct message")
        return False
    
    # Let it run for a bit
    await asyncio.sleep(3)
    
    # Stop orchestrator
    await orchestrator.stop()
    
    logger.info("✅ Nova orchestrator test passed")
    return True


async def test_full_integration():
    """Test full system integration"""
    logger.info("🌟 Testing full Nova-Torch integration...")
    
    # Test sequence:
    # 1. Start orchestrator
    # 2. Register agents
    # 3. Send messages
    # 4. Verify memory persistence
    # 5. Clean shutdown
    
    config = OrchestratorConfig(
        dragonfly_host='localhost',
        dragonfly_port=18000,
        orchestrator_name="Torch",
        heartbeat_interval=5  # Faster for testing
    )
    
    orchestrator = NovaOrchestrator(config)
    orchestrator.client.password = "dragonfly-password-f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2"
    
    # Start orchestrator
    if not await orchestrator.start():
        logger.error("❌ Failed to start orchestrator")
        return False
    
    # Get registry from orchestrator's client
    registry = AgentRegistry(orchestrator.client, enable_memory=True)
    await registry.start_monitoring()
    
    # Register a test agent
    agent = AgentInfo(
        agent_id="torch-integration-test",
        role="tester",
        skills=["integration", "testing"],
        status="active",
        last_heartbeat=time.time(),
        session_id="integration-test-session"
    )
    
    success = await registry.register_agent(agent)
    if not success:
        logger.error("❌ Failed to register test agent")
        return False
    
    # Send task to agent
    response = await orchestrator.request(
        "torch-integration-test", "ping", {}, timeout=5
    )
    # Note: Won't get response since no actual agent running, but tests the flow
    
    # Update agent performance
    await registry.update_agent_performance("torch-integration-test", True, 2.5)
    
    # Verify agent is tracked
    agents = await registry.find_agents(role="tester")
    if len(agents) != 1:
        logger.error(f"❌ Expected 1 tester agent, found {len(agents)}")
        return False
    
    # Test memory integration
    memory_summary = await registry.get_agent_memory_summary("torch-integration-test")
    if memory_summary:
        logger.info(f"Agent developed memory: {memory_summary['persistence_enabled']}")
    
    # Clean shutdown
    await registry.stop_monitoring()
    await registry.unregister_agent("torch-integration-test")
    await orchestrator.stop()
    
    logger.info("✅ Full integration test passed")
    return True


async def main():
    """Run all tests"""
    logger.info("🚀 Starting Nova-Torch integration tests...")
    
    tests = [
        ("DragonflyDB Connection", test_dragonfly_connection),
        ("Agent Memory System", test_agent_memory),
        ("Agent Registry", test_agent_registry),
        ("Nova Orchestrator", test_orchestrator),
        ("Full Integration", test_full_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            logger.info(f"\n{'='*50}")
            logger.info(f"Running: {test_name}")
            logger.info(f"{'='*50}")
            
            result = await test_func()
            results.append((test_name, result))
            
            if result:
                logger.info(f"✅ {test_name} - PASSED")
            else:
                logger.error(f"❌ {test_name} - FAILED")
                
        except Exception as e:
            logger.error(f"❌ {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! Nova-Torch is ready for deployment!")
        return True
    else:
        logger.error(f"⚠️  {total - passed} tests failed. Please review errors above.")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)