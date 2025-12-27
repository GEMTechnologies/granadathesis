"""
Agent State Monitor

Monitors agent health, state, and availability.
"""
import asyncio
import importlib
import inspect
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from core.cache import cache
from services.self_healing import self_healing_system
from services.rag_system import rag_system


class AgentMonitor:
    """Monitor agent states and health."""
    
    def __init__(self):
        self.agents_dir = Path("agents")
        self.workers_dir = Path("workers")
        self.services_dir = Path("services")
        
        # Known agent types
        self.agent_types = {
            "agents": self.agents_dir,
            "workers": self.workers_dir,
            "services": self.services_dir
        }
    
    async def get_all_agents(self) -> Dict[str, Dict]:
        """Get status of all agents."""
        all_agents = {}
        
        for agent_type, agent_dir in self.agent_types.items():
            if not agent_dir.exists():
                continue
            
            for file_path in agent_dir.glob("*.py"):
                if file_path.name.startswith("__"):
                    continue
                
                agent_name = file_path.stem
                full_name = f"{agent_type}.{agent_name}"
                
                # Check health
                health = await self_healing_system.check_agent_health(agent_name)
                
                # Get state from cache
                state_key = f"agent:state:{full_name}"
                state = await cache.get(state_key) or {
                    "status": "unknown",
                    "last_used": None,
                    "usage_count": 0,
                    "error_count": 0
                }
                
                all_agents[full_name] = {
                    "name": agent_name,
                    "type": agent_type,
                    "file": str(file_path),
                    "health": health,
                    "state": state
                }
        
        return all_agents
    
    async def update_agent_state(
        self,
        agent_name: str,
        status: str = "active",
        success: bool = True
    ):
        """Update agent state after use."""
        state_key = f"agent:state:{agent_name}"
        state = await cache.get(state_key) or {
            "status": "unknown",
            "last_used": None,
            "usage_count": 0,
            "error_count": 0,
            "success_count": 0
        }
        
        state["status"] = status
        state["last_used"] = datetime.now().isoformat()
        state["usage_count"] = state.get("usage_count", 0) + 1
        
        if success:
            state["success_count"] = state.get("success_count", 0) + 1
        else:
            state["error_count"] = state.get("error_count", 0) + 1
        
        await cache.set(state_key, state, ttl=86400 * 7)  # 7 days
    
    async def check_missing_agents(self, required_agents: List[str]) -> Dict:
        """Check if required agents exist, generate missing ones."""
        missing = []
        existing = []
        
        for agent_name in required_agents:
            # Check if agent exists
            found = False
            for agent_type, agent_dir in self.agent_types.items():
                agent_file = agent_dir / f"{agent_name}.py"
                if agent_file.exists():
                    existing.append(f"{agent_type}.{agent_name}")
                    found = True
                    break
            
            if not found:
                missing.append(agent_name)
        
        # Generate missing agents
        generated = []
        for agent_name in missing:
            try:
                # Infer purpose from name
                purpose = agent_name.replace("_", " ").title()
                
                result = await self_healing_system.generate_missing_agent(
                    agent_name=agent_name,
                    purpose=f"Handle {purpose} tasks",
                    requirements=["Async support", "Error handling", "Type hints"]
                )
                
                if result.get("success"):
                    generated.append(agent_name)
            except Exception as e:
                print(f"⚠️ Failed to generate agent {agent_name}: {e}")
        
        return {
            "existing": existing,
            "missing": missing,
            "generated": generated
        }
    
    async def get_agent_stats(self) -> Dict:
        """Get statistics about all agents."""
        agents = await self.get_all_agents()
        
        stats = {
            "total": len(agents),
            "healthy": 0,
            "unhealthy": 0,
            "missing": 0,
            "total_usage": 0,
            "total_errors": 0,
            "by_type": {}
        }
        
        for agent_name, agent_info in agents.items():
            health_status = agent_info["health"]["status"]
            agent_type = agent_info["type"]
            
            if health_status == "healthy":
                stats["healthy"] += 1
            elif health_status == "missing":
                stats["missing"] += 1
            else:
                stats["unhealthy"] += 1
            
            state = agent_info["state"]
            stats["total_usage"] += state.get("usage_count", 0)
            stats["total_errors"] += state.get("error_count", 0)
            
            if agent_type not in stats["by_type"]:
                stats["by_type"][agent_type] = {
                    "count": 0,
                    "healthy": 0,
                    "unhealthy": 0
                }
            
            stats["by_type"][agent_type]["count"] += 1
            if health_status == "healthy":
                stats["by_type"][agent_type]["healthy"] += 1
            else:
                stats["by_type"][agent_type]["unhealthy"] += 1
        
        return stats
    
    async def auto_heal_agents(self) -> Dict:
        """Automatically heal unhealthy agents."""
        agents = await self.get_all_agents()
        healed = []
        failed = []
        
        for agent_name, agent_info in agents.items():
            health = agent_info["health"]
            
            if health["status"] in ["missing", "incomplete", "error"]:
                # Try to heal
                issues = health.get("issues", [])
                suggestions = health.get("suggestions", [])
                
                if "Generate missing agent" in suggestions:
                    # Generate agent
                    result = await self_healing_system.generate_missing_agent(
                        agent_name=agent_info["name"],
                        purpose=f"Handle {agent_info['name']} tasks"
                    )
                    
                    if result.get("success"):
                        healed.append(agent_name)
                    else:
                        failed.append({"agent": agent_name, "error": result.get("error")})
                
                elif "Add methods" in str(suggestions):
                    # Try to fix incomplete agent
                    result = await self_healing_system.fix_code(
                        file_path=agent_info["file"],
                        issue_description=f"Missing methods: {issues}"
                    )
                    
                    if result.get("success"):
                        healed.append(agent_name)
                    else:
                        failed.append({"agent": agent_name, "error": result.get("error")})
        
        return {
            "healed": healed,
            "failed": failed,
            "total_checked": len(agents)
        }


# Global instance
agent_monitor = AgentMonitor()




