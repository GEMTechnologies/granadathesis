"""
Autonomous Agent Brain - Tool Creator

Dynamic code generation and tool creation.
The agent writes code for capabilities it doesn't have.
"""

from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import ast
import hashlib


@dataclass
class ToolSpec:
    """Specification for a new tool."""
    name: str
    purpose: str
    inputs: Dict[str, str]  # param_name: type
    outputs: str  # return type
    requirements: list[str]  # dependencies


@dataclass
class Tool:
    """A generated tool/function."""
    name: str
    code: str
    signature: str
    description: str
    tests: str
    workspace_id: str


class ToolCreator:
    """
    REAL POWER: Agent creates its own tools.
    
    Capabilities:
    - Generates Python functions from specs
    - Tests code in sandbox
    - Self-heals errors
    - Persists tools for reuse
    """
    
    def __init__(self, llm_service, sandbox_manager):
        self.llm = llm_service
        self.sandbox = sandbox_manager
    
    async def create_tool(
        self,
        tool_spec: ToolSpec,
        workspace_id: str,
        max_retries: int = 3
    ) -> Tool:
        """
        Generate, test, and deploy new tool.
        
        Process:
        1. Generate code from spec
        2. Test in sandbox
        3. Fix errors if any (self-healing)
        4. Deploy to workspace
        """
        
        # 1. Generate code
        code = await self._generate_code(tool_spec)
        
        # 2. Test in sandbox
        test_result = await self._test_code(code, workspace_id)
        
        # 3. Self-heal if needed
        retry_count = 0
        while not test_result['success'] and retry_count < max_retries:
            print(f"⚠️ Code failed, attempting self-heal (attempt {retry_count + 1}/{max_retries})")
            code = await self._fix_code(code, test_result['stderr'], tool_spec)
            test_result = await self._test_code(code, workspace_id)
            retry_count += 1
        
        if not test_result['success']:
            raise RuntimeError(f"Failed to create working tool after {max_retries} attempts: {test_result['stderr']}")
        
        # 4. Create Tool object
        tool = Tool(
            name=tool_spec.name,
            code=code,
            signature=self._generate_signature(tool_spec),
            description=tool_spec.purpose,
            tests=test_result.get('tests', ''),
            workspace_id=workspace_id
        )
        
        # 5. Persist tool
        await self._save_tool(tool)
        
        print(f"✅ Created tool: {tool.name}")
        
        return tool
    
    async def _generate_code(self, spec: ToolSpec) -> str:
        """Generate production-ready Python code."""
        
        inputs_str = ", ".join([f"{name}: {type_}" for name, type_ in spec.inputs.items()])
        
        code_prompt = f"""Generate a PRODUCTION-READY Python function with this specification:

FUNCTION NAME: {spec.name}
PURPOSE: {spec.purpose}
INPUTS: {inputs_str}
OUTPUT TYPE: {spec.outputs}
REQUIREMENTS: {', '.join(spec.requirements)}

Generate code with:
1. Type hints
2. Comprehensive docstring (Google style)
3. Input validation
4. Error handling (try/except)
5. Logging for debugging
6. Unit tests (pytest style)

Make it ROBUST and REUSABLE. Handle edge cases.

Format:
```python
def {spec.name}({inputs_str}) -> {spec.outputs}:
    \"\"\"
    [Docstring]
    
    Args:
        ...
    
    Returns:
        ...
    
    Raises:
        ...
    \"\"\"
    # Implementation
    pass


# Unit tests
def test_{spec.name}():
    # Test cases
    pass
```

ONLY return Python code, no explanation.
"""
        
        code = await self.llm.generate(
            prompt=code_prompt,
            temperature=0.2,  # Low temp for precise code
            max_tokens=1500
        )
        
        # Extract code from markdown if present
        if '```python' in code:
            code = code.split('```python')[1].split('```')[0]
        elif '```' in code:
            code = code.split('```')[1].split('```')[0]
        
        return code.strip()
    
    async def _test_code(self, code: str, workspace_id: str) -> Dict:
        """Test code in sandbox."""
        
        test_code = f"""
{code}

# Run tests
if __name__ == '__main__':
    import sys
    try:
        # Find and run test functions
        test_funcs = [name for name in dir() if name.startswith('test_')]
        for test_func in test_funcs:
            print(f"Running {{test_func}}...")
            eval(test_func + '()')
        print("✅ All tests passed")
    except Exception as e:
        print(f"❌ Test failed: {{e}}")
        sys.exit(1)
"""
        
        result = await self.sandbox.execute_code(
            workspace_id=workspace_id,
            code=test_code,
            language='python',
            timeout=10
        )
        
        return result
    
    async def _fix_code(
        self,
        broken_code: str,
        error: str,
        spec: ToolSpec
    ) -> str:
        """Self-healing: Fix code that failed tests."""
        
        fix_prompt = f"""This code has errors. Fix it.

ORIGINAL SPEC:
Name: {spec.name}
Purpose: {spec.purpose}

BROKEN CODE:
```python
{broken_code}
```

ERROR:
{error}

Analyze the error and fix the code. Return ONLY the corrected Python code.
"""
        
        fixed_code = await self.llm.generate(fix_prompt, temperature=0.3)
        
        # Extract code
        if '```python' in fixed_code:
            fixed_code = fixed_code.split('```python')[1].split('```')[0]
        elif '```' in fixed_code:
            fixed_code = fixed_code.split('```')[1].split('```')[0]
        
        return fixed_code.strip()
    
    def _generate_signature(self, spec: ToolSpec) -> str:
        """Generate function signature."""
        inputs_str = ", ".join([f"{name}: {type_}" for name, type_ in spec.inputs.items()])
        return f"def {spec.name}({inputs_str}) -> {spec.outputs}"
    
    async def _save_tool(self, tool: Tool):
        """Persist tool to workspace."""
        from config import get_tools_dir
        
        tools_dir = get_tools_dir(tool.workspace_id)
        tools_dir.mkdir(parents=True, exist_ok=True)
        
        tool_file = tools_dir / f"{tool.name}.py"
        tool_file.write_text(tool.code)
        
        # Also save metadata
        metadata_file = tools_dir / f"{tool.name}.json"
        import json
        metadata_file.write_text(json.dumps({
            "name": tool.name,
            "signature": tool.signature,
            "description": tool.description,
            "created_at": str(datetime.now())
        }, indent=2))
