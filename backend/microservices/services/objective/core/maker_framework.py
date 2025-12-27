"""
MAKER Framework - Core Implementation

This module implements the core components of the MAKER framework:
1. VotingOrchestrator - Manages first-to-ahead-by-k voting
2. Cost estimation based on paper's Equation 18
3. Parallel voting support

Based on: "Solving a Million-Step LLM Task with Zero Errors" (Meyerson et al., 2025)
"""

import asyncio
import math
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from datetime import datetime
from collections import Counter


@dataclass
class VotingResult:
    """Result of a voting session."""
    winner: str
    winner_votes: int
    total_samples: int
    flagged_samples: int
    convergence_rounds: int
    all_votes: List[Dict[str, Any]]
    vote_distribution: Dict[str, int]
    estimated_cost: float
    actual_cost: float
    timestamp: str


@dataclass
class VotingConfig:
    """Configuration for voting process."""
    k: int = 3  # Votes ahead threshold
    max_samples: int = 20  # Maximum samples before giving up
    enable_parallel: bool = True  # Generate samples in parallel
    temperature_range: Tuple[float, float] = (0.0, 0.1)  # (first_sample, others)
    cost_per_1k_tokens: float = 0.0016  # gpt-4.1-mini pricing


class VotingOrchestrator:
    """
    Implements first-to-ahead-by-k voting from MAKER framework.
    
    Algorithm:
    1. Generate samples until one candidate is ahead by k votes
    2. First sample uses temperature=0 (best guess)
    3. Subsequent samples use temperature>0 for diversity
    4. Tracks all votes and costs
    """
    
    def __init__(self, config: Optional[VotingConfig] = None):
        self.config = config or VotingConfig()
        
    async def vote_until_consensus(
        self,
        generate_sample: Callable,  # async function that generates one sample
        validate_sample: Callable,  # function that validates/parses sample
        red_flag_detector: Optional[Callable] = None,  # optional red flag check
        context: Optional[Dict[str, Any]] = None
    ) -> VotingResult:
        """
        Run first-to-ahead-by-k voting until consensus.
        
        Args:
            generate_sample: Async function(temperature) -> str
            validate_sample: Function(response) -> parsed_result or None
            red_flag_detector: Optional function(response) -> bool (True if should flag)
            context: Optional context for red flag detection
            
        Returns:
            VotingResult with winner and statistics
        """
        vote_counts: Counter = Counter()
        all_votes: List[Dict[str, Any]] = []
        flagged_count = 0
        sample_count = 0
        convergence_rounds = 0
        
        print(f"\n🗳️  VOTING SESSION STARTED (k={self.config.k})")
        
        while sample_count < self.config.max_samples:
            # Determine temperature for this sample
            temperature = self.config.temperature_range[0] if sample_count == 0 else self.config.temperature_range[1]
            
            # Generate sample
            try:
                response = await generate_sample(temperature=temperature)
                sample_count += 1
                
                # Check for red flags
                if red_flag_detector and red_flag_detector(response, context or {}):
                    flagged_count += 1
                    all_votes.append({
                        "sample_number": sample_count,
                        "response": response,
                        "flagged": True,
                        "vote_for": None,
                        "temperature": temperature
                    })
                    print(f"   🚩 Sample {sample_count}: FLAGGED (discarded)")
                    continue
                
                # Validate and parse
                parsed = validate_sample(response)
                if parsed is None:
                    flagged_count += 1
                    all_votes.append({
                        "sample_number": sample_count,
                        "response": response,
                        "flagged": True,
                        "vote_for": None,
                        "temperature": temperature
                    })
                    print(f"   🚩 Sample {sample_count}: INVALID (discarded)")
                    continue
                
                # Convert to hashable string for voting
                vote_key = self._to_vote_key(parsed)
                vote_counts[vote_key] += 1
                
                all_votes.append({
                    "sample_number": sample_count,
                    "response": response,
                    "flagged": False,
                    "vote_for": vote_key,
                    "parsed": parsed,
                    "temperature": temperature
                })
                
                convergence_rounds += 1
                print(f"   ✓ Sample {sample_count}: Vote for candidate (total: {vote_counts[vote_key]})")
                
                # Check for consensus (first-to-ahead-by-k)
                if self._has_consensus(vote_counts):
                    winner_key = vote_counts.most_common(1)[0][0]
                    winner_votes = vote_counts[winner_key]
                    print(f"\n   🎉 CONSENSUS REACHED!")
                    print(f"   Winner: {winner_votes} votes (ahead by {self._get_lead(vote_counts)})")
                    
                    # Find the actual parsed result for winner
                    winner_parsed = next(
                        v["parsed"] for v in all_votes 
                        if not v["flagged"] and v["vote_for"] == winner_key
                    )
                    
                    return VotingResult(
                        winner=winner_parsed,
                        winner_votes=winner_votes,
                        total_samples=sample_count,
                        flagged_samples=flagged_count,
                        convergence_rounds=convergence_rounds,
                        all_votes=all_votes,
                        vote_distribution=dict(vote_counts),
                        estimated_cost=self.estimate_cost(sample_count),
                        actual_cost=self.estimate_cost(sample_count),  # TODO: track actual
                        timestamp=datetime.now().isoformat()
                    )
                    
            except Exception as e:
                print(f"   ✗ Sample {sample_count}: Error - {str(e)}")
                sample_count += 1
                continue
        
        # Max samples reached without consensus
        print(f"\n   ⚠️  MAX SAMPLES REACHED ({self.config.max_samples})")
        if vote_counts:
            # Return best candidate
            winner_key = vote_counts.most_common(1)[0][0]
            winner_votes = vote_counts[winner_key]
            winner_parsed = next(
                v["parsed"] for v in all_votes 
                if not v["flagged"] and v["vote_for"] == winner_key
            )
            
            print(f"   Selecting best candidate: {winner_votes} votes")
            
            return VotingResult(
                winner=winner_parsed,
                winner_votes=winner_votes,
                total_samples=sample_count,
                flagged_samples=flagged_count,
                convergence_rounds=convergence_rounds,
                all_votes=all_votes,
                vote_distribution=dict(vote_counts),
                estimated_cost=self.estimate_cost(sample_count),
                actual_cost=self.estimate_cost(sample_count),
                timestamp=datetime.now().isoformat()
            )
        else:
            raise Exception("No valid samples generated")
    
    def _has_consensus(self, vote_counts: Counter) -> bool:
        """Check if any candidate is ahead by k votes."""
        if len(vote_counts) < 2:
            return len(vote_counts) == 1 and vote_counts.most_common(1)[0][1] >= self.config.k
        
        most_common = vote_counts.most_common(2)
        first_count = most_common[0][1]
        second_count = most_common[1][1] if len(most_common) > 1 else 0
        
        return (first_count - second_count) >= self.config.k
    
    def _get_lead(self, vote_counts: Counter) -> int:
        """Get the lead of the top candidate."""
        if len(vote_counts) < 2:
            return vote_counts.most_common(1)[0][1]
        
        most_common = vote_counts.most_common(2)
        return most_common[0][1] - most_common[1][1]
    
    def _to_vote_key(self, parsed: Any) -> str:
        """Convert parsed result to hashable vote key."""
        if isinstance(parsed, str):
            return parsed
        elif isinstance(parsed, list):
            return str(sorted(parsed))  # Sort for consistency
        elif isinstance(parsed, dict):
            return str(sorted(parsed.items()))
        else:
            return str(parsed)
    
    def estimate_cost(
        self,
        num_samples: int,
        avg_input_tokens: int = 500,
        avg_output_tokens: int = 300
    ) -> float:
        """
        Estimate cost based on number of samples.
        
        Uses gpt-4.1-mini pricing:
        - Input: $0.00040 per 1K tokens
        - Output: $0.00160 per 1K tokens
        """
        input_cost = (avg_input_tokens * num_samples / 1000) * 0.0004
        output_cost = (avg_output_tokens * num_samples / 1000) * 0.0016
        return input_cost + output_cost


class MAKERCostEstimator:
    """
    Cost estimation based on MAKER paper's Equation 18.
    
    E[cost] = (c × s × k_min) / (v × p × (2p - 1))
    
    where:
    - c = cost per sample
    - s = number of steps
    - k_min = minimum votes required
    - v = probability of valid (non-flagged) response
    - p = per-step success rate
    """
    
    @staticmethod
    def estimate_k_min(
        per_step_success_rate: float,
        total_steps: int,
        target_success_prob: float = 0.95
    ) -> int:
        """
        Calculate minimum k required for target success probability.
        
        From paper's Eq. 14:
        k_min = ⌈ln(t^(-1/s) - 1) / ln((1-p)/p)⌉
        """
        p = per_step_success_rate
        s = total_steps
        t = target_success_prob
        
        if p <= 0.5:
            raise ValueError("per_step_success_rate must be > 0.5 for voting to converge")
        
        numerator = math.log(t ** (-1/s) - 1)
        denominator = math.log((1 - p) / p)
        
        k_min = math.ceil(numerator / denominator)
        return max(1, k_min)  # At least 1
    
    @staticmethod
    def estimate_total_cost(
        cost_per_sample: float,
        total_steps: int,
        k_min: int,
        valid_response_rate: float = 0.95,
        per_step_success_rate: float = 0.998
    ) -> float:
        """
        Estimate total cost for full task.
        
        From paper's Eq. 19:
        E[cost] = (c × s × k_min) / (v × p × (2p - 1))
        """
        c = cost_per_sample
        s = total_steps
        k = k_min
        v = valid_response_rate
        p = per_step_success_rate
        
        return (c * s * k) / (v * p * (2 * p - 1))
    
    @staticmethod
    def estimate_objective_generation_cost(
        num_objectives: int = 4,
        k: int = 3,
        cost_per_objective_sample: float = 0.05
    ) -> Dict[str, float]:
        """
        Estimate cost for objective generation with voting.
        
        Returns breakdown of costs.
        """
        # Each objective voted on separately
        samples_per_objective = k + 2  # k + some overhead for flags
        total_samples = num_objectives * samples_per_objective
        total_cost = total_samples * cost_per_objective_sample
        
        return {
            "num_objectives": num_objectives,
            "k_threshold": k,
            "samples_per_objective": samples_per_objective,
            "total_samples": total_samples,
            "cost_per_sample": cost_per_objective_sample,
            "total_cost": total_cost,
            "cost_per_objective": total_cost / num_objectives
        }


# Convenience function for simple voting
async def vote_on_task(
    task_prompt: str,
    llm_generate: Callable,
    parser: Callable,
    k: int = 3,
    red_flag_detector: Optional[Callable] = None
) -> VotingResult:
    """
    Convenience function for simple voting on a task.
    
    Args:
        task_prompt: The prompt for the task
        llm_generate: Function(prompt, temperature) -> response
        parser: Function(response) -> parsed or None
        k: Vote threshold
        red_flag_detector: Optional red flag function
        
    Returns:
        VotingResult
    """
    config = VotingConfig(k=k)
    orchestrator = VotingOrchestrator(config)
    
    async def generate_sample(temperature: float) -> str:
        return await llm_generate(task_prompt, temperature)
    
    return await orchestrator.vote_until_consensus(
        generate_sample=generate_sample,
        validate_sample=parser,
        red_flag_detector=red_flag_detector
    )
