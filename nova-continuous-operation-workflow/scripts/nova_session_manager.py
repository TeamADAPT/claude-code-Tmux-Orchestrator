#!/usr/bin/env python3
"""
Nova Session Manager v2.0
Manages Claude Code (claude) sessions in gnome-terminal windows
Tracks PIDs, ports, and session states for Nova entities
"""

import os
import subprocess
import json
import psutil
import signal
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Optional, List
import time

class NovaSessionManager:
    """Manage Claude Code sessions for Nova entities."""
    
    def __init__(self):
        self.nova_base = Path("/nfs/novas/profiles")
        self.sessions = {}
        self.load_sessions()
    
    def load_sessions(self):
        """Load existing session data from Nova directories."""
        for nova_dir in self.nova_base.iterdir():
            if nova_dir.is_dir() and (nova_dir / "identity.yaml").exists():
                nova_id = nova_dir.name
                self.sessions[nova_id] = self._get_nova_session_info(nova_id)
    
    def _get_nova_session_info(self, nova_id: str) -> Dict:
        """Get session info for a specific Nova."""
        nova_path = self.nova_base / nova_id
        info = {
            "nova_id": nova_id,
            "path": str(nova_path),
            "pid": None,
            "port": None,
            "status": "stopped",
            "terminal_pid": None,
            "last_updated": None
        }
        
        # Check for PID file
        pid_file = nova_path / "nova.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                if self._is_process_running(pid):
                    info["pid"] = pid
                    info["status"] = "running"
                else:
                    # Stale PID, clean it up
                    pid_file.unlink()
            except:
                pass
        
        # Check for port file
        port_file = nova_path / "nova.port"
        if port_file.exists():
            try:
                info["port"] = int(port_file.read_text().strip())
            except:
                pass
        
        # Check status file
        status_file = nova_path / "nova.status"
        if status_file.exists():
            try:
                status_data = json.loads(status_file.read_text())
                # Don't let status file override runtime status check
                current_status = info.get("status")
                info.update(status_data)
                if current_status is not None:
                    info["status"] = current_status
            except:
                pass
        
        # Clean up status file if process is not running
        if info["status"] == "stopped" and status_file.exists():
            status_file.unlink()
        
        return info
    
    def _is_process_running(self, pid: int) -> bool:
        """Check if a process with given PID is running."""
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except psutil.NoProcessFound:
            return False
    
    def launch_nova(self, nova_id: str, mode: str = "interactive") -> Dict:
        """Launch a Nova in a new gnome-terminal window."""
        if nova_id not in self.sessions:
            return {"error": f"Nova {nova_id} not found"}
        
        nova_path = self.nova_base / nova_id
        
        # Check if already running
        if self.sessions[nova_id]["status"] == "running":
            return {"error": f"Nova {nova_id} is already running", "pid": self.sessions[nova_id]["pid"]}
        
        # Ensure session directories exist
        self._ensure_session_structure(nova_path)
        
        # Prepare launch command
        if mode == "interactive":
            # Interactive Claude Code session
            cc_command = f"cd {nova_path} && claude --dangerously-skip-permissions"
        else:
            # Task mode (could be extended)
            cc_command = f"cd {nova_path} && claude --print --dangerously-skip-permissions"
        
        # Create wrapper script to capture PID
        wrapper_script = nova_path / ".launch_wrapper.sh"
        wrapper_content = f"""#!/bin/bash
# Nova Session Wrapper for {nova_id}
cd {nova_path}

# Launch claude in background to capture its PID
claude --dangerously-skip-permissions &
CLAUDE_PID=$!

# Write the actual Claude PID
echo $CLAUDE_PID > nova.pid
echo "running" > nova.status.tmp
echo '{{"status": "running", "started": "{datetime.now(UTC).isoformat()}", "mode": "{mode}", "pid": '$CLAUDE_PID'}}' > nova.status

# Wait for Claude to finish
wait $CLAUDE_PID
"""
        wrapper_script.write_text(wrapper_content)
        wrapper_script.chmod(0o755)
        
        # Launch in gnome-terminal
        terminal_cmd = [
            "gnome-terminal",
            "--title", f"Nova: {nova_id.upper()}",
            "--geometry", "120x40",
            "--", 
            str(wrapper_script)
        ]
        
        try:
            # Launch the terminal
            proc = subprocess.Popen(terminal_cmd)
            terminal_pid = proc.pid
            
            # Wait a moment for the session to start
            time.sleep(2)
            
            # Read the actual Claude Code PID
            pid_file = nova_path / "nova.pid"
            if pid_file.exists():
                cc_pid = int(pid_file.read_text().strip())
                
                # Update session info
                self.sessions[nova_id].update({
                    "pid": cc_pid,
                    "terminal_pid": terminal_pid,
                    "status": "running",
                    "mode": mode,
                    "started": datetime.now(UTC).isoformat()
                })
                
                # Save terminal PID separately
                (nova_path / "nova.terminal_pid").write_text(str(terminal_pid))
                
                # Archive the launch
                self._archive_launch(nova_id)
                
                return {
                    "success": True,
                    "nova_id": nova_id,
                    "pid": cc_pid,
                    "terminal_pid": terminal_pid,
                    "message": f"Launched {nova_id} in gnome-terminal"
                }
            else:
                return {"error": "Failed to capture Claude Code PID"}
                
        except Exception as e:
            return {"error": f"Failed to launch: {str(e)}"}
    
    def stop_nova(self, nova_id: str, graceful: bool = True) -> Dict:
        """Stop a running Nova session."""
        if nova_id not in self.sessions:
            return {"error": f"Nova {nova_id} not found"}
        
        session = self.sessions[nova_id]
        if session["status"] != "running":
            return {"error": f"Nova {nova_id} is not running"}
        
        nova_path = self.nova_base / nova_id
        pid = session["pid"]
        terminal_pid = session.get("terminal_pid")
        
        try:
            if graceful:
                # Try graceful shutdown first
                if terminal_pid and self._is_process_running(terminal_pid):
                    os.kill(terminal_pid, signal.SIGTERM)
                    time.sleep(2)
                
                # If Claude Code is still running, terminate it
                if pid and self._is_process_running(pid):
                    os.kill(pid, signal.SIGTERM)
                    time.sleep(1)
            else:
                # Force kill
                if pid and self._is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
                if terminal_pid and self._is_process_running(terminal_pid):
                    os.kill(terminal_pid, signal.SIGKILL)
            
            # Clean up files
            (nova_path / "nova.pid").unlink(missing_ok=True)
            (nova_path / "nova.terminal_pid").unlink(missing_ok=True)
            
            # Update status
            status_data = {
                "status": "stopped",
                "stopped": datetime.now(UTC).isoformat(),
                "stop_method": "graceful" if graceful else "forced"
            }
            (nova_path / "nova.status").write_text(json.dumps(status_data, indent=2))
            
            # Update session info
            self.sessions[nova_id]["status"] = "stopped"
            self.sessions[nova_id]["pid"] = None
            self.sessions[nova_id]["terminal_pid"] = None
            
            # Archive the session
            self._archive_session(nova_id)
            
            return {
                "success": True,
                "nova_id": nova_id,
                "message": f"Stopped {nova_id}"
            }
            
        except Exception as e:
            return {"error": f"Failed to stop: {str(e)}"}
    
    def _ensure_session_structure(self, nova_path: Path):
        """Ensure proper session directory structure exists."""
        # Create session directories
        sessions_dir = nova_path / "sessions"
        sessions_dir.mkdir(exist_ok=True)
        (sessions_dir / "active").mkdir(exist_ok=True)
        (sessions_dir / "archived").mkdir(exist_ok=True)
    
    def _archive_launch(self, nova_id: str):
        """Archive launch information."""
        nova_path = self.nova_base / nova_id
        archive_dir = nova_path / "sessions" / "archived" / datetime.now(UTC).strftime("%Y%m%d")
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        launch_info = {
            "nova_id": nova_id,
            "launched": datetime.now(UTC).isoformat(),
            "pid": self.sessions[nova_id]["pid"],
            "mode": self.sessions[nova_id].get("mode", "interactive")
        }
        
        launch_file = archive_dir / f"launch_{datetime.now(UTC).strftime('%H%M%S')}.json"
        launch_file.write_text(json.dumps(launch_info, indent=2))
    
    def _archive_session(self, nova_id: str):
        """Archive session when stopped."""
        nova_path = self.nova_base / nova_id
        active_dir = nova_path / "sessions" / "active"
        
        # Move active session logs to archive if they exist
        if active_dir.exists():
            archive_dir = nova_path / "sessions" / "archived" / datetime.now(UTC).strftime("%Y%m%d")
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            # Move any active session files
            for file in active_dir.iterdir():
                if file.is_file():
                    target = archive_dir / f"{file.stem}_{datetime.now(UTC).strftime('%H%M%S')}{file.suffix}"
                    file.rename(target)
    
    def get_status(self, nova_id: Optional[str] = None) -> Dict:
        """Get status of Nova(s)."""
        if nova_id:
            # Single Nova status
            if nova_id not in self.sessions:
                return {"error": f"Nova {nova_id} not found"}
            
            # Refresh status
            self.sessions[nova_id] = self._get_nova_session_info(nova_id)
            return self.sessions[nova_id]
        else:
            # All Novas status
            status = {
                "running": [],
                "stopped": [],
                "total": len(self.sessions)
            }
            
            for nova_id, session in self.sessions.items():
                # Refresh status
                self.sessions[nova_id] = self._get_nova_session_info(nova_id)
                
                if self.sessions[nova_id]["status"] == "running":
                    status["running"].append({
                        "nova_id": nova_id,
                        "pid": self.sessions[nova_id]["pid"],
                        "uptime": self._get_uptime(self.sessions[nova_id]["pid"])
                    })
                else:
                    status["stopped"].append(nova_id)
            
            return status
    
    def _get_uptime(self, pid: Optional[int]) -> str:
        """Get process uptime."""
        if not pid:
            return "N/A"
        
        try:
            process = psutil.Process(pid)
            create_time = process.create_time()
            uptime_seconds = time.time() - create_time
            
            hours = int(uptime_seconds // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return f"{hours}h {minutes}m"
        except:
            return "N/A"
    
    def list_novas(self) -> List[Dict]:
        """List all available Novas with their status."""
        nova_list = []
        
        for nova_id, session in self.sessions.items():
            # Get Nova type from position history
            nova_type = "specialist"
            position_file = self.nova_base / nova_id / "00_CORE_SYSTEMS" / "position_history.json"
            if position_file.exists():
                try:
                    position_data = json.loads(position_file.read_text())
                    current_position = position_data.get("current_position", "")
                    if any(title in current_position for title in ["Chief", "CSO", "COO", "CAO", "CAIO"]):
                        nova_type = "c_level"
                    elif "Group Head" in current_position:
                        nova_type = "group_head"
                except:
                    pass
            
            nova_list.append({
                "nova_id": nova_id,
                "type": nova_type,
                "status": session["status"],
                "pid": session.get("pid"),
                "port": session.get("port")
            })
        
        # Sort by type then name
        type_order = {"c_level": 0, "group_head": 1, "specialist": 2}
        nova_list.sort(key=lambda x: (type_order.get(x["type"], 99), x["nova_id"]))
        
        return nova_list


# CLI Interface
def main():
    """Command line interface for Nova session management."""
    import sys
    
    manager = NovaSessionManager()
    
    if len(sys.argv) < 2:
        print("Nova Session Manager v2.0")
        print("Usage: nova_session_manager.py [command] [args]")
        print("\nCommands:")
        print("  list                    - List all Novas and their status")
        print("  status [nova_id]        - Get status of specific Nova or all")
        print("  launch <nova_id>        - Launch Nova in gnome-terminal")
        print("  stop <nova_id>          - Stop running Nova")
        print("  stop-all                - Stop all running Novas")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        novas = manager.list_novas()
        print(f"\n{'Nova ID':<15} {'Type':<12} {'Status':<10} {'PID':<8}")
        print("-" * 50)
        for nova in novas:
            pid_str = str(nova['pid']) if nova['pid'] else "-"
            print(f"{nova['nova_id']:<15} {nova['type']:<12} {nova['status']:<10} {pid_str:<8}")
        
        # Summary
        running = sum(1 for n in novas if n['status'] == 'running')
        print(f"\nTotal: {len(novas)} | Running: {running} | Stopped: {len(novas) - running}")
    
    elif command == "status":
        if len(sys.argv) > 2:
            nova_id = sys.argv[2]
            status = manager.get_status(nova_id)
        else:
            status = manager.get_status()
        
        print(json.dumps(status, indent=2))
    
    elif command == "launch":
        if len(sys.argv) < 3:
            print("Error: nova_id required")
            return
        
        nova_id = sys.argv[2]
        result = manager.launch_nova(nova_id)
        
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ {result['message']}")
            print(f"   PID: {result['pid']}")
            print(f"   Terminal PID: {result['terminal_pid']}")
    
    elif command == "stop":
        if len(sys.argv) < 3:
            print("Error: nova_id required")
            return
        
        nova_id = sys.argv[2]
        result = manager.stop_nova(nova_id)
        
        if "error" in result:
            print(f"❌ {result['error']}")
        else:
            print(f"✅ {result['message']}")
    
    elif command == "stop-all":
        status = manager.get_status()
        stopped = 0
        
        for nova in status.get("running", []):
            result = manager.stop_nova(nova["nova_id"])
            if result.get("success"):
                print(f"✅ Stopped {nova['nova_id']}")
                stopped += 1
            else:
                print(f"❌ Failed to stop {nova['nova_id']}: {result.get('error')}")
        
        print(f"\nStopped {stopped} Novas")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()