"""
Intelligent Router - LLM-based Natural Language to Function Mapping

Maps natural language requests to thesis generation workflows without requiring slash commands.
Uses Gemini's function calling to intelligently route requests and ask clarifying questions.
"""

import re
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
import google.generativeai as genai
import os


class IntelligentRouter:
    """Routes natural language requests to appropriate thesis generation functions."""
    
    
    def __init__(self):
        # Define available thesis workflows
        self.thesis_workflows = {
            "generate_chapter_1": {
                "description": "Generate Chapter 1 (Introduction) of the thesis",
                "required_params": ["topic", "case_study", "objectives"],
                "workflow_path": ".agent/workflows/generate-chapter1.md"
            },
            "generate_chapter_2": {
                "description": "Generate Chapter 2 (Literature Review) of the thesis",
                "required_params": ["topic", "case_study", "objectives"],
                "workflow_path": ".agent/workflows/generate-chapter2.md"
            },
            "generate_chapter_3": {
                "description": "Generate Chapter 3 (Methodology) of the thesis",
                "required_params": ["topic", "case_study", "objectives"],
                "workflow_path": ".agent/workflows/generate-chapter3.md"
            },
            "generate_chapter_4": {
                "description": "Generate Chapter 4 (Data Analysis) of the thesis",
                "required_params": ["topic", "case_study", "objectives"],
                "workflow_path": ".agent/workflows/generate-chapter4.md"
            },
            "generate_dataset": {
                "description": "Generate synthetic research dataset (questionnaires, interviews, etc.)",
                "required_params": ["objectives"],
                "workflow_path": ".agent/workflows/generate-dataset.md"
            },
            "generate_study_tools": {
                "description": "Generate study tools (questionnaires, interview guides)",
                "required_params": ["objectives"],
                "workflow_path": ".agent/workflows/generate-study-tools.md"
            },
            "combine_thesis": {
                "description": "Combine all chapters into a single thesis document",
                "required_params": [],
                "workflow_path": ".agent/workflows/combine-thesis.md"
            },
            "generate_full_thesis": {
                "description": "Generate complete PhD thesis (all 6 chapters)",
                "required_params": ["topic", "case_study", "objectives"],
                "workflow_path": ".agent/workflows/generate-full-thesis.md"
            }
        }
        
        # Intent patterns for quick matching (fallback if LLM unavailable)
        self.intent_patterns = {
            "generate_chapter": [
                r"(?:write|generate|create|make).*chapter\s*(\d+)",
                r"chapter\s*(\d+)",
                r"(?:do|start|begin).*chapter\s*(\d+)",
            ],
            "generate_dataset": [
                r"(?:create|generate|make).*(?:dataset|data)",
                r"(?:need|want).*data",
                r"synthetic.*data",
            ],
            "generate_study_tools": [
                r"(?:create|generate|make).*(?:questionnaire|interview|survey)",
                r"study.*tools",
            ],
            "combine_thesis": [
                r"(?:combine|merge|join).*(?:chapters|thesis)",
                r"(?:create|make).*(?:full|complete).*(?:thesis|document)",
            ],
            "generate_full_thesis": [
                r"(?:generate|create|write).*(?:full|complete|entire).*thesis",
                r"(?:all|every).*chapters",
            ]
        }
    
    async def route(self, user_message: str, session_context: Dict = None) -> Dict[str, Any]:
        """
        Route user message to appropriate function.
        
        Args:
            user_message: User's natural language request
            session_context: Session metadata (topic, objectives, etc.)
            
        Returns:
            {
                "action": "function_name" or "clarify",
                "params": {...},
                "needs_clarification": bool,
                "clarification_message": str (if needs clarification),
                "workflow_path": str (if action found)
            }
        """
        session_context = session_context or {}
        
        # Try LLM-based routing first
        try:
            return await self._route_with_llm(user_message, session_context)
        except Exception as e:
            print(f"⚠️ LLM routing failed, using pattern matching: {e}")
            return self._route_with_patterns(user_message, session_context)
    
    async def _route_with_llm(self, user_message: str, session_context: Dict) -> Dict[str, Any]:
        """Use DeepSeek function calling (or prompt engineering) to route the request."""
        
        # Build context prompt
        context_parts = []
        if session_context.get("topic"):
            context_parts.append(f"Topic: {session_context['topic']}")
        if session_context.get("case_study"):
            context_parts.append(f"Case Study: {session_context['case_study']}")
        if session_context.get("objectives"):
            objectives = session_context['objectives']
            if isinstance(objectives, list):
                context_parts.append(f"Objectives: {', '.join(objectives)}")
            else:
                context_parts.append(f"Objectives: {objectives}")
        
        context_str = "\n".join(context_parts) if context_parts else "No context available yet."
        
        # Build function descriptions
        function_descriptions = []
        for func_name, func_info in self.thesis_workflows.items():
            params = ", ".join(func_info["required_params"])
            function_descriptions.append(f"- {func_name}: {func_info['description']} (Requires: {params})")
        
        functions_str = "\n".join(function_descriptions)

        prompt = f"""You are an intelligent router for a thesis generation system. 
Your goal is to map the user's natural language request to one of the available functions.

Current Session Context:
{context_str}

User Request: "{user_message}"

Available Functions:
{functions_str}

Instructions:
1. Analyze the user's request and the current context.
2. EXTRACT any usage information (topic, case study, objectives) from the request.
3. If the user wants to perform an action available in the functions list:
   - Check if all required parameters are present (either in context or extracted from request).
   - If YES: Return JSON {{ "action": "function_name", "params": {{...all params...}}, "needs_clarification": false }}
   - If NO: Return JSON {{ "action": "clarify", "params": {{...extracted partial params...}}, "needs_clarification": true, "clarification_message": "Question asking for the FIRST missing parameter" }}
4. If the user is just chatting or the request doesn't match a function, return JSON {{ "action": "unknown", "params": {{}}, "needs_clarification": false }}

IMPORTANT: 
- ALWAYS put extracted information in 'params' (e.g., if user says "topic is X", put "topic": "X" in params).
- If user says "make chapter 1 on [topic]", extract [topic] as the "topic" parameter.

Return ONLY valid JSON.
"""
        
        try:
            from services.deepseek_direct import deepseek_direct_service
            response_text = await deepseek_direct_service.generate_content(
                prompt=prompt,
                system_prompt="You are a strict JSON-outputting routing agent.",
                temperature=0.1
            )
            
            # clean response
            response_text = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(response_text)
            
        except Exception as e:
            print(f"⚠️ DeepSeek routing failed: {e}")
            # Fallback to pattern matching
            return self._route_with_patterns(user_message, session_context)
    
    def _route_with_patterns(self, user_message: str, session_context: Dict) -> Dict[str, Any]:
        """Fallback pattern-based routing."""
        msg_lower = user_message.lower().strip()
        
        # Check for chapter generation
        for pattern in self.intent_patterns["generate_chapter"]:
            match = re.search(pattern, msg_lower)
            if match:
                chapter_num = match.group(1)
                func_name = f"generate_chapter_{chapter_num}"
                
                if func_name in self.thesis_workflows:
                    # Check if we have required params
                    missing_params = self._check_missing_params(func_name, session_context)
                    
                    if missing_params:
                        return {
                            "action": "clarify",
                            "params": {"chapter_number": chapter_num},
                            "needs_clarification": True,
                            "clarification_message": self._build_clarification_message(missing_params)
                        }
                    
                    return {
                        "action": func_name,
                        "params": self._extract_params(func_name, session_context),
                        "needs_clarification": False,
                        "workflow_path": self.thesis_workflows[func_name]["workflow_path"]
                    }
        
        # Check for dataset generation
        for pattern in self.intent_patterns["generate_dataset"]:
            if re.search(pattern, msg_lower):
                missing_params = self._check_missing_params("generate_dataset", session_context)
                
                if missing_params:
                    return {
                        "action": "clarify",
                        "params": {},
                        "needs_clarification": True,
                        "clarification_message": self._build_clarification_message(missing_params)
                    }
                
                return {
                    "action": "generate_dataset",
                    "params": self._extract_params("generate_dataset", session_context),
                    "needs_clarification": False,
                    "workflow_path": self.thesis_workflows["generate_dataset"]["workflow_path"]
                }
        
        # Check for combine thesis
        for pattern in self.intent_patterns["combine_thesis"]:
            if re.search(pattern, msg_lower):
                return {
                    "action": "combine_thesis",
                    "params": {},
                    "needs_clarification": False,
                    "workflow_path": self.thesis_workflows["combine_thesis"]["workflow_path"]
                }
        
        # Check for full thesis generation
        for pattern in self.intent_patterns["generate_full_thesis"]:
            if re.search(pattern, msg_lower):
                missing_params = self._check_missing_params("generate_full_thesis", session_context)
                
                if missing_params:
                    return {
                        "action": "clarify",
                        "params": {},
                        "needs_clarification": True,
                        "clarification_message": self._build_clarification_message(missing_params)
                    }
                
                return {
                    "action": "generate_full_thesis",
                    "params": self._extract_params("generate_full_thesis", session_context),
                    "needs_clarification": False,
                    "workflow_path": self.thesis_workflows["generate_full_thesis"]["workflow_path"]
                }
        
        # No match found
        return {
            "action": "unknown",
            "params": {},
            "needs_clarification": False,
            "clarification_message": None
        }
    
    def _check_missing_params(self, func_name: str, session_context: Dict) -> List[str]:
        """Check which required parameters are missing from context."""
        required = self.thesis_workflows[func_name]["required_params"]
        missing = []
        
        for param in required:
            if param not in session_context or not session_context[param]:
                missing.append(param)
        
        return missing
    
    def _extract_params(self, func_name: str, session_context: Dict) -> Dict[str, Any]:
        """Extract parameters from session context."""
        required = self.thesis_workflows[func_name]["required_params"]
        params = {}
        
        for param in required:
            if param in session_context:
                params[param] = session_context[param]
        
        return params
    
    def _build_clarification_message(self, missing_params: List[str]) -> str:
        """Build a friendly clarification message - asks ONE question at a time."""
        if not missing_params:
            return ""
        
        # Ask for the FIRST missing parameter only (more conversational)
        first_missing = missing_params[0]
        
        messages = {
            "topic": "What is your research topic? (e.g., 'Teacher Performance in Uganda')",
            "case_study": "What is your case study or research context? (e.g., 'Kampala District')",
            "objectives": (
                "What are your research objectives?\n\n"
                "Please provide 3-5 specific objectives. For example:\n"
                "1. To assess factors influencing teacher performance\n"
                "2. To evaluate the impact of training programs\n"
                "3. To recommend improvements for teacher development\n\n"
                "You can list them separated by commas or as numbered points."
            )
        }
        
        question = messages.get(first_missing, f"What is the {first_missing}?")
        
        # Add a friendly intro
        return f"Great! I can help you with that. {question}"
    
    def validate_and_suggest_objectives(self, objectives: List[str]) -> Dict[str, Any]:
        """
        Validate objectives and suggest improvements (like Manus would).
        
        Returns:
            {
                "valid": bool,
                "message": str (suggestion or confirmation),
                "suggested_objectives": List[str] (if improvements suggested)
            }
        """
        if not objectives or len(objectives) < 3:
            return {
                "valid": False,
                "message": (
                    "I notice you have fewer than 3 objectives. "
                    "For a strong thesis, I recommend having at least 3-5 specific objectives. "
                    "Would you like me to suggest some based on your topic?"
                ),
                "suggested_objectives": []
            }
        
        # Check if objectives are too vague
        vague_words = ["study", "research", "investigate", "examine"]
        vague_count = sum(1 for obj in objectives if any(word in obj.lower() for word in vague_words))
        
        if vague_count >= len(objectives) * 0.7:  # 70% are vague
            return {
                "valid": False,
                "message": (
                    "Your objectives seem a bit general. "
                    "Strong objectives should be specific and measurable. "
                    "For example, instead of 'To study teacher performance', "
                    "try 'To assess the impact of training programs on teacher performance metrics'.\n\n"
                    "Would you like me to help refine these?"
                ),
                "suggested_objectives": []
            }
        
        # Check if objectives are too long
        long_objectives = [obj for obj in objectives if len(obj.split()) > 20]
        if long_objectives:
            return {
                "valid": False,
                "message": (
                    "Some of your objectives are quite lengthy. "
                    "Objectives should be concise and focused. "
                    "Would you like me to help break them down into clearer, more focused statements?"
                ),
                "suggested_objectives": []
            }
        
        # All good!
        return {
            "valid": True,
            "message": (
                f"Perfect! I have {len(objectives)} objectives:\n" +
                "\n".join(f"{i+1}. {obj}" for i, obj in enumerate(objectives)) +
                "\n\nShall I proceed with generating the chapter?"
            ),
            "suggested_objectives": objectives
        }


# Global instance
intelligent_router = IntelligentRouter()
