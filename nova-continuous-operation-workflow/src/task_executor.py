#!/usr/bin/env python3
"""
Nova Task Executor - The brain that actually processes tasks
"""
import redis
import json
import time
import subprocess
import threading
from datetime import datetime
from typing import Dict, Any, Optional
import logging

class TaskExecutor:
    def __init__(self, nova_id: str):
        self.nova_id = nova_id
        self.redis = redis.Redis(host='localhost', port=18000, decode_responses=True)
        self.running = False
        self.current_task = None
        
        # Task handlers registry
        self.handlers = {
            'EXECUTE_COMMAND': self._handle_command,
            'RUN_SCRIPT': self._handle_script,
            'CHECK_STATUS': self._handle_status_check,
            'SEND_MESSAGE': self._handle_message,
            'ANALYZE_CODE': self._handle_code_analysis,
            'RUN_TESTS': self._handle_test_run,
            'BUILD_PROJECT': self._handle_build,
            'DEPLOY': self._handle_deploy,
        }
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(f'TaskExecutor:{nova_id}')
    
    def start(self):
        """Start the task executor"""
        self.running = True
        self.logger.info(f"Task executor starting for Nova {self.nova_id}")
        
        while self.running:
            try:
                # XREAD BLOCK for new tasks
                result = self.redis.xread(
                    {f'nova.tasks.{self.nova_id}': '$'},
                    block=5000  # 5 second timeout
                )
                
                if result:
                    for stream_name, messages in result:
                        for msg_id, task_data in messages:
                            self._process_task(msg_id, task_data)
                            
            except KeyboardInterrupt:
                self.logger.info("Shutting down task executor")
                break
            except Exception as e:
                self.logger.error(f"Task executor error: {e}")
                time.sleep(5)
    
    def _process_task(self, task_id: str, task_data: Dict[str, Any]):
        """Process a single task"""
        start_time = time.time()
        self.current_task = task_id
        
        task_type = task_data.get('type', 'unknown')
        priority = task_data.get('priority', 'normal')
        
        self.logger.info(f"Processing task {task_id}: {task_type} (priority: {priority})")
        
        # Update workflow state
        self.redis.hset(f'workflow:state:{self.nova_id}', 'current_task', task_id)
        
        # Execute task
        try:
            handler = self.handlers.get(task_type, self._handle_unknown)
            result = handler(task_data)
            
            # Record success
            duration_ms = (time.time() - start_time) * 1000
            self._record_completion(task_id, task_data, 'success', result, duration_ms)
            
            # Remove from queue
            self.redis.xdel(f'nova.tasks.{self.nova_id}', task_id)
            
        except Exception as e:
            # Record failure
            duration_ms = (time.time() - start_time) * 1000
            self._record_completion(task_id, task_data, 'failed', str(e), duration_ms)
            self.logger.error(f"Task {task_id} failed: {e}")
            
            # Move to dead letter queue
            self.redis.xadd(f'nova.tasks.{self.nova_id}.failed', task_data)
            self.redis.xdel(f'nova.tasks.{self.nova_id}', task_id)
        
        finally:
            self.current_task = None
            self.redis.hdel(f'workflow:state:{self.nova_id}', 'current_task')
    
    def _record_completion(self, task_id: str, task_data: Dict, status: str, 
                          result: Any, duration_ms: float):
        """Record task completion in history"""
        history_entry = {
            'task_id': task_id,
            'type': task_data.get('type'),
            'priority': task_data.get('priority', 'normal'),
            'status': status,
            'duration_ms': str(duration_ms),
            'completed_at': datetime.now().isoformat(),
            'nova_id': self.nova_id
        }
        
        if status == 'success':
            history_entry['result'] = str(result)[:500]  # Truncate long results
        else:
            history_entry['error'] = str(result)
        
        # Add to history stream
        self.redis.xadd(f'nova.tasks.{self.nova_id}.history', history_entry)
        
        # Update stats
        self.redis.hincrby(f'workflow:stats:{self.nova_id}', f'{status}_count', 1)
        self.redis.hincrby(f'workflow:stats:{self.nova_id}', 'total_count', 1)
        
        # Update today's count
        today = datetime.now().strftime('%Y-%m-%d')
        self.redis.hincrby(f'workflow:stats:{self.nova_id}:{today}', 'completed', 1)
    
    # Task Handlers
    def _handle_command(self, task_data: Dict) -> str:
        """Execute a shell command"""
        command = task_data.get('command', '')
        timeout = int(task_data.get('timeout', 30))
        
        try:
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=timeout
            )
            
            if result.returncode == 0:
                return result.stdout
            else:
                raise Exception(f"Command failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise Exception(f"Command timed out after {timeout}s")
    
    def _handle_script(self, task_data: Dict) -> str:
        """Run a Python script"""
        script_path = task_data.get('script_path', '')
        args = task_data.get('args', [])
        
        cmd = ['python3', script_path] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout
        else:
            raise Exception(f"Script failed: {result.stderr}")
    
    def _handle_status_check(self, task_data: Dict) -> Dict:
        """Check system status"""
        checks = []
        
        # Check workflow state
        state = self.redis.hgetall(f'workflow:state:{self.nova_id}')
        checks.append({'component': 'workflow', 'status': 'active' if state else 'inactive'})
        
        # Check task queue
        queue_size = self.redis.xlen(f'nova.tasks.{self.nova_id}')
        checks.append({'component': 'task_queue', 'size': queue_size})
        
        # Check Redis connection
        try:
            self.redis.ping()
            checks.append({'component': 'redis', 'status': 'connected'})
        except:
            checks.append({'component': 'redis', 'status': 'disconnected'})
        
        return {'checks': checks, 'timestamp': datetime.now().isoformat()}
    
    def _handle_message(self, task_data: Dict) -> str:
        """Send a message to another Nova or stream"""
        target = task_data.get('target', '')
        message = task_data.get('message', '')
        
        if target.startswith('nova.'):
            # Send to another Nova
            self.redis.xadd(f'nova.coordination.{target[5:]}', {
                'from': self.nova_id,
                'type': 'MESSAGE',
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        else:
            # Send to stream
            self.redis.xadd(target, {
                'from': self.nova_id,
                'message': message,
                'timestamp': datetime.now().isoformat()
            })
        
        return f"Message sent to {target}"
    
    def _handle_code_analysis(self, task_data: Dict) -> Dict:
        """Analyze code for quality, security, and performance issues"""
        file_path = task_data.get('file_path', '')
        analysis_type = task_data.get('analysis_type', 'basic')
        
        if not file_path or not os.path.exists(file_path):
            return {
                'file': file_path,
                'analysis': analysis_type,
                'error': 'File not found',
                'issues': 0,
                'suggestions': []
            }
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            issues = []
            suggestions = []
            
            # Basic security analysis
            if 'password' in content.lower() and ('=' in content or ':' in content):
                issues.append('SECURITY: Potential hardcoded password detected')
                suggestions.append('Move sensitive data to environment variables')
            
            if 'api_key' in content.lower() and ('=' in content or ':' in content):
                issues.append('SECURITY: Potential hardcoded API key detected')
                suggestions.append('Use secure credential management')
            
            # Code quality analysis
            if content.count('TODO') > 5:
                issues.append('QUALITY: High number of TODO comments')
                suggestions.append('Prioritize completing TODO items')
            
            if content.count('except:') > 0:
                issues.append('QUALITY: Bare except clauses found')
                suggestions.append('Use specific exception types')
            
            # Performance analysis
            if 'time.sleep(' in content and file_path.endswith('.py'):
                issues.append('PERFORMANCE: Sleep calls may impact performance')
                suggestions.append('Consider async alternatives or shorter delays')
            
            # Python-specific analysis
            if file_path.endswith('.py'):
                lines = content.split('\n')
                long_lines = [i+1 for i, line in enumerate(lines) if len(line) > 120]
                if long_lines:
                    issues.append(f'STYLE: Lines too long: {long_lines[:5]}...' if len(long_lines) > 5 else f'STYLE: Lines too long: {long_lines}')
                    suggestions.append('Break long lines for better readability')
            
            return {
                'file': file_path,
                'analysis': analysis_type,
                'issues': len(issues),
                'problems': issues,
                'suggestions': suggestions,
                'lines_analyzed': len(content.split('\n'))
            }
            
        except Exception as e:
            return {
                'file': file_path,
                'analysis': analysis_type,
                'error': f'Analysis failed: {str(e)}',
                'issues': 0,
                'suggestions': []
            }
    
    def _handle_test_run(self, task_data: Dict) -> Dict:
        """Run tests"""
        test_command = task_data.get('command', 'pytest')
        test_path = task_data.get('path', '.')
        
        cmd = f"{test_command} {test_path}"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        return {
            'passed': result.returncode == 0,
            'output': result.stdout,
            'errors': result.stderr
        }
    
    def _handle_build(self, task_data: Dict) -> Dict:
        """Build project"""
        build_command = task_data.get('command', 'make')
        build_path = task_data.get('path', '.')
        
        start = time.time()
        result = subprocess.run(
            f"cd {build_path} && {build_command}", 
            shell=True, 
            capture_output=True, 
            text=True
        )
        
        return {
            'success': result.returncode == 0,
            'duration': time.time() - start,
            'output': result.stdout[-1000:]  # Last 1000 chars
        }
    
    def _handle_deploy(self, task_data: Dict) -> Dict:
        """Deploy application using systemd services (no Docker/Kubernetes allowed)"""
        environment = task_data.get('environment', 'staging')
        version = task_data.get('version', 'latest')
        service_name = task_data.get('service_name', 'nova-app')
        
        try:
            start_time = time.time()
            deployment_steps = []
            
            # Validate environment
            if environment not in ['staging', 'production', 'development']:
                return {
                    'success': False,
                    'error': f'Invalid environment: {environment}',
                    'environment': environment
                }
            
            # Step 1: Check service status
            result = subprocess.run(
                f'systemctl is-active {service_name}',
                shell=True, capture_output=True, text=True
            )
            current_status = result.stdout.strip()
            deployment_steps.append(f'Current service status: {current_status}')
            
            # Step 2: Stop service if running
            if current_status == 'active':
                subprocess.run(f'sudo systemctl stop {service_name}', shell=True)
                deployment_steps.append(f'Stopped {service_name}')
            
            # Step 3: Update service configuration (if needed)
            config_path = f'/etc/systemd/system/{service_name}.service'
            deployment_steps.append(f'Using config: {config_path}')
            
            # Step 4: Reload systemd and start service
            subprocess.run('sudo systemctl daemon-reload', shell=True)
            subprocess.run(f'sudo systemctl start {service_name}', shell=True)
            deployment_steps.append(f'Started {service_name}')
            
            # Step 5: Enable service for auto-start
            subprocess.run(f'sudo systemctl enable {service_name}', shell=True)
            deployment_steps.append(f'Enabled {service_name} for auto-start')
            
            # Step 6: Verify deployment
            time.sleep(2)  # Give service time to start
            verify_result = subprocess.run(
                f'systemctl is-active {service_name}',
                shell=True, capture_output=True, text=True
            )
            
            deployment_time = time.time() - start_time
            success = verify_result.stdout.strip() == 'active'
            
            return {
                'success': success,
                'environment': environment,
                'version': version,
                'service': service_name,
                'status': verify_result.stdout.strip(),
                'deployment_time': round(deployment_time, 2),
                'steps': deployment_steps,
                'method': 'systemd'
            }
            
        except Exception as e:
            return {
                'success': False,
                'environment': environment,
                'version': version,
                'error': f'Deployment failed: {str(e)}',
                'method': 'systemd'
            }
    
    def _handle_unknown(self, task_data: Dict) -> str:
        """Handle unknown task types"""
        task_type = task_data.get('type', 'unknown')
        self.logger.warning(f"Unknown task type: {task_type}")
        
        # Try to pass to Claude for processing
        return f"Unknown task type: {task_type}. Implement handler in task_executor.py"

if __name__ == "__main__":
    import sys
    nova_id = sys.argv[1] if len(sys.argv) > 1 else 'torch'
    
    executor = TaskExecutor(nova_id)
    executor.start()