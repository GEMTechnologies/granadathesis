"""
MDAP Search Orchestrator - Main service for MDAP-powered academic search

Orchestrates 15 microagents with voting to achieve reliable academic search.
"""

import asyncio
from typing import Dict, List, Any, Optional
from core.maker_framework import (
    VotingOrchestrator,
    RedFlagDetector,
    AgentPool,
    AgentResponse,
    VotingMetrics,
    estimate_k_min
)
from services.search_microagents import *
from services.mdap_llm_client import MDAPlLMClient
from services.academic_search import academic_search_service


class MicroAgentWithLLM(MicroAgent):
    """Extended MicroAgent with LLM call implementation."""
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM using MDAP client."""
        return await self.llm_client.call(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )


class MDAPSearchOrchestrator:
    """
    Main orchestrator for MDAP-powered academic search.
    
    Coordinates 15 specialized microagents with voting for reliable results.
    """
    
    def __init__(
        self,
        k: int = 3,
        model_key: str = "deepseek",
        max_concurrent: Optional[int] = None
    ):
        """
        Args:
            k: Voting threshold (first-to-ahead-by-k)
            model_key: LLM model to use (deepseek, claude, gpt4, gemini)
            max_concurrent: Max concurrent agent executions (defaults to config setting)
        """
        self.k = k
        self.model_key = model_key
        
        # Initialize LLM client
        self.llm_client = MDAPlLMClient(model_key=model_key)
        
        # Initialize voting orchestrator
        self.orchestrator = VotingOrchestrator(
            k=k,
            max_rounds=20,
            red_flag_detector=RedFlagDetector(max_tokens=750)
        )
        
        # Initialize agent pool - use configurable max_concurrent if not provided
        if max_concurrent is None:
            from core.config import settings
            max_concurrent = settings.MAX_CONCURRENT_AGENTS
        self.agent_pool = AgentPool(max_concurrent=max_concurrent)
        
        # Initialize all 15 microagents
        self._init_agents()
        
        # Metrics tracking
        self.total_metrics: Dict[str, VotingMetrics] = {}
    
    def _init_agents(self):
        """Initialize all 15 specialized microagents."""
        # Query Processing (3)
        self.query_decomposer = QueryDecomposerAgent(
            "QueryDecomposer", self.llm_client, max_tokens=300
        )
        self.query_refiner = QueryRefinerAgent(
            "QueryRefiner", self.llm_client, max_tokens=200
        )
        self.source_selector = SourceSelectorAgent(
            "SourceSelector", self.llm_client, max_tokens=150
        )
        
        # Result Processing (7)
        self.result_extractor = ResultExtractorAgent(
            "ResultExtractor", self.llm_client, max_tokens=400
        )
        self.result_validator = ResultValidatorAgent(
            "ResultValidator", self.llm_client, max_tokens=200
        )
        self.relevance_scorer = RelevanceScorerAgent(
            "RelevanceScorer", self.llm_client, max_tokens=250
        )
        self.deduplicator = DeduplicationAgent(
            "Deduplicator", self.llm_client, max_tokens=150
        )
        self.citation_extractor = CitationExtractorAgent(
            "CitationExtractor", self.llm_client, max_tokens=200
        )
        self.abstract_summarizer = AbstractSummarizerAgent(
            "AbstractSummarizer", self.llm_client, max_tokens=150
        )
        self.metadata_enricher = MetadataEnricherAgent(
            "MetadataEnricher", self.llm_client, max_tokens=200
        )
        
        # Synthesis (5)
        self.result_aggregator = ResultAggregatorAgent(
            "ResultAggregator", self.llm_client, max_tokens=600
        )
        self.insight_extractor = InsightExtractorAgent(
            "InsightExtractor", self.llm_client, max_tokens=400
        )
        self.gap_analyzer = GapAnalysisAgent(
            "GapAnalyzer", self.llm_client, max_tokens=300
        )
        self.trend_detector = TrendDetectorAgent(
            "TrendDetector", self.llm_client, max_tokens=300
        )
        self.recommender = RecommendationAgent(
            "Recommender", self.llm_client, max_tokens=300
        )
    
    async def search_with_mdap(
        self,
        query: str,
        max_results: int = 10
    ) -> Dict[str, Any]:
        """
        Execute MDAP-powered academic search.
        
        Args:
            query: Research query
            max_results: Maximum number of results
            
        Returns:
            Comprehensive search results with papers, insights, gaps, trends
        """
        print(f"\n🤖 MDAP SEARCH (k={self.k}, model={self.model_key})")
        print(f"   Query: {query}\n")
        
        # Phase 1: Query Processing
        print("📋 Phase 1: Query Processing")
        refined_query, sources = await self._process_query(query)
        
        # Phase 2: Fetch Raw Results
        print("\n🔍 Phase 2: Fetching Raw Results")
        raw_results = await self._fetch_raw_results(refined_query, sources)
        
        # Phase 3: Process Results
        print("\n⚙️  Phase 3: Processing Results")
        processed_papers = await self._process_results(raw_results, query)
        
        # Phase 4: Synthesis
        print("\n🧠 Phase 4: Synthesis")
        synthesis = await self._synthesize_results(processed_papers, query)
        
        # Compile final results
        results = {
            "query": query,
            "refined_query": refined_query,
            "sources_used": sources,
            "papers": processed_papers[:max_results],
            "insights": synthesis.get("insights", []),
            "research_gaps": synthesis.get("gaps", []),
            "trends": synthesis.get("trends", []),
            "recommendations": synthesis.get("recommendations", []),
            "metrics": self._compile_metrics()
        }
        
        print(f"\n✅ MDAP Search Complete")
        print(f"   Papers: {len(results['papers'])}")
        print(f"   Insights: {len(results['insights'])}")
        print(f"   Total voting rounds: {results['metrics']['total_voting_rounds']}")
        print(f"   Consensus rate: {results['metrics']['consensus_rate']:.1%}\n")
        
        return results
    
    async def _process_query(self, query: str) -> tuple[str, List[str]]:
        """Phase 1: Process query with voting."""
        # Refine query with voting
        refined_response, metrics = await self.agent_pool.execute_with_voting(
            self.query_refiner,
            self.orchestrator,
            {"query": query}
        )
        self.total_metrics["query_refiner"] = metrics
        
        refined_query = refined_response.content.get("refined_query", query)
        print(f"   ✓ Refined: {refined_query}")
        
        # Select sources with voting
        sources_response, metrics = await self.agent_pool.execute_with_voting(
            self.source_selector,
            self.orchestrator,
            {"query": refined_query}
        )
        self.total_metrics["source_selector"] = metrics
        
        sources = sources_response.content.get("sources", ["semantic_scholar"])
        print(f"   ✓ Sources: {', '.join(sources)}")
        
        return refined_query, sources
    
    async def _fetch_raw_results(
        self,
        query: str,
        sources: List[str]
    ) -> List[Dict[str, Any]]:
        """Phase 2: Fetch raw results from APIs."""
        raw_results = []
        
        # Use existing academic_search_service for API calls
        if "semantic_scholar" in sources:
            papers = await academic_search_service.search_academic_papers(query, max_results=10)
            raw_results.extend(papers)
        
        if "exa" in sources:
            exa_results = await academic_search_service.search_with_exa(query, max_results=5)
            raw_results.extend(exa_results)
        
        print(f"   ✓ Fetched {len(raw_results)} raw results")
        return raw_results
    
    async def _process_results(
        self,
        raw_results: List[Dict[str, Any]],
        query: str
    ) -> List[Dict[str, Any]]:
        """Phase 3: Process results with microagents."""
        processed_papers = []
        
        for i, raw_paper in enumerate(raw_results[:15]):  # Limit for speed
            # Extract with voting
            extract_response, metrics = await self.agent_pool.execute_with_voting(
                self.result_extractor,
                self.orchestrator,
                {"api_response": raw_paper}
            )
            self.total_metrics[f"extractor_{i}"] = metrics
            
            paper = extract_response.content
            
            # Validate
            valid_response, metrics = await self.agent_pool.execute_with_voting(
                self.result_validator,
                self.orchestrator,
                {"paper": paper}
            )
            self.total_metrics[f"validator_{i}"] = metrics
            
            if not valid_response.content.get("is_valid", False):
                continue  # Skip invalid papers
            
            # Score relevance
            score_response, metrics = await self.agent_pool.execute_with_voting(
                self.relevance_scorer,
                self.orchestrator,
                {"query": query, "paper": paper}
            )
            self.total_metrics[f"scorer_{i}"] = metrics
            
            paper["relevance_score"] = score_response.content.get("relevance_score", 0.5)
            
            processed_papers.append(paper)
            
            if (i + 1) % 5 == 0:
                print(f"   ✓ Processed {i + 1}/{len(raw_results[:15])} papers")
        
        # Sort by relevance
        processed_papers.sort(key=lambda p: p.get("relevance_score", 0), reverse=True)
        
        print(f"   ✓ Total valid papers: {len(processed_papers)}")
        return processed_papers
    
    async def _synthesize_results(
        self,
        papers: List[Dict[str, Any]],
        query: str
    ) -> Dict[str, Any]:
        """Phase 4: Synthesize insights, gaps, trends, recommendations."""
        # Extract insights
        insights_response, metrics = await self.agent_pool.execute_with_voting(
            self.insight_extractor,
            self.orchestrator,
            {"papers": papers[:5]}
        )
        self.total_metrics["insight_extractor"] = metrics
        insights = insights_response.content.get("insights", [])
        
        # Identify gaps
        gaps_response, metrics = await self.agent_pool.execute_with_voting(
            self.gap_analyzer,
            self.orchestrator,
            {"papers": papers[:5], "query": query}
        )
        self.total_metrics["gap_analyzer"] = metrics
        gaps = gaps_response.content.get("research_gaps", [])
        
        # Detect trends
        trends_response, metrics = await self.agent_pool.execute_with_voting(
            self.trend_detector,
            self.orchestrator,
            {"papers": papers[:5]}
        )
        self.total_metrics["trend_detector"] = metrics
        trends = trends_response.content.get("trends", [])
        
        # Generate recommendations
        rec_response, metrics = await self.agent_pool.execute_with_voting(
            self.recommender,
            self.orchestrator,
            {"insights": insights, "gaps": gaps, "trends": trends}
        )
        self.total_metrics["recommender"] = metrics
        recommendations = rec_response.content.get("recommendations", [])
        
        print(f"   ✓ Insights: {len(insights)}")
        print(f"   ✓ Gaps: {len(gaps)}")
        print(f"   ✓ Trends: {len(trends)}")
        print(f"   ✓ Recommendations: {len(recommendations)}")
        
        return {
            "insights": insights,
            "gaps": gaps,
            "trends": trends,
            "recommendations": recommendations
        }
    
    def _compile_metrics(self) -> Dict[str, Any]:
        """Compile metrics from all voting sessions."""
        total_rounds = sum(m.voting_rounds for m in self.total_metrics.values())
        total_samples = sum(m.total_samples for m in self.total_metrics.values())
        total_valid = sum(m.valid_samples for m in self.total_metrics.values())
        consensus_count = sum(1 for m in self.total_metrics.values() if m.consensus_achieved)
        
        return {
            "total_voting_rounds": total_rounds,
            "total_samples": total_samples,
            "valid_samples": total_valid,
            "invalid_samples": total_samples - total_valid,
            "consensus_rate": consensus_count / len(self.total_metrics) if self.total_metrics else 0,
            "agents_used": len(self.total_metrics)
        }


# Singleton instance
mdap_search_orchestrator = MDAPSearchOrchestrator(k=3, model_key="deepseek")
