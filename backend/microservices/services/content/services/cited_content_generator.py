"""
Cited Content Generator - Generates heavily-cited academic content

Uses MDAP citation microagents to generate content with:
- 70-80% citation density (most sentences cited)
- Real academic papers from search APIs
- Proper APA/Harvard formatting
- Reference list generation
"""

import asyncio
from typing import Dict, List, Any, Optional
from app.services.citation_microagents import (
    CitationFinderAgent,
    CitationValidatorAgent,
    CitationFormatterAgent,
    ReferenceGeneratorAgent,
    CitationDensityAgent,
    SentenceCitationAgent
)
from app.services.maker_framework import VotingOrchestrator, RedFlagDetector, AgentPool
from app.services.mdap_llm_client import MDAPlLMClient
from app.services.academic_search import academic_search_service


class CitedContentGenerator:
    """
    Generates heavily-cited academic content using MDAP citation agents.
    
    Target: 70-80% of sentences should have citations.
    """
    
    def __init__(
        self,
        k: int = 3,
        model_key: str = "deepseek",
        citation_style: str = "APA"
    ):
        """
        Args:
            k: Voting threshold
            model_key: LLM model (deepseek, claude, gpt4, gemini)
            citation_style: Citation style (APA or Harvard)
        """
        self.k = k
        self.model_key = model_key
        self.citation_style = citation_style
        
        # Initialize LLM client
        self.llm_client = MDAPlLMClient(model_key=model_key)
        
        # Initialize voting orchestrator with relaxed red flag detection
        self.orchestrator = VotingOrchestrator(
            k=k,
            max_rounds=20,  # Increased from 15 to allow more attempts
            red_flag_detector=RedFlagDetector(
                max_tokens=2000,  # Increased from 1000 for citation-heavy content
                enable_format_check=False,  # Disable strict format check for citations
                enable_academic_check=False,  # Disable methodology creep detection
                enable_length_check=False  # Allow longer responses for citations
            )
        )
        
        # Initialize agent pool
        self.agent_pool = AgentPool(max_concurrent=10)
        
        # Initialize citation agents
        self._init_agents()
        
        # Citation database (for this session)
        self.cited_papers: List[Dict[str, Any]] = []
        self.citations_used: Dict[str, int] = {}  # Track citation frequency
    
    def _init_agents(self):
        """Initialize citation microagents."""
        self.citation_finder = CitationFinderAgent(
            "CitationFinder", self.llm_client, max_tokens=300
        )
        self.citation_validator = CitationValidatorAgent(
            "CitationValidator", self.llm_client, max_tokens=200
        )
        self.citation_formatter = CitationFormatterAgent(
            "CitationFormatter", self.llm_client, max_tokens=250
        )
        self.reference_generator = ReferenceGeneratorAgent(
            "ReferenceGenerator", self.llm_client, max_tokens=600
        )
        self.density_analyzer = CitationDensityAgent(
            "DensityAnalyzer", self.llm_client, max_tokens=300
        )
        self.sentence_writer = SentenceCitationAgent(
            "SentenceWriter", self.llm_client, max_tokens=200
        )
    
    async def generate_cited_section(
        self,
        section_title: str,
        topic: str,
        word_count: int = 500,
        target_density: float = 0.75
    ) -> Dict[str, Any]:
        """
        Generate a section with heavy citations.
        
        Args:
            section_title: Section title (e.g., "Setting the Scene")
            topic: Main topic to write about
            word_count: Target word count
            target_density: Target citation density (0.75 = 75% of sentences)
            
        Returns:
            Dict with content, references, and metrics
        """
        print(f"\n📝 GENERATING CITED SECTION: {section_title}")
        print(f"   Topic: {topic}")
        print(f"   Target: {word_count} words, {target_density:.0%} citation density\n")
        
        # Step 1: Search for relevant papers
        print("🔍 Step 1: Searching for relevant papers...")
        papers = await self._search_papers(topic, max_results=20)
        print(f"   ✓ Found {len(papers)} papers\n")
        
        if not papers:
            print("   ⚠️  No papers found - cannot generate cited content")
            print("   Check internet connection and API keys\n")
            return {
                "error": "No papers found",
                "section_title": section_title,
                "content": "",
                "references": [],
                "metrics": {
                    "word_count": 0,
                    "sentence_count": 0,
                    "citation_count": 0,
                    "citation_density": 0.0,
                    "unique_papers": 0
                }
            }
        
        # Step 2: Generate cited sentences
        print("✍️  Step 2: Generating cited sentences...")
        sentences = []
        current_word_count = 0
        target_sentences = int(word_count / 15)  # ~15 words per sentence
        
        for i in range(target_sentences):
            # Should this sentence have a citation?
            should_cite = (i / target_sentences) < target_density or (i % 2 == 0)
            
            if should_cite and papers:
                # Generate sentence with citation
                sentence_data = await self._generate_cited_sentence(
                    topic=topic,
                    papers=papers,
                    context=" ".join(sentences[-2:]) if len(sentences) >= 2 else None
                )
                sentences.append(sentence_data['sentence'])
                current_word_count += len(sentence_data['sentence'].split())
            else:
                # Generate sentence without citation (transition/context)
                sentence = await self._generate_plain_sentence(
                    topic=topic,
                    context=" ".join(sentences[-2:]) if len(sentences) >= 2 else None
                )
                sentences.append(sentence)
                current_word_count += len(sentence.split())
            
            if current_word_count >= word_count:
                break
            
            if (i + 1) % 5 == 0:
                print(f"   ✓ Generated {i + 1}/{target_sentences} sentences ({current_word_count} words)")
        
        content = " ".join(sentences)
        print(f"   ✓ Total: {len(sentences)} sentences, {current_word_count} words\n")
        
        # Step 3: Analyze citation density
        print("📊 Step 3: Analyzing citation density...")
        density_response, _ = await self.agent_pool.execute_with_voting(
            self.density_analyzer,
            self.orchestrator,
            {"text": content}
        )
        density_data = density_response.content
        print(f"   ✓ Citation density: {density_data.get('citation_density', 0):.1%}\n")
        
        # Step 4: Generate reference list
        print("📚 Step 4: Generating reference list...")
        references = await self._generate_references()
        print(f"   ✓ {len(references)} unique references\n")
        
        # Compile results
        result = {
            "section_title": section_title,
            "content": content,
            "references": references,
            "metrics": {
                "word_count": current_word_count,
                "sentence_count": len(sentences),
                "citation_count": len(self.cited_papers),
                "citation_density": density_data.get('citation_density', 0),
                "unique_papers": len(self.cited_papers)
            }
        }
        
        print(f"✅ Section complete!")
        print(f"   Words: {current_word_count}")
        print(f"   Citations: {len(self.cited_papers)}")
        print(f"   Density: {density_data.get('citation_density', 0):.1%}\n")
        
        return result
    
    async def _search_papers(
        self,
        topic: str,
        max_results: int = 20
    ) -> List[Dict[str, Any]]:
        """Search for relevant papers using academic search service."""
        papers = await academic_search_service.search_academic_papers(
            query=topic,
            max_results=max_results
        )
        return papers
    
    async def _generate_cited_sentence(
        self,
        topic: str,
        papers: List[Dict[str, Any]],
        context: Optional[str] = None
    ) -> Dict[str, str]:
        """Generate a single sentence with citation using voting."""
        # Select a paper (with voting)
        paper_response, _ = await self.agent_pool.execute_with_voting(
            self.citation_finder,
            self.orchestrator,
            {"claim": topic, "papers": papers}
        )
        
        selected_index = paper_response.content.get('selected_paper_index', 0)
        selected_paper = papers[min(selected_index, len(papers) - 1)]
        
        # Generate sentence with citation (with voting)
        sentence_response, _ = await self.agent_pool.execute_with_voting(
            self.sentence_writer,
            self.orchestrator,
            {"topic": topic, "paper": selected_paper, "context": context}
        )
        
        # Add to cited papers
        if selected_paper not in self.cited_papers:
            self.cited_papers.append(selected_paper)
        
        # Track citation usage
        paper_key = selected_paper.get('title', 'Unknown')
        self.citations_used[paper_key] = self.citations_used.get(paper_key, 0) + 1
        
        return sentence_response.content
    
    async def _generate_plain_sentence(
        self,
        topic: str,
        context: Optional[str] = None
    ) -> str:
        """Generate a plain sentence without citation (for transitions)."""
        # Simple prompt for transition sentence
        prompt = f"Write ONE transition sentence about {topic}"
        if context:
            prompt += f" following this context: {context}"
        
        response = await self.llm_client.call(
            system_prompt="You are an academic writer. Write clear, concise sentences.",
            user_prompt=prompt + ". Return ONLY the sentence, no JSON."
        )
        
        # Extract first sentence
        sentences = response.split('.')
        return sentences[0].strip() + '.' if sentences else response[:100]
    
    async def _generate_references(self) -> List[str]:
        """Generate formatted reference list from cited papers."""
        if not self.cited_papers:
            return []
        
        # Format each paper (with voting)
        references = []
        
        for paper in self.cited_papers:
            format_response, _ = await self.agent_pool.execute_with_voting(
                self.citation_formatter,
                self.orchestrator,
                {"paper": paper, "style": self.citation_style}
            )
            
            reference = format_response.content.get('reference', '')
            if reference:
                references.append(reference)
        
        # Sort alphabetically
        references.sort()
        
        return references
    
    def reset_citations(self):
        """Reset citation database for new section."""
        self.cited_papers = []
        self.citations_used = {}


# Singleton instance
cited_content_generator = CitedContentGenerator(
    k=3,
    model_key="deepseek",
    citation_style="APA"
)
