"""
Red Flag Detection for Academic Writing

Implements red-flagging heuristics from MAKER paper Section 3.3:
1. Length-based flags (responses >750 tokens often indicate confusion)
2. Format validation (incorrectly formatted responses correlate with errors)
3. Academic quality flags (methodology creep, vague language, missing citations)

Based on findings from Figure 9 in the MAKER paper.
"""

import re
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class RedFlagResult:
    """Result of red flag detection."""
    should_flag: bool
    reasons: List[str]
    severity: str  # 'minor', 'moderate', 'critical'
    details: Dict[str, Any]


class RedFlagDetector:
    """
    Detects unreliable LLM responses for academic writing.
    
    Red flags indicate higher probability of errors and should trigger
    sample discarding in the voting process.
    """
    
    def __init__(
        self,
        max_tokens: int = 750,
        enable_length_check: bool = True,
        enable_format_check: bool = True,
        enable_academic_check: bool = True
    ):
        self.max_tokens = max_tokens
        self.enable_length_check = enable_length_check
        self.enable_format_check = enable_format_check
        self.enable_academic_check = enable_academic_check
        
        # Methodology creep patterns (from objective.py)
        self.methodology_patterns = [
            r'\b(employ|utilize|utilising|utilizing)\b',
            r'\b(contextualize|contextualise)\b',
            r'\b(integrated\s+(?:explanatory\s+)?model)\b',
            r'\b(mixed\s+methods?\s+approach)\b',
            r'\b(holistic\s+understanding)\b',
            r'\b(n\s*=\s*\d+)\b',
            r'\b(p\s*[<>]\s*0\.\d+)\b',
            r'\b(r\s*=\s*0\.\d+)\b',
            r'\b(regression\s+analysis)\b',
            r'\b(using\s+surveys?)\b',
            r'\b(through\s+interviews?)\b',
            r'\b(via\s+questionnaires?)\b',
        ]
        
        # Vague language patterns
        self.vague_patterns = [
            r'\b(may|might|could|possibly|perhaps)\s+\w+\s+\w+\s+\w+',  # Multiple vague words
            r'\b(various|numerous|several|many)\s+(?:factors?|aspects?|elements?)\b',
            r'\b(to\s+some\s+extent)\b',
            r'\b(in\s+general)\b',
        ]
    
    def should_flag(self, response: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Quick check if response should be flagged.
        
        Args:
            response: LLM response text
            context: Optional context (task_type, expected_format, etc.)
            
        Returns:
            True if response should be flagged and discarded
        """
        result = self.detect_flags(response, context)
        return result.should_flag
    
    def detect_flags(self, response: str, context: Optional[Dict[str, Any]] = None) -> RedFlagResult:
        """
        Comprehensive red flag detection.
        
        Returns detailed analysis of all flags detected.
        """
        reasons = []
        details = {}
        severity = 'minor'
        
        context = context or {}
        task_type = context.get('task_type', 'unknown')
        
        # 1. Length-based flags (from paper Fig 9a)
        if self.enable_length_check:
            token_count = self._estimate_tokens(response)
            details['token_count'] = token_count
            
            if token_count > self.max_tokens:
                reasons.append(f"Response too long ({token_count} tokens > {self.max_tokens})")
                severity = 'moderate'
                details['length_flag'] = True
        
        # 2. Format validation
        if self.enable_format_check:
            format_issues = self._check_format(response, context)
            if format_issues:
                reasons.extend(format_issues)
                severity = 'critical'  # Format errors strongly correlate with other errors
                details['format_issues'] = format_issues
        
        # 3. Academic quality checks (for objectives)
        if self.enable_academic_check and task_type == 'objective':
            academic_issues = self._check_academic_quality(response)
            if academic_issues:
                reasons.extend(academic_issues)
                if severity != 'critical':
                    severity = 'moderate'
                details['academic_issues'] = academic_issues
        
        should_flag = len(reasons) > 0
        
        return RedFlagResult(
            should_flag=should_flag,
            reasons=reasons,
            severity=severity,
            details=details
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation (1 token ≈ 4 characters for English)."""
        return len(text) // 4
    
    def _check_format(self, response: str, context: Dict[str, Any]) -> List[str]:
        """
        Check for format violations.
        
        From paper: "when an agent produces an answer in an incorrect format,
        it is more likely to have become confused at some point"
        """
        issues = []
        expected_format = context.get('expected_format', 'json')
        
        if expected_format == 'json':
            # Try to parse as JSON
            clean_response = response.replace("```json", "").replace("```", "").strip()
            try:
                parsed = json.loads(clean_response)
                
                # Check if it's the expected type
                expected_type = context.get('expected_type', 'list')
                if expected_type == 'list' and not isinstance(parsed, list):
                    issues.append(f"Expected JSON list, got {type(parsed).__name__}")
                elif expected_type == 'dict' and not isinstance(parsed, dict):
                    issues.append(f"Expected JSON object, got {type(parsed).__name__}")
                    
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON format: {str(e)}")
        
        elif expected_format == 'objective_list':
            # Check for objective format: ["General Objective: ...", "Specific Objective 1: ...", ...]
            try:
                clean_response = response.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean_response)
                
                if not isinstance(parsed, list):
                    issues.append("Objectives must be a JSON list")
                elif len(parsed) < 2:
                    issues.append("Must have at least 1 General + 1 Specific objective")
                else:
                    # Check first is General
                    if not parsed[0].startswith("General Objective:"):
                        issues.append("First objective must start with 'General Objective:'")
                    
                    # Check rest are Specific
                    for i, obj in enumerate(parsed[1:], 1):
                        if not obj.startswith(f"Specific Objective {i}:"):
                            issues.append(f"Objective {i+1} must start with 'Specific Objective {i}:'")
                            
            except (json.JSONDecodeError, TypeError):
                issues.append("Could not parse objectives as JSON list")
        
        return issues
    
    def _check_academic_quality(self, response: str) -> List[str]:
        """
        Check for academic quality issues in objectives.
        
        Focuses on methodology creep and vague language.
        """
        issues = []
        
        # Check for methodology creep
        methodology_matches = []
        for pattern in self.methodology_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                methodology_matches.extend(matches)
        
        if methodology_matches:
            issues.append(f"Methodology creep detected: {', '.join(set(methodology_matches))}")
        
        # Check for excessive vague language
        vague_matches = []
        for pattern in self.vague_patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            if matches:
                vague_matches.extend(matches)
        
        if len(vague_matches) > 2:  # Allow some vagueness, but not too much
            issues.append(f"Excessive vague language: {len(vague_matches)} instances")
        
        # Check for SMART violations (objectives should be specific)
        if self._is_too_vague(response):
            issues.append("Objectives too vague (SMART violation)")
        
        return issues
    
    def _is_too_vague(self, text: str) -> bool:
        """Check if text is too vague to be a good objective."""
        # Count specific indicators vs vague indicators
        specific_verbs = ['examine', 'assess', 'analyze', 'identify', 'evaluate', 'measure', 'compare']
        vague_verbs = ['explore', 'understand', 'investigate', 'study', 'consider']
        
        specific_count = sum(1 for verb in specific_verbs if verb in text.lower())
        vague_count = sum(1 for verb in vague_verbs if verb in text.lower())
        
        # If mostly vague verbs, flag it
        return vague_count > specific_count and vague_count > 2


class AcademicRedFlags:
    """
    Specialized red flags for different academic writing tasks.
    """
    
    @staticmethod
    def for_objectives() -> RedFlagDetector:
        """Red flag detector configured for objectives."""
        return RedFlagDetector(
            max_tokens=750,
            enable_length_check=True,
            enable_format_check=True,
            enable_academic_check=True
        )
    
    @staticmethod
    def for_paragraphs() -> RedFlagDetector:
        """Red flag detector configured for paragraph generation."""
        return RedFlagDetector(
            max_tokens=500,  # Paragraphs should be concise
            enable_length_check=True,
            enable_format_check=False,  # Paragraphs are free-form
            enable_academic_check=False  # Different quality checks needed
        )
    
    @staticmethod
    def for_sections() -> RedFlagDetector:
        """Red flag detector configured for section generation."""
        return RedFlagDetector(
            max_tokens=2000,  # Sections can be longer
            enable_length_check=True,
            enable_format_check=False,
            enable_academic_check=False
        )


# Convenience function for quick red flag check
def quick_red_flag_check(
    response: str,
    task_type: str = 'objective',
    max_tokens: int = 750
) -> bool:
    """
    Quick red flag check for a response.
    
    Args:
        response: LLM response
        task_type: Type of task ('objective', 'paragraph', 'section')
        max_tokens: Maximum allowed tokens
        
    Returns:
        True if response should be flagged
    """
    if task_type == 'objective':
        detector = AcademicRedFlags.for_objectives()
    elif task_type == 'paragraph':
        detector = AcademicRedFlags.for_paragraphs()
    else:
        detector = AcademicRedFlags.for_sections()
    
    detector.max_tokens = max_tokens
    
    return detector.should_flag(response, {'task_type': task_type})
