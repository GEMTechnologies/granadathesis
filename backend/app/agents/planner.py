import json
from typing import List, Dict, Any, Any
from app.services.deepseek import deepseek_service
from app.models.thesis import ThesisCreate

class PlannerAgent:
    def __init__(self):
        self.llm = deepseek_service

    async def generate_objectives(self, topic: str, case_study: str) -> Dict[str, Any]:
        # 1. Initial Draft
        print(f"\n   📝 Phase 1: Drafting initial objectives for '{topic}'...")
        draft_prompt = f"""
        You are an expert academic research consultant for a PhD thesis at the University of Juba.
        
        Topic: "{topic}"
        Case Study: "{case_study}"
        
        Generate 1 General Objective and 3-4 Specific Objectives.
        
        CRITICAL RULES:
        1. Objectives state WHAT you will study, NOT HOW you will study it.
        2. NO methodology details: no "n=", no "p<0.05", no "using surveys", no "regression analysis".
        3. NO jargon: avoid "integrated explanatory model", "contextualize", "holistic understanding".
        4. Use simple, direct verbs: "examine", "assess", "explore", "identify", "develop".
        5. Be specific about WHAT you're measuring/exploring, not the TOOL.
        
        BAD EXAMPLE (too methodological):
        "To employ qualitative findings to contextualize quantitative relationships between X and Y"
        
        GOOD EXAMPLE (clear goal):
        "To explore the relationship between X and Y"
        
        Return ONLY a JSON array of strings.
        """
        
        draft_response = await self.llm.generate_content(draft_prompt)
        draft_objectives = self._parse_json(draft_response)
        print("   ... Draft complete.")
        
        # 2. Critical Review (The "Reviewer 1, 2, 3" Step)
        print("\n   🕵️  Phase 2: Review Board is critiquing (Methodologist, Skeptic, Pedant)...")
        critique = await self.review_objectives(topic, case_study, draft_objectives)
        print("   ... Critique received.")
        
        # 3. Refinement based on Critique
        print("\n   ✨ Phase 3: Refining objectives based on feedback...")
        final_objectives = await self.refine_objectives(topic, case_study, draft_objectives, critique)
        print("   ... Refinement complete!")
        
        return {
            "initial": draft_objectives,
            "critique": critique,
            "final": final_objectives
        }

    async def review_objectives(self, topic: str, case_study: str, objectives: List[str]) -> str:
        prompt = f"""
        You are a panel of 3 strict PhD Reviewers at a top university.
        
        Topic: "{topic}"
        Case Study: "{case_study}"
        Proposed Objectives: {json.dumps(objectives, indent=2)}
        
        CRITICIZE these objectives mercilessly:
        
        Reviewer 1 (Methodologist): 
        - Are they ACHIEVABLE in this case study context?
        - Do they describe WHAT to study (good) or HOW to study it (bad)?
        - Flag any methodology creep: "integrated model", "contextualize", "employ", "utilize".
        
        Reviewer 2 (The Skeptic): 
        - So What? Why does this matter?
        - Is the topic clearly defined or vague?
        - Is this PhD-level or undergraduate-level?
        
        Reviewer 3 (The Pedant): 
        - Is the language clear and direct?
        - Any jargon, verbosity, or redundancy?
        - Are there any n-values, p-values, or method names?
        
        Output: A consolidated critique (be harsh but constructive).
        """
        return await self.llm.generate_content(prompt)

    async def refine_objectives(self, topic: str, case_study: str, draft: List[str], critique: str) -> List[str]:
        prompt = f"""
        You are the PhD Candidate revising your objectives based on review feedback.
        
        Topic: "{topic}"
        Case Study: "{case_study}"
        Draft Objectives: {json.dumps(draft, indent=2)}
        
        Review Board Critique:
        {critique}
        
        REWRITE the objectives to address ALL concerns:
        
        RULES:
        1. Keep it SIMPLE and CLEAR.
        2. Remove ALL methodology language: no "employ", "utilize", "contextualize", "integrated model".
        3. Remove ALL statistical/method references: no "n=", "p<", "regression", "surveys".
        4. Use direct verbs: "examine", "assess", "explore", "identify", "develop".
        5. Focus on WHAT you will study, not HOW.
        
        EXAMPLE TRANSFORMATION:
        BAD: "To employ qualitative findings to contextualize quantitative relationships between romantic involvement and academic performance"
        GOOD: "To explore the relationship between romantic relationships and academic performance"
        
        Return ONLY the final JSON array of strings (1 General + 3-4 Specific).
        """
        response = await self.llm.generate_content(prompt)
        return self._parse_json(response)

    def _parse_json(self, response: str) -> List[str]:
        clean_response = response.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_response)
        except json.JSONDecodeError:
            return [line.strip() for line in clean_response.split('\n') if line.strip()]

planner_agent = PlannerAgent()
