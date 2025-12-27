"""
Intelligent Task Classifier

Uses pattern matching and heuristics to classify tasks and determine
the best execution strategy (direct, worker, parallel, etc.)
"""
from typing import Dict, List, Optional, Tuple
import re


class TaskClassifier:
    """Classify tasks and determine execution strategy."""
    
    # FORCE these PHRASES to use workers - must be multi-word to avoid false positives
    # Single words like "write" would match "write the equation" which should be direct
    FORCE_WORKER_KEYWORDS = [
        "essay about", "essay on", "write an essay", "write essay",
        "document about", "document on", "create a document", "create document",
        "report about", "report on", "write a report", "write report",
        "paper about", "paper on", "write a paper", "write paper",
        "article about", "article on", "write an article", "write article",
        "create a file", "make a file", "generate a file",
        "long form", "multi-page", "multiple pages",
    ]
    
    # Task complexity patterns
    SIMPLE_PATTERNS = [
        r"^(hi|hello|hey|greetings)",
        r"^(what|how|when|where|why)\s+",
        r"^(show|list|get|fetch)\s+",
        r"^(help|assist)\s*$"
    ]
    
    COMPLEX_PATTERNS = [
        r"(write|create|generate|make|build|develop)\s+(an?\s+)?(essay|document|report|paper|article|content)",
        r"(and|with|include|add|plus)\s+(image|picture|photo|graph|chart|diagram)",
        r"(search|find|look\s+for)\s+(and|then|after)\s+",
        r"(multiple|several|many|various)\s+",
        r"(step|stage|phase|process)\s+",
        r"\d+\s+(word|page|section|chapter|image|picture)"
    ]
    
    PARALLEL_PATTERNS = [
        r"(search|find)\s+.*\s+(and|&)\s+(generate|create|make)",
        r"(image|picture).*\s+(and|&)\s+(image|picture)",
        r"multiple\s+(search|image|task)"
    ]
    
    WORKER_REQUIRED_PATTERNS = [
        r"(essay|document|report|paper).*\s+\d+\s+word",  # With word count
        r"(write|create|generate|make)\s+(an?\s+)?(essay|document|report|paper)",  # Any essay request
        r"(generate|create).*\s+(and|with).*\s+(image|picture|photo)",  # With images
        r"complex\s+(task|request|job)",
        r"(multi|many|several)\s+step",
        r"(essay|paper|document).*\s+(with|and).*\s+(image|picture|photo)",  # Essay + image
        r"(write|create).*\s+about\s+.*\s+(with|and).*\s+(pic|image|picture)",  # "about X with pic"
    ]
    
    def classify(self, message: str) -> Dict:
        """
        Classify a task and return execution strategy.
        
        Returns:
            {
                "complexity": "simple|medium|complex",
                "strategy": "direct|worker|parallel",
                "estimated_time": seconds,
                "requires_planning": bool,
                "parallel_tools": List[str],
                "priority": "low|normal|high|urgent"
            }
        """
        message_lower = message.lower().strip()
        word_count = len(message.split())
        
        # FORCE workers for ANY content generation - check this FIRST
        if any(keyword in message_lower for keyword in self.FORCE_WORKER_KEYWORDS):
            result = {
                "complexity": "complex",
                "strategy": "worker",  # ALWAYS worker for content
                "estimated_time": 30,
                "requires_planning": True,
                "parallel_tools": [],
                "priority": "normal",
                "word_count_requirement": 0
            }
            print(f"🔍 FORCE WORKER: Detected keywords {[k for k in self.FORCE_WORKER_KEYWORDS if k in message_lower]}")
            print(f"   Strategy: WORKER (forced)")
            return result
        
        # Check for simple tasks
        is_simple = any(re.match(pattern, message_lower) for pattern in self.SIMPLE_PATTERNS)
        if is_simple and word_count < 10:
            return {
                "complexity": "simple",
                "strategy": "direct",
                "estimated_time": 1,
                "requires_planning": False,
                "parallel_tools": [],
                "priority": "normal"
            }
        
        # Check for complex tasks requiring workers
        is_worker_required = any(re.search(pattern, message_lower) for pattern in self.WORKER_REQUIRED_PATTERNS)
        is_complex = any(re.search(pattern, message_lower) for pattern in self.COMPLEX_PATTERNS)
        is_parallel = any(re.search(pattern, message_lower) for pattern in self.PARALLEL_PATTERNS)
        
        # Check if it's an essay/document request
        is_essay = re.search(r"(write|create|generate|make)\s+(an?\s+)?(essay|document|report|paper)", message_lower)
        has_images = "image" in message_lower or "picture" in message_lower or "pic" in message_lower
        
        # Extract word count requirements
        word_count_match = re.search(r"(\d+)\s+word", message_lower)
        required_words = int(word_count_match.group(1)) if word_count_match else 0
        
        # Determine complexity
        if is_worker_required or (is_essay and has_images) or (is_complex and word_count > 15) or required_words > 500:
            complexity = "complex"
            strategy = "worker"
            estimated_time = max(30, required_words // 50)  # ~50 words per second
            priority = "high" if required_words > 1000 else "normal"
        elif is_complex or word_count > 10:
            complexity = "medium"
            strategy = "parallel" if is_parallel else "direct"
            estimated_time = 10 + (word_count * 0.5)
            priority = "normal"
        else:
            complexity = "simple"
            strategy = "direct"
            estimated_time = 5
            priority = "normal"
        
        # Detect parallel tools needed
        parallel_tools = []
        if "image" in message_lower or "picture" in message_lower:
            if "search" in message_lower or "find" in message_lower:
                parallel_tools.append("image_search")
            if "generate" in message_lower or "create" in message_lower:
                parallel_tools.append("image_generate")
        
        if "search" in message_lower or "research" in message_lower:
            parallel_tools.append("web_search")
        
        # Determine if planning is needed
        requires_planning = complexity != "simple" or len(parallel_tools) > 1
        
        return {
            "complexity": complexity,
            "strategy": strategy,
            "estimated_time": int(estimated_time),
            "requires_planning": requires_planning,
            "parallel_tools": parallel_tools,
            "priority": priority,
            "word_count_requirement": required_words
        }
    
    def should_use_worker(self, message: str) -> bool:
        """Quick check if task should use worker."""
        classification = self.classify(message)
        return classification["strategy"] == "worker"
    
    def get_priority(self, message: str) -> str:
        """Get task priority."""
        classification = self.classify(message)
        return classification["priority"]


# Global instance
task_classifier = TaskClassifier()




