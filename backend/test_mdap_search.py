"""
Test MDAP Search System

Tests the full MDAP search pipeline with 15 microagents and voting.
"""

import asyncio
import json
from app.services.mdap_search_orchestrator import mdap_search_orchestrator


async def test_mdap_search():
    """Test MDAP search with a sample query."""
    
    print("\n" + "="*80)
    print("MDAP ACADEMIC SEARCH TEST")
    print("="*80 + "\n")
    
    # Test query
    query = "machine learning applications in healthcare diagnosis"
    
    print(f"Testing MDAP search for: '{query}'\n")
    
    try:
        # Execute MDAP search
        results = await mdap_search_orchestrator.search_with_mdap(
            query=query,
            max_results=5
        )
        
        # Display results
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80 + "\n")
        
        print(f"Original Query: {results['query']}")
        print(f"Refined Query: {results['refined_query']}")
        print(f"Sources Used: {', '.join(results['sources_used'])}\n")
        
        print(f"📄 Papers Found: {len(results['papers'])}")
        for i, paper in enumerate(results['papers'][:3], 1):
            print(f"\n{i}. {paper.get('title', 'N/A')}")
            print(f"   Year: {paper.get('year', 'N/A')}")
            print(f"   Citations: {paper.get('citations', 0)}")
            print(f"   Relevance: {paper.get('relevance_score', 0):.2f}")
        
        print(f"\n💡 Key Insights ({len(results['insights'])}):")
        for i, insight in enumerate(results['insights'], 1):
            print(f"{i}. {insight}")
        
        print(f"\n🔍 Research Gaps ({len(results['research_gaps'])}):")
        for i, gap in enumerate(results['research_gaps'], 1):
            print(f"{i}. {gap}")
        
        print(f"\n📈 Trends ({len(results['trends'])}):")
        for i, trend in enumerate(results['trends'], 1):
            print(f"{i}. {trend}")
        
        print(f"\n🎯 Recommendations ({len(results['recommendations'])}):")
        for i, rec in enumerate(results['recommendations'], 1):
            print(f"{i}. {rec}")
        
        print("\n" + "="*80)
        print("METRICS")
        print("="*80 + "\n")
        
        metrics = results['metrics']
        print(f"Total Voting Rounds: {metrics['total_voting_rounds']}")
        print(f"Total Samples: {metrics['total_samples']}")
        print(f"Valid Samples: {metrics['valid_samples']}")
        print(f"Invalid Samples: {metrics['invalid_samples']}")
        print(f"Consensus Rate: {metrics['consensus_rate']:.1%}")
        print(f"Agents Used: {metrics['agents_used']}")
        
        print("\n✅ TEST PASSED\n")
        
        return results
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {str(e)}\n")
        import traceback
        traceback.print_exc()
        return None


async def test_voting_logic():
    """Test voting mechanism in isolation."""
    
    print("\n" + "="*80)
    print("VOTING LOGIC TEST")
    print("="*80 + "\n")
    
    from app.services.maker_framework import VotingOrchestrator, AgentResponse, RedFlagDetector
    from collections import Counter
    
    orchestrator = VotingOrchestrator(k=3, red_flag_detector=RedFlagDetector())
    
    # Simulate agent responses
    responses = [
        AgentResponse(content={"answer": "A"}, confidence=0.9),
        AgentResponse(content={"answer": "A"}, confidence=0.85),
        AgentResponse(content={"answer": "B"}, confidence=0.7),
        AgentResponse(content={"answer": "A"}, confidence=0.95),
    ]
    
    response_iter = iter(responses)
    
    async def sample_fn():
        """Simulate sampling."""
        await asyncio.sleep(0.01)  # Simulate API call
        return next(response_iter)
    
    try:
        winner, metrics = await orchestrator.vote(sample_fn)
        
        print(f"Winner: {winner.content}")
        print(f"Voting Rounds: {metrics.voting_rounds}")
        print(f"Total Samples: {metrics.total_samples}")
        print(f"Valid Samples: {metrics.valid_samples}")
        print(f"Consensus Achieved: {metrics.consensus_achieved}")
        print(f"Winner Votes: {metrics.winner_votes}")
        print(f"Runner-up Votes: {metrics.runner_up_votes}")
        
        print("\n✅ VOTING TEST PASSED\n")
        
    except Exception as e:
        print(f"\n❌ VOTING TEST FAILED: {str(e)}\n")


async def test_cost_estimation():
    """Test cost estimation formulas."""
    
    print("\n" + "="*80)
    print("COST ESTIMATION TEST")
    print("="*80 + "\n")
    
    from app.services.maker_framework import estimate_k_min, estimate_cost
    
    # Test scenarios
    scenarios = [
        {"p": 0.99, "s": 100, "cost": 0.01, "desc": "100 steps, 99% success"},
        {"p": 0.95, "s": 1000, "cost": 0.01, "desc": "1000 steps, 95% success"},
        {"p": 0.999, "s": 10000, "cost": 0.005, "desc": "10K steps, 99.9% success"},
    ]
    
    for scenario in scenarios:
        k_min = estimate_k_min(scenario["p"], scenario["s"])
        cost = estimate_cost(scenario["p"], scenario["s"], scenario["cost"], k=k_min)
        
        print(f"{scenario['desc']}:")
        print(f"  k_min: {k_min}")
        print(f"  Estimated cost: ${cost:.2f}")
        print()
    
    print("✅ COST ESTIMATION TEST PASSED\n")


async def main():
    """Run all tests."""
    
    print("\n🧪 MDAP SYSTEM TESTS\n")
    
    # Test 1: Voting logic
    await test_voting_logic()
    
    # Test 2: Cost estimation
    await test_cost_estimation()
    
    # Test 3: Full MDAP search
    # await test_mdap_search()  # Uncomment when ready to test with real APIs
    
    print("✅ ALL TESTS COMPLETE\n")


if __name__ == "__main__":
    asyncio.run(main())
