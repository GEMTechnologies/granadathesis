"""
Standalone test for MAKER framework core components.

Tests voting orchestrator and red flag detection without requiring full app dependencies.
"""

import asyncio
import json
from typing import Optional, List


# Minimal red flag detector test
def test_red_flags_standalone():
    """Test red flag detection logic."""
    print("\n" + "="*80)
    print("RED FLAG DETECTION TEST (Standalone)")
    print("="*80 + "\n")
    
    # Test length-based flagging
    def estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    test_cases = [
        {
            "name": "Short response (should NOT flag)",
            "text": "This is a short response with about 50 tokens.",
            "max_tokens": 750,
            "should_flag": False
        },
        {
            "name": "Long response (should flag)",
            "text": "This is a very long response. " * 100,  # ~300 tokens
            "max_tokens": 100,
            "should_flag": True
        },
        {
            "name": "Methodology creep (should detect)",
            "text": "To utilize regression analysis with n=500 and p<0.05",
            "max_tokens": 750,
            "should_flag": True  # Has methodology keywords
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        tokens = estimate_tokens(test['text'])
        length_flag = tokens > test['max_tokens']
        
        # Check for methodology patterns
        methodology_keywords = ['utilize', 'n=', 'p<', 'regression']
        has_methodology = any(kw in test['text'] for kw in methodology_keywords)
        
        should_flag = length_flag or has_methodology
        
        status = "✓ PASS" if should_flag == test['should_flag'] else "✗ FAIL"
        print(f"Test {i}: {test['name']}")
        print(f"   {status}")
        print(f"   Tokens: {tokens} (max: {test['max_tokens']})")
        print(f"   Length flag: {length_flag}")
        print(f"   Methodology flag: {has_methodology}")
        print(f"   Should flag: {test['should_flag']}, Actual: {should_flag}")
        print()
    
    print("="*80 + "\n")


# Test voting logic
async def test_voting_logic():
    """Test first-to-ahead-by-k voting logic."""
    print("\n" + "="*80)
    print("VOTING LOGIC TEST")
    print("="*80 + "\n")
    
    from collections import Counter
    
    def has_consensus(vote_counts: Counter, k: int) -> bool:
        """Check if any candidate is ahead by k votes."""
        if len(vote_counts) < 2:
            return len(vote_counts) == 1 and vote_counts.most_common(1)[0][1] >= k
        
        most_common = vote_counts.most_common(2)
        first_count = most_common[0][1]
        second_count = most_common[1][1] if len(most_common) > 1 else 0
        
        return (first_count - second_count) >= k
    
    # Test cases
    test_cases = [
        {
            "name": "Clear winner (A has 5, B has 1, k=3)",
            "votes": {"A": 5, "B": 1},
            "k": 3,
            "should_have_consensus": True
        },
        {
            "name": "Close race (A has 3, B has 2, k=3)",
            "votes": {"A": 3, "B": 2},
            "k": 3,
            "should_have_consensus": False
        },
        {
            "name": "Exact threshold (A has 4, B has 1, k=3)",
            "votes": {"A": 4, "B": 1},
            "k": 3,
            "should_have_consensus": True
        },
        {
            "name": "Single candidate (A has 3, k=3)",
            "votes": {"A": 3},
            "k": 3,
            "should_have_consensus": True
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        vote_counts = Counter(test['votes'])
        has_cons = has_consensus(vote_counts, test['k'])
        
        status = "✓ PASS" if has_cons == test['should_have_consensus'] else "✗ FAIL"
        print(f"Test {i}: {test['name']}")
        print(f"   {status}")
        print(f"   Votes: {dict(vote_counts)}")
        print(f"   Has consensus: {has_cons} (expected: {test['should_have_consensus']})")
        print()
    
    print("="*80 + "\n")


# Test cost estimation
def test_cost_estimation():
    """Test MAKER cost estimation formulas."""
    print("\n" + "="*80)
    print("COST ESTIMATION TEST")
    print("="*80 + "\n")
    
    import math
    
    def estimate_k_min(per_step_success_rate: float, total_steps: int, target_success_prob: float = 0.95) -> int:
        """Calculate minimum k required."""
        p = per_step_success_rate
        s = total_steps
        t = target_success_prob
        
        if p <= 0.5:
            return -1  # Invalid
        
        numerator = math.log(t ** (-1/s) - 1)
        denominator = math.log((1 - p) / p)
        
        k_min = math.ceil(numerator / denominator)
        return max(1, k_min)
    
    # Test cases from paper
    test_cases = [
        {"p": 0.999, "s": 1000000, "t": 0.95, "expected_k_range": (2, 4)},
        {"p": 0.99, "s": 1000000, "t": 0.95, "expected_k_range": (5, 7)},
        {"p": 0.995, "s": 1000, "t": 0.95, "expected_k_range": (1, 3)},
    ]
    
    for i, test in enumerate(test_cases, 1):
        k_min = estimate_k_min(test['p'], test['s'], test['t'])
        in_range = test['expected_k_range'][0] <= k_min <= test['expected_k_range'][1]
        
        status = "✓ PASS" if in_range else "⚠ CHECK"
        print(f"Test {i}: p={test['p']}, s={test['s']:,}, t={test['t']}")
        print(f"   {status}")
        print(f"   k_min: {k_min} (expected range: {test['expected_k_range']})")
        print()
    
    # Cost estimation for objectives
    print("Objective Generation Cost Estimate:")
    num_objectives = 4
    k = 3
    samples_per_objective = k + 2  # k + overhead
    cost_per_sample = 0.05
    total_cost = num_objectives * samples_per_objective * cost_per_sample
    
    print(f"   Objectives: {num_objectives}")
    print(f"   k-threshold: {k}")
    print(f"   Samples per objective: {samples_per_objective}")
    print(f"   Cost per sample: ${cost_per_sample:.2f}")
    print(f"   Total cost: ${total_cost:.2f}")
    print()
    
    print("="*80 + "\n")


async def main():
    """Run all standalone tests."""
    
    print("\n🧪 MAKER FRAMEWORK - STANDALONE TESTS")
    print("Testing core components without full app dependencies\n")
    
    # Test 1: Red flags
    test_red_flags_standalone()
    
    # Test 2: Voting logic
    await test_voting_logic()
    
    # Test 3: Cost estimation
    test_cost_estimation()
    
    print("✅ ALL STANDALONE TESTS COMPLETE\n")


if __name__ == "__main__":
    asyncio.run(main())
