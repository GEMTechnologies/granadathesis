"""
Action Agent - Executes Tasks Based on Understanding

This agent:
1. Creates and edits files
2. Executes code
3. Performs browser automation
4. Completes tasks
"""

from typing import Dict, Any, List, Optional
from pathlib import Path
from services.agent_spawner import BaseAgent, AgentType, AgentStatus, AgentContext


class ActionAgent(BaseAgent):
    """
    Action Agent - Executes tasks after understanding.
    
    Capabilities:
    - Create files
    - Edit files
    - Execute code
    - Browser automation
    - Task completion
    """
    
    def __init__(self, agent_type: AgentType, session_id: str, parent_id: Optional[str] = None):
        super().__init__(agent_type, session_id, parent_id)
    
    async def run(self, context: AgentContext) -> AgentContext:
        """
        Main action execution process.
        
        Based on context.required_actions, performs:
        - create_file
        - edit_file
        - execute_code
        - present_results
        """
        await self.report_status(AgentStatus.THINKING, "⚡ Planning execution...")
        
        actions = context.required_actions
        
        # Execute actions based on plan
        if "create_file" in actions:
            await self._handle_create_file(context)
        
        if "edit_file" in actions:
            await self._handle_edit_file(context)
        
        if "present_results" in actions:
            await self._handle_present_results(context)
        
        if "write_summary" in actions:
            await self._handle_write_summary(context)
        
        await self.report_status(
            AgentStatus.COMPLETED,
            f"✅ Completed {len([a for a in context.action_plan if a.get('status') == 'completed'])} actions"
        )
        
        return context
    
    async def _handle_create_file(self, context: AgentContext):
        """Create a file based on context."""
        await self.report_status(AgentStatus.WORKING, "📄 Creating file...")
        
        # Get filename from entities
        filename = context.entities.get("filename", "new_file.md")
        if not isinstance(filename, str):
            filename = filename[0] if filename else "new_file.md"
        
        # Get content from entities or goals
        content = context.entities.get("word_content", "")
        if not content and context.entities.get("quoted_content"):
            content = context.entities["quoted_content"][0]
        
        # Create file
        workspace_id = context.workspace_id or "default"
        if workspace_id == "default":
            workspace_dir = Path("/home/gemtech/Desktop/thesis")
        else:
            workspace_dir = Path(f"workspaces/{workspace_id}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = workspace_dir / filename
        file_path.write_text(content)
        
        # Record action
        context.completed_actions.append({
            "action": "create_file",
            "filename": filename,
            "path": str(file_path),
            "content": content
        })
        
        # Update action plan
        for action in context.action_plan:
            if action["action"] == "create_file":
                action["status"] = "completed"
                action["result"] = {"path": str(file_path)}
        
        # Publish file created event
        await self._ensure_connections()
        if self.events:
            await self.events.publish(
                self.id,
                "file_created",
                {"path": filename, "full_path": str(file_path)},
                session_id=self.session_id
            )
        
        await self.report_status(AgentStatus.WORKING, f"✅ Created: {filename}")
    
    async def _handle_edit_file(self, context: AgentContext):
        """Edit an existing file."""
        await self.report_status(AgentStatus.WORKING, "✏️ Editing file...")
        
        # Get file to edit (from recent files or entities)
        from services.central_brain import central_brain
        brain_ctx = await central_brain.get_context(self.session_id)
        
        if brain_ctx.recent_files:
            file_path = Path(brain_ctx.recent_files[0])
        else:
            await self.report_status(AgentStatus.FAILED, "❌ No file to edit")
            return
        
        # Get new content
        new_content = context.entities.get("word_content", context.user_message)
        
        # Write content
        file_path.write_text(new_content)
        
        context.completed_actions.append({
            "action": "edit_file",
            "path": str(file_path),
            "content": new_content
        })
        
        await self.report_status(AgentStatus.WORKING, f"✅ Updated: {file_path.name}")
    
    async def _handle_present_results(self, context: AgentContext):
        """Format and present search results."""
        await self.report_status(AgentStatus.WORKING, "📊 Formatting results...")
        
        results = context.search_results
        if not results:
            return
        
        # Format results for display
        formatted = []
        for i, r in enumerate(results[:10]):
            if r.get("type") == "paper":
                formatted.append(f"📚 **{r.get('title', 'Untitled')}** ({r.get('year', 'N/A')})")
                formatted.append(f"   Authors: {', '.join(r.get('authors', [])[:3])}")
                if r.get("abstract"):
                    formatted.append(f"   {r['abstract'][:150]}...")
            else:
                formatted.append(f"🌐 **[{r.get('title', 'Result')}]({r.get('url', '')})**")
                if r.get("content"):
                    formatted.append(f"   {r['content'][:150]}...")
            formatted.append("")
        
        context.gathered_data["formatted_results"] = "\n".join(formatted)
    
    async def _handle_write_summary(self, context: AgentContext):
        """Write a summary of gathered research."""
        await self.report_status(AgentStatus.WORKING, "📝 Writing summary...")
        
        # Use LLM to summarize
        try:
            from services.deepseek_direct import deepseek_direct
            
            # Build prompt from research results
            research_content = []
            for r in context.search_results[:5]:
                if r.get("content"):
                    research_content.append(r["content"][:500])
                elif r.get("abstract"):
                    research_content.append(r["abstract"])
            
            prompt = f"""Based on the following research findings, write a concise summary:

{chr(10).join(research_content)}

Write a clear, well-structured summary of the key findings."""

            summary = ""
            async for chunk in deepseek_direct.generate_stream(prompt):
                summary += chunk
            
            context.gathered_data["summary"] = summary
            
            # Save summary to file
            workspace_id = context.workspace_id or "default"
            if workspace_id == "default":
                workspace_dir = Path("/home/gemtech/Desktop/thesis")
            else:
                workspace_dir = Path(f"workspaces/{workspace_id}")
            workspace_dir.mkdir(parents=True, exist_ok=True)
            
            summary_path = workspace_dir / "summary.md"
            summary_path.write_text(f"# Research Summary\n\n{summary}")
            
            context.completed_actions.append({
                "action": "write_summary",
                "path": str(summary_path),
                "content": summary
            })
            
        except Exception as e:
            print(f"⚠️ Summary writing failed: {e}")


# Export for agent spawner
__agent_class__ = ActionAgent
