"""
Objective Agent - The Heart of the Thesis System

This agent is the central authority for all objective-related operations:
1. Generates objectives with multi-stage review and criticism
2. Validates objectives against PhD standards
3. Monitors thesis content for alignment with objectives
4. Detects deviations and ensures logical coherence
5. Warns other agents about inconsistencies
6. Triggers replanning when necessary

The objectives are the foundation of the entire thesis - this agent ensures
they remain central throughout the research and writing process.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

from services.openrouter import openrouter_service
from models.thesis import ThesisCreate
from core.events import events


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues"""
    MINOR = "minor"
    MODERATE = "moderate"
    CRITICAL = "critical"


class ObjectiveAgent:
    """
    The Objective Agent - Central authority for thesis objectives.
    
    This agent ensures that objectives are:
    - PhD-standard and SMART
    - Free from methodological creep
    - Aligned with the research topic
    - Consistently followed throughout the thesis
    """
    
    def __init__(self):
        self.llm = openrouter_service
        self.validation_history: List[Dict] = []
        self.warnings: List[Dict] = []
    
    async def _generate(self, prompt: str, temperature: float = 0.7) -> str:
        """Helper to call LLM with default model."""
        return await self.llm.generate_content(
            prompt=prompt,
            model_key="deepseek",
            temperature=temperature
        )
    
    # ============================================================================
    # OBJECTIVE GENERATION (Multi-Stage with Criticism)
    # ============================================================================
    
    async def generate_objectives(
        self, 
        topic: str, 
        case_study: str,
        methodology: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate objectives through a rigorous multi-stage process.
        
        Process:
        1. Draft initial objectives
        2. Subject them to harsh academic criticism
        3. Refine based on critique
        4. Validate the final objectives
        
        Args:
            topic: Research topic
            case_study: Case study context
            methodology: Optional methodology preference (Quantitative/Qualitative/Mixed)
            
        Returns:
            Dict containing initial draft, critique, final objectives, and validation
        """
        print(f"\n🎯 OBJECTIVE AGENT: Starting objective generation for '{topic}'")
        
        # Phase 1: Draft
        print("   📝 Phase 1: Drafting initial objectives...")
        draft_objectives = await self._draft_objectives(topic, case_study, methodology)
        print(f"   ✓ Generated {len(draft_objectives)} draft objectives")
        
        # Phase 2: Criticism
        print("   🔍 Phase 2: Subjecting to academic review board...")
        critique = await self._criticize_objectives(topic, case_study, draft_objectives, methodology)
        print("   ✓ Critique complete")
        
        # Phase 3: Refinement
        print("   ✨ Phase 3: Refinement based on critique...")
        final_objectives = await self._refine_objectives(
            topic, case_study, draft_objectives, critique, methodology
        )
        print(f"   ✓ Refined to {len(final_objectives)} final objectives")
        
        # Phase 4: Validation
        print("   ✅ Phase 4: Validating final objectives...")
        validation = await self.validate_objectives(final_objectives, topic, case_study)
        print(f"   ✓ Validation complete (Valid: {validation['is_valid']})")
        
        return {
            "initial": draft_objectives,
            "critique": critique,
            "final": final_objectives,
            "validation": validation,
            "generated_at": datetime.now().isoformat()
        }
    
    async def generate_single_thought(
        self,
        role: str,
        topic: str,
        case_study: str
    ) -> str:
        """Generate a single thought for a specific role."""
        role_desc = {
            "Methodologist": "Focus on feasibility, measurability, and SMART criteria.",
            "Skeptic": "Focus on significance, 'so what?', and scope creep.",
            "Pedant": "Focus on precision, clarity, and avoiding jargon."
        }
        
        prompt = f"""
You are the {role} on an academic review board.
Topic: "{topic}"
Case Study: "{case_study}"

{role_desc.get(role, "")}

Generate a brief (1-2 sentence) initial thought/critique.
Return ONLY the text of the thought.
"""
        return await self._generate(prompt, temperature=0.8)

    async def generate_initial_thoughts(
        self,
        topic: str,
        case_study: str
    ) -> Dict[str, str]:
        """
        Generate initial thoughts/perspectives from the academic committee.
        
        This provides immediate, relevant feedback to the user before the full
        voting process begins.
        """
        prompt = f"""
You are simulating a pre-meeting discussion between three academic reviewers regarding a new PhD thesis proposal.

Topic: "{topic}"
Case Study: "{case_study}"

Generate a brief (1-2 sentence) initial thought from each reviewer's perspective:

1. Methodologist: Focuses on feasibility and measurability.
2. Skeptic: Focuses on the "so what?", significance, and scope.
3. Pedant: Focuses on precision, clarity, and avoiding jargon.

Return ONLY a JSON object:
{{
    "Methodologist": "...",
    "Skeptic": "...",
    "Pedant": "..."
}}
"""
        response = await self._generate(prompt, temperature=0.8)
        return self._parse_json(response)

    async def _draft_objectives(
        self, 
        topic: str, 
        case_study: str,
        methodology: Optional[str] = None
    ) -> List[str]:
        """Draft initial objectives."""
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology Preference: {methodology}"
        
        prompt = f"""
You are an expert academic research consultant for PhD thesis development at the University of Juba.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Generate 1 General Objective and 3-4 Specific Objectives.

CRITICAL RULES - OBJECTIVES STATE WHAT, NOT HOW:
1. Objectives describe WHAT you will study, NOT HOW you will study it
2. NO methodology details: no "n=", no "p<0.05", no "using surveys", no "regression analysis"
3. NO jargon: avoid "integrated explanatory model", "contextualize", "holistic understanding"
4. Use simple, direct verbs: "examine", "assess", "explore", "identify", "develop", "analyze"
5. Be specific about WHAT you're measuring/exploring, not the TOOL or METHOD
6. Each objective should be independently achievable and measurable

BAD EXAMPLES (too methodological):
❌ "To employ qualitative findings to contextualize quantitative relationships between X and Y"
❌ "To utilize regression analysis to determine the impact of X on Y"
❌ "To develop an integrated explanatory model of X using mixed methods"

GOOD EXAMPLES (clear goals):
✅ "To examine the relationship between X and Y"
✅ "To identify the factors influencing X"
✅ "To assess the impact of X on Y"

Return ONLY a JSON array of strings in this format:
["General Objective: ...", "Specific Objective 1: ...", "Specific Objective 2: ...", ...]
"""
        
        response = await self._generate(prompt)
        return self._parse_json(response)
    
    async def _criticize_objectives(
        self,
        topic: str,
        case_study: str,
        objectives: List[str],
        methodology: Optional[str] = None
    ) -> str:
        """
        Subject objectives to harsh academic criticism.
        
        This simulates a PhD review board with three critical reviewers.
        """
        methodology_context = ""
        if methodology:
            methodology_context = f"\nIntended Methodology: {methodology}"
        
        prompt = f"""
You are a panel of 3 STRICT PhD Reviewers at a top-tier university.
Your job is to CRITICIZE these proposed objectives MERCILESSLY but CONSTRUCTIVELY.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Proposed Objectives:
{json.dumps(objectives, indent=2)}

REVIEW PANEL:

**Reviewer 1 - The Methodologist:**
- Are these objectives ACHIEVABLE within this case study context?
- Do they describe WHAT to study (good) or HOW to study it (bad)?
- Flag ANY methodology creep: "integrated model", "contextualize", "employ", "utilize", "mixed methods approach"
- Are they specific enough to guide research but broad enough to allow exploration?

**Reviewer 2 - The Skeptic:**
- So what? Why does this matter? What's the contribution?
- Is the topic clearly defined or vague?
- Is this PhD-level research or undergraduate-level?
- Are the objectives too ambitious or too trivial?
- Do they address a real gap in knowledge?

**Reviewer 3 - The Pedant:**
- Is the language clear, direct, and professional?
- Any jargon, verbosity, or redundancy?
- Are there ANY statistical references (n-values, p-values)?
- Are there ANY method names (surveys, regression, interviews)?
- Is the grammar and structure correct?

OUTPUT FORMAT:
Provide a consolidated critique addressing all three perspectives.
Be HARSH but CONSTRUCTIVE. Point out specific problems and suggest improvements.
If objectives are good, acknowledge it but still find room for improvement.
"""
        
        return await self._generate(prompt)
    
    async def _refine_objectives(
        self,
        topic: str,
        case_study: str,
        draft: List[str],
        critique: str,
        methodology: Optional[str] = None
    ) -> List[str]:
        """Refine objectives based on criticism."""
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology Preference: {methodology}"
        
        prompt = f"""
You are the PhD Candidate revising your objectives based on review board feedback.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Draft Objectives:
{json.dumps(draft, indent=2)}

Review Board Critique:
{critique}

REWRITE the objectives to address ALL concerns raised by the reviewers.

RULES FOR REVISION:
1. Keep it SIMPLE and CLEAR
2. Remove ALL methodology language: no "employ", "utilize", "contextualize", "integrated model"
3. Remove ALL statistical/method references: no "n=", "p<", "regression", "surveys", "interviews"
4. Use direct verbs: "examine", "assess", "explore", "identify", "develop", "analyze"
5. Focus on WHAT you will study, not HOW
6. Ensure each objective is independently achievable
7. Make sure objectives are PhD-level (not too simple, not too ambitious)

TRANSFORMATION EXAMPLE:
BAD: "To employ qualitative findings to contextualize quantitative relationships between romantic involvement and academic performance"
GOOD: "To explore the relationship between romantic relationships and academic performance"

Return ONLY the final JSON array of strings (1 General + 3-4 Specific objectives).
Format: ["General Objective: ...", "Specific Objective 1: ...", ...]
"""
        
        response = await self._generate(prompt)
        return self._parse_json(response)
    
    # ============================================================================
    # OBJECTIVE VALIDATION
    # ============================================================================
    
    async def validate_objectives(
        self,
        objectives: List[str],
        topic: str,
        case_study: str
    ) -> Dict[str, Any]:
        """
        Validate objectives against PhD standards.
        
        Checks for:
        - SMART criteria (Specific, Measurable, Achievable, Relevant, Time-bound)
        - Absence of methodological details
        - Clarity and directness
        - PhD-level rigor
        
        Returns:
            Validation result with issues and suggestions
        """
        prompt = f"""
You are a STRICT PhD Thesis Examiner at a top-tier university with 25+ years of experience. You have rejected hundreds of weak proposals. Be RIGOROUS.

Topic: "{topic}"
Case Study: "{case_study}"

Objectives to Validate:
{json.dumps(objectives, indent=2)}

STRICT VALIDATION CRITERIA (PhD STANDARDS):

1. **SMART Check** (All must pass):
   - Specific: Clear, precise, unambiguous about WHAT will be studied
   - Measurable: Can completion/progress be objectively assessed?
   - Achievable: Realistic scope for 3-5 year PhD research
   - Relevant: Directly addresses the research topic and case study
   - Time-bound: Feasible within PhD timeframe (not too ambitious, not too trivial)

2. **PhD-Level Rigor** (CRITICAL):
   - Is this appropriate for PhD research? (Not undergraduate-level)
   - Does it demonstrate potential for ORIGINAL CONTRIBUTION to knowledge?
   - Is the scope appropriate? (Not too narrow/trivial, not too broad/impossible)
   - Does it address a genuine knowledge gap or research question?
   - Would this pass a PhD proposal defense at a top university?

3. **Methodology Check** (ZERO TOLERANCE):
   - REJECT if contains: "using surveys", "through regression", "via interviews", "n=", "p<", "employ", "utilize", "contextualize"
   - Objectives must state WHAT, never HOW
   - Any mention of tools, methods, or statistical techniques = FAIL

4. **Academic Language** (PhD Standard):
   - Uses precise academic verbs: "investigate", "examine", "analyze", "evaluate", "establish"
   - Avoids weak language: "look at", "check", "see", "find out"
   - Avoids vague jargon: "holistic", "contextualize", "integrated framework"
   - Length: 20-35 words per objective (PhD objectives are detailed)

5. **Originality & Significance**:
   - Does it address a real knowledge gap?
   - Is it original, not just replicating existing studies?
   - Does it have potential to contribute meaningfully to the field?

AUTOMATIC REJECTION CRITERIA (Score = 0):
- Contains methodology details (surveys, regression, n=, p<, etc.)
- Too simple/undergraduate-level ("To find out about X", "To see if Y works")
- Too vague/jargon-heavy ("To contextualize holistic understanding")
- Too narrow/trivial ("To count how many...")
- Too broad/impossible ("To solve all problems in X field")
- No clear contribution to knowledge

SCORING GUIDE:
- 90-100: Excellent PhD-level objectives, ready for defense
- 70-89: Good but needs minor improvements
- 50-69: Acceptable but requires significant revision
- 0-49: REJECT - Not PhD standard, major issues

Return a JSON object with this structure:
{{
    "is_valid": true/false,
    "overall_score": 0-100,
    "issues": [
        {{"objective_index": 0, "severity": "critical/moderate/minor", "issue": "detailed description", "suggestion": "specific fix"}}
    ],
    "strengths": ["what meets PhD standards"],
    "recommendations": ["specific improvements to reach PhD level"]
}}

Be STRICT. PhD standards are HIGH. Reject weak objectives.
"""
        
        response = await self._generate(prompt)
        validation_result = self._parse_json(response)
        
        # Store validation in history
        self.validation_history.append({
            "timestamp": datetime.now().isoformat(),
            "objectives": objectives,
            "result": validation_result
        })
        
        return validation_result
    
    # ============================================================================
    # COHERENCE MONITORING
    # ============================================================================
    
    async def check_section_alignment(
        self,
        section_title: str,
        section_content: str,
        objectives: List[str],
        thesis_topic: str
    ) -> Dict[str, Any]:
        """
        Check if a thesis section aligns with the objectives.
        
        This is called during content generation to ensure each section
        stays true to the objectives.
        
        Returns:
            Alignment analysis with warnings if deviations detected
        """
        prompt = f"""
You are the Objective Guardian for a PhD thesis.

Thesis Topic: "{thesis_topic}"

Research Objectives:
{json.dumps(objectives, indent=2)}

Section Being Checked:
Title: "{section_title}"
Content Preview: {section_content[:2000]}...

ANALYSIS TASK:
1. Which objectives does this section address?
2. Is the content aligned with those objectives?
3. Are there any deviations or scope creep?
4. Does the content maintain logical coherence with the objectives?

Return JSON:
{{
    "aligned_objectives": [list of objective indices that this section addresses],
    "alignment_score": 0-100,
    "deviations": [
        {{"severity": "critical/moderate/minor", "issue": "description", "suggestion": "correction"}}
    ],
    "coherence_issues": ["list any logical inconsistencies"],
    "recommendations": ["specific suggestions for improvement"]
}}
"""
        
        response = await self._generate(prompt)
        alignment = self._parse_json(response)
        
        # Emit warnings if critical deviations found
        if alignment.get("deviations"):
            critical_deviations = [
                d for d in alignment["deviations"] 
                if d.get("severity") == "critical"
            ]
            if critical_deviations:
                await self._emit_warning(
                    target_agent="writer",
                    severity="critical",
                    message=f"Section '{section_title}' has critical deviations from objectives",
                    details=critical_deviations,
                    suggested_action="Review and revise section to align with objectives"
                )
        
        return alignment
    
    async def check_thesis_coherence(
        self,
        thesis_id: str,
        objectives: List[str],
        sections: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Perform overall coherence check across the entire thesis.
        
        This is called periodically or before final submission to ensure
        the entire thesis maintains logical coherence with objectives.
        
        Args:
            thesis_id: Thesis identifier
            objectives: List of objectives
            sections: List of dicts with 'title' and 'content'
            
        Returns:
            Overall coherence analysis with replan trigger if needed
        """
        sections_summary = "\n".join([
            f"- {s['title']}: {s['content'][:200]}..."
            for s in sections[:10]  # Limit to avoid token overflow
        ])
        
        prompt = f"""
You are conducting a COMPREHENSIVE COHERENCE AUDIT of a PhD thesis.

Research Objectives:
{json.dumps(objectives, indent=2)}

Thesis Sections Summary:
{sections_summary}

AUDIT TASKS:
1. Are ALL objectives adequately addressed across the thesis?
2. Is there logical flow and coherence throughout?
3. Are there sections that don't contribute to any objective?
4. Are there gaps where objectives aren't sufficiently covered?
5. Is the overall narrative consistent with the objectives?

Return JSON:
{{
    "coherence_score": 0-100,
    "objectives_coverage": {{
        "0": {{"covered": true/false, "sections": [list], "adequacy": "sufficient/insufficient"}},
        ...
    }},
    "critical_issues": [list of major problems],
    "moderate_issues": [list of moderate problems],
    "minor_issues": [list of minor problems],
    "requires_replan": true/false,
    "replan_reason": "explanation if replan needed",
    "recommendations": [list of specific actions]
}}
"""
        
        response = await self._generate(prompt)
        coherence = self._parse_json(response)
        
        # Trigger replan if necessary
        if coherence.get("requires_replan"):
            await self._trigger_replan(
                thesis_id=thesis_id,
                reason=coherence.get("replan_reason"),
                issues=coherence.get("critical_issues", [])
            )
        
        return coherence
    
    # ============================================================================
    # WARNING AND REPLAN SYSTEM
    # ============================================================================
    
    async def _emit_warning(
        self,
        target_agent: str,
        severity: str,
        message: str,
        details: Any,
        suggested_action: str
    ):
        """
        Emit a warning to another agent.
        
        This is how the objective agent communicates issues to other agents
        (writer, researcher, etc.)
        """
        warning = {
            "warning_id": f"warn_{datetime.now().timestamp()}",
            "source": "objective_agent",
            "target": target_agent,
            "severity": severity,
            "message": message,
            "details": details,
            "suggested_action": suggested_action,
            "timestamp": datetime.now().isoformat()
        }
        
        self.warnings.append(warning)
        
        # Log the warning
        print(f"\n⚠️  OBJECTIVE AGENT WARNING [{severity.upper()}]")
        print(f"   Target: {target_agent}")
        print(f"   Message: {message}")
        print(f"   Action: {suggested_action}\n")
        
        # TODO: Integrate with agent communication service when available
        # await agent_communication_service.emit_warning(warning)
    
    async def _trigger_replan(
        self,
        thesis_id: str,
        reason: str,
        issues: List[str]
    ):
        """
        Trigger a replanning process.
        
        This is called when critical deviations or coherence issues are detected
        that require restructuring the thesis.
        """
        replan_event = {
            "event_id": f"replan_{datetime.now().timestamp()}",
            "thesis_id": thesis_id,
            "triggered_by": "objective_agent",
            "reason": reason,
            "issues": issues,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n🔄 REPLAN TRIGGERED")
        print(f"   Thesis ID: {thesis_id}")
        print(f"   Reason: {reason}")
        print(f"   Issues: {len(issues)}")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        print()
        
        # TODO: Integrate with thesis management service
        # await thesis_service.trigger_replan(replan_event)
    
    def get_warnings(self, target_agent: Optional[str] = None) -> List[Dict]:
        """Get warnings, optionally filtered by target agent."""
        if target_agent:
            return [w for w in self.warnings if w["target"] == target_agent]
        return self.warnings
    
    def clear_warnings(self, warning_ids: Optional[List[str]] = None):
        """Clear specific warnings or all warnings."""
        if warning_ids:
            self.warnings = [w for w in self.warnings if w["warning_id"] not in warning_ids]
        else:
            self.warnings = []
    
    # ============================================================================
    # MAKER FRAMEWORK - VOTING-BASED OBJECTIVE GENERATION
    # ============================================================================
    
    async def generate_objectives_with_voting(
        self,
        topic: str,
        case_study: str,
        methodology: Optional[str] = None,
        k: int = 3,
        enable_red_flags: bool = True,
        thesis_id: Optional[str] = None,
        on_sample_callback: Optional[callable] = None  # NEW: callback for each valid sample
    ) -> Dict[str, Any]:
        """
        Generate objectives using MAKER framework with voting.
        
        This method implements:
        1. Maximal Agentic Decomposition - Each objective voted on separately
        2. First-to-ahead-by-k Voting - Multiple samples until consensus
        3. Red-flagging - Discard unreliable responses
        
        Args:
            topic: Research topic
            case_study: Case study context
            methodology: Optional methodology preference
            k: Vote threshold (default: 3)
            enable_red_flags: Whether to use red flag detection
            thesis_id: Optional thesis ID for tracking
            
        Returns:
            Dict with objectives, voting stats, and cost estimates
        """
        from core.maker_framework import VotingOrchestrator, VotingConfig, MAKERCostEstimator
        from core.red_flags import AcademicRedFlags
        
        print(f"\n🎯 MAKER OBJECTIVE GENERATION")
        print(f"   Topic: {topic}")
        print(f"   k-threshold: {k}")
        print(f"   Red-flagging: {'Enabled' if enable_red_flags else 'Disabled'}")
        print(f"   {'='*60}\n")
        
        # Setup voting configuration - OPTIMIZED FOR SPEED
        # Reduced max_samples from 20 to 8 for faster completion
        # k=2 is sufficient for quality while being faster
        config = VotingConfig(
            k=k,
            max_samples=8,  # Reduced from 10 to 8 for even faster completion
            enable_parallel=True,
            temperature_range=(0.0, 0.1),
            progress_callback=voting_progress_callback  # Real-time progress
        )
        orchestrator = VotingOrchestrator(config)
        
        # Setup red flag detector
        red_flag_detector = AcademicRedFlags.for_objectives() if enable_red_flags else None
        
        # Generate prompt
        prompt = await self._build_voting_prompt(topic, case_study, methodology)
        
        # Define sample generator with progress events
        async def generate_sample(temperature: float) -> str:
            # Emit progress event before generation
            if job_id:
                await events.log(job_id, f"🤖 Generating objectives sample (temperature={temperature:.1f})...", "info")
                await events.publish(job_id, "llm_generation", {
                    "status": "starting",
                    "model": "DeepSeek",
                    "temperature": temperature,
                    "message": "LLM is generating objectives..."
                })
            
            try:
                response = await self.llm.generate_content(
                    prompt=prompt,
                    model_key="deepseek",
                    temperature=temperature
                )
                
                # Emit progress event after generation
                if job_id:
                    await events.publish(job_id, "llm_generation", {
                        "status": "completed",
                        "model": "DeepSeek",
                        "message": "Objectives sample generated successfully"
                    })
                
                return response
            except Exception as e:
                if job_id:
                    await events.log(job_id, f"⚠️ LLM generation error: {str(e)}", "warning")
                    await events.publish(job_id, "llm_generation", {
                        "status": "error",
                        "model": "DeepSeek",
                        "error": str(e)
                    })
                raise
        
        # Define validator/parser
        def validate_sample(response: str) -> Optional[List[str]]:
            try:
                objectives = self._parse_json(response)
                if not isinstance(objectives, list) or len(objectives) < 2:
                    return None
                # Basic format check
                if not objectives[0].startswith("General Objective:"):
                    return None
                return objectives
            except:
                return None
        
        # Track sample number for callback
        sample_number = {"count": 0}
        
        # Progress callback for real-time voting updates
        async def voting_progress_callback(progress_data: dict):
            """Emit real-time voting progress to frontend."""
            if job_id:
                await events.publish(job_id, "voting_progress", progress_data)
        
        # Wrap validator to call callback
        def validate_and_notify(response: str) -> Optional[List[str]]:
            result = validate_sample(response)
            if result and on_sample_callback:
                sample_number["count"] += 1
                # Call callback asynchronously
                import asyncio
                asyncio.create_task(on_sample_callback(sample_number["count"], result))
            return result
        
        # Define red flag checker
        def check_red_flags(response: str, context: Dict) -> bool:
            if not enable_red_flags or not red_flag_detector:
                return False
            
            result = red_flag_detector.detect_flags(response, {
                'task_type': 'objective',
                'expected_format': 'objective_list',
                'expected_type': 'list'
            })
            
            if result.should_flag:
                print(f"      Red flags: {', '.join(result.reasons)}")
            
            return result.should_flag
        
        # Run voting
        voting_result = await orchestrator.vote_until_consensus(
            generate_sample=generate_sample,
            validate_sample=validate_and_notify,  # Use wrapped validator
            red_flag_detector=check_red_flags if enable_red_flags else None,
            context={'task_type': 'objective'}
        )
        
        # Validate final objectives
        # Ensure winner is a list
        winner_objectives = voting_result.winner
        if not isinstance(winner_objectives, list):
            print(f"⚠️ Warning: voting_result.winner is not a list, type: {type(winner_objectives)}")
            if isinstance(winner_objectives, str):
                winner_objectives = [winner_objectives]
            else:
                winner_objectives = []
        
        validation = await self.validate_objectives(
            winner_objectives,
            topic,
            case_study
        )
        
        # Calculate cost estimates
        cost_estimate = MAKERCostEstimator.estimate_objective_generation_cost(
            num_objectives=len(voting_result.winner),
            k=k,
            cost_per_objective_sample=0.05
        )
        
        # Store voting session in database (if thesis_id provided)
        session_id = None
        if thesis_id:
            session_id = await self._store_voting_session(
                thesis_id=thesis_id,
                voting_result=voting_result,
                task_type='objective',
                task_description=f"Objectives for: {topic}",
                k=k
            )
        
        print(f"\n{'='*60}")
        print(f"✅ VOTING COMPLETE")
        print(f"   Winner: {voting_result.winner_votes} votes")
        print(f"   Total samples: {voting_result.total_samples}")
        print(f"   Flagged: {voting_result.flagged_samples}")
        print(f"   Convergence rounds: {voting_result.convergence_rounds}")
        print(f"   Estimated cost: ${voting_result.estimated_cost:.4f}")
        print(f"   Validation: {'✓ PASSED' if validation['is_valid'] else '✗ FAILED'}")
        print(f"{'='*60}\n")
        
        # Ensure objectives is always a list
        objectives_list = winner_objectives if isinstance(winner_objectives, list) else []
        
        # Ensure validation is always a dict
        if not isinstance(validation, dict):
            print(f"⚠️ Warning: validation is not a dict, type: {type(validation)}, converting")
            validation = {"is_valid": False, "message": f"Validation returned {type(validation)}"}
        
        return {
            "objectives": objectives_list,
            "validation": validation,
            "voting_stats": {
                "k_threshold": k,
                "total_samples": voting_result.total_samples,
                "flagged_samples": voting_result.flagged_samples,
                "convergence_rounds": voting_result.convergence_rounds,
                "winner_votes": voting_result.winner_votes,
                "vote_distribution": dict(voting_result.vote_distribution) if hasattr(voting_result.vote_distribution, 'items') else {},
                "all_votes": voting_result.all_votes if isinstance(voting_result.all_votes, list) else []
            },
            "cost_estimate": cost_estimate,
            "actual_cost": float(voting_result.actual_cost) if hasattr(voting_result, 'actual_cost') else 0.0,
            "session_id": session_id,
            "timestamp": voting_result.timestamp if hasattr(voting_result, 'timestamp') else datetime.now().isoformat(),
            "mode": "maker_voting"
        }
    
    async def _build_voting_prompt(
        self,
        topic: str,
        case_study: str,
        methodology: Optional[str]
    ) -> str:
        """Build prompt for voting-based objective generation."""
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology Preference: {methodology}"
        
        return f"""
You are a senior PhD supervisor and academic research consultant with 20+ years of experience evaluating PhD thesis proposals at top-tier universities.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Generate 1 General Objective and 3-4 Specific Objectives that meet RIGOROUS PhD STANDARDS.

CRITICAL REQUIREMENTS FOR PhD-LEVEL OBJECTIVES:

1. **RESEARCH SIGNIFICANCE**: Each objective must address a genuine knowledge gap and contribute to the field
2. **ORIGINALITY**: Objectives should demonstrate originality, not just replicate existing studies
3. **SCOPE**: Appropriate for PhD-level research (not too narrow/undergraduate, not too broad/impossible)
4. **CLARITY**: State WHAT will be studied, NOT HOW (no methodology, no statistical methods, no tools)
5. **MEASURABILITY**: Each objective must be independently verifiable and achievable
6. **ACADEMIC RIGOR**: Use precise academic language appropriate for PhD research
7. **LENGTH**: 20-35 words per objective (PhD objectives are more detailed than undergraduate)

VERB USAGE (PhD-appropriate):
- Strong: "investigate", "examine", "analyze", "evaluate", "assess", "explore", "identify", "determine", "establish", "elucidate"
- Avoid weak verbs: "look at", "check", "see", "find out"

FORBIDDEN ELEMENTS (These make objectives non-PhD):
❌ Methodology details: "using surveys", "through regression analysis", "n=500", "p<0.05"
❌ Vague jargon: "contextualize", "holistic understanding", "integrated framework"
❌ Undergraduate-level simplicity: "To find out about X", "To see if Y works"
❌ Overly ambitious/impossible: "To solve all problems in X field"
❌ Too narrow/trivial: "To count how many people use X"

EXCELLENT PhD-LEVEL EXAMPLES:

General Objective:
✅ "To investigate the causal relationships between [specific variables] in [context] and their implications for [field/theory]"

Specific Objectives:
✅ "To examine the extent to which [factor A] influences [outcome B] in [specific context/population]"
✅ "To identify and analyze the key determinants of [phenomenon] in [context], with particular focus on [specific aspect]"
✅ "To evaluate the effectiveness of [intervention/policy/approach] in addressing [specific problem] within [context]"
✅ "To establish the relationship between [variable X] and [variable Y] and determine the mediating role of [factor Z]"

BAD EXAMPLES (Reject these):
❌ "To use surveys to find out about X" (methodology)
❌ "To see if Y affects Z" (too simple, undergraduate-level)
❌ "To contextualize the holistic understanding of X through integrated analysis" (jargon, meaningless)
❌ "To solve all problems in healthcare" (too broad, impossible)
❌ "To count how many people like X" (too narrow, trivial)

OUTPUT FORMAT:
Return ONLY a JSON array of strings:
["General Objective: [your general objective]", "Specific Objective 1: [first specific objective]", "Specific Objective 2: [second specific objective]", "Specific Objective 3: [third specific objective]", "Specific Objective 4: [fourth specific objective if applicable]"]

Each objective must:
- Be 20-35 words
- State WHAT will be studied (not HOW)
- Demonstrate PhD-level rigor and significance
- Be independently achievable
- Contribute original knowledge to the field
"""
    
    async def _store_voting_session(
        self,
        thesis_id: str,
        voting_result: Any,
        task_type: str,
        task_description: str,
        k: int
    ) -> Optional[str]:
        """Store voting session in database."""
        try:
            from services.supabase import supabase
            
            session_data = {
                "thesis_id": thesis_id,
                "task_type": task_type,
                "task_description": task_description,
                "k_threshold": k,
                "total_samples": voting_result.total_samples,
                "flagged_samples": voting_result.flagged_samples,
                "convergence_rounds": voting_result.convergence_rounds,
                "estimated_cost": float(voting_result.estimated_cost),
                "actual_cost": float(voting_result.actual_cost),
                "winner": str(voting_result.winner),
                "winner_votes": voting_result.winner_votes,
                "completed_at": datetime.now().isoformat(),
                "metadata": {
                    "vote_distribution": voting_result.vote_distribution,
                    "timestamp": voting_result.timestamp
                }
            }
            
            result = supabase.table("voting_sessions").insert(session_data).execute()
            
            if result.data and len(result.data) > 0:
                session_id = result.data[0]["id"]
                
                # Store individual votes
                for vote in voting_result.all_votes:
                    vote_data = {
                        "session_id": session_id,
                        "sample_number": vote["sample_number"],
                        "temperature": float(vote["temperature"]),
                        "response_text": vote["response"],
                        "was_flagged": vote["flagged"],
                        "vote_for": vote.get("vote_for"),
                        "parsed_result": vote.get("parsed")
                    }
                    supabase.table("votes").insert(vote_data).execute()
                
                return session_id
            
        except Exception as e:
            print(f"   ⚠️  Failed to store voting session: {str(e)}")
        
        return None
    
    # ============================================================================
    # UTILITIES
    # ============================================================================
    
    def _parse_json(self, response: str) -> Any:
        """Parse JSON from LLM response, handling various formats."""
        clean_response = response.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_response)
        except json.JSONDecodeError:
            # Fallback: try to extract lines as array
            lines = [line.strip() for line in clean_response.split('\n') if line.strip()]
            if lines and lines[0].startswith('['):
                return json.loads('\n'.join(lines))
            return lines
    
    # ============================================================================
    # COMPETITIVE MULTI-MODEL GENERATION
    # ============================================================================
    
    async def generate_objectives_competitive(
        self,
        topic: str,
        case_study: str,
        methodology: Optional[str] = None,
        models: Optional[List[str]] = None,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate objectives through competitive multi-model process with academic rigor.
        
        Enhanced Process:
        0. Context Research - Web search for key periods, factors, variables
        1. Variable Decomposition - Break topic into measurable variables
        2. Parallel Generation - Models generate with context awareness
        3. Cross-Critique - Each model critiques all others
        4. Central Ranking - Judge with substance-focused scoring
        5. Save Results - Comprehensive competition data
        
        Args:
            topic: Research topic
            case_study: Case study context
            methodology: Optional methodology preference
            models: List of model keys to use (default: all 4)
            job_id: Optional job ID for event streaming
            
        Returns:
            Competition results with winner, rankings, and detailed reasoning
        """
        from app.services.openrouter import openrouter_service
        from app.agents.objective_ranker import objective_ranker
        from app.services.web_search import web_search_service
        from app.agents.variable_decomposer import variable_decomposer
        
        if models is None:
            models = ["claude", "gpt4", "deepseek"]  # Gemini removed
        
        # Helper to safely emit events
        async def emit(speaker, message, data=None):
            if job_id:
                payload = {"speaker": speaker, "message": message}
                if data:
                    payload["data"] = data
                await events.publish(job_id, "debate_message", payload)
        
        print(f"\n🏆 COMPETITIVE OBJECTIVE GENERATION (Enhanced)")
        print(f"   Topic: {topic}")
        print(f"   Case Study: {case_study}")
        print(f"   Competing Models: {', '.join(models)}")
        print(f"   {'='*60}\n")
        
        await emit("Judge", f"I am initiating a competitive review for the topic: '{topic}' in the context of '{case_study}'.")
        
        # Phase 0: Context Research (NEW)
        print("🔍 PHASE 0: Context Research")
        await emit("Judge", "First, I will conduct background research to establish the academic context.")
        context = await web_search_service.research_topic_context(topic, case_study)
        await emit("Judge", f"Research complete. I've identified key themes: {', '.join(context.get('key_themes', [])[:3]) if context.get('key_themes') else 'N/A'}...")
        
        # Phase 1: Variable Decomposition (NEW)
        print("📊 PHASE 1: Variable Decomposition")
        await emit("Judge", "Now, I am decomposing the topic into measurable variables to guide the models.")
        variables = await variable_decomposer.decompose_topic(topic, case_study, context)
        
        # Handle variables - could be dict or list
        if isinstance(variables, dict):
            indep_vars = variables.get('independent_variables', [])
            var_names = ', '.join([v['name'] for v in indep_vars[:2]]) if indep_vars else 'N/A'
        elif isinstance(variables, list):
            var_names = ', '.join([str(v)[:20] for v in variables[:2]]) if variables else 'N/A'
        else:
            var_names = 'N/A'
        
        await emit("Judge", f"Variables identified: {var_names}...")
        
        # Phase 2: Parallel Generation (Enhanced with context)
        print("📝 PHASE 2: Parallel Generation (Context-Aware)")
        print("   All models generating objectives with context research...")
        await emit("Judge", "Models, please generate your best objectives based on this research.")
        
        generation_prompt = self._build_generation_prompt_enhanced(
            topic, case_study, methodology, context, variables
        )
        
        # Announce start
        for m in models:
            await emit(m.capitalize(), "I am analyzing the context and generating objectives...")
        
        results = await openrouter_service.generate_parallel(
            prompt=generation_prompt,
            model_keys=models,
            system_prompt="You are an expert academic research consultant for PhD thesis development.",
            temperature=0.7
        )
        
        # Parse objectives from each model
        submissions = {}
        for model_key, result in results.items():
            if result["success"]:
                try:
                    objectives = self._parse_json(result["content"])
                    submissions[model_key] = objectives
                    print(f"   ✓ {result['model_name']}: {len(objectives)} objectives")
                    submissions[model_key] = objectives
                    print(f"   ✓ {result['model_name']}: {len(objectives)} objectives")
                    await emit(
                        model_key.capitalize(), 
                        f"I have generated {len(objectives)} objectives focusing on {objectives[0][:50]}...",
                        data={"objectives": objectives}
                    )
                except Exception as e:
                    print(f"   ✗ {result['model_name']}: Failed to parse - {str(e)}")
                    await emit(model_key.capitalize(), "I encountered an error formatting my objectives.")
            else:
                print(f"   ✗ {result['model_name']}: {result['error']}")
                await emit(model_key.capitalize(), "I failed to generate a response.")
        
        if len(submissions) < 2:
            raise Exception("Need at least 2 successful submissions for competition")
        
        # Phase 3: Cross-Critique
        print(f"\n🔍 PHASE 3: Cross-Critique")
        print("   Each model critiquing all others...")
        await emit("Judge", "Now, critique each other's work. Be rigorous.")
        
        critiques = await self._cross_critique(
            topic, case_study, submissions, methodology, openrouter_service
        )
        
        # Emit critique summaries (simulated for now as _cross_critique doesn't return easy-to-stream chunks yet, 
        # but we can iterate over the result)
        for model, model_critiques in critiques.items():
            for target, critique in model_critiques.items():
                await emit(model.capitalize(), f"Critique of {target}: {critique[:100]}...")
        
        print(f"   ✓ Collected {sum(len(c) for c in critiques.values())} critiques")
        
        # Phase 4: Central Ranking (Enhanced with substance focus)
        print(f"\n🏅 PHASE 4: Central Ranking (Substance-Focused)")
        print("   Meta-judge evaluating with 70/30 substance/structure split...")
        await emit("Judge", "I am now evaluating all submissions based on substance, feasibility, and academic rigor.")
        
        ranking = await objective_ranker.rank_submissions(
            topic=topic,
            case_study=case_study,
            submissions=submissions,
            critiques=critiques
        )
        
        winner_model = ranking['winner']['model']
        await emit("Judge", f"The winner is {winner_model.capitalize()} with a score of {ranking['winner']['score']}/100.")
        await emit("Judge", f"Reason: {ranking['winner']['why_it_won'][0]}")
        
        # Phase 5: Compile Results
        competition_result = {
            "competition_id": f"comp_{int(datetime.now().timestamp())}",
            "topic": topic,
            "case_study": case_study,
            "methodology": methodology,
            "timestamp": datetime.now().isoformat(),
            "participants": list(submissions.keys()),
            "context_research": context,
            "variables": variables,
            "submissions": submissions,
            "critiques": critiques,
            "ranking": ranking,
            "winner": ranking.get("winner", {}),
            "mode": "competitive_enhanced"
        }
        
        print(f"\n{'='*60}")
        print(f"🎉 WINNER: {ranking['winner']['model'].upper()}")
        print(f"   Score: {ranking['winner']['score']}/100")
        print(f"   Why it won:")
        for reason in ranking['winner']['why_it_won']:
            print(f"   • {reason}")
        print(f"{'='*60}\n")
        
        return competition_result
    
    
    def _build_generation_prompt_enhanced(
        self,
        topic: str,
        case_study: str,
        methodology: Optional[str],
        context: Dict[str, Any],
        variables: List[Dict[str, Any]]
    ) -> str:
        """Build enhanced prompt with context research and variable decomposition."""
        
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology Preference: {methodology}"
        
        # Format context research
        key_periods = "\n".join([f"  - {p}" for p in context.get('key_periods', [])])
        context_factors = "\n".join([f"  - {f}" for f in context.get('context_factors', [])])
        
        # Format variables
        variables_text = ""
        for i, var in enumerate(variables, 1):
            indicators = "\n    ".join([f"• {ind}" for ind in var.get('indicators', [])])
            variables_text += f"""
{i}. **{var['name']}**
   Indicators:
    {indicators}
   Relevance: {var.get('relevance', 'N/A')}
"""
        
        return f"""
You are competing to generate the BEST PhD thesis objectives.

**Topic:** "{topic}"
**Case Study:** "{case_study}"{methodology_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 CONTEXT RESEARCH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Key Historical Periods:**
{key_periods}

**Context-Specific Factors:**
{context_factors}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 VARIABLE DECOMPOSITION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{variables_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 CRITICAL REQUIREMENTS (CLARITY > COVERAGE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ **MOST IMPORTANT: BREVITY** (Worth 30 points)
   - Each objective must be **15-25 words**
   - Short, sharp, directional statements
   - NO paragraph-long objectives
   
   ❌ TERRIBLE (87 words): "To quantify the affordability barriers of mobile phone acquisition in Uganda by analyzing household income-to-device-price ratios, examining the relationship between GDP per capita and smartphone penetration rates across different income quintiles, and assessing the impact of taxation policies, import tariffs, and currency fluctuations on final consumer prices in both urban centers and rural communities, while considering the role of microfinance schemes and mobile money platforms in facilitating device acquisition among low-income populations."
   
   ✅ EXCELLENT (18 words): "To analyze trends in mobile phone prices in Uganda from 2010–2023 and their implications for household affordability."

1. **NO METHODOLOGY CREEP** (Worth 40 points - MOST CRITICAL):
   - Objectives state WHAT, not HOW
   - NO embedded metrics, formulas, or measurement techniques
   - NO statistical terms (p<0.05, n=100, r=0.85)
   - NO specific measurement units in objectives
   
   ❌ BAD: "assess GDP per capita correlation with smartphone penetration (r>0.7, p<0.05)"
   ❌ BAD: "measure stockout frequencies per month across 50 retail locations"
   ❌ BAD: "calculate agent density per 1000 population using GIS mapping"
   ❌ BAD: "analyze price inflation rates (%) using CPI data from 2010-2023"
   
   ✅ GOOD: "assess how mobile phone affordability affects adoption of digital services"
   ✅ GOOD: "examine the economic and market factors that shape mobile phone pricing"
   ✅ GOOD: "evaluate the role of alternative acquisition pathways in expanding access"

2. **CONTEXT-APPROPRIATE** (Worth 20 points):
   - Use variables from decomposition above
   - Match the actual context (don't assume conflict if not conflict-affected)
   - Be realistic about the case study
   
   ❌ BAD (for Uganda): "assess impact of armed conflict on supply chains"
   ❌ BAD (for Uganda): "examine network tower downtime during bombardment"
   
   ✅ GOOD (for Uganda): "examine taxation, vendor competition, and import dependence"
   ✅ GOOD (for Uganda): "assess urban/rural divide in mobile phone access"

3. **REALISTIC TIMEFRAME** (Worth 10 points):
   - 5-15 years for PhD
   - Use specific periods from context research
   
   ❌ BAD: "from 2000 to present" (too broad)
   ✅ GOOD: "from 2010 to 2023"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏆 GOLD STANDARD EXAMPLES (ChatGPT-Level Quality)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**Example 1: Mobile Phone Prices in Uganda**

General Objective (15 words):
"To examine how mobile phone prices influence technological acquisition and digital inclusion in Uganda between 2010 and 2023."

Specific Objectives (15-20 words each):
1. "To analyze trends in mobile phone prices in Uganda from 2010–2023 and their implications for household affordability."
2. "To assess how mobile phone affordability affects the adoption of digital services, including mobile internet and smartphone applications."
3. "To examine the economic and market factors that shape the pricing of mobile phones in Uganda."
4. "To evaluate the role of alternative acquisition pathways in expanding access to mobile technologies."

**Example 2: War Impact on Economic Development**

General Objective (18 words):
"To analyze the impact of armed conflict on economic development in the Nuba Mountains of Sudan between 2011 and 2023."

Specific Objectives (18-22 words each):
1. "To assess changes in agricultural productivity in the Nuba Mountains from 2011-2023 using indicators such as crop yields and livestock losses."
2. "To examine how conflict-related road blockades affected commodity prices and market integration between Nuba and surrounding regions."
3. "To evaluate the economic effects of displacement on household income sources and livelihood diversification among affected communities."

**Notice:**
- ✅ 15-25 words each
- ✅ No metrics embedded (no "GDP per capita", no "p<0.05", no "n=100")
- ✅ Clear WHAT, no HOW
- ✅ Action-oriented verbs (analyze, assess, examine, evaluate)
- ✅ Context-appropriate
- ✅ Realistic timeframes

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generate:
- **1 General Objective** (15-20 words)
- **3-4 Specific Objectives** (15-25 words each)

**SCORING BREAKDOWN:**
- Brevity (30 pts): 15-25 words per objective
- No Methodology Creep (40 pts): No embedded metrics/formulas
- Context Appropriateness (20 pts): Matches actual conditions
- Timeframe (10 pts): Realistic scope

**You will be HEAVILY PENALIZED for:**
- Verbose objectives (>25 words)
- Embedded metrics (GDP, percentages, ratios, frequencies)
- Methodology details (using surveys, through regression, n=100)
- Context mismatches (conflict terms for non-conflict zones)

Return ONLY a JSON array of strings:
["General Objective: ...", "Specific Objective 1: ...", "Specific Objective 2: ...", ...]
"""
    
    def _build_generation_prompt(
        self,
        topic: str,
        case_study: str,
        methodology: Optional[str] = None
    ) -> str:
        """Build prompt for competitive objective generation."""
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology Preference: {methodology}"
        
        return f"""
You are competing with other AI models to generate the BEST PhD thesis objectives.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Generate 1 General Objective and 3-4 Specific Objectives.

CRITICAL RULES - OBJECTIVES STATE WHAT, NOT HOW:
1. Objectives describe WHAT you will study, NOT HOW you will study it
2. NO methodology details: no "n=", no "p<0.05", no "using surveys", no "regression analysis"
3. NO jargon: avoid "integrated explanatory model", "contextualize", "holistic understanding"
4. Use simple, direct verbs: "examine", "assess", "explore", "identify", "develop", "analyze"
5. Be specific about WHAT you're measuring/exploring, not the TOOL or METHOD
6. Each objective should be independently achievable and measurable
7. PhD-level rigor without verbosity

Your objectives will be critiqued by other AI models and judged by a meta-evaluator.
Aim for EXCELLENCE.

Return ONLY a JSON array of strings:
["General Objective: ...", "Specific Objective 1: ...", "Specific Objective 2: ...", ...]
"""
    
    async def _cross_critique(
        self,
        topic: str,
        case_study: str,
        submissions: Dict[str, List[str]],
        methodology: Optional[str],
        openrouter_service
    ) -> Dict[str, Dict[str, str]]:
        """
        Each model critiques all other models' objectives.
        
        Returns:
            Dict mapping critic_model -> {target_model -> critique}
        """
        critiques = {}
        
        for critic_model in submissions.keys():
            critiques[critic_model] = {}
            
            for target_model, target_objectives in submissions.items():
                if critic_model == target_model:
                    continue  # Don't critique yourself
                
                critique_prompt = self._build_critique_prompt(
                    topic, case_study, target_model, target_objectives, methodology
                )
                
                try:
                    critique = await openrouter_service.generate_content(
                        prompt=critique_prompt,
                        model_key=critic_model,
                        system_prompt="You are a critical PhD thesis reviewer.",
                        temperature=0.6
                    )
                    critiques[critic_model][target_model] = critique
                    print(f"   ✓ {critic_model} → {target_model}")
                except Exception as e:
                    print(f"   ✗ {critic_model} → {target_model}: {str(e)}")
                    critiques[critic_model][target_model] = f"Error: {str(e)}"
        
        return critiques
    
    def _build_critique_prompt(
        self,
        topic: str,
        case_study: str,
        target_model: str,
        objectives: List[str],
        methodology: Optional[str]
    ) -> str:
        """Build prompt for critiquing another model's objectives."""
        methodology_context = ""
        if methodology:
            methodology_context = f"\nMethodology: {methodology}"
        
        return f"""
You are critiquing a competitor's PhD thesis objectives.

Topic: "{topic}"
Case Study: "{case_study}"{methodology_context}

Competitor's Objectives:
{json.dumps(objectives, indent=2)}

CRITIQUE THESE OBJECTIVES:
- Do they state WHAT to study or HOW to study it? (WHAT is good, HOW is bad)
- Any methodology creep? (statistical terms, method names, etc.)
- Are they SMART? (Specific, Measurable, Achievable, Relevant, Time-bound)
- PhD-level rigor?
- Clear and direct language?
- Any jargon or verbosity?

Be HARSH but FAIR. Point out specific flaws with examples.
If objectives are good, acknowledge it but still find areas for improvement.

Provide a 2-3 paragraph critique.
"""


# Singleton instance
objective_agent = ObjectiveAgent()
