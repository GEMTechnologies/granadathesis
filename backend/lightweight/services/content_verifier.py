"""
Content Verification Service
Prevents hallucinations by cross-checking generated content against internet search results.
"""

import asyncio
from typing import Dict, List, Any, Optional
from core.events import events
from services.deepseek_client import deepseek_client
from services.web_search import web_search_service

class ContentVerifier:
    """
    Verifies content accuracy by:
    1. Extracting factual claims
    2. Searching for evidence
    3. Verifying claims against evidence
    4. Correcting hallucinations
    """
    
    def __init__(self):
        self.deepseek = deepseek_client
        self.search = web_search_service
        
    async def verify_and_correct(
        self, 
        content: str, 
        topic: str,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main entry point: Verify content and return corrected version if needed.
        """
        if job_id:
            await events.log(job_id, "🕵️ Starting content verification...")
            
        # 1. Extract Claims
        claims = await self._extract_claims(content, topic)
        if not claims:
            if job_id:
                await events.log(job_id, "✓ No verifiable claims found (opinion/general knowledge).")
            return {"content": content, "corrections": []}
            
        if job_id:
            await events.log(job_id, f"📋 Verifying {len(claims)} factual claims...")
            
        # 2. Verify Claims
        verification_results = []
        hallucinations = []
        
        for claim in claims:
            # Search for evidence
            evidence = await self.search.verify_claim(claim)
            
            # Evaluate claim
            status, reasoning = await self._evaluate_claim(claim, evidence)
            
            result = {
                "claim": claim,
                "status": status,
                "reasoning": reasoning,
                "evidence": evidence
            }
            verification_results.append(result)
            
            if status == "Contradicted" or status == "Unverified":
                # Attempt to find the correct information
                print(f"   ❌ Hallucination detected: {claim} -> {status}")
                if job_id:
                    await events.log(job_id, f"❌ Issue found: {claim[:50]}... ({status})", "warning")
                
                # Active Research for Correction
                corrective_evidence = []
                if status == "Unverified":
                    print(f"   🔎 Searching for correct info for: {claim[:50]}...")
                    if job_id:
                        await events.log(job_id, f"🔎 Researching correct facts...", "info")
                    try:
                        # Search for the truth
                        corrective_evidence = await self.search.verify_claim(f"fact check {claim}")
                    except Exception as e:
                        print(f"   ⚠️ Correction search failed: {e}")

                result["corrective_evidence"] = corrective_evidence
                hallucinations.append(result)
            else:
                print(f"   ✓ Verified: {claim[:50]}...")
        
        # 3. Correct Content if needed
        if hallucinations:
            if job_id:
                await events.log(job_id, f"🛠️ Correcting {len(hallucinations)} issues...", "info")
            
            corrected_content = await self._correct_content(content, hallucinations)
            
            return {
                "content": corrected_content,
                "corrections": hallucinations,
                "verification_report": verification_results
            }
        
        if job_id:
            await events.log(job_id, "✅ Verification passed!", "success")
            
        return {
            "content": content,
            "corrections": [],
            "verification_report": verification_results
        }
    
    async def _extract_claims(self, content: str, topic: str) -> List[str]:
        """Extract testable factual claims from content."""
        prompt = f"""Analyze the following text about "{topic}" and extract the top 3-5 most important FACTUAL CLAIMS that should be verified.
        Focus on:
        - Specific dates, numbers, or statistics
        - Causal relationships
        - Specific events or outcomes
        
        Ignore general knowledge, opinions, or vague statements.
        
        Text:
        {content[:2000]}
        
        Output format: Return ONLY a bulleted list of claims. No intro/outro."""
        
        response = await self.deepseek.generate(prompt, max_tokens=300)
        
        # Parse bullets
        claims = []
        for line in response.split('\n'):
            line = line.strip()
            if line.startswith('- ') or line.startswith('* '):
                claims.append(line[2:].strip())
            elif line and line[0].isdigit() and '. ' in line:
                claims.append(line.split('. ', 1)[1].strip())
                
        return claims[:5]  # Limit to 5 to save time
        
    async def _evaluate_claim(self, claim: str, evidence: List[str]) -> tuple[str, str]:
        """Evaluate if a claim is supported by evidence."""
        if not evidence:
            return "Unverified", "No evidence found."
            
        evidence_text = "\n".join(evidence)
        
        prompt = f"""Verify the following claim based ONLY on the provided evidence.
        
        Claim: "{claim}"
        
        Evidence:
        {evidence_text}
        
        Task: Determine if the claim is Supported, Contradicted, or Unverified (if evidence is irrelevant).
        
        Output format:
        Status: [Supported/Contradicted/Unverified]
        Reasoning: [Brief explanation]"""
        
        response = await self.deepseek.generate(prompt, max_tokens=100)
        
        status = "Unverified"
        reasoning = response
        
        if "Status: Supported" in response:
            status = "Supported"
        elif "Status: Contradicted" in response:
            status = "Contradicted"
        elif "Status: Unverified" in response:
            status = "Unverified"
            
        return status, reasoning

    async def _correct_content(self, content: str, issues: List[Dict]) -> str:
        """Rewrite content to fix hallucinations."""
        issues_text = ""
        issues_text = ""
        for issue in issues:
            issues_text += f"- Claim: {issue['claim']}\n  Status: {issue['status']}\n  Evidence against/for: {issue['evidence']}\n"
            if issue.get('corrective_evidence'):
                issues_text += f"  CORRECT INFO FOUND: {issue['corrective_evidence']}\n"
            issues_text += "\n"
            
        prompt = f"""The following text contains verified inaccuracies (hallucinations). Rewrite the text to correct these errors based on the evidence provided.
        
        Original Text:
        {content}
        
        Issues to Fix:
        {issues_text}
        
        Task: Rewrite the text to be factually accurate. 
        - If "CORRECT INFO FOUND" is provided, REPLACE the incorrect claim with the correct facts.
        - If no correct info is found, remove or qualify the claim to be safe.
        - Keep the original tone and structure as much as possible. 
        - Do NOT add meta-comments like "Correction:". Just output the corrected text."""
        
        return await self.deepseek.generate(prompt, max_tokens=len(content) + 500)

# Singleton instance
content_verifier = ContentVerifier()
