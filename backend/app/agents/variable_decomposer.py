"""
Variable Decomposer - Break Down Topics into Measurable Variables

Takes broad research topics and decomposes them into specific,
measurable variables with clear indicators.
"""

import json
from typing import Dict, List, Any
from app.services.deepseek import deepseek_service


class VariableDecomposer:
    """
    Decompose broad research topics into specific measurable variables.
    
    Example:
        "Economic development" → 
        - Agricultural Production (yields, area, livestock)
        - Market Functioning (prices, trade routes)
        - Infrastructure (roads, water, schools)
        - Household Livelihoods (income, diversification)
    """
    
    def __init__(self):
        self.llm = deepseek_service
    
    async def decompose_topic(
        self,
        topic: str,
        case_study: str,
        context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Decompose topic into measurable variables.
        
        Args:
            topic: Research topic
            case_study: Case study context
            context: Context research findings
            
        Returns:
            List of variables with indicators and relevance
        """
        print(f"\n📊 VARIABLE DECOMPOSITION")
        print(f"   Analyzing topic: {topic}")
        
        prompt = self._build_decomposition_prompt(topic, case_study, context)
        
        response = await self.llm.generate_content(
            prompt=prompt,
            system_prompt="You are an expert research methodologist specializing in variable operationalization."
        )
        
        # Parse JSON response
        variables = self._parse_variables(response)
        
        print(f"   ✓ Identified {len(variables)} main variables")
        for var in variables:
            print(f"     • {var['name']}")
        print()
        
        return variables
    
    def _build_decomposition_prompt(
        self,
        topic: str,
        case_study: str,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for variable decomposition."""
        
        context_factors = "\n".join([f"- {f}" for f in context.get('context_factors', [])])
        
        return f"""
You are decomposing a research topic into specific, measurable variables.

**Topic:** "{topic}"
**Case Study:** "{case_study}"

**Context-Specific Factors:**
{context_factors}

**Your Task:**
Break down this topic into 5-7 main variables that should be studied.

For each variable, provide:
1. **Variable Name** (clear, specific)
2. **Measurement Indicators** (3-5 specific, quantifiable indicators)
3. **Relevance** (why this matters for this specific context)

**CRITICAL RULES:**

1. **Be Specific, Not Generic:**
   ❌ BAD: "Economic impact"
   ✅ GOOD: "Agricultural Production"

2. **Provide Measurable Indicators:**
   ❌ BAD: "productivity levels"
   ✅ GOOD: "crop yields (tons/hectare), cultivated area (hectares), livestock numbers"

3. **Context-Appropriate:**
   - Use context-specific factors above
   - Don't suggest variables that can't be measured in this context
   - Consider data availability

**Example Output Format (JSON):**
```json
[
  {{
    "name": "Agricultural Production",
    "indicators": [
      "Crop yields (tons/hectare)",
      "Cultivated area (hectares)",
      "Livestock numbers and losses",
      "Food production per capita",
      "Agricultural labor force size"
    ],
    "relevance": "Primary livelihood source in {case_study}; directly affected by conflict disruptions"
  }},
  {{
    "name": "Market Functioning",
    "indicators": [
      "Commodity prices (local vs regional)",
      "Trade volume (tons/month)",
      "Number of active markets",
      "Market accessibility (travel time/cost)",
      "Price volatility indices"
    ],
    "relevance": "Markets disrupted by blockades and isolation in {case_study}"
  }}
]
```

**Now decompose the topic above. Return ONLY valid JSON array.**
"""
    
    def _parse_variables(self, response: str) -> List[Dict[str, Any]]:
        """Parse variables from LLM response."""
        # Clean response
        clean_response = response.replace("```json", "").replace("```", "").strip()
        
        try:
            variables = json.loads(clean_response)
            
            # Validate structure
            if not isinstance(variables, list):
                raise ValueError("Response is not a list")
            
            for var in variables:
                if not all(k in var for k in ["name", "indicators", "relevance"]):
                    raise ValueError("Missing required keys in variable")
            
            return variables
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"   ⚠️  Failed to parse variables: {str(e)}")
            # Return fallback variables
            return self._fallback_variables()
    
    def _fallback_variables(self) -> List[Dict[str, Any]]:
        """Fallback variables if parsing fails."""
        return [
            {
                "name": "Primary Outcome Variable",
                "indicators": ["Specific metric 1", "Specific metric 2", "Specific metric 3"],
                "relevance": "Core variable for this research"
            },
            {
                "name": "Secondary Outcome Variable",
                "indicators": ["Specific metric 1", "Specific metric 2"],
                "relevance": "Supporting variable"
            }
        ]


# Singleton instance
variable_decomposer = VariableDecomposer()
