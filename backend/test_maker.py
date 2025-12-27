"""
Test script for MAKER framework implementation.

Run this to test the voting-based objective generation.
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.objective import objective_agent


async def test_maker_voting():
    """Test MAKER voting for objective generation."""
    
    print("\n" + "="*80)
    print("MAKER FRAMEWORK TEST - Objective Generation with Voting")
    print("="*80 + "\n")
    
    # Test case
    topic = "Impact of Mobile Phone Prices on Digital Inclusion in Uganda"
    case_study = "Uganda, 2010-2023"
    methodology = "Mixed Methods"
    
    print(f"Topic: {topic}")
    print(f"Case Study: {case_study}")
    print(f"Methodology: {methodology}\n")
    
    # Run voting-based generation
    result = await objective_agent.generate_objectives_with_voting(
        topic=topic,
        case_study=case_study,
        methodology=methodology,
        k=3,
        enable_red_flags=True,
        thesis_id=None  # No thesis_id for testing
    )
    
    # Display results
    print("\n" + "="*80)
    print("RESULTS")
    print("="*80 + "\n")
    
    print("📋 FINAL OBJECTIVES:")
    for i, obj in enumerate(result["objectives"], 1):
        print(f"   {i}. {obj}")
    
    print(f"\n📊 VOTING STATISTICS:")
    stats = result["voting_stats"]
    print(f"   K-threshold: {stats['k_threshold']}")
    print(f"   Total samples: {stats['total_samples']}")
    print(f"   Flagged samples: {stats['flagged_samples']}")
    print(f"   Valid samples: {stats['total_samples'] - stats['flagged_samples']}")
    print(f"   Convergence rounds: {stats['convergence_rounds']}")
    print(f"   Winner votes: {stats['winner_votes']}")
    
    print(f"\n💰 COST ANALYSIS:")
    cost = result["cost_estimate"]
    print(f"   Samples per objective: {cost['samples_per_objective']}")
    print(f"   Total samples: {cost['total_samples']}")
    print(f"   Total cost: ${cost['total_cost']:.4f}")
    print(f"   Cost per objective: ${cost['cost_per_objective']:.4f}")
    
    print(f"\n✅ VALIDATION:")
    validation = result["validation"]
    print(f"   Valid: {validation['is_valid']}")
    print(f"   Overall score: {validation.get('overall_score', 'N/A')}/100")
    
    if validation.get('issues'):
        print(f"\n   Issues found:")
        for issue in validation['issues']:
            print(f"      - [{issue['severity']}] {issue['issue']}")
    
    if validation.get('strengths'):
        print(f"\n   Strengths:")
        for strength in validation['strengths']:
            print(f"      ✓ {strength}")
    
    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")
    
    return result


async def test_red_flags():
    """Test red flag detection."""
    from app.core.red_flags import AcademicRedFlags
    
    print("\n" + "="*80)
    print("RED FLAG DETECTION TEST")
    print("="*80 + "\n")
    
    detector = AcademicRedFlags.for_objectives()
    
    # Test cases
    test_cases = [
        {
            "name": "Good objective (should NOT flag)",
            "response": '["General Objective: To examine mobile phone prices in Uganda", "Specific Objective 1: To assess affordability trends"]',
            "should_flag": False
        },
        {
            "name": "Too long (should flag)",
            "response": "This is a very long response that goes on and on and on... " * 100,
            "should_flag": True
        },
        {
            "name": "Methodology creep (should flag)",
            "response": '["General Objective: To utilize regression analysis with n=500 and p<0.05 to contextualize the integrated model"]',
            "should_flag": True
        },
        {
            "name": "Invalid JSON (should flag)",
            "response": "This is not JSON at all",
            "should_flag": True
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['name']}")
        result = detector.detect_flags(test['response'], {'task_type': 'objective', 'expected_format': 'objective_list'})
        
        status = "✓ PASS" if result.should_flag == test['should_flag'] else "✗ FAIL"
        print(f"   {status} - Flagged: {result.should_flag} (expected: {test['should_flag']})")
        
        if result.should_flag:
            print(f"   Reasons: {', '.join(result.reasons)}")
            print(f"   Severity: {result.severity}")
        
        print()
    
    print("="*80 + "\n")


async def main():
    """Run all tests."""
    
    # Test 1: Red flag detection
    await test_red_flags()
    
    # Test 2: MAKER voting (commented out by default to avoid API costs)
    print("\n⚠️  Skipping MAKER voting test to avoid API costs.")
    print("   Uncomment the line below to run the full voting test.\n")
    
    # Uncomment to run full test:
    # await test_maker_voting()


if __name__ == "__main__":
    asyncio.run(main())
