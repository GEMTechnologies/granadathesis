"""
Self-Healing System

Detects issues, fixes code, and improves the system automatically.
"""
import ast
import importlib
import inspect
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import traceback
import subprocess

from services.deepseek_direct import deepseek_direct_service
from services.rag_system import rag_system
from core.events import events


class SelfHealingSystem:
    """System that can detect and fix issues automatically."""
    
    def __init__(self):
        self.code_base_path = Path(".")
        self.backup_path = Path("../../backups")
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    async def diagnose_issue(self, error: Exception, context: Dict) -> Dict:
        """
        Diagnose an issue and suggest fixes.
        
        Args:
            error: The exception that occurred
            context: Context (file, function, etc.)
            
        Returns:
            Diagnosis with suggested fix
        """
        error_msg = str(error)
        error_trace = traceback.format_exc()
        
        # Check RAG for similar errors
        similar_fixes = await rag_system.retrieve_similar(
            query=f"Error: {error_msg}",
            category="errors",
            top_k=3
        )
        
        # Build diagnosis prompt
        diagnosis_prompt = f"""Analyze this error and provide a fix:

Error: {error_msg}

Traceback:
{error_trace[:1000]}

Context:
{json.dumps(context, indent=2)}

{"Similar past fixes:" if similar_fixes else ""}
{json.dumps([{"problem": s["problem"], "solution": s["solution"]} for s in similar_fixes], indent=2) if similar_fixes else ""}

Provide:
1. Root cause analysis
2. Specific fix (code if applicable)
3. Prevention strategy

Return JSON:
{{
    "root_cause": "...",
    "fix": "...",
    "code_fix": "..." (if code needs fixing),
    "prevention": "..."
}}
"""
        
        try:
            response = await deepseek_direct_service.generate_content(
                prompt=diagnosis_prompt,
                system_prompt="You are a code debugging expert. Return only valid JSON.",
                temperature=0.2,
                max_tokens=2000,
                use_reasoning=True  # Use reasoning for complex debugging
            )
            
            # Parse JSON from response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                diagnosis = json.loads(json_match.group())
                return diagnosis
        except Exception as e:
            print(f"⚠️ Diagnosis error: {e}")
        
        # Fallback diagnosis
        return {
            "root_cause": f"Error: {error_msg}",
            "fix": "Manual review required",
            "code_fix": None,
            "prevention": "Add error handling"
        }
    
    async def fix_code(
        self,
        file_path: str,
        issue_description: str,
        error: Optional[Exception] = None
    ) -> Dict:
        """
        Automatically fix code in a file.
        
        Args:
            file_path: Path to file to fix
            issue_description: Description of the issue
            error: Optional exception that occurred
            
        Returns:
            Fix result
        """
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        
        # Backup original
        backup_file = self.backup_path / f"{file_path_obj.name}.{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        original_code = file_path_obj.read_text(encoding='utf-8')
        backup_file.write_text(original_code, encoding='utf-8')
        
        print(f"💾 Backed up {file_path} to {backup_file}")
        
        # Check RAG for similar fixes
        similar_fixes = await rag_system.retrieve_similar(
            query=issue_description,
            category="code_fixes",
            top_k=3
        )
        
        # Build fix prompt
        fix_prompt = f"""Fix this Python code issue:

File: {file_path}
Issue: {issue_description}

Current Code:
```python
{original_code[:3000]}  # First 3000 chars
```

{"Similar past fixes:" if similar_fixes else ""}
{json.dumps([s["solution"] for s in similar_fixes], indent=2) if similar_fixes else ""}

{"Error:" if error else ""}
{str(error)[:500] if error else ""}

Provide the COMPLETE fixed code. Return only the Python code, no explanations.
"""
        
        try:
            fixed_code = await deepseek_direct_service.generate_content(
                prompt=fix_prompt,
                system_prompt="You are a Python code fixer. Return only the fixed Python code, no markdown, no explanations.",
                temperature=0.1,
                max_tokens=4000,
                use_reasoning=True
            )
            
            # Clean up response (remove markdown if present)
            import re
            code_match = re.search(r'```python\n([\s\S]*?)\n```', fixed_code)
            if code_match:
                fixed_code = code_match.group(1)
            else:
                # Try without language tag
                code_match = re.search(r'```\n([\s\S]*?)\n```', fixed_code)
                if code_match:
                    fixed_code = code_match.group(1)
            
            # Validate Python syntax
            try:
                ast.parse(fixed_code)
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"Generated code has syntax errors: {e}",
                    "backup": str(backup_file)
                }
            
            # Write fixed code
            file_path_obj.write_text(fixed_code, encoding='utf-8')
            
            # Store fix in RAG
            await rag_system.store_solution(
                problem=f"{file_path}: {issue_description}",
                solution=fixed_code,
                context={"original": original_code[:500], "error": str(error) if error else None},
                category="code_fixes"
            )
            
            print(f"✅ Fixed {file_path}")
            
            return {
                "success": True,
                "file": file_path,
                "backup": str(backup_file),
                "message": "Code fixed successfully"
            }
            
        except Exception as e:
            # Restore backup on failure
            file_path_obj.write_text(original_code, encoding='utf-8')
            
            return {
                "success": False,
                "error": f"Fix failed: {str(e)}",
                "backup": str(backup_file),
                "restored": True
            }
    
    async def check_agent_health(self, agent_name: str) -> Dict:
        """
        Check health of an agent.
        
        Args:
            agent_name: Name of agent to check
            
        Returns:
            Health status
        """
        health = {
            "agent": agent_name,
            "status": "unknown",
            "issues": [],
            "suggestions": []
        }
        
        try:
            # Try to import agent
            try:
                module = importlib.import_module(f"agents.{agent_name}")
                health["status"] = "imported"
            except ImportError as e:
                health["status"] = "missing"
                health["issues"].append(f"Import error: {str(e)}")
                health["suggestions"].append("Generate missing agent")
                return health
            
            # Check if agent class exists
            agent_class = None
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and name.lower().endswith("agent"):
                    agent_class = obj
                    break
            
            if not agent_class:
                health["status"] = "incomplete"
                health["issues"].append("Agent class not found")
                health["suggestions"].append("Add agent class")
                return health
            
            # Check required methods
            required_methods = ["generate", "execute", "process"]
            missing_methods = []
            for method in required_methods:
                if not hasattr(agent_class, method):
                    missing_methods.append(method)
            
            if missing_methods:
                health["status"] = "incomplete"
                health["issues"].append(f"Missing methods: {', '.join(missing_methods)}")
                health["suggestions"].append(f"Add methods: {', '.join(missing_methods)}")
            else:
                health["status"] = "healthy"
            
            return health
            
        except Exception as e:
            health["status"] = "error"
            health["issues"].append(f"Health check error: {str(e)}")
            return health
    
    async def generate_missing_agent(
        self,
        agent_name: str,
        purpose: str,
        requirements: Optional[List[str]] = None
    ) -> Dict:
        """
        Generate a missing agent automatically.
        
        Args:
            agent_name: Name of agent to generate
            purpose: What the agent should do
            requirements: List of requirements
            
        Returns:
            Generation result
        """
        agents_dir = Path("agents")
        agents_dir.mkdir(exist_ok=True)
        
        agent_file = agents_dir / f"{agent_name}.py"
        
        if agent_file.exists():
            return {
                "success": False,
                "error": f"Agent {agent_name} already exists"
            }
        
        # Check RAG for similar agents
        similar_agents = await rag_system.retrieve_similar(
            query=f"Agent: {purpose}",
            category="agents",
            top_k=2
        )
        
        # Build generation prompt
        generation_prompt = f"""Generate a Python agent class for:

Name: {agent_name}
Purpose: {purpose}
Requirements: {requirements or ['Standard agent functionality']}

{"Similar agents:" if similar_agents else ""}
{json.dumps([s["solution"][:1000] for s in similar_agents], indent=2) if similar_agents else ""}

Create a complete Python file with:
1. Imports
2. Agent class with __init__, generate/execute method
3. Error handling
4. Type hints
5. Docstrings

Return only the Python code, no markdown.
"""
        
        try:
            agent_code = await deepseek_direct_service.generate_content(
                prompt=generation_prompt,
                system_prompt="You are a Python agent generator. Return only valid Python code, no markdown.",
                temperature=0.3,
                max_tokens=3000,
                use_reasoning=True
            )
            
            # Clean up response
            import re
            code_match = re.search(r'```python\n([\s\S]*?)\n```', agent_code)
            if code_match:
                agent_code = code_match.group(1)
            else:
                code_match = re.search(r'```\n([\s\S]*?)\n```', agent_code)
                if code_match:
                    agent_code = code_match.group(1)
            
            # Validate syntax
            try:
                ast.parse(agent_code)
            except SyntaxError as e:
                return {
                    "success": False,
                    "error": f"Generated code has syntax errors: {e}"
                }
            
            # Write agent file
            agent_file.write_text(agent_code, encoding='utf-8')
            
            # Store in RAG
            await rag_system.store_solution(
                problem=f"Generate agent: {agent_name} for {purpose}",
                solution=agent_code,
                context={"requirements": requirements},
                category="agents"
            )
            
            print(f"✅ Generated agent: {agent_name}")
            
            return {
                "success": True,
                "file": str(agent_file),
                "message": f"Agent {agent_name} generated successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Generation failed: {str(e)}"
            }


# Global instance
self_healing_system = SelfHealingSystem()

