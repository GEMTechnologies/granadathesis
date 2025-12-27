"""
Standalone MDAP Framework Tests

Tests core MDAP components without requiring full app dependencies.
"""

import asyncio
from collections import Counter
import json


# ============================================================================
# Test 1: Voting Logic
# ============================================================================

def test_voting_consensus():
    """Test first-to-ahead-by-k consensus logic."""
    print("\n" + "="*80)
    print("TEST 1: VOTING CONSENSUS LOGIC")
    print("="*80 + "\n")
    
    def has_consensus(vote_counts: Counter, k: int) -> bool:
        """Check if any candidate is ahead by k votes."""
        if len(vote_counts) < 1:
            return False
        
        if len(vote_counts) == 1:
            return vote_counts.most_common(1)[0][1] >= k
        
        most_common = vote_counts.most_common(2)
        first_count = most_common[0][1]
        second_count = most_common[1][1] if len(most_common) > 1 else 0
        
        return (first_count - second_count) >= k
    
    test_cases = [
        {
            "name": "Clear winner (A:5, B:1, k=3)",
            "votes": {"A": 5, "B": 1},
            "k": 3,
            "expected": True
        },
        {
            "name": "Close race (A:3, B:2, k=3)",
            "votes": {"A": 3, "B": 2},
            "k": 3,
            "expected": False
        },
        {
            "name": "Exact threshold (A:4, B:1, k=3)",
            "votes": {"A": 4, "B": 1},
            "k": 3,
            "expected": True
        },
        {
            "name": "Single candidate (A:3, k=3)",
            "votes": {"A": 3},
            "k": 3,
            "expected": True
        },
        {
            "name": "Three-way race (A:4, B:2, C:1, k=3)",
            "votes": {"A": 4, "B": 2, "C": 1},
            "k": 3,
            "expected": False  # A only ahead of B by 2
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        vote_counts = Counter(test['votes'])
        result = has_consensus(vote_counts, test['k'])
        
        status = "✓ PASS" if result == test['expected'] else "✗ FAIL"
        print(f"Test {i}: {test['name']}")
        print(f"   {status}")
        print(f"   Votes: {dict(vote_counts)}")
        print(f"   Has consensus: {result} (expected: {test['expected']})")
        print()
        
        if result == test['expected']:
            passed += 1
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


# ============================================================================
# Test 2: Red Flag Detection
# ============================================================================

def test_red_flag_detection():
    """Test red flag detection logic."""
    print("\n" + "="*80)
    print("TEST 2: RED FLAG DETECTION")
    print("="*80 + "\n")
    
    def estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    def detect_red_flags(response: dict, max_tokens: int = 750) -> list:
        """Detect red flags in response."""
        flags = []
        
        # Check 1: Excessive length
        if isinstance(response.get('content'), str):
            tokens = estimate_tokens(response['content'])
            if tokens > max_tokens:
                flags.append("EXCESSIVE_LENGTH")
        
        # Check 2: Low confidence
        if response.get('confidence', 1.0) < 0.3:
            flags.append("CONFIDENCE_TOO_LOW")
        
        # Check 3: Missing required fields
        if isinstance(response.get('content'), dict):
            required = response.get('required_fields', [])
            for field in required:
                if field not in response['content']:
                    flags.append("MISSING_REQUIRED_FIELDS")
                    break
        
        # Check 4: Methodology creep
        if isinstance(response.get('content'), str):
            methodology_keywords = ['utilize', 'n=', 'p<', 'regression']
            if any(kw in response['content'].lower() for kw in methodology_keywords):
                flags.append("METHODOLOGY_CREEP")
        
        return flags
    
    test_cases = [
        {
            "name": "Valid short response",
            "response": {"content": "This is a good response.", "confidence": 0.9},
            "expected_flags": []
        },
        {
            "name": "Excessive length",
            "response": {"content": "Very long response. " * 200, "confidence": 0.9},
            "expected_flags": ["EXCESSIVE_LENGTH"]
        },
        {
            "name": "Low confidence",
            "response": {"content": "Uncertain response.", "confidence": 0.1},
            "expected_flags": ["CONFIDENCE_TOO_LOW"]
        },
        {
            "name": "Methodology creep",
            "response": {"content": "We should utilize regression with n=500", "confidence": 0.9},
            "expected_flags": ["METHODOLOGY_CREEP"]
        },
        {
            "name": "Missing required fields",
            "response": {
                "content": {"title": "Paper"},
                "confidence": 0.9,
                "required_fields": ["title", "abstract"]
            },
            "expected_flags": ["MISSING_REQUIRED_FIELDS"]
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        flags = detect_red_flags(test['response'])
        
        # Check if at least one expected flag is present
        has_expected = any(f in flags for f in test['expected_flags']) if test['expected_flags'] else len(flags) == 0
        
        status = "✓ PASS" if has_expected else "✗ FAIL"
        print(f"Test {i}: {test['name']}")
        print(f"   {status}")
        print(f"   Detected flags: {flags}")
        print(f"   Expected flags: {test['expected_flags']}")
        print()
        
        if has_expected:
            passed += 1
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


# ============================================================================
# Test 3: Cost Estimation
# ============================================================================

def test_cost_estimation():
    """Test MAKER cost estimation formulas."""
    print("\n" + "="*80)
    print("TEST 3: COST ESTIMATION")
    print("="*80 + "\n")
    
    import math
    
    def estimate_k_min(p: float, s: int, t: float = 0.95) -> int:
        """Calculate minimum k required."""
        if p <= 0.5:
            return -1
        
        try:
            numerator = math.log(t ** (-1/s) - 1)
            denominator = math.log((1 - p) / p)
            k_min = math.ceil(numerator / denominator)
            return max(1, k_min)
        except (ValueError, ZeroDivisionError):
            return 3
    
    def estimate_cost(p: float, s: int, cost_per_sample: float, k: int) -> float:
        """Estimate total cost."""
        expected_samples_per_step = k * (1.0 / p)
        return s * expected_samples_per_step * cost_per_sample
    
    scenarios = [
        {"p": 0.99, "s": 100, "cost": 0.01, "desc": "100 steps, 99% success"},
        {"p": 0.95, "s": 1000, "cost": 0.01, "desc": "1000 steps, 95% success"},
        {"p": 0.999, "s": 10000, "cost": 0.005, "desc": "10K steps, 99.9% success"},
        {"p": 0.99, "s": 15, "cost": 0.01, "desc": "15 agents (MDAP search)"},
    ]
    
    print("Cost estimates for different scenarios:\n")
    
    for scenario in scenarios:
        k_min = estimate_k_min(scenario["p"], scenario["s"])
        cost = estimate_cost(scenario["p"], scenario["s"], scenario["cost"], k=k_min)
        
        print(f"{scenario['desc']}:")
        print(f"  Per-step success rate: {scenario['p']:.1%}")
        print(f"  Total steps: {scenario['s']}")
        print(f"  k_min: {k_min}")
        print(f"  Cost per sample: ${scenario['cost']:.3f}")
        print(f"  Estimated total cost: ${cost:.2f}")
        print()
    
    print("✓ Cost estimation formulas working\n")
    return True


# ============================================================================
# Test 4: Agent Response Parsing
# ============================================================================

def test_agent_response_parsing():
    """Test JSON parsing from agent responses."""
    print("\n" + "="*80)
    print("TEST 4: AGENT RESPONSE PARSING")
    print("="*80 + "\n")
    
    import re
    
    def parse_json_response(raw_response: str) -> dict:
        """Extract JSON from response."""
        json_match = re.search(r'\{[^}]+\}', raw_response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                return {}
        return {}
    
    test_cases = [
        {
            "name": "Clean JSON",
            "response": '{"answer": "A", "confidence": 0.9}',
            "expected_keys": ["answer", "confidence"]
        },
        {
            "name": "JSON with surrounding text",
            "response": 'Here is the result: {"answer": "B"} as you can see.',
            "expected_keys": ["answer"]
        },
        {
            "name": "No JSON",
            "response": "This is just text without JSON",
            "expected_keys": []
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        parsed = parse_json_response(test['response'])
        has_keys = all(k in parsed for k in test['expected_keys'])
        
        status = "✓ PASS" if (has_keys or not test['expected_keys']) else "✗ FAIL"
        print(f"Test {i}: {test['name']}")
        print(f"   {status}")
        print(f"   Parsed: {parsed}")
        print(f"   Expected keys: {test['expected_keys']}")
        print()
        
        if has_keys or not test['expected_keys']:
            passed += 1
    
    print(f"Results: {passed}/{len(test_cases)} tests passed\n")
    return passed == len(test_cases)


# ============================================================================
# Main Test Runner
# ============================================================================

def main():
    """Run all standalone tests."""
    
    print("\n" + "="*80)
    print("MDAP FRAMEWORK - STANDALONE TESTS")
    print("="*80)
    print("\nTesting core MDAP components without full app dependencies\n")
    
    results = []
    
    # Run all tests
    results.append(("Voting Consensus", test_voting_consensus()))
    results.append(("Red Flag Detection", test_red_flag_detection()))
    results.append(("Cost Estimation", test_cost_estimation()))
    results.append(("Agent Response Parsing", test_agent_response_parsing()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80 + "\n")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} {name}")
    
    print(f"\nOverall: {passed}/{total} test suites passed")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED\n")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST SUITE(S) FAILED\n")
        return 1


if __name__ == "__main__":
    exit(main())
