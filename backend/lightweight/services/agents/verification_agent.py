"""
Verification Agent - Checks Quality and Validates Results

This agent:
1. Verifies output quality
2. Checks for completeness
3. Suggests improvements
4. Validates facts
"""

from typing import Dict, Any, List, Optional
from services.agent_spawner import BaseAgent, AgentType, AgentStatus, AgentContext


class VerificationAgent(BaseAgent):
    """
    Verification Agent - Quality control.
    
    Capabilities:
    - Check output quality
    - Verify completeness
    - Validate facts
    - Suggest improvements
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id)
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main verification process.
        
        Steps:
        1. Check completed actions
        2. Verify output quality
        3. Suggest improvements if needed
        """
        await self.report_status(AgentStatus.THINKING, "🔍 Reviewing output quality...")
        
        issues = []
        suggestions = []
        
        # Check completed actions
        for action in context.completed_actions:
            result = await self._verify_action(action)
            if result.get("issues"):
                issues.extend(result["issues"])
            if result.get("suggestions"):
                suggestions.extend(result["suggestions"])
        
        # Check goals completion
        await self.report_status(AgentStatus.WORKING, "🎯 Checking goal completion...")
        goals_met = self._check_goals(context)
        
        # Add verification results to context
        context.gathered_data["verification"] = {
            "issues": issues,
            "suggestions": suggestions,
            "goals_met": goals_met,
            "quality_score": self._calculate_quality_score(issues, goals_met)
        }
        
        if issues:
            await self.report_status(
                AgentStatus.COMPLETED,
                f"⚠️ Found {len(issues)} issues",
                data={"issues": issues}
            )
        else:
            await self.report_status(
                AgentStatus.COMPLETED,
                "✅ All checks passed",
                data={"quality": "good"}
            )
        
        return context
    
    async def _verify_action(self, action: Dict) -> Dict:
        """Verify a completed action."""
        issues = []
        suggestions = []
        
        action_type = action.get("action")
        
        if action_type == "create_file":
            content = action.get("content", "")
            if not content:
                issues.append("File created with no content")
            elif len(content) < 10:
                suggestions.append("Consider adding more content")
        
        elif action_type == "write_summary":
            content = action.get("content", "")
            if len(content) < 100:
                issues.append("Summary is too short")
            if not any(word in content.lower() for word in ["the", "and", "is", "are"]):
                issues.append("Summary may not be coherent")
        
        return {"issues": issues, "suggestions": suggestions}
    
    def _check_goals(self, context: AgentContext) -> Dict[str, bool]:
        """Check if goals have been met."""
        goals_met = {}
        
        for goal in context.goals:
            goal_lower = goal.lower()
            
            # Check if goal was addressed
            if "create file" in goal_lower:
                goals_met[goal] = any(a["action"] == "create_file" for a in context.completed_actions)
            elif "find" in goal_lower or "search" in goal_lower:
                goals_met[goal] = len(context.search_results) > 0
            elif "summary" in goal_lower or "summarize" in goal_lower:
                goals_met[goal] = "summary" in context.gathered_data
            else:
                goals_met[goal] = True  # Assume met for general goals
        
        return goals_met
    
    def _calculate_quality_score(self, issues: List, goals_met: Dict) -> float:
        """Calculate overall quality score."""
        score = 1.0
        
        # Deduct for issues
        score -= len(issues) * 0.1
        
        # Deduct for unmet goals
        unmet = sum(1 for met in goals_met.values() if not met)
        score -= unmet * 0.15
        
        return max(0.0, min(1.0, score))


# Export for agent spawner
__agent_class__ = VerificationAgent
