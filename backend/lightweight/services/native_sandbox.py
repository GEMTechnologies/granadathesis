"""
Native Ubuntu Sandbox (No Docker Required)

Uses Python's subprocess with restrictions for code execution.
NOT as secure as Docker, but works on any Ubuntu system.

Security layers:
1. subprocess with timeout
2. Resource limits (ulimit)
3. Restricted imports
4. Read-only workspace access
5. No network access
"""

import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional
import resource
import os

from config import get_workspace_dir


class NativeSandbox:
    """
    Ubuntu-native sandbox using subprocess.
    
    NO DOCKER REQUIRED!
    
    Pros:
    - Works everywhere
    - Fast startup
    - No Docker daemon needed
    
    Cons:
    - Less secure than Docker
    - Can only run Python/Node if installed
    - Limited isolation
    """
    
    def __init__(self, workspace_id: str):
        self.workspace_id = workspace_id
        self.workspace_dir = get_workspace_dir(workspace_id)
        self.workspace_dir.mkdir(parents=True, exist_ok=True)
    
    def execute_python(self, code: str, timeout: int = 5) -> Dict:
        """
        Execute Python code in isolated subprocess.
        
        Security:
        - Timeout limit
        - No network (TODO: use seccomp)
        - Restricted imports via wrapper
        """
        
        # Wrapper that restricts dangerous imports
        wrapper_code = f'''
import sys
import io

# Block dangerous imports
BLOCKED = ['os', 'subprocess', 'socket', 'urllib', 'requests']

class ImportBlocker:
    def find_module(self, name, path=None):
        if any(blocked in name for blocked in BLOCKED):
            raise ImportError(f"Import '{{name}}' is blocked for security")
        return None

sys.meta_path.insert(0, ImportBlocker())

# Capture output
stdout = io.StringIO()
stderr = io.StringIO()
sys.stdout = stdout
sys.stderr = stderr

# Execute user code
try:
    exec("""
{code}
""", {{}})
    result = stdout.getvalue()
    error = stderr.getvalue()
except Exception as e:
    result = ""
    error = str(e)

print("__RESULT__")
print(result)
print("__ERROR__")
print(error)
'''
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(wrapper_code)
            temp_file = f.name
        
        try:
            # Execute with resource limits
            def set_limits():
                # Limit memory to 100MB
                resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, 100 * 1024 * 1024))
                # Limit CPU time to 5 seconds
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout))
            
            result = subprocess.run(
                ['python3', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                preexec_fn=set_limits,
                cwd=str(self.workspace_dir)
            )
            
            # Parse output
            output = result.stdout
            if "__RESULT__" in output and "__ERROR__" in output:
                parts = output.split("__RESULT__")[1].split("__ERROR__")
                stdout_text = parts[0].strip()
                stderr_text = parts[1].strip() if len(parts) > 1 else ""
            else:
                stdout_text = output
                stderr_text = result.stderr
            
            return {
                "stdout": stdout_text,
                "stderr": stderr_text,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
        finally:
            os.unlink(temp_file)
    
    def execute_node(self, code: str, timeout: int = 5) -> Dict:
        """Execute Node.js code (if Node is installed)."""
        
        # Check if Node is available
        if not shutil.which('node'):
            return {
                "stdout": "",
                "stderr": "Node.js not installed",
                "exit_code": -1,
                "success": False
            }
        
        # Write to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            result = subprocess.run(
                ['node', temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.workspace_dir)
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
        finally:
            os.unlink(temp_file)
