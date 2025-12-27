"""
Objective Ranker - Central Judge for Multi-Model Competition

This is the meta-judge that evaluates all model submissions,
analyzes cross-critiques, and selects the winner with detailed reasoning.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
from app.services.openrouter import openrouter_service


class ObjectiveRanker:
    """
    Central judge that scores objective submissions from multiple models.
    
    Evaluates based on:
    - Objective quality (SMART, PhD-level, no methodology creep)
    - Resilience to criticism
    - Quality of critiques given to others
    """
    
    def __init__(self):
        self.llm = openrouter_service
        # Use Claude as the meta-judge (best at nuanced evaluation)
        self.judge_model = "claude"
    
    async def rank_submissions(
        self,
        topic: str,
        case_study: str,
        submissions: Dict[str, List[str]],
        critiques: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Rank all objective submissions and select winner.
        
        Args:
            topic: Research topic
            case_study: Case study
            submissions: Dict mapping model_key -> objectives list
            critiques: Dict mapping critic_model -> {target_model -> critique}
            
        Returns:
            Ranking results with detailed reasoning
        """
        from app.agents.academic_rigor_validator import academic_rigor_validator
        
        print(f"\n🏆 CENTRAL RANKER: Evaluating {len(submissions)} submissions...")
        
        # Phase 1: Validate all submissions for academic rigor
        print("   📋 Phase 1: Academic Rigor Validation")
        validation_results = {}
        for model_key, objectives in submissions.items():
            validation = academic_rigor_validator.validate_objectives(
                objectives=objectives,
                case_study=case_study,
                topic=topic
            )
            validation_results[model_key] = validation
            
            # Print validation summary
            print(f"      {model_key.upper()}: Rigor Score = {validation['total_score']:.0f}/100")
            if validation['issues']:
                print(f"         Issues: {len(validation['issues'])} (brevity: {sum(1 for i in validation['issues'] if i['type']=='VERBOSITY')}, methodology: {sum(1 for i in validation['issues'] if i['type']=='METHODOLOGY_CREEP')})")
        
        # Phase 2: Build comprehensive evaluation prompt with validation results
        print("   🎯 Phase 2: Meta-Judge Evaluation")
        prompt = self._build_ranking_prompt_enhanced(
            topic, case_study, submissions, critiques, validation_results
        )
        
        # Get ranking from meta-judge
        response = await self.llm.generate_content(
            prompt=prompt,
            model_key=self.judge_model,
            system_prompt="You are an expert PhD thesis examiner and meta-judge evaluating objective quality.",
            temperature=0.3  # Lower temperature for more consistent judging
        )
        
        # Parse ranking result
        ranking_result = self._parse_json(response)
        
        # Add validation results to ranking
        ranking_result["validation_results"] = validation_results
        
        # Add metadata
        ranking_result["judged_by"] = self.llm.MODELS[self.judge_model]["name"]
        ranking_result["judged_at"] = datetime.now().isoformat()
        
        
        print(f"   ✓ Winner: {ranking_result['winner']['model']} (Score: {ranking_result['winner']['score']})")
        
        return ranking_result
    
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
        
        return f"""
You are the META-JUDGE for a PhD thesis objective generation competition.

**RESEARCH CONTEXT:**
Topic: "{topic}"
Case Study: "{case_study}"

**COMPETING SUBMISSIONS (with Academic Rigor Validation):**
{submissions_text}

**CROSS-CRITIQUES:**
{critiques_text}

**YOUR TASK:**
Evaluate all submissions using the NEW SCORING CRITERIA:

1. **Brevity & Clarity (30 points)** - HEAVILY WEIGHTED
   - Each objective should be 15-25 words
   - PENALIZE HEAVILY for verbose objectives (>25 words): -5 to -10 points each

2. **No Methodology Creep (40 points)** - MOST CRITICAL
   - NO embedded metrics (GDP, percentages, ratios)
   - NO statistical terms (p<0.05, n=100)
   - PENALIZE HEAVILY for methodology details: -10 to -15 points each

3. **Context Appropriateness (20 points)**
   - Matches actual case study conditions
   - Don't assume conflict if not conflict-affected

4. **Coherence (10 points)**
   - Logical flow, no overlap

**OUTPUT FORMAT (JSON):**
{{
    "winner": {{
        "model": "model_key",
        "score": 0-100,
        "objectives": ["list"],
        "why_it_won": ["reason 1", "reason 2", "reason 3"]
    }},
    "rankings": [
        {{
            "model": "model_key",
            "rank": 1,
            "score": 0-100,
            "strengths": ["strength 1"],
            "weaknesses": ["weakness 1"],
            "brevity_score": 0-30,
            "methodology_score": 0-40,
            "context_score": 0-20,
            "coherence_score": 0-10
        }}
    ],
    "detailed_reasoning": "Explanation...",
    "lessons_learned": ["lesson 1", "lesson 2"]
}}

Be STRICT. Penalize verbosity and methodology creep HEAVILY.
"""
    
    def _build_ranking_prompt(
        self,
        topic: str,
        case_study: str,
        submissions: Dict[str, List[str]],
        critiques: Dict[str, Dict[str, str]]
    ) -> str:
        """Build comprehensive ranking prompt for meta-judge."""
        
        # Format submissions
        submissions_text = "\n\n".join([
            f"**{model.upper()} SUBMISSION:**\n" + "\n".join([f"{i+1}. {obj}" for i, obj in enumerate(objs)])
            for model, objs in submissions.items()
        ])
        
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

**COMPETING SUBMISSIONS:**
{submissions_text}

**CROSS-CRITIQUES:**
{critiques_text}

**YOUR TASK:**
Evaluate all submissions and rank them. Consider:

1. **Objective Quality (40 points)**
   - SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
   - Clear WHAT vs HOW distinction (no methodology details)
   - PhD-level rigor without jargon
   - Clarity and directness

2. **Resilience to Criticism (30 points)**
   - How well did objectives hold up to peer critique?
   - Were criticisms valid or nitpicky?
   - Did objectives have fundamental flaws?

3. **Critique Quality Given (20 points)**
   - Did this model provide insightful critiques of others?
   - Were critiques constructive and specific?
   - Did they catch real issues?

4. **Overall Excellence (10 points)**
   - Innovation, elegance, potential impact

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
            "quality_score": 0-40,
            "resilience_score": 0-30,
            "critique_score": 0-20,
            "excellence_score": 0-10
        }},
        ...
    ],
    "detailed_reasoning": "Multi-paragraph explanation of your decision process...",
    "critique_analysis": {{
        "model1": {{
            "received": ["summary of critiques received"],
            "gave": ["summary of critiques given"],
            "critique_quality": "excellent/good/fair/poor"
        }},
        ...
    }},
    "lessons_learned": [
        "Key lesson 1 about what makes great objectives",
        "Key lesson 2 about common pitfalls",
        "Key lesson 3 for future improvements"
    ],
    "close_call": "If rankings were close, explain why. Otherwise null."
}}

Be RIGOROUS and FAIR. Provide specific examples in your reasoning.
"""
        return prompt
    
    def _parse_json(self, response: str) -> Dict[str, Any]:
        """Parse JSON from LLM response."""
        clean_response = response.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_response)
        except json.JSONDecodeError as e:
            # If parsing fails, return error structure
            return {
                "error": "Failed to parse ranking",
                "raw_response": response,
                "parse_error": str(e)
            }


# Singleton instance
objective_ranker = ObjectiveRanker()
