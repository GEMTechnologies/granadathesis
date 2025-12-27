"""
Intelligent Intent System - TRUE AI Understanding

Handles ANY user request with intelligence:
- Fast pattern matching for common cases
- LLM-based understanding for ambiguous/weird cases  
- Graceful handling of impossible requests
- Context-aware responses
- Speed-first, intelligence-always

Users are weird and aggressive - this handles EVERYTHING.
"""

import json
import re
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class IntentType(Enum):
    """All possible user intents."""
    # Fast/Simple
    GREETING = "greeting"
    SIMPLE_QUESTION = "simple_question"
    CASUAL_CHAT = "casual_chat"
    
    # Search
    IMAGE_SEARCH = "image_search"
    WEB_SEARCH = "web_search"
    PAPER_SEARCH = "paper_search"
    
    # Generation
    IMAGE_GENERATE = "image_generate"
    CONTENT_WRITE = "content_write"
    CODE_GENERATE = "code_generate"
    
    # File Operations
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_LIST = "file_list"
    PDF_ACTION = "pdf_action"
    
    # Complex Pipelines
    RESEARCH_SYNTHESIS = "research_synthesis"
    CHAPTER_GENERATE = "chapter_generate"  # Thesis chapter generation
    CHAPTER_FOUR_GENERATE = "chapter_four_generate"  # Chapter 4 data analysis
    CHAPTER_FIVE_GENERATE = "chapter_five_generate"  # Chapter 5 results and discussion
    CHAPTER_SIX_GENERATE = "chapter_six_generate"  # Chapter 6 conclusions and recommendations
    THESIS_COMBINE_GENERATE = "thesis_combine_generate"  # Combine chapters into single thesis
    DATA_GENERATE = "data_generate"  # Synthetic dataset generation
    COMPLEX_TASK = "complex_task"
    
    # Special Cases
    UNSUPPORTED = "unsupported"
    CLARIFICATION_NEEDED = "clarification_needed"
    OFF_TOPIC = "off_topic"
    UNKNOWN = "unknown"


class RouteType(Enum):
    """Where to route the request."""
    INSTANT = "instant"           # Pre-computed response
    DIRECT_LLM = "direct_llm"     # Stream LLM directly (fastest)
    TOOL_DIRECT = "tool_direct"   # Call tool directly, no planner
    PIPELINE = "pipeline"         # Multi-step pipeline
    ORCHESTRATOR = "orchestrator" # Full intelligent orchestrator
    GRACEFUL = "graceful"         # Graceful decline


@dataclass
class IntentResult:
    """Result of intent understanding."""
    intent: IntentType
    route: RouteType
    confidence: float  # 0.0 to 1.0
    params: Dict[str, Any]  # Extracted parameters
    message: str  # Message to user (for graceful/clarification)
    reasoning: str  # Why this intent was detected


class IntelligentIntentSystem:
    """
    TRUE intelligent intent understanding.
    
    Strategy:
    1. FAST PATH: Pattern matching for obvious cases (< 5ms)
    2. SMART PATH: LLM classification for ambiguous cases (< 500ms)
    3. GRACEFUL: Handle impossible/weird requests politely
    """
    
    def __init__(self):
        self.llm = None  # Lazy load
        
    async def understand(self, message: str, context: Optional[Dict] = None) -> IntentResult:
        """
        Understand user intent with true intelligence.
        
        Args:
            message: User's message
            context: Optional context (conversation history, workspace state, etc.)
            
        Returns:
            IntentResult with intent, route, and parameters
        """
        message_lower = message.lower().strip()
        word_count = len(message.split())
        
        # =====================================================
        # FAST PATH - Pattern matching for obvious cases
        # =====================================================
        
        # 1. GREETINGS (instant)
        if self._is_greeting(message_lower, word_count):
            return IntentResult(
                intent=IntentType.GREETING,
                route=RouteType.INSTANT,
                confidence=0.99,
                params={},
                message="",
                reasoning="Detected greeting pattern"
            )
        
        # 2. UNSUPPORTED REQUESTS (video, audio, etc.)
        unsupported = self._check_unsupported(message_lower)
        if unsupported:
            return unsupported
        
        # 3. DATA/DATASET GENERATION
        data_intent = self._classify_data_request(message_lower)
        if data_intent:
            return data_intent
        
        # 4. CHAPTER GENERATION (thesis chapters) - PRIORITY before other detections
        chapter_intent = self._classify_chapter_request(message_lower, message)
        if chapter_intent:
            return chapter_intent
        
        # 4. IMAGE REQUESTS - Search vs Generate
        image_intent = self._classify_image_request(message_lower)
        if image_intent:
            return image_intent
        
        # 5. SEARCH REQUESTS
        search_intent = self._classify_search_request(message_lower)
        if search_intent:
            return search_intent
        
        # 6. FILE OPERATIONS
        file_intent = self._classify_file_request(message_lower)
        if file_intent:
            return file_intent
        
        # 7. WRITING/CONTENT REQUESTS
        writing_intent = self._classify_writing_request(message_lower)
        if writing_intent:
            return writing_intent
        
        # 7. SIMPLE QUESTIONS (direct LLM)
        if self._is_simple_question(message_lower, word_count):
            return IntentResult(
                intent=IntentType.SIMPLE_QUESTION,
                route=RouteType.DIRECT_LLM,
                confidence=0.85,
                params={"question": message},
                message="",
                reasoning="Detected simple question pattern"
            )
        
        # 8. CASUAL CHAT (direct LLM)
        if word_count < 25 and not self._needs_tools(message_lower):
            return IntentResult(
                intent=IntentType.CASUAL_CHAT,
                route=RouteType.DIRECT_LLM,
                confidence=0.8,
                params={},
                message="",
                reasoning="Short message without tool keywords"
            )
        
        # =====================================================
        # SMART PATH - LLM classification for ambiguous cases
        # =====================================================
        
        # If we reach here, use LLM to understand intent
        return await self._llm_classify(message, context)
    
    def _is_greeting(self, msg: str, word_count: int) -> bool:
        """Check if message is a greeting."""
        greetings = ["hi", "hello", "hey", "greetings", "sup", "yo", "howdy", "hola", "good morning", "good afternoon", "good evening"]
        
        # If it's short and contains a greeting
        if word_count <= 5 and any(g in msg for g in greetings):
            # BUT if it also contains tool keywords or URLs, it's NOT just a greeting
            tool_keywords = ["search", "find", "generate", "create", "make", "write", "save", "file", "go to", "open", "browse", "google.com", "http", ".com", ".org", ".net"]
            if any(t in msg for t in tool_keywords):
                return False
            return True
        return False
    
    def _check_unsupported(self, msg: str) -> Optional[IntentResult]:
        """Check for unsupported request types."""
        unsupported_map = {
            ("video", "make video", "create video", "generate video"): 
                "Video generation is not yet supported. I can help with text, images, documents, and research.",
            ("audio", "make audio", "create audio", "generate audio", "record"):
                "Audio generation is not yet supported. I can help with text, images, documents, and research.",
            ("music", "make music", "compose", "song"):
                "Music creation is not yet supported. I can help with text, images, documents, and research.",
            ("voice", "text to speech", "tts", "speak"):
                "Voice synthesis is not yet supported. I can help with text, images, documents, and research.",
            ("3d model", "3d render", "blender", "cad"):
                "3D modeling is not yet supported. I can help with text, images, documents, and research.",
            ("translate", "translation"):
                None,  # We CAN do translation via LLM
        }
        
        for keywords, response in unsupported_map.items():
            if response and any(k in msg for k in keywords):
                # Check if it's a creation request (not just mentioning)
                if any(action in msg for action in ["make", "create", "generate", "produce", "build", "record"]):
                    return IntentResult(
                        intent=IntentType.UNSUPPORTED,
                        route=RouteType.GRACEFUL,
                        confidence=0.95,
                        params={"requested": keywords[0]},
                        message=response,
                        reasoning=f"Detected unsupported request: {keywords[0]}"
                    )
        return None
    
    def _classify_data_request(self, msg: str) -> Optional[IntentResult]:
        """Classify dataset/data collection requests."""
        
        # Keywords that indicate dataset generation
        dataset_keywords = [
            'generate dataset', 'create dataset', 'make dataset',
            'generate data', 'create data', 'synthetic data',
            'collect data', 'data collection', 'fill questionnaire',
            'simulate responses', 'generate responses', 'sample data',
            'create csv', 'generate csv', 'spss data', 'survey data',
            'respondent data', 'generate respondents'
        ]
        
        if any(keyword in msg for keyword in dataset_keywords):
            # Try to extract sample size
            import re
            sample_size = None
            
            # Pattern: "100 respondents", "sample of 50", "n=385"
            size_patterns = [
                r'(\d+)\s+respondents?',
                r'(\d+)\s+samples?',
                r'sample\s+(?:size\s+)?(?:of\s+)?(\d+)',
                r'n\s*=\s*(\d+)',
                r'(\d+)\s+(?:data\s+)?points?',
            ]
            
            for pattern in size_patterns:
                match = re.search(pattern, msg)
                if match:
                    sample_size = int(match.group(1))
                    break
            
            return IntentResult(
                intent=IntentType.DATA_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.95,
                params={
                    "sample_size": sample_size,
                    "generation_type": "dataset_generate"
                },
                message="",
                reasoning="Dataset/data collection generation request detected"
            )
        
        # Check for Chapter 5 generation (results and discussion)
        chapter5_keywords = [
            'chapter 5', 'chapter five', 'chapter5',
            'results and discussion', 'discussion of findings',
            'interpret findings', 'findings discussion',
            'generate chapter 5', 'create chapter 5', 'write chapter 5',
            'chapter five results', 'synthesis of findings',
            'compare with literature', 'discussion chapter'
        ]
        
        if any(keyword in msg for keyword in chapter5_keywords):
            return IntentResult(
                intent=IntentType.CHAPTER_FIVE_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.95,
                params={
                    "chapter_type": "chapter_five",
                    "generation_type": "chapter_five_generate"
                },
                message="",
                reasoning="Chapter 5 results and discussion generation request"
            )
        
        # Check for Chapter 6 generation (conclusions and recommendations)
        chapter6_keywords = [
            'chapter 6', 'chapter six', 'chapter6',
            'summary conclusion recommendation', 'conclusions and recommendations',
            'conclusion and recommendation', 'summary conclusion',
            'generate chapter 6', 'create chapter 6', 'write chapter 6',
            'chapter six conclusion', 'conclusion chapter', 'recommendations chapter',
            'final chapter', 'thesis conclusion'
        ]
        
        if any(keyword in msg for keyword in chapter6_keywords):
            return IntentResult(
                intent=IntentType.CHAPTER_SIX_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.95,
                params={
                    "chapter_type": "chapter_six",
                    "generation_type": "chapter_six_generate"
                },
                message="",
                reasoning="Chapter 6 conclusion and recommendations generation request"
            )
        
        # Check for Chapter 4 generation (data analysis)
        chapter4_keywords = [
            'chapter 4', 'chapter four', 'chapter4',
            'data analysis', 'analyze data', 'analyse data',
            'data presentation', 'present findings', 'present data',
            'analyze findings', 'analyse findings', 'interpret data',
            'generate chapter 4', 'create chapter 4', 'write chapter 4',
            'data and analysis', 'findings chapter'
        ]
        
        if any(keyword in msg for keyword in chapter4_keywords):
            return IntentResult(
                intent=IntentType.CHAPTER_FOUR_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.95,
                params={
                    "chapter_type": "chapter_four",
                    "generation_type": "chapter_four_generate"
                },
                message="",
                reasoning="Chapter 4 data presentation and analysis generation request"
            )
        
        # Check for thesis combination/complete thesis generation
        thesis_keywords = [
            'generate complete thesis', 'generate full thesis', 'generate entire thesis',
            'combine chapters', 'combine all chapters', 'one file thesis',
            'complete thesis', 'full thesis', 'entire thesis',
            'thesis status', 'thesis combined', 'all chapters in one',
            'generate thesis', 'create thesis', 'make thesis',
            'thesis chapter 1 to 6', 'chapters 1-6', 'chapters 1 through 6'
        ]
        
        if any(keyword in msg for keyword in thesis_keywords):
            return IntentResult(
                intent=IntentType.THESIS_COMBINE_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.95,
                params={
                    "generation_type": "thesis_combine_generate"
                },
                message="",
                reasoning="Complete thesis generation or chapter combination request"
            )
        
        return None
    
    def _classify_image_request(self, msg: str) -> Optional[IntentResult]:
        """Classify image-related requests - search vs generate."""
        
        # Check if it's an image request at all
        image_keywords = ["image", "picture", "photo", "pic", "photograph", "illustration"]
        if not any(k in msg for k in image_keywords):
            return None
        
        # SEARCH indicators (prioritize these!) - must be combined with image keywords
        search_indicators = ["search", "find", "look for", "get me", "show me", "image of", "picture of", "photo of"]
        is_search = any(s in msg for s in search_indicators)
        
        # GENERATE indicators (only for specific content)
        generate_indicators = ["generate", "create", "make", "draw", "design"]
        generate_content = ["diagram", "flowchart", "chart", "infographic", "framework", 
                          "schematic", "visualization", "concept", "illustration of concept"]
        
        needs_generation = any(g in msg for g in generate_content)
        explicit_generate = any(f"{g} image" in msg or f"{g} picture" in msg for g in generate_indicators)
        
        # Decision logic
        if is_search and not needs_generation and not explicit_generate:
            # Extract search query
            query = msg
            for remove in ["search for", "find", "look for", "get me", "show me", "image of", "picture of", "photo of", "images of", "pictures of"]:
                query = query.replace(remove, "").strip()
            
            return IntentResult(
                intent=IntentType.IMAGE_SEARCH,
                route=RouteType.TOOL_DIRECT,
                confidence=0.9,
                params={"query": query, "limit": 6},
                message="",
                reasoning="Image request with search indicators, using image search APIs"
            )
        
        if needs_generation or explicit_generate:
            # Extract generation prompt
            prompt = msg
            for remove in ["generate", "create", "make", "draw", "design", "an image of", "a picture of"]:
                prompt = prompt.replace(remove, "").strip()
            
            return IntentResult(
                intent=IntentType.IMAGE_GENERATE,
                route=RouteType.TOOL_DIRECT,
                confidence=0.9,
                params={"prompt": prompt, "size": "1024x1024"},
                message="",
                reasoning="Image generation needed for diagram/illustration content"
            )
        
        # Default ambiguous image request -> search (safer, faster)
        query = msg
        for remove in ["image of", "picture of", "photo of"]:
            query = query.replace(remove, "").strip()
        
        return IntentResult(
            intent=IntentType.IMAGE_SEARCH,
            route=RouteType.TOOL_DIRECT,
            confidence=0.75,
            params={"query": query, "limit": 6},
            message="",
            reasoning="Ambiguous image request, defaulting to search"
        )
    
    def _classify_search_request(self, msg: str) -> Optional[IntentResult]:
        """Classify search requests - web, papers, etc."""
        
        # PAPER/ACADEMIC search
        paper_indicators = ["paper", "research", "study", "academic", "literature", "journal", "article", "publication"]
        search_verbs = ["search", "find", "look for"]
        
        if any(p in msg for p in paper_indicators) and any(s in msg for s in search_verbs):
            # Check for synthesis request
            if any(s in msg for s in ["synthesis", "synthesize", "review", "summarize", "analyze"]):
                # Extract topic
                topic = msg
                for remove in ["search", "find", "papers", "research", "and", "synthesize", "write", "synthesis", "on", "about"]:
                    topic = topic.replace(remove, "").strip()
                
                return IntentResult(
                    intent=IntentType.RESEARCH_SYNTHESIS,
                    route=RouteType.PIPELINE,
                    confidence=0.9,
                    params={"topic": topic},
                    message="",
                    reasoning="Research synthesis request detected"
                )
            
            # Just paper search
            query = msg
            for remove in ["search for", "find", "look for", "papers", "research", "on", "about"]:
                query = query.replace(remove, "").strip()
            
            return IntentResult(
                intent=IntentType.PAPER_SEARCH,
                route=RouteType.TOOL_DIRECT,
                confidence=0.85,
                params={"query": query, "max_results": 10},
                message="",
                reasoning="Academic paper search detected"
            )
        
        # WEB search
        if any(s in msg for s in ["search", "look up", "find out", "google", "go to", "browse", "open"]):
            if len(msg.split()) < 20:  # Slightly longer queries allowed for URLs
                import re
                # Use regex to only remove prefix verbs/meta from the START of the query
                query = re.sub(r'^(?:search\s+for|search|look\s+up|find\s+out|google|go\s+to|browse|visit|open)\s+', '', msg, flags=re.IGNORECASE).strip()
                
                # If it looks like a URL but we didn't extract a query, use the whole msg
                if not query and (".com" in msg or ".org" in msg or "http" in msg):
                    query = msg
                
                return IntentResult(
                    intent=IntentType.WEB_SEARCH,
                    route=RouteType.TOOL_DIRECT,
                    confidence=0.85,
                    params={"query": query},
                    message="",
                    reasoning="Web search or direct navigation detected"
                )
        
        return None
    
    def _classify_file_request(self, msg: str) -> Optional[IntentResult]:
        """Classify file operation requests."""
        
        # PDF actions
        if "pdf" in msg:
            if any(a in msg for a in ["summarize", "read", "analyze", "extract", "what's in"]):
                # Extract PDF name if mentioned
                pdf_match = re.search(r'(\S+\.pdf)', msg, re.IGNORECASE)
                pdf_name = pdf_match.group(1) if pdf_match else None
                
                return IntentResult(
                    intent=IntentType.PDF_ACTION,
                    route=RouteType.TOOL_DIRECT,
                    confidence=0.9,
                    params={"action": "summarize", "pdf_name": pdf_name},
                    message="",
                    reasoning="PDF action detected"
                )
        
        # FILE CREATION/WRITE detection (NEW!)
        write_verbs = ["create", "make", "write", "save", "generate"]
        file_types = ["file", "md file", "markdown file", "txt file", "text file", "json file"]
        
        has_write_verb = any(v in msg for v in write_verbs)
        has_file_type = any(f in msg for f in file_types)
        
        if has_write_verb and has_file_type:
            # Extract filename if provided
            filename_match = re.search(r'(?:called|named|as|filename[:\s]+)\s*["\']?([^\s"\']+)["\']?', msg)
            filename = filename_match.group(1) if filename_match else None
            
            # If no explicit filename, try to detect file extension patterns like "test.md"
            if not filename:
                ext_match = re.search(r'(\S+\.(md|txt|json|py|js|html|css))', msg)
                if ext_match:
                    filename = ext_match.group(1)
            
            # Extract content from patterns like "with the word X", "containing X", "with content X"
            content_patterns = [
                r'(?:with|containing|with the word|with content|content[:\s]+)[:\s]*["\']?([^"\']+)["\']?$',
                r'(?:with|containing)[:\s]+(.+?)(?:\s*$)',
            ]
            content = None
            for pattern in content_patterns:
                content_match = re.search(pattern, msg, re.IGNORECASE)
                if content_match:
                    content = content_match.group(1).strip()
                    break
            
            return IntentResult(
                intent=IntentType.FILE_WRITE,
                route=RouteType.TOOL_DIRECT,
                confidence=0.9,
                params={
                    "filename": filename,
                    "content": content,
                    "action": "create"
                },
                message="",
                reasoning="File creation/write request detected"
            )
        
        # File listing
        if any(l in msg for l in ["list files", "show files", "what files", "see files"]):
            return IntentResult(
                intent=IntentType.FILE_LIST,
                route=RouteType.TOOL_DIRECT,
                confidence=0.9,
                params={},
                message="",
                reasoning="File listing request"
            )
        
        # File reading
        if any(r in msg for r in ["read file", "open file", "show file", "view file"]):
            return IntentResult(
                intent=IntentType.FILE_READ,
                route=RouteType.TOOL_DIRECT,
                confidence=0.85,
                params={},
                message="",
                reasoning="File read request"
            )
        
        return None
    
    def _classify_writing_request(self, msg: str) -> Optional[IntentResult]:
        """Classify writing/content requests."""
        
        write_verbs = ["write", "create", "generate", "make", "draft", "compose"]
        content_types = ["essay", "document", "report", "paper", "article", "content", "text"]
        
        # Check for writing request
        has_write_verb = any(v in msg for v in write_verbs)
        has_content_type = any(c in msg for c in content_types)
        
        if has_write_verb and has_content_type:
            # Extract topic
            topic = msg
            for remove in write_verbs + content_types + ["an", "a", "about", "on"]:
                topic = topic.replace(remove, "").strip()
            
            return IntentResult(
                intent=IntentType.CONTENT_WRITE,
                route=RouteType.ORCHESTRATOR,  # Complex task
                confidence=0.85,
                params={"topic": topic},
                message="",
                reasoning="Content writing request detected"
            )
        
        return None
    
    def _classify_chapter_request(self, msg: str, original: str) -> Optional[IntentResult]:
        """Classify thesis chapter generation requests."""
        
        # Chapter One indicators
        chapter_one_keywords = ["chapter one", "chapter 1", "chapter i", "introduction chapter", 
                          "thesis introduction", "write chapter one", "generate chapter one",
                          "dissertation chapter one", "thesis chapter one"]
        
        # Chapter Two indicators
        chapter_two_keywords = ["chapter two", "chapter 2", "chapter ii", "literature review",
                          "lit review", "write chapter two", "generate chapter two",
                          "write literature review", "generate literature review",
                          "review of literature", "related literature"]
        
        # Section indicators (user might just mention sections)
        section_keywords = ["background of the study", "statement of the problem", 
                          "objectives of the study", "research questions", "justification",
                          "setting the scene", "delimitations", "limitations"]
        
        # Chapter-specific keywords
        chapter_one_keywords = ['chapter 1', 'chapter one', 'introduction chapter', 'first chapter']
        chapter_two_keywords = ['chapter 2', 'chapter two', 'literature review', 'second chapter', 'chapter two']
        chapter_three_keywords = ['chapter 3', 'chapter three', 'methodology', 'research methodology', 'third chapter', 'methods chapter']
        
        # PROPOSAL keywords - for generating all 3 chapters
        proposal_keywords = ['proposal', 'first 3 chapters', 'first three chapters', 'chapters 1-3', 
                            'chapters 1 to 3', 'full proposal', 'complete proposal', 'thesis proposal',
                            'research proposal', 'make me proposal', 'generate proposal']
        
        message_lower = msg.lower() # Convert message to lowercase once for efficiency
        
        # Check for proposal request FIRST (highest priority)
        if any(keyword in message_lower for keyword in proposal_keywords):
            # Extract topic and case study from message
            topic = ""
            case_study = ""
            
            # Pattern: "Topic: X, Case Study: Y"
            import re
            topic_match = re.search(r'topic[:\s]+([^,\n]+)', message_lower, re.IGNORECASE)
            if topic_match:
                topic = topic_match.group(1).strip()
            
            # Pattern: "proposal on X" or "proposal about X"
            if not topic:
                on_match = re.search(r'proposal\s+(?:on|about|for|regarding)\s+(.+)', original, re.IGNORECASE)
                if on_match:
                    topic = on_match.group(1).strip()
            
            case_match = re.search(r'case\s*study[:\s]+([^,\n]+)', message_lower, re.IGNORECASE)
            if case_match:
                case_study = case_match.group(1).strip()
            
            # If still no topic, try to get from session context
            if not topic:
                # Try to get from workspace session database
                try:
                    from services.thesis_session_db import ThesisSessionDB
                    db = ThesisSessionDB("default")
                    stored_topic = db.get_topic()
                    if stored_topic:
                        topic = stored_topic
                        print(f"📚 Using stored topic from session: {topic}")
                except Exception as e:
                    print(f"⚠️ Could not fetch topic from session: {e}")
                
                # If still no topic, use cleaned message as fallback
                if not topic:
                    topic = original
                    for kw in proposal_keywords + ["write", "generate", "create"]:
                        topic = topic.lower().replace(kw, "").strip()
                    topic = topic.strip()

            return IntentResult(
                intent=IntentType.CHAPTER_GENERATE,
                route=RouteType.PIPELINE,
                confidence=0.98,
                params={
                    "topic": topic,
                    "case_study": case_study,
                    "chapter": "proposal", # Special indicator for full proposal
                    "chapter_name": "Research Proposal (Chapters 1-3)",
                    "generation_type": "full_proposal_generate"
                },
                message="",
                reasoning="Full research proposal (Chapters 1-3) generation request detected"
            )
        
        # Then check for individual chapters
        is_chapter_one = any(keyword in message_lower for keyword in chapter_one_keywords)
        is_chapter_two = any(keyword in message_lower for keyword in chapter_two_keywords)
        is_chapter_three = any(keyword in message_lower for keyword in chapter_three_keywords)
        is_section_request = any(k in msg for k in section_keywords) and any(w in msg for w in ["write", "generate", "create"])
        
        # Generic chapter request (fallback to chapter one)
        generic_chapter = any(k in msg for k in ["write chapter", "generate chapter", "thesis chapter", "dissertation chapter"])
        
        if is_chapter_three or is_chapter_two or is_chapter_one or is_section_request or generic_chapter:
            # Try to extract topic and case study from message
            topic = ""
            case_study = ""
            
            # Pattern: "Topic: X, Case Study: Y"
            import re
            topic_match = re.search(r'topic[:\s]+([^,\n]+)', msg, re.IGNORECASE)
            if topic_match:
                topic = topic_match.group(1).strip()
            
            case_match = re.search(r'case\s*study[:\s]+([^,\n]+)', msg, re.IGNORECASE)
            if case_match:
                case_study = case_match.group(1).strip()
            
            # Pattern: "chapter X on Y"  
            if not topic:
                on_match = re.search(r'(?:chapter\s*(?:one|two|1|2|i|ii)|introduction|literature\s+review)[\s,]+(?:on|about)\s+(.+?)(?:\.|$)', msg, re.IGNORECASE)
                if on_match:
                    topic = on_match.group(1).strip()
            
            # If still no topic, use message as topic
            if not topic:
                # Remove chapter keywords
                topic = original
                for kw in chapter_one_keywords + chapter_two_keywords + ["write", "generate", "create"]:
                    topic = topic.lower().replace(kw, "").strip()
                topic = topic.strip()
            
            # Determine intent type based on chapter
            if is_chapter_three:
                return IntentResult(
                    intent=IntentType.CHAPTER_GENERATE,
                    route=RouteType.PIPELINE,
                    confidence=0.95,
                    params={
                        "topic": topic,
                        "case_study": case_study,
                        "chapter": "3",
                        "chapter_name": "Research Methodology",
                        "generation_type": "chapter_three_generate"
                    },
                    message="",
                    reasoning="Chapter Three (Research Methodology) generation request detected"
                )
            elif is_chapter_two:
                return IntentResult(
                    intent=IntentType.CHAPTER_GENERATE,
                    route=RouteType.PIPELINE,
                    confidence=0.95,
                    params={
                        "topic": topic,
                        "case_study": case_study,
                        "chapter": "2",
                        "chapter_name": "Literature Review",
                        "generation_type": "chapter_two_generate"
                    },
                    message="",
                    reasoning="Chapter Two (Literature Review) generation request detected"
                )
            else:
                return IntentResult(
                    intent=IntentType.CHAPTER_GENERATE,
                    route=RouteType.PIPELINE,
                    confidence=0.95,
                    params={
                        "topic": topic,
                        "case_study": case_study,
                        "chapter": "1",
                        "chapter_name": "Introduction"
                    },
                    message="",
                    reasoning="Thesis chapter generation request detected"
                )
        
        return None
    
    def _is_simple_question(self, msg: str, word_count: int) -> bool:
        """Check if it's a simple question that LLM can answer directly."""
        question_starters = ["what", "who", "when", "where", "why", "how", "is", "are", 
                           "can", "do", "does", "will", "would", "should", "could", 
                           "explain", "define", "describe", "tell me"]
        
        if word_count < 30 and any(msg.startswith(q) for q in question_starters):
            # Make sure it doesn't need tools
            if not self._needs_tools(msg):
                return True
        return False
    
    def _needs_tools(self, msg: str) -> bool:
        """Check if message needs external tools."""
        tool_triggers = [
            "search", "find", "generate", "create", "make", "write", "save", 
            "file", "document", "image", "picture", "paper", "pdf"
        ]
        return any(t in msg for t in tool_triggers)
    
    async def _llm_classify(self, message: str, context: Optional[Dict] = None) -> IntentResult:
        """Use LLM to classify ambiguous intents."""
        from services.deepseek_direct import deepseek_direct_service
        
        try:
            prompt = f"""Classify this user request and determine the best action.

User message: "{message}"

You must respond with ONLY a JSON object (no other text):
{{
    "intent": "one of: simple_question, image_search, image_generate, web_search, paper_search, content_write, file_operation, complex_task, casual_chat, clarification_needed, off_topic",
    "route": "one of: direct_llm, tool_direct, orchestrator, graceful",
    "confidence": 0.0 to 1.0,
    "params": {{}},
    "message": "message to user if clarification needed or graceful decline",
    "reasoning": "brief explanation"
}}

Guidelines:
- simple_question/casual_chat → direct_llm (fastest, just answer)
- image_search → tool_direct (search real photos from APIs)
- image_generate → tool_direct (create with AI, only for diagrams/illustrations)
- web_search/paper_search → tool_direct
- content_write/complex_task → orchestrator
- If unsure what user wants → clarification_needed with helpful message
- If impossible request → graceful decline with alternatives

JSON only:"""

            response = await deepseek_direct_service.generate_content(
                prompt=prompt,
                system_prompt="You are an intent classification system. Output ONLY valid JSON.",
                temperature=0.3,
                max_tokens=300
            )
            
            # Parse JSON response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                data = json.loads(json_match.group())
                
                intent_map = {
                    "simple_question": IntentType.SIMPLE_QUESTION,
                    "image_search": IntentType.IMAGE_SEARCH,
                    "image_generate": IntentType.IMAGE_GENERATE,
                    "web_search": IntentType.WEB_SEARCH,
                    "paper_search": IntentType.PAPER_SEARCH,
                    "content_write": IntentType.CONTENT_WRITE,
                    "file_operation": IntentType.FILE_READ,
                    "complex_task": IntentType.COMPLEX_TASK,
                    "casual_chat": IntentType.CASUAL_CHAT,
                    "clarification_needed": IntentType.CLARIFICATION_NEEDED,
                    "off_topic": IntentType.OFF_TOPIC,
                }
                
                route_map = {
                    "direct_llm": RouteType.DIRECT_LLM,
                    "tool_direct": RouteType.TOOL_DIRECT,
                    "orchestrator": RouteType.ORCHESTRATOR,
                    "graceful": RouteType.GRACEFUL,
                }
                
                return IntentResult(
                    intent=intent_map.get(data.get("intent"), IntentType.UNKNOWN),
                    route=route_map.get(data.get("route"), RouteType.DIRECT_LLM),
                    confidence=float(data.get("confidence", 0.7)),
                    params=data.get("params", {}),
                    message=data.get("message", ""),
                    reasoning=data.get("reasoning", "LLM classification")
                )
                
        except Exception as e:
            print(f"LLM classification error: {e}")
        
        # Fallback: treat as casual chat
        return IntentResult(
            intent=IntentType.CASUAL_CHAT,
            route=RouteType.DIRECT_LLM,
            confidence=0.5,
            params={},
            message="",
            reasoning="Fallback to casual chat due to classification error"
        )


# Singleton
intelligent_intent = IntelligentIntentSystem()
