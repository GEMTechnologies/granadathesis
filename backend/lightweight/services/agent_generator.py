"""
Agent Generator Service

Generates custom Python agents using LLM based on dataset analysis.
Creates processing logic tailored to specific dataset characteristics.
"""
from typing import Dict, Any, Optional
import json
import re
from services.deepseek_direct import deepseek_direct_service


class AgentGenerator:
    """Generate custom agents using LLM."""
    
    def __init__(self):
        self.agent_template = """
async def process_dataset(file_path: str, params: Dict, job_id: str) -> Dict[str, Any]:
    \"\"\"
    Custom generated agent for dataset processing.
    
    Args:
        file_path: Path to dataset file
        params: Processing parameters
        job_id: Job ID for logging
        
    Returns:
        Processing results as dictionary
    \"\"\"
    import pandas as pd
    import numpy as np
    from core.events import events
    
    # Generated processing logic will be inserted here
    {processing_logic}
"""
    
    async def generate_agent(
        self,
        dataset_analysis: Dict[str, Any],
        task_description: str,
        job_id: Optional[str] = None
    ) -> str:
        """
        Generate Python agent code using LLM.
        
        Args:
            dataset_analysis: Analysis from DatasetAnalyzer
            task_description: What the user wants to do
            job_id: Optional job ID for logging
            
        Returns:
            Python code for custom agent
        """
        if job_id:
            from core.events import events
            await events.log(job_id, "🤖 Generating custom agent code...")
        
        # Build comprehensive prompt
        prompt = self._build_generation_prompt(dataset_analysis, task_description)
        
        # Generate code using LLM
        code = await deepseek_direct_service.generate_content(
            prompt=prompt,
            system_prompt=self._get_system_prompt(),
            temperature=0.2,  # Low temperature for consistent code
            max_tokens=3000,
            use_reasoning=False
        )
        
        # Clean and validate code
        code = self._clean_generated_code(code)
        
        if job_id:
            await events.log(job_id, f"✅ Agent code generated ({len(code)} chars)")
        
        return code
    
    def _build_generation_prompt(
        self,
        analysis: Dict[str, Any],
        task: str
    ) -> str:
        """Build detailed prompt for LLM."""
        
        # Extract key information
        schema = analysis.get("schema", {})
        stats = analysis.get("statistics", {})
        patterns = analysis.get("patterns", [])
        suggestions = analysis.get("suggested_operations", [])
        
        prompt = f"""Generate a Python function to process this dataset.

## Dataset Information

**File**: {analysis.get('file_info', {}).get('filename', 'unknown')}
**Format**: {analysis.get('file_info', {}).get('format', 'unknown')}
**Rows**: {schema.get('rows', 0):,}
**Columns**: {schema.get('columns', 0)}

## Schema
{json.dumps(schema.get('dtypes', {}), indent=2)}

## Detected Patterns
{json.dumps(patterns, indent=2)}

## Task Description
{task}

## Requirements

1. Function signature MUST be:
```python
async def process_dataset(file_path: str, params: Dict, job_id: str) -> Dict[str, Any]:
```

2. Import required libraries at function start:
```python
import pandas as pd
import numpy as np
from core.events import events
```

3. Load dataset based on file extension
4. Add progress logging using: `await events.log(job_id, "message")`
5. Implement the task logic
6. Return results as JSON-serializable dictionary

## Output Format

Return ONLY the complete function code. Include:
- Data loading
- Processing logic
- Error handling (try/except)
- Progress logging
- Results dictionary

Generate clean, production-ready code."""

        return prompt
    
    def _get_system_prompt(self) -> str:
        """System prompt for code generation."""
        return """You are an expert Python data engineer and code generator.

Your task is to generate clean, efficient, production-ready Python code for data processing.

Guidelines:
1. Write async functions using pandas for data manipulation
2. Include comprehensive error handling
3. Add progress logging at key steps
4. Return structured results as dictionaries
5. Use type hints
6. Follow Python best practices (PEP 8)
7. Keep code concise but readable
8. No explanatory comments - code should be self-documenting
9. Use meaningful variable names

Generate ONLY executable Python code, no markdown formatting or explanations."""
    
    def _clean_generated_code(self, code: str) -> str:
        """Clean and format generated code."""
        # Remove markdown code blocks if present
        code = re.sub(r'```python\n?', '', code)
        code = re.sub(r'```\n?', '', code)
        
        # Remove leading/trailing whitespace
        code = code.strip()
        
        # Ensure proper indentation
        lines = code.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip empty lines at start
            if not cleaned_lines and not line.strip():
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def generate_simple_analyzer(
        self,
        dataset_analysis: Dict[str, Any]
    ) -> str:
        """Generate a simple statistical analyzer as fallback."""
        
        schema = dataset_analysis.get("schema", {})
        numeric_cols = [
            col for col, dtype in schema.get("dtypes", {}).items()
            if "int" in dtype or "float" in dtype
        ]
        categorical_cols = [
            col for col, dtype in schema.get("dtypes", {}).items()
            if "object" in dtype
        ]
        
        code = """async def process_dataset(file_path: str, params: Dict, job_id: str) -> Dict[str, Any]:
    \"\"\"Simple statistical analyzer.\"\"\"
    import pandas as pd
    import numpy as np
    from core.events import events
    
    try:
        await events.log(job_id, "📊 Loading dataset...")
        
        # Load dataset
        ext = file_path.split('.')[-1].lower()
        if ext in ['xlsx', 'xls']:
            df = pd.read_excel(file_path)
        elif ext == 'csv':
            df = pd.read_csv(file_path)
        elif ext == 'json':
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported format: {ext}")
        
        await events.log(job_id, f"✓ Loaded {len(df):,} rows")
        
        results = {
            "summary": {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns)
            },
            "numeric_analysis": {},
            "categorical_analysis": {}
        }
        
        await events.log(job_id, "📈 Analyzing numeric columns...")
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            results["numeric_analysis"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            }
        
        await events.log(job_id, "📊 Analyzing categorical columns...")
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            value_counts = df[col].value_counts().head(10)
            results["categorical_analysis"][col] = {
                "unique_count": int(df[col].nunique()),
                "top_values": value_counts.to_dict()
            }
        
        await events.log(job_id, "✅ Analysis complete!")
        return results
        
    except Exception as e:
        await events.log(job_id, f"❌ Error: {str(e)}", "error")
        return {"error": str(e)}
"""
        return code


# Global instance
agent_generator = AgentGenerator()
