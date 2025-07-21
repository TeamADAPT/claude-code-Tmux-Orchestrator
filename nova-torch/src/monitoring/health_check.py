"""
Health Check System for Nova-Torch
Author: Torch
Department: DevOps
Project: Nova-Torch
Date: 2025-01-20

Comprehensive health monitoring for all system components
"""

import time
import logging
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status values"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Individual health check definition"""
    name: str
    check_func: Callable
    timeout: float = 5.0
    interval: float = 30.0
    warning_threshold: float = 2.0
    critical_threshold: float = 5.0
    enabled: bool = True
    last_run: Optional[float] = None
    last_status: HealthStatus = HealthStatus.UNKNOWN
    last_duration: float = 0.0
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "name": self.name,
            "status": self.last_status.value,
            "last_run": self.last_run,
            "last_duration": self.last_duration,
            "last_error": self.last_error,
            "consecutive_failures": self.consecutive_failures,
            "enabled": self.enabled,
            "timeout": self.timeout,
            "interval": self.interval
        }


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    timestamp: float
    checks: Dict[str, HealthCheck] = field(default_factory=dict)
    uptime: float = 0.0
    version: str = "0.2.0"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "uptime": self.uptime,
            "version": self.version,
            "checks": {name: check.to_dict() for name, check in self.checks.items()},
            "summary": {
                "total_checks": len(self.checks),
                "healthy_checks": len([c for c in self.checks.values() if c.last_status == HealthStatus.HEALTHY]),
                "warning_checks": len([c for c in self.checks.values() if c.last_status == HealthStatus.WARNING]),
                "critical_checks": len([c for c in self.checks.values() if c.last_status == HealthStatus.CRITICAL]),
                "unknown_checks": len([c for c in self.checks.values() if c.last_status == HealthStatus.UNKNOWN])
            }
        }


class HealthChecker:
    """
    Health check manager for Nova-Torch system
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.checks: Dict[str, HealthCheck] = {}
        self.start_time = time.time()
        self._running = False
        self._check_task: Optional[asyncio.Task] = None
        self._check_interval = 10.0  # Run health checks every 10 seconds
        
        # Register default health checks
        self._register_default_checks()
        
        logger.info("Health checker initialized")
    
    def _register_default_checks(self):
        """Register default system health checks"""
        # DragonflyDB connectivity
        self.register_check(
            "dragonfly_connection",
            self._check_dragonfly_connection,
            timeout=5.0,
            interval=30.0
        )
        
        # Agent registry health
        self.register_check(
            "agent_registry",
            self._check_agent_registry,
            timeout=3.0,
            interval=60.0
        )
        
        # Task orchestrator health
        self.register_check(
            "task_orchestrator",
            self._check_task_orchestrator,
            timeout=3.0,
            interval=60.0
        )
        
        # Memory usage
        self.register_check(
            "memory_usage",
            self._check_memory_usage,
            timeout=2.0,
            interval=30.0
        )
        
        # Disk space
        self.register_check(
            "disk_space",
            self._check_disk_space,
            timeout=2.0,
            interval=120.0
        )
        
        # System load
        self.register_check(
            "system_load",
            self._check_system_load,
            timeout=1.0,
            interval=30.0
        )
    
    def register_check(self, name: str, check_func: Callable, **kwargs):
        """Register a new health check"""
        check = HealthCheck(name=name, check_func=check_func, **kwargs)
        self.checks[name] = check
        logger.info(f"Registered health check: {name}")
    
    def unregister_check(self, name: str):
        """Unregister a health check"""
        if name in self.checks:
            del self.checks[name]
            logger.info(f"Unregistered health check: {name}")
    
    def enable_check(self, name: str):
        """Enable a health check"""
        if name in self.checks:
            self.checks[name].enabled = True
            logger.info(f"Enabled health check: {name}")
    
    def disable_check(self, name: str):
        """Disable a health check"""
        if name in self.checks:
            self.checks[name].enabled = False
            logger.info(f"Disabled health check: {name}")
    
    async def run_check(self, name: str) -> HealthCheck:
        """Run a specific health check"""
        if name not in self.checks:
            raise ValueError(f"Health check '{name}' not found")
        
        check = self.checks[name]
        if not check.enabled:
            logger.debug(f"Health check '{name}' is disabled")
            return check
        
        start_time = time.time()
        
        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                check.check_func(),
                timeout=check.timeout
            )
            
            duration = time.time() - start_time
            check.last_run = start_time
            check.last_duration = duration
            check.last_error = None
            check.consecutive_failures = 0
            
            # Determine status based on duration and result
            if result is False:
                check.last_status = HealthStatus.CRITICAL
            elif duration > check.critical_threshold:
                check.last_status = HealthStatus.CRITICAL
            elif duration > check.warning_threshold:
                check.last_status = HealthStatus.WARNING
            else:
                check.last_status = HealthStatus.HEALTHY
                
        except asyncio.TimeoutError:
            check.last_status = HealthStatus.CRITICAL
            check.last_error = f"Health check timed out after {check.timeout}s"
            check.consecutive_failures += 1
            check.last_duration = time.time() - start_time
            logger.warning(f"Health check '{name}' timed out")
            
        except Exception as e:
            check.last_status = HealthStatus.CRITICAL
            check.last_error = str(e)
            check.consecutive_failures += 1
            check.last_duration = time.time() - start_time
            logger.error(f"Health check '{name}' failed: {e}")
        
        return check
    
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """Run all enabled health checks"""
        results = {}
        
        # Run checks concurrently
        tasks = []
        for name, check in self.checks.items():
            if check.enabled:
                tasks.append(self.run_check(name))
        
        if tasks:
            completed_checks = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(completed_checks):
                check_name = list(self.checks.keys())[i]
                if isinstance(result, Exception):
                    logger.error(f"Health check '{check_name}' failed with exception: {result}")
                    # Set error status
                    check = self.checks[check_name]
                    check.last_status = HealthStatus.CRITICAL
                    check.last_error = str(result)
                    check.consecutive_failures += 1
                    results[check_name] = check
                else:
                    results[check_name] = result
        
        return results
    
    async def get_system_health(self) -> SystemHealth:
        """Get overall system health status"""
        # Run all checks
        await self.run_all_checks()
        
        # Determine overall status
        overall_status = HealthStatus.HEALTHY
        
        for check in self.checks.values():
            if not check.enabled:
                continue
                
            if check.last_status == HealthStatus.CRITICAL:
                overall_status = HealthStatus.CRITICAL
                break
            elif check.last_status == HealthStatus.WARNING and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.WARNING
            elif check.last_status == HealthStatus.UNKNOWN and overall_status in [HealthStatus.HEALTHY]:
                overall_status = HealthStatus.WARNING
        
        return SystemHealth(
            status=overall_status,
            timestamp=time.time(),
            checks=self.checks.copy(),
            uptime=time.time() - self.start_time
        )
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self._running:
            logger.warning("Health monitoring already running")
            return
        
        self._running = True
        self._check_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Health monitoring started")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass
        logger.info("Health monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main health monitoring loop"""
        while self._running:
            try:
                # Run checks that are due
                current_time = time.time()
                
                for name, check in self.checks.items():
                    if not check.enabled:
                        continue
                    
                    # Check if it's time to run this check
                    if (check.last_run is None or 
                        current_time - check.last_run >= check.interval):
                        await self.run_check(name)
                
                # Wait before next iteration
                await asyncio.sleep(self._check_interval)
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self._check_interval)
    
    # Default health check implementations
    async def _check_dragonfly_connection(self) -> bool:
        """Check DragonflyDB connection health"""
        try:
            # This would be implemented to actually check DragonflyDB
            # For now, return True as placeholder
            await asyncio.sleep(0.01)  # Simulate check
            return True
        except Exception as e:
            logger.error(f"DragonflyDB health check failed: {e}")
            return False
    
    async def _check_agent_registry(self) -> bool:
        """Check agent registry health"""
        try:
            # This would check if agent registry is responsive
            await asyncio.sleep(0.01)  # Simulate check
            return True
        except Exception as e:
            logger.error(f"Agent registry health check failed: {e}")
            return False
    
    async def _check_task_orchestrator(self) -> bool:
        """Check task orchestrator health"""
        try:
            # This would check if task orchestrator is responsive
            await asyncio.sleep(0.01)  # Simulate check
            return True
        except Exception as e:
            logger.error(f"Task orchestrator health check failed: {e}")
            return False
    
    async def _check_memory_usage(self) -> bool:
        """Check system memory usage"""
        try:
            import psutil
            
            memory = psutil.virtual_memory()
            # Consider warning if > 80% memory usage
            # Consider critical if > 95% memory usage
            
            if memory.percent > 95:
                return False
            
            return True
            
        except ImportError:
            # psutil not available, skip check
            return True
        except Exception as e:
            logger.error(f"Memory usage health check failed: {e}")
            return False
    
    async def _check_disk_space(self) -> bool:
        """Check disk space"""
        try:
            import psutil
            
            disk = psutil.disk_usage('/')
            # Consider warning if > 80% disk usage
            # Consider critical if > 90% disk usage
            
            usage_percent = (disk.used / disk.total) * 100
            
            if usage_percent > 90:
                return False
            
            return True
            
        except ImportError:
            # psutil not available, skip check
            return True
        except Exception as e:
            logger.error(f"Disk space health check failed: {e}")
            return False
    
    async def _check_system_load(self) -> bool:
        """Check system load average"""
        try:
            import psutil
            
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Consider critical if > 95% CPU usage
            if cpu_percent > 95:
                return False
            
            return True
            
        except ImportError:
            # psutil not available, skip check
            return True
        except Exception as e:
            logger.error(f"System load health check failed: {e}")
            return False
    
    def get_check_status(self, name: str) -> Optional[HealthCheck]:
        """Get status of a specific health check"""
        return self.checks.get(name)
    
    def get_all_checks(self) -> Dict[str, HealthCheck]:
        """Get all health checks"""
        return self.checks.copy()
    
    def is_healthy(self) -> bool:
        """Check if system is overall healthy"""
        for check in self.checks.values():
            if check.enabled and check.last_status == HealthStatus.CRITICAL:
                return False
        return True