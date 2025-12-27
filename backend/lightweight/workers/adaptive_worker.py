"""
Adaptive Worker - Self-Learning Dataset Processor

Automatically analyzes unknown datasets, generates custom agents,
and executes them to process data.

Flow:
1. User uploads dataset (Excel, CSV, JSON)
2. Worker analyzes dataset structure
3. Generates custom processing agent using LLM
4. Validates and stores agent
5. Executes agent on dataset
6. Returns results
"""
import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any
import json
import traceback

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, '..')

from core.queue import worker, JobQueue
from core.events import events
from services.dataset_analyzer import dataset_analyzer
from services.agent_generator import agent_generator
from services.agent_registry import agent_registry


@worker("adaptive")
async def process_adaptive_job(data: dict):
    """
    Process datasets with auto-generated custom agents.
    
    Handles:
    - Unknown dataset formats
    - Custom processing tasks
    - Agent generation and caching
    - Dynamic code execution
    """
    job_id = data.get("job_id")
    if not job_id:
        import uuid
        job_id = str(uuid.uuid4())
        data["job_id"] = job_id
    
    file_path = data.get("file_path")
    task = data.get("task", "analyze dataset")
    workspace_id = data.get("workspace_id", "default")
    
    try:
        print(f"⚡ Adaptive Worker awakened! Processing: {file_path}")
        
        # Step 1: Analyze dataset
        await events.log(job_id, f"📊 Analyzing dataset: {Path(file_path).name}")
        await events.publish(job_id, "progress", {"stage": "analysis", "percent": 10})
        
        analysis = await dataset_analyzer.analyze(file_path)
        
        await events.log(job_id, f"✅ Dataset analyzed: {analysis['file_info']['format'].upper()} with {analysis['schema']['rows']:,} rows")
        await events.publish(job_id, "progress", {"stage": "analysis_complete", "percent": 25})
        
        # Step 2: Check for existing agent
        await events.log(job_id, "🔍 Checking for existing agent...")
        agent_id = await agent_registry.find_similar(analysis, task)
        
        if agent_id:
            await events.log(job_id, f"♻️  Found existing agent: {agent_id}")
            await events.publish(job_id, "progress", {"stage": "agent_found", "percent": 40})
        else:
            # Step 3: Generate new agent
            await events.log(job_id, "🤖 No existing agent found. Generating custom agent...")
            await events.publish(job_id, "progress", {"stage": "generating_agent", "percent": 30})
            
            agent_code = await agent_generator.generate_agent(
                dataset_analysis=analysis,
                task_description=task,
                job_id=job_id
            )
            
            await events.log(job_id, f"✅ Agent generated ({len(agent_code)} chars)")
            
            # Step 4: Validate and save agent
            await events.log(job_id, "💾 Saving agent to registry...")
            
            metadata = {
                "task": task,
                "file_info": analysis["file_info"],
                "schema": analysis["schema"],
                "patterns": analysis["patterns"]
            }
            
            agent_id = await agent_registry.save(agent_code, metadata)
            await events.log(job_id, f"✅ Agent saved: {agent_id}")
            await events.publish(job_id, "progress", {"stage": "agent_ready", "percent": 50})
        
        # Step 5: Check and install required packages
        await events.log(job_id, "📦 Checking required packages...")
        
        # Extract package requirements from agent code
        required_packages = extract_required_packages(agent_code)
        
        if required_packages:
            from services.package_manager import package_manager
            await events.log(job_id, f"📋 Required packages: {', '.join(required_packages)}")
            
            packages_ok = await package_manager.ensure_packages(required_packages, job_id)
            
            if not packages_ok:
                raise Exception("Failed to install required packages")
        
        await events.publish(job_id, "progress", {"stage": "packages_ready", "percent": 55})
        
        # Step 6: Execute agent
        await events.log(job_id, "⚡ Executing agent on dataset...")
        await events.publish(job_id, "progress", {"stage": "executing", "percent": 60})
        
        agent_code = await agent_registry.load(agent_id)
        
        if not agent_code:
            raise Exception(f"Failed to load agent: {agent_id}")
        
        # Execute agent
        results = await execute_agent_safely(
            agent_code=agent_code,
            file_path=file_path,
            params=data.get("params", {}),
            job_id=job_id
        )
        
        await events.log(job_id, "✅ Processing complete!")
        await events.publish(job_id, "progress", {"stage": "complete", "percent": 100})
        
        # Save results to file
        results_file = Path(file_path).parent / f"{Path(file_path).stem}_results.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        await events.log(job_id, f"💾 Results saved to {results_file.name}")
        await events.file_created(job_id, f"{workspace_id}/{results_file.name}", "json")
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "results": results,
            "results_file": str(results_file),
            "dataset_analysis": analysis
        }
        
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        
        await events.log(job_id, f"❌ Processing failed: {error_msg}", "error")
        await events.publish(job_id, "progress", {"stage": "error", "percent": 0})
        
        await JobQueue.fail(job_id, error_msg)
        
        return {
            "status": "error",
            "error": error_msg,
            "message": f"Adaptive processing failed: {error_msg}"
        }


def extract_required_packages(code: str) -> List[str]:
    """
    Extract required packages from Python code.
    
    Parses import statements to identify needed packages.
    """
    import re
    
    packages = set()
    
    # Match: import package
    for match in re.finditer(r'^import\s+(\w+)', code, re.MULTILINE):
        packages.add(match.group(1))
    
    # Match: from package import ...
    for match in re.finditer(r'^from\s+(\w+)', code, re.MULTILINE):
        packages.add(match.group(1))
    
    # Filter out built-ins
    builtins = {'sys', 'os', 'json', 'time', 'datetime', 're', 'pathlib', 'typing', 'asyncio'}
    packages = packages - builtins
    
    return list(packages)


async def execute_agent_safely(
    agent_code: str,
    file_path: str,
    params: Dict[str, Any],
    job_id: str
) -> Dict[str, Any]:
    """
    Execute generated agent code safely.
    
    Args:
        agent_code: Python code to execute
        file_path: Path to dataset
        params: Processing parameters
        job_id: Job ID for logging
        
    Returns:
        Processing results
    """
    # Create execution namespace with required imports
    namespace = {
        "__builtins__": __builtins__,
        "pd": None,  # Will be imported in agent code
        "np": None,
        "events": events,
        "Dict": Dict,
        "Any": Any
    }
    
    try:
        # Execute agent code to define the function
        exec(agent_code, namespace)
        
        # Get the process_dataset function
        if "process_dataset" not in namespace:
            raise Exception("Generated agent missing 'process_dataset' function")
        
        process_func = namespace["process_dataset"]
        
        # Execute the function
        results = await process_func(file_path, params, job_id)
        
        return results
        
    except Exception as e:
        await events.log(job_id, f"❌ Agent execution error: {str(e)}", "error")
        raise Exception(f"Agent execution failed: {str(e)}")


if __name__ == "__main__":
    print("🤖 Adaptive Worker - Starting...")
    print("   Waiting for dataset processing tasks...")
    try:
        asyncio.run(process_adaptive_job())
    except KeyboardInterrupt:
        print("\n👋 Adaptive Worker stopped")
    except Exception as e:
        print(f"❌ Worker crashed: {e}")
        traceback.print_exc()
        raise
