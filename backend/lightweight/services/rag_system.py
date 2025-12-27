"""
RAG (Retrieval-Augmented Generation) System

Stores and retrieves past solutions, patterns, and knowledge to improve future responses.
"""
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio

from core.cache import cache
from services.deepseek_direct import deepseek_direct_service


class RAGSystem:
    """Retrieval-Augmented Generation system for self-improvement."""
    
    def __init__(self):
        self.knowledge_base_path = Path("../../knowledge_base")
        self.knowledge_base_path.mkdir(parents=True, exist_ok=True)
        
        # Categories of knowledge
        self.categories = {
            "solutions": "solutions/",
            "patterns": "patterns/",
            "errors": "errors/",
            "agents": "agents/",
            "code_fixes": "code_fixes/"
        }
        
        # Initialize categories
        for cat_path in self.categories.values():
            (self.knowledge_base_path / cat_path).mkdir(parents=True, exist_ok=True)
    
    async def store_solution(
        self,
        problem: str,
        solution: str,
        context: Optional[Dict] = None,
        category: str = "solutions"
    ) -> str:
        """
        Store a problem-solution pair in the knowledge base.
        
        Args:
            problem: The problem description
            solution: The solution
            context: Additional context (code, errors, etc.)
            category: Category to store in
            
        Returns:
            Solution ID
        """
        # Generate ID from problem hash
        solution_id = hashlib.sha256(problem.encode()).hexdigest()[:16]
        
        entry = {
            "id": solution_id,
            "problem": problem,
            "solution": solution,
            "context": context or {},
            "category": category,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0,
            "success_rate": 0.0
        }
        
        # Store in file system
        file_path = self.knowledge_base_path / self.categories[category] / f"{solution_id}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, indent=2, ensure_ascii=False)
        
        # Also store in Redis for fast retrieval
        await cache.set(f"rag:{category}:{solution_id}", entry, ttl=86400 * 30)  # 30 days
        
        # Update index
        await self._update_index(category, solution_id, problem)
        
        print(f"💾 Stored solution: {solution_id} in {category}")
        return solution_id
    
    async def retrieve_similar(
        self,
        query: str,
        category: str = "solutions",
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve similar solutions to a query.
        
        Uses semantic similarity via LLM.
        """
        # Get all solutions in category
        category_path = self.knowledge_base_path / self.categories[category]
        solutions = []
        
        if category_path.exists():
            for file_path in category_path.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        solutions.append(json.load(f))
                except:
                    continue
        
        if not solutions:
            return []
        
        # Use LLM to find most similar solutions
        solutions_text = "\n\n".join([
            f"Solution {i+1}:\nProblem: {s['problem']}\nSolution: {s['solution'][:200]}..."
            for i, s in enumerate(solutions)
        ])
        
        similarity_prompt = f"""Given the following query and a list of past solutions, identify the top {top_k} most relevant solutions.

Query: {query}

Past Solutions:
{solutions_text}

Return a JSON array of indices (0-based) of the most relevant solutions, ordered by relevance.
Format: [0, 3, 1, ...]
"""
        
        try:
            response = await deepseek_direct_service.generate_content(
                prompt=similarity_prompt,
                system_prompt="You are a retrieval system. Return only JSON array of indices.",
                temperature=0.1,
                max_tokens=200,
                use_reasoning=False
            )
            
            # Parse response
            import re
            indices_match = re.search(r'\[[\d,\s]+\]', response)
            if indices_match:
                indices = json.loads(indices_match.group())
                # Get top_k solutions
                retrieved = [solutions[i] for i in indices[:top_k] if i < len(solutions)]
                return retrieved
        except Exception as e:
            print(f"⚠️ RAG retrieval error: {e}")
        
        # Fallback: return most recently used
        return sorted(solutions, key=lambda x: x.get("usage_count", 0), reverse=True)[:top_k]
    
    async def get_solution(self, problem: str, category: str = "solutions") -> Optional[Dict]:
        """Get exact solution for a problem."""
        solution_id = hashlib.sha256(problem.encode()).hexdigest()[:16]
        
        # Try Redis first
        entry = await cache.get(f"rag:{category}:{solution_id}")
        if entry:
            return entry
        
        # Try file system
        file_path = self.knowledge_base_path / self.categories[category] / f"{solution_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
                # Cache in Redis
                await cache.set(f"rag:{category}:{solution_id}", entry, ttl=86400 * 30)
                return entry
        
        return None
    
    async def update_success(self, solution_id: str, category: str = "solutions", success: bool = True):
        """Update success rate for a solution."""
        entry = await self._get_entry(solution_id, category)
        if entry:
            entry["usage_count"] = entry.get("usage_count", 0) + 1
            if success:
                current_rate = entry.get("success_rate", 0.0)
                count = entry.get("usage_count", 1)
                entry["success_rate"] = ((current_rate * (count - 1)) + 1.0) / count
            else:
                current_rate = entry.get("success_rate", 0.0)
                count = entry.get("usage_count", 1)
                entry["success_rate"] = ((current_rate * (count - 1)) + 0.0) / count
            
            # Save updated entry
            file_path = self.knowledge_base_path / self.categories[category] / f"{solution_id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(entry, f, indent=2, ensure_ascii=False)
            
            await cache.set(f"rag:{category}:{solution_id}", entry, ttl=86400 * 30)
    
    async def _get_entry(self, solution_id: str, category: str) -> Optional[Dict]:
        """Get entry by ID."""
        # Try Redis
        entry = await cache.get(f"rag:{category}:{solution_id}")
        if entry:
            return entry
        
        # Try file system
        file_path = self.knowledge_base_path / self.categories[category] / f"{solution_id}.json"
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None
    
    async def _update_index(self, category: str, solution_id: str, problem: str):
        """Update search index."""
        index_key = f"rag:index:{category}"
        index = await cache.get(index_key) or {}
        index[solution_id] = problem[:200]  # Store first 200 chars
        await cache.set(index_key, index, ttl=86400 * 30)


# Global instance
rag_system = RAGSystem()




