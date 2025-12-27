"""
Code Execution API Endpoint

Allows agents to execute code safely and stream results back.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import subprocess
import asyncio
import tempfile
import os
from pathlib import Path
import json
from app.api.stream import streamer
import time

router = APIRouter(prefix="/api/code", tags=["Code Execution"])


class CodeExecutionRequest(BaseModel):
    """Code execution request."""
    code: str
    language: str = "python"  # python, bash, javascript, etc.
    session_id: str = "default"
    timeout: int = 30  # seconds


class CodeExecutionResponse(BaseModel):
    """Code execution response."""
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None


async def execute_python_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute Python code safely."""
    import time
    start_time = time.time()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Execute code with timeout
        process = await asyncio.create_subprocess_exec(
            'python3', temp_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tempfile.gettempdir()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "success": False,
                "output": "",
                "error": f"Code execution timed out after {timeout} seconds",
                "exit_code": -1,
                "execution_time": time.time() - start_time
            }
        
        execution_time = time.time() - start_time
        output = stdout.decode('utf-8', errors='replace')
        error = stderr.decode('utf-8', errors='replace') if stderr else None
        
        return {
            "success": process.returncode == 0,
            "output": output,
            "error": error if process.returncode != 0 else None,
            "exit_code": process.returncode,
            "execution_time": execution_time
        }
    finally:
        # Cleanup
        try:
            os.unlink(temp_file)
        except:
            pass


async def execute_bash_code(code: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute bash code safely."""
    import time
    start_time = time.time()
    
    try:
        process = await asyncio.create_subprocess_shell(
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tempfile.gettempdir()
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return {
                "success": False,
                "output": "",
                "error": f"Code execution timed out after {timeout} seconds",
                "exit_code": -1,
                "execution_time": time.time() - start_time
            }
        
        execution_time = time.time() - start_time
        output = stdout.decode('utf-8', errors='replace')
        error = stderr.decode('utf-8', errors='replace') if stderr else None
        
        return {
            "success": process.returncode == 0,
            "output": output,
            "error": error if process.returncode != 0 else None,
            "exit_code": process.returncode,
            "execution_time": execution_time
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "exit_code": -1,
            "execution_time": time.time() - start_time
        }


@router.post("/execute", response_model=CodeExecutionResponse)
async def execute_code(request: CodeExecutionRequest):
    """
    Execute code and return results.
    
    Supports:
    - Python
    - Bash/Shell
    """
    # Publish start action
    await streamer.publish_action(request.session_id, {
        "id": f"code-exec-{int(time.time() * 1000)}",
        "type": "code_execution",
        "title": f"Executing {request.language} code",
        "status": "running",
        "content": request.code,
        "metadata": {
            "language": request.language,
            "timeout": request.timeout
        }
    })
    
    try:
        if request.language == "python":
            result = await execute_python_code(request.code, request.timeout)
        elif request.language in ["bash", "sh", "shell"]:
            result = await execute_bash_code(request.code, request.timeout)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported language: {request.language}"
            )
        
        # Publish result action
        action_id = f"code-exec-{int(time.time() * 1000)}"
        await streamer.publish_action(request.session_id, {
            "id": action_id,
            "type": "code_execution",
            "title": f"{request.language.capitalize()} execution {'successful' if result['success'] else 'failed'}",
            "status": "completed" if result['success'] else "error",
            "content": result['output'] if result['success'] else result.get('error', ''),
            "metadata": {
                "language": request.language,
                "exit_code": result.get('exit_code'),
                "execution_time": result.get('execution_time'),
                "success": result['success']
            }
        })
        
        return CodeExecutionResponse(**result)
        
    except Exception as e:
        # Publish error action
        await streamer.publish_action(request.session_id, {
            "id": f"code-exec-{int(time.time() * 1000)}",
            "type": "code_execution",
            "title": f"Code execution error",
            "status": "error",
            "content": str(e),
            "metadata": {
                "language": request.language,
                "error": str(e)
            }
        })
        
        raise HTTPException(
            status_code=500,
            detail=f"Code execution failed: {str(e)}"
        )


@router.get("/health")
async def code_execution_health():
    """Health check for code execution endpoint."""
    return {"status": "ok", "supported_languages": ["python", "bash", "sh", "shell"]}



