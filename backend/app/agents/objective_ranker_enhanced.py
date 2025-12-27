    
    def _build_ranking_prompt_enhanced(
        self,
        topic: str,
        case_study: str,
        submissions: Dict[str, List[str]],
        critiques: Dict[str, Dict[str, str]],
        validation_results: Dict[str, Dict[str, Any]]
    ) -> str:
        """Build enhanced ranking prompt with validation results."""
        
        # Format submissions with validation scores
        submissions_text = ""
        for model, objs in submissions.items():
            validation = validation_results[model]
            submissions_text += f"\n**{model.upper()} SUBMISSION (Rigor Score: {validation['total_score']:.0f}/100):**\n"
            submissions_text += "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objs)])
            
            # Add validation issues
            if validation['issues']:
                submissions_text += f"\n\n⚠️ **Validation Issues:**\n"
                for issue in validation['issues'][:3]:  # Show top 3 issues
                    submissions_text += f"- {issue['message']}\n"
            submissions_text += "\n"
        
        # Format critiques
        critiques_text = ""
        for critic, targets in critiques.items():
            critiques_text += f"\n**{critic.upper()}'S CRITIQUES:**\n"
            for target, critique in targets.items():
                critiques_text += f"\nOf {target}: {critique[:300]}...\n"
        
        prompt = f"""
You are the META-JUDGE for a PhD thesis objective generation competition.

**RESEARCH CONTEXT:**
Topic: "{topic}"
Case Study: "{case_study}"

**COMPETING SUBMISSIONS (with Academic Rigor Validation):**
{submissions_text}

**CROSS-CRITIQUES:**
{critiques_text}

**YOUR TASK:**
Evaluate all submissions and rank them. Use the NEW SCORING CRITERIA:

**NEW SCORING CRITERIA (100 points total):**

1. **Brevity & Clarity (30 points)** - HEAVILY WEIGHTED
   - Each objective should be 15-25 words
   - Short, sharp, directional statements
   - PENALIZE HEAVILY for verbose objectives (>25 words)
   - Reward conciseness and clarity

2. **No Methodology Creep (40 points)** - MOST CRITICAL
   - Objectives state WHAT, not HOW
   - NO embedded metrics (GDP per capita, percentages, ratios)
   - NO statistical terms (p<0.05, n=100, r=0.85)
   - NO measurement techniques (using surveys, through regression)
   - PENALIZE HEAVILY for any methodology details in objectives

3. **Context Appropriateness (20 points)**
   - Matches actual case study conditions
   - Don't assume conflict if not conflict-affected
   - Uses realistic variables for the context

4. **Resilience & Coherence (10 points)**
   - How well objectives hold up to critique
   - Logical flow between objectives
   - No overlap or redundancy

**CRITICAL RULES:**
- A verbose objective (>25 words) should LOSE 5-10 points
- An objective with embedded metrics should LOSE 10-15 points
- Context mismatches should LOSE 5-10 points
- Clarity and discipline are MORE IMPORTANT than coverage

**GOLD STANDARD REFERENCE:**
Good objectives are 15-25 words, have NO metrics embedded, state WHAT not HOW, and are context-appropriate.

Example GOOD objective (18 words):
"To analyze trends in mobile phone prices in Uganda from 2010–2023 and their implications for household affordability."

Example BAD objective (too verbose, methodology creep):
"To quantify the affordability barriers by analyzing household income-to-device-price ratios, examining GDP per capita correlation with smartphone penetration rates (r>0.7, p<0.05)..."

**OUTPUT FORMAT (JSON):**
{{
    "winner": {{
        "model": "model_key",
        "score": 0-100,
        "objectives": ["list of winning objectives"],
        "why_it_won": [
            "Specific reason 1",
            "Specific reason 2",
            "Specific reason 3"
        ]
    }},
    "rankings": [
        {{
            "model": "model_key",
            "rank": 1,
            "score": 0-100,
            "strengths": ["strength 1", "strength 2"],
            "weaknesses": ["weakness 1", "weakness 2"],
            "brevity_score": 0-30,
            "methodology_score": 0-40,
            "context_score": 0-20,
            "coherence_score": 0-10
        }},
        ...
    ],
    "detailed_reasoning": "Multi-paragraph explanation focusing on brevity, methodology creep, and context appropriateness...",
    "lessons_learned": [
        "Key lesson about brevity and clarity",
        "Key lesson about avoiding methodology creep",
        "Key lesson about context appropriateness"
    ]
}}

Be RIGOROUS and STRICT. Penalize verbosity and methodology creep HEAVILY.
"""
        return prompt
