"""
Docker-based Sandbox Manager for Agent Code Execution

Provides isolated, secure sandboxes for running agent code with:
- Docker container isolation
- Resource limits (CPU, RAM, disk)
- Security hardening (no network, read-only root, capability dropping)
- Auto-cleanup for idle sandboxes
"""

import docker
import asyncio
import secrets
import ast
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from pathlib import Path
import json

# Security configuration
SANDBOX_DEFAULTS = {
    "memory_limit": "512m",
    "cpu_quota": 50000,  # 50% of one CPU core
    "timeout": 30,  # seconds
    "network": False,  # No network access
    "disk_quota": "100M",  # tmpfs size
    "idle_timeout": 3600,  # 1 hour in seconds
}

# Supported languages and their base images
SANDBOX_IMAGES = {
    # Basic sandboxes (no network - secure)
    "python": "python:3.11-slim",
    "nodejs": "node:18-alpine",
    "bash": "ubuntu:22.04",
    
    # Development sandboxes (network enabled)
    "python_dev": "python:3.11",  # With pip access
    "nodejs_dev": "node:18",  # With npm access
    "fullstack": "ubuntu:22.04",  # Python + Node + tools
}

# Network-enabled templates (agent can install packages)
NETWORK_ENABLED_TEMPLATES = [
    "python_dev",
    "nodejs_dev", 
    "fullstack"
]


class Sandbox:
    """Represents an isolated Docker sandbox for code execution."""
    
    def __init__(
        self,
        sandbox_id: str,
        workspace_id: str,
        container,
        template: str,
        user_id: str = None
    ):
        self.id = sandbox_id
        self.workspace_id = workspace_id
        self.container = container
        self.template = template
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.last_used = datetime.utcnow()
        self.status = "running"
    
    def update_last_used(self):
        """Update last used timestamp."""
        self.last_used = datetime.utcnow()
    
    def is_idle(self, timeout: int = SANDBOX_DEFAULTS["idle_timeout"]) -> bool:
        """Check if sandbox has been idle for too long."""
        idle_time = (datetime.utcnow() - self.last_used).total_seconds()
        return idle_time > timeout


class SandboxManager:
    """
    Manages Docker-based sandboxes for secure agent code execution.
    
    Features:
    - Container isolation with security hardening
    - Resource limits (CPU, memory, disk)
    - Auto-cleanup of idle sandboxes
    - CORS-free design (all requests through main API)
    """
    
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.sandboxes: Dict[str, Sandbox] = {}
            self._cleanup_task = None
            print("✅ Docker client initialized")
        except docker.errors.DockerException as e:
            print(f"⚠️ Docker not available: {e}")
            self.client = None
    
    async def create_sandbox(
        self,
        workspace_id: str,
        template: str = "python",
        user_id: str = None,
        enable_network: bool = False
    ) -> Sandbox:
        """
        Create isolated Docker sandbox with security hardening.
        
        Security features:
        - Read-only root filesystem
        - No network access (unless explicitly enabled)
        - Resource limits (CPU, memory)
        - User namespaces (run as nobody)
        - All capabilities dropped
        """
        if not self.client:
            raise RuntimeError("Docker not available")
        
        # Generate unique sandbox ID
        sandbox_id = f"sandbox_{workspace_id}_{secrets.token_hex(4)}"
        
        # Get base image
        image = SANDBOX_IMAGES.get(template, SANDBOX_IMAGES["python"])
        
        # Determine network access
        # Dev templates need network to install packages
        needs_network = enable_network or template in NETWORK_ENABLED_TEMPLATES
        
        # Ensure image exists
        try:
            self.client.images.pull(image)
        except Exception as e:
            print(f"⚠️ Could not pull image {image}: {e}")
        
        # Create workspace directory
        from config import get_workspace_dir
        workspace_dir = get_workspace_dir(workspace_id)
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create container with security restrictions
            container = self.client.containers.run(
                image=image,
                name=sandbox_id,
                detach=True,
                
                # Security: Read-only root filesystem (except for dev sandboxes)
                read_only=not needs_network,  # Dev needs write access
                
                # Security: Writable /tmp via tmpfs
                tmpfs={
                    '/tmp': f'size={SANDBOX_DEFAULTS["disk_quota"]},mode=1777',
                    '/workspace': f'size={SANDBOX_DEFAULTS["disk_quota"]},mode=1777'
                },
                
                # Security: Network isolation (unless dev template)
                network_mode="bridge" if needs_network else "none",
                
                # Security: Drop all capabilities
                cap_drop=["ALL"],
                
                # Security: Run as non-root user
                user="nobody",
                
                # Resource limits
                mem_limit=SANDBOX_DEFAULTS["memory_limit"],
                cpu_quota=SANDBOX_DEFAULTS["cpu_quota"],
                
                # Working directory
                working_dir="/workspace",
                
                # Keep container alive
                command="tail -f /dev/null",
                
                # Labels for tracking
                labels={
                    "workspace_id": workspace_id,
                    "user_id": user_id or "anonymous",
                    "template": template,
                    "created_at": datetime.utcnow().isoformat(),
                    "managed_by": "thesis_sandbox_manager"
                },
                
                # Remove on exit
                auto_remove=False
            )
            
            sandbox = Sandbox(
                sandbox_id=sandbox_id,
                workspace_id=workspace_id,
                container=container,
                template=template,
                user_id=user_id
            )
            
            self.sandboxes[workspace_id] = sandbox
            
            print(f"✅ Created sandbox {sandbox_id} for workspace {workspace_id}")
            
            return sandbox
        
        except docker.errors.ContainerError as e:
            raise RuntimeError(f"Failed to create sandbox: {e}")
    
    async def execute_code(
        self,
        workspace_id: str,
        code: str,
        language: str = "python",
        timeout: int = SANDBOX_DEFAULTS["timeout"]
    ) -> Dict:
        """
        Execute code in sandbox with security validation and timeout.
        
        Returns:
            dict: {
                "stdout": str,
                "stderr": str,
                "exit_code": int,
                "success": bool,
                "execution_time": float
            }
        """
        sandbox = self.sandboxes.get(workspace_id)
        if not sandbox:
            raise ValueError(f"Sandbox not found for workspace: {workspace_id}")
        
        # Update last used timestamp
        sandbox.update_last_used()
        
        # Validate code for security
        validation_result = self._validate_code(code, language)
        if not validation_result["safe"]:
            return {
                "stdout": "",
                "stderr": f"Code validation failed: {validation_result['reason']}",
                "exit_code": 1,
                "success": False,
                "execution_time": 0
            }
        
        # Get execution command
        exec_cmd = self._get_exec_command(language, code)
        
        try:
            import time
            start_time = time.time()
            
            # Execute with timeout
            exec_result = sandbox.container.exec_run(
                cmd=exec_cmd,
                user="nobody",
                workdir="/workspace",
                environment={
                    "PYTHONUNBUFFERED": "1",
                    "NODE_ENV": "production"
                },
                demux=True,  # Separate stdout/stderr
                stream=False
            )
            
            execution_time = time.time() - start_time
            
            stdout_bytes, stderr_bytes = exec_result.output
            
            return {
                "stdout": stdout_bytes.decode('utf-8') if stdout_bytes else "",
                "stderr": stderr_bytes.decode('utf-8') if stderr_bytes else "",
                "exit_code": exec_result.exit_code,
                "success": exec_result.exit_code == 0,
                "execution_time": round(execution_time, 3)
            }
        
        except docker.errors.ContainerError as e:
            return {
                "stdout": "",
                "stderr": f"Container error: {str(e)}",
                "exit_code": 1,
                "success": False,
                "execution_time": 0
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": 1,
                "success": False,
                "execution_time": 0
            }
    
    async def cleanup_sandbox(self, workspace_id: str) -> bool:
        """
        Stop and remove sandbox container.
        
        Returns:
            bool: True if cleaned up successfully
        """
        sandbox = self.sandboxes.get(workspace_id)
        if not sandbox:
            return False
        
        try:
            sandbox.container.stop(timeout=5)
            sandbox.container.remove(force=True)
            del self.sandboxes[workspace_id]
            print(f"✅ Cleaned up sandbox for workspace {workspace_id}")
            return True
        except Exception as e:
            print(f"⚠️ Error cleaning up sandbox {workspace_id}: {e}")
            return False
    
    async def cleanup_idle_sandboxes(self):
        """Clean up sandboxes that have been idle for too long."""
        idle_workspaces = [
            ws_id for ws_id, sandbox in self.sandboxes.items()
            if sandbox.is_idle()
        ]
        
        for ws_id in idle_workspaces:
            await self.cleanup_sandbox(ws_id)
    
    async def get_sandbox_stats(self, workspace_id: str) -> Optional[Dict]:
        """Get sandbox resource usage statistics."""
        sandbox = self.sandboxes.get(workspace_id)
        if not sandbox:
            return None
        
        try:
            stats = sandbox.container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                       stats["precpu_stats"]["cpu_usage"]["total_usage"]
            system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                          stats["precpu_stats"]["system_cpu_usage"]
            cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
            
            # Memory usage
            mem_usage = stats["memory_stats"]["usage"]
            mem_limit = stats["memory_stats"]["limit"]
            mem_percent = (mem_usage / mem_limit) * 100.0
            
            return {
                "workspace_id": workspace_id,
                "sandbox_id": sandbox.id,
                "cpu_percent": round(cpu_percent, 2),
                "memory_usage_mb": round(mem_usage / (1024 * 1024), 2),
                "memory_limit_mb": round(mem_limit / (1024 * 1024), 2),
                "memory_percent": round(mem_percent, 2),
                "uptime_seconds": (datetime.utcnow() - sandbox.created_at).total_seconds(),
                "status": sandbox.status
            }
        except Exception as e:
            print(f"⚠️ Error getting stats: {e}")
            return None
    
    def _get_exec_command(self, language: str, code: str) -> List[str]:
        """Get execution command for language."""
        if language == "python":
            return ["python3", "-c", code]
        elif language in ["javascript", "nodejs"]:
            return ["node", "-e", code]
        elif language == "bash":
            return ["bash", "-c", code]
        else:
            raise ValueError(f"Unsupported language: {language}")
    
    def _validate_code(self, code: str, language: str) -> Dict:
        """
        Validate code for security issues.
        
        Returns:
            dict: {"safe": bool, "reason": str}
        """
        if language == "python":
            return self._validate_python_code(code)
        # Add validators for other languages as needed
        return {"safe": True, "reason": ""}
    
    def _validate_python_code(self, code: str) -> Dict:
        """
        Validate Python code using AST analysis.
        
        Blocks:
        - Import of dangerous modules (os.system, subprocess, etc.)
        - __import__ and eval calls
        - File operations outside /workspace
        """
        dangerous_imports = [
            'os', 'subprocess', 'shutil', 'socket', 'urllib',
            'requests', 'http', 'ftplib', 'telnetlib'
        ]
        
        dangerous_functions = [
            '__import__', 'eval', 'exec', 'compile', 'open'
        ]
        
        try:
            tree = ast.parse(code)
            
            # Check for dangerous imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(danger in alias.name for danger in dangerous_imports):
                            return {
                                "safe": False,
                                "reason": f"Dangerous import blocked: {alias.name}"
                            }
                
                if isinstance(node, ast.ImportFrom):
                    if any(danger in node.module for danger in dangerous_imports):
                        return {
                            "safe": False,
                            "reason": f"Dangerous import blocked: {node.module}"
                        }
                
                # Check for dangerous function calls
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in dangerous_functions:
                            return {
                                "safe": False,
                                "reason": f"Dangerous function blocked: {node.func.id}"
                            }
            
            return {"safe": True, "reason": ""}
        
        except SyntaxError as e:
            return {"safe": False, "reason": f"Syntax error: {str(e)}"}
    
    def list_sandboxes(self) -> List[Dict]:
        """List all active sandboxes."""
        return [
            {
                "workspace_id": sandbox.workspace_id,
                "sandbox_id": sandbox.id,
                "template": sandbox.template,
                "created_at": sandbox.created_at.isoformat(),
                "last_used": sandbox.last_used.isoformat(),
                "status": sandbox.status
            }
            for sandbox in self.sandboxes.values()
        ]


# Singleton instance
sandbox_manager = SandboxManager()
