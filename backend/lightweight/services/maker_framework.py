"""
MAKER Framework - Massively Decomposed Agentic Processes

Inspired by "SOLVING A MILLION-STEP LLM TASK WITH ZERO ERRORS" (Meyerson et al., 2025)

Core components:
1. MicroAgent - Base class for focused, single-purpose agents
2. VotingOrchestrator - First-to-ahead-by-k consensus mechanism
3. RedFlagDetector - Response quality filtering
4. AgentPool - Parallel execution management
"""

import asyncio
import time
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable, TypeVar, Generic
from enum import Enum
import json
import hashlib


class RedFlag(Enum):
    """Types of red flags that indicate unreliable responses."""
    EXCESSIVE_LENGTH = "excessive_length"
    FORMAT_ERROR = "format_error"
    METHODOLOGY_CREEP = "methodology_creep"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"
    CONFIDENCE_TOO_LOW = "confidence_too_low"


@dataclass
class AgentResponse:
    """Structured response from a microagent."""
    content: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    red_flags: List[RedFlag] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    
    def is_valid(self) -> bool:
        """Check if response has no red flags."""
        return len(self.red_flags) == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for caching."""
        return {
            "content": self.content,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "red_flags": [flag.value for flag in self.red_flags],
            "tokens_used": self.tokens_used,
            "latency_ms": self.latency_ms
        }


@dataclass
class VotingMetrics:
    """Metrics from a voting session."""
    total_samples: int = 0
    valid_samples: int = 0
    invalid_samples: int = 0
    voting_rounds: int = 0
    consensus_achieved: bool = False
    winner_votes: int = 0
    runner_up_votes: int = 0
    total_cost_estimate: float = 0.0
    total_latency_ms: float = 0.0
    red_flags_by_type: Dict[str, int] = field(default_factory=dict)


class RedFlagDetector:
    """
    Detects signs of unreliable LLM responses.
    
    Based on MAKER paper Section 3.3: Red-flagging to reduce correlated errors.
    """
    
    def __init__(
        self,
        max_tokens: int = 750,
        min_confidence: float = 0.3,
        required_fields: Optional[List[str]] = None,
        enable_format_check: bool = True,
        enable_academic_check: bool = True,
        enable_length_check: bool = True
    ):
        self.max_tokens = max_tokens
        self.min_confidence = min_confidence
        self.required_fields = required_fields or []
        self.enable_format_check = enable_format_check
        self.enable_academic_check = enable_academic_check
        self.enable_length_check = enable_length_check
        
        # Methodology keywords that indicate over-analysis
        self.methodology_keywords = [
            'utilize', 'leverage', 'implement', 'deploy',
            'n=', 'p<', 'p>', 'regression', 'anova',
            'statistical significance', 'correlation coefficient'
        ]
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars ≈ 1 token)."""
        return len(text) // 4
    
    def detect(self, response: AgentResponse) -> List[RedFlag]:
        """
        Detect red flags in agent response.
        
        Returns:
            List of detected red flags
        """
        flags = []
        
        # Check 1: Excessive length
        if self.enable_length_check and isinstance(response.content, str):
            tokens = self.estimate_tokens(response.content)
            if tokens > self.max_tokens:
                flags.append(RedFlag.EXCESSIVE_LENGTH)
        
        # Check 2: Low confidence
        if response.confidence < self.min_confidence:
            flags.append(RedFlag.CONFIDENCE_TOO_LOW)
        
        # Check 3: Format errors (missing required fields)
        if self.enable_format_check and isinstance(response.content, dict):
            for field in self.required_fields:
                if field not in response.content:
                    flags.append(RedFlag.MISSING_REQUIRED_FIELDS)
                    break
        
        # Check 4: Methodology creep (over-analysis)
        if self.enable_academic_check and isinstance(response.content, str):
            content_lower = response.content.lower()
            if any(kw in content_lower for kw in self.methodology_keywords):
                flags.append(RedFlag.METHODOLOGY_CREEP)
        
        return flags


T = TypeVar('T')


class VotingOrchestrator(Generic[T]):
    """
    First-to-ahead-by-k voting mechanism.
    
    Based on MAKER paper Section 3.2: Sequential probability ratio test (SPRT)
    for optimal voting convergence.
    """
    
    def __init__(
        self,
        k: int = 3,
        max_rounds: int = 20,
        red_flag_detector: Optional[RedFlagDetector] = None
    ):
        """
        Args:
            k: Margin required to win (first-to-ahead-by-k)
            max_rounds: Maximum voting rounds before fallback to plurality
            red_flag_detector: Optional detector for filtering responses
        """
        self.k = k
        self.max_rounds = max_rounds
        self.red_flag_detector = red_flag_detector or RedFlagDetector()
    
    def _response_to_vote_key(self, response: AgentResponse) -> str:
        """Convert response to hashable vote key."""
        if isinstance(response.content, dict):
            # Sort keys for consistent hashing
            content_str = json.dumps(response.content, sort_keys=True)
        else:
            content_str = str(response.content)
        
        return hashlib.md5(content_str.encode()).hexdigest()[:16]
    
    def _has_consensus(self, vote_counts: Counter, k: int) -> bool:
        """
        Check if any candidate is ahead by k votes.
        
        Based on gambler's ruin hitting probability.
        """
        if len(vote_counts) < 1:
            return False
        
        if len(vote_counts) == 1:
            # Single candidate needs at least k votes
            return vote_counts.most_common(1)[0][1] >= k
        
        # Multiple candidates: leader must be ahead by k
        most_common = vote_counts.most_common(2)
        first_count = most_common[0][1]
        second_count = most_common[1][1] if len(most_common) > 1 else 0
        
        return (first_count - second_count) >= k
    
    async def vote(
        self,
        sample_fn: Callable[[], Any],
        vote_key_fn: Optional[Callable[[AgentResponse], str]] = None
    ) -> tuple[AgentResponse, VotingMetrics]:
        """
        Run voting until consensus or max rounds.
        
        Args:
            sample_fn: Async function that returns an AgentResponse
            vote_key_fn: Optional custom function to extract vote key
            
        Returns:
            Tuple of (winning response, voting metrics)
        """
        metrics = VotingMetrics()
        vote_counts: Counter = Counter()
        responses_by_key: Dict[str, AgentResponse] = {}
        
        key_fn = vote_key_fn or self._response_to_vote_key
        
        for round_num in range(1, self.max_rounds + 1):
            metrics.voting_rounds = round_num
            
            # Sample response
            response = await sample_fn()
            metrics.total_samples += 1
            metrics.total_latency_ms += response.latency_ms
            
            # Check for red flags
            flags = self.red_flag_detector.detect(response)
            response.red_flags = flags
            
            # Track red flags
            for flag in flags:
                metrics.red_flags_by_type[flag.value] = \
                    metrics.red_flags_by_type.get(flag.value, 0) + 1
            
            if not response.is_valid():
                metrics.invalid_samples += 1
                continue  # Discard flagged response
            
            metrics.valid_samples += 1
            
            # Get vote key and record vote
            vote_key = key_fn(response)
            vote_counts[vote_key] += 1
            
            # Store response (keep highest confidence for each key)
            if vote_key not in responses_by_key or \
               response.confidence > responses_by_key[vote_key].confidence:
                responses_by_key[vote_key] = response
            
            # Check for consensus
            if self._has_consensus(vote_counts, self.k):
                metrics.consensus_achieved = True
                winner_key = vote_counts.most_common(1)[0][0]
                metrics.winner_votes = vote_counts[winner_key]
                
                if len(vote_counts) > 1:
                    metrics.runner_up_votes = vote_counts.most_common(2)[1][1]
                
                return responses_by_key[winner_key], metrics
        
        # Max rounds reached - fallback to plurality
        if len(vote_counts) > 0:
            winner_key = vote_counts.most_common(1)[0][0]
            metrics.winner_votes = vote_counts[winner_key]
            if len(vote_counts) > 1:
                metrics.runner_up_votes = vote_counts.most_common(2)[1][1]
            return responses_by_key[winner_key], metrics
        
        # No valid responses - raise error
        raise RuntimeError(
            f"No valid responses after {self.max_rounds} rounds. "
            f"Invalid samples: {metrics.invalid_samples}"
        )


class MicroAgent(ABC):
    """
    Base class for focused, single-purpose agents.
    
    Each microagent:
    - Handles ONE specific subtask
    - Returns structured AgentResponse
    - Participates in voting for reliability
    """
    
    def __init__(
        self,
        name: str,
        llm_client: Any,
        temperature: float = 0.1,
        max_tokens: int = 500
    ):
        self.name = name
        self.llm_client = llm_client
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return focused system prompt for this agent's role."""
        pass
    
    @abstractmethod
    def get_user_prompt(self, **kwargs) -> str:
        """Generate user prompt from input parameters."""
        pass
    
    @abstractmethod
    def parse_response(self, raw_response: str) -> Any:
        """Parse LLM response into structured output."""
        pass
    
    async def execute(self, **kwargs) -> AgentResponse:
        """
        Execute agent's task and return structured response.
        
        Returns:
            AgentResponse with parsed content and metadata
        """
        start_time = time.time()
        
        try:
            # Build prompts
            system_prompt = self.get_system_prompt()
            user_prompt = self.get_user_prompt(**kwargs)
            
            # Call LLM
            raw_response = await self._call_llm(system_prompt, user_prompt)
            
            # Parse response
            parsed_content = self.parse_response(raw_response)
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            return AgentResponse(
                content=parsed_content,
                confidence=self._estimate_confidence(raw_response),
                metadata={
                    "agent_name": self.name,
                    "raw_response": raw_response[:200]  # Truncate for storage
                },
                tokens_used=len(raw_response) // 4,  # Rough estimate
                latency_ms=latency_ms
            )
            
        except Exception as e:
            # Return error response with low confidence
            return AgentResponse(
                content={"error": str(e)},
                confidence=0.0,
                metadata={"agent_name": self.name, "error": str(e)},
                red_flags=[RedFlag.FORMAT_ERROR]
            )
    
    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Call LLM client (override for specific LLM APIs)."""
        # Default implementation - override in subclasses
        raise NotImplementedError("Subclass must implement _call_llm")
    
    def _estimate_confidence(self, raw_response: str) -> float:
        """
        Estimate confidence from response characteristics.
        
        Simple heuristic - can be improved with uncertainty quantification.
        """
        # Longer, more detailed responses tend to be more confident
        # But not too long (red flag territory)
        length = len(raw_response)
        
        if length < 50:
            return 0.5  # Too short, uncertain
        elif length > 2000:
            return 0.6  # Too long, possibly confused
        else:
            return 0.9  # Good length, likely confident


class AgentPool:
    """
    Manages parallel execution of multiple agents.
    
    Enables speed through parallelization while maintaining reliability
    through voting.
    """
    
    def __init__(self, max_concurrent: int = 10):
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute_with_voting(
        self,
        agent: MicroAgent,
        orchestrator: VotingOrchestrator,
        agent_kwargs: Dict[str, Any]
    ) -> tuple[AgentResponse, VotingMetrics]:
        """
        Execute agent with voting orchestration.
        
        Args:
            agent: MicroAgent to execute
            orchestrator: VotingOrchestrator for consensus
            agent_kwargs: Arguments to pass to agent.execute()
            
        Returns:
            Tuple of (consensus response, voting metrics)
        """
        async def sample_fn():
            async with self.semaphore:
                return await agent.execute(**agent_kwargs)
        
        return await orchestrator.vote(sample_fn)
    
    async def execute_pipeline(
        self,
        agents: List[tuple[MicroAgent, Dict[str, Any]]],
        orchestrator: VotingOrchestrator
    ) -> List[tuple[AgentResponse, VotingMetrics]]:
        """
        Execute multiple agents in parallel with voting.
        
        Args:
            agents: List of (agent, kwargs) tuples
            orchestrator: VotingOrchestrator for all agents
            
        Returns:
            List of (response, metrics) for each agent
        """
        tasks = [
            self.execute_with_voting(agent, orchestrator, kwargs)
            for agent, kwargs in agents
        ]
        
        return await asyncio.gather(*tasks)


# Cost estimation utilities (from MAKER paper Eq. 14, 18)

def estimate_k_min(
    per_step_success_rate: float,
    total_steps: int,
    target_success_prob: float = 0.95
) -> int:
    """
    Calculate minimum k required for target success probability.
    
    Based on MAKER paper Eq. 14.
    
    Args:
        per_step_success_rate: Probability of correct response per step (p)
        total_steps: Number of steps in task (s)
        target_success_prob: Target overall success probability (t)
        
    Returns:
        Minimum k threshold
    """
    import math
    
    p = per_step_success_rate
    s = total_steps
    t = target_success_prob
    
    if p <= 0.5:
        return -1  # Invalid - voting won't converge
    
    try:
        numerator = math.log(t ** (-1/s) - 1)
        denominator = math.log((1 - p) / p)
        k_min = math.ceil(numerator / denominator)
        return max(1, k_min)
    except (ValueError, ZeroDivisionError):
        return 3  # Safe default


def estimate_cost(
    per_step_success_rate: float,
    total_steps: int,
    cost_per_sample: float,
    k: Optional[int] = None,
    target_success_prob: float = 0.95
) -> float:
    """
    Estimate total cost for MDAP execution.
    
    Based on MAKER paper Eq. 18: E[cost] = Θ(s * ln(s))
    
    Args:
        per_step_success_rate: p
        total_steps: s
        cost_per_sample: Cost per LLM call
        k: Vote threshold (auto-calculated if None)
        target_success_prob: t
        
    Returns:
        Estimated total cost
    """
    import math
    
    if k is None:
        k = estimate_k_min(per_step_success_rate, total_steps, target_success_prob)
    
    # Expected samples per step ≈ k * (1 + overhead)
    # Overhead from invalid samples: 1 / per_step_success_rate
    expected_samples_per_step = k * (1.0 / per_step_success_rate)
    
    total_cost = total_steps * expected_samples_per_step * cost_per_sample
    
    return total_cost
