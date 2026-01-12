"""Objective generation helpers for /good flow."""

from __future__ import annotations

import re
from typing import List, Optional


def format_location(case_study: str, country: str) -> str:
    location = (case_study or "").strip()
    country = (country or "").strip()
    if not location:
        return country or "the study area"
    if country and re.search(rf"\b{re.escape(country)}\b", location, re.IGNORECASE):
        return location
    if country:
        return f"{location}, {country}"
    return location


def strip_location_from_topic(topic: str, location: str) -> str:
    cleaned = (topic or "").strip()
    if not cleaned or not location:
        return cleaned
    pattern = re.escape(location)
    cleaned = re.sub(rf'(?i)\s+in\s+{pattern}', '', cleaned)
    cleaned = re.sub(rf'(?i)\s*,?\s*{pattern}', '', cleaned)
    return cleaned.strip(" ,")


def build_good_objectives_prompt(topic: str, case_study: str, country: str) -> str:
    location = format_location(case_study, country)
    topic = strip_location_from_topic(topic, location) or topic
    return (
        "Use UK English throughout.\n\n"
        "Write the following section exactly in this structure:\n"
        "1.4 Objectives of the Study\n"
        "The study will be guided by both a general objective and a list of specific objectives as presented below;\n"
        "1.4.1 General objective of the study\n"
        "The general objective of the study is to ...\n"
        "1.4.2 Specific Objectives\n"
        "1. ...\n"
        "2. ...\n"
        "3. ...\n"
        "4. ...\n\n"
        f"Write the general objective for the study titled {topic} in {location}.\n"
        "Summarise and present it in one small paragraph. Be brief.\n"
        f"List four SMART study specific objectives about {topic} in {location}.\n"
        "Write short sentences and brief, don't include time.\n"
        "Objectives have to have the last two on challenges and then solutions.\n"
        "Return ONLY the section above in the same order and headings."
    )


_OBJECTIVE_VERBS = (
    "identify",
    "assess",
    "examine",
    "evaluate",
    "analyse",
    "analyze",
    "determine",
    "investigate",
    "explore",
    "propose",
    "understand",
    "describe",
    "measure",
    "estimate",
    "compare",
)


def parse_objectives(text: str) -> List[str]:
    if not text:
        return []
    lines: List[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if re.search(r'\b1\.4(\.\d+)?\b', line, re.IGNORECASE):
            continue
        if re.search(r'objectives of the study', line, re.IGNORECASE):
            continue
        if re.search(r'study will be guided by', line, re.IGNORECASE):
            continue
        if re.search(r'general objective', line, re.IGNORECASE):
            continue
        line = re.sub(r'^[\-\*\d\.\)\s]+', '', line).strip()
        if line:
            if re.search(r'general objective', line, re.IGNORECASE):
                continue
            lines.append(line)
    if len(lines) == 1:
        # Try to split a single paragraph into objectives.
        parts = [p.strip() for p in re.split(r';|\n|\.(?=\s+[A-Z])', lines[0]) if p.strip()]
        if len(parts) > 1:
            lines = parts
    return lines


def parse_general_objective(text: str) -> str:
    if not text:
        return ""
    lines = [line.strip() for line in text.splitlines()]
    start_idx: Optional[int] = None
    for i, line in enumerate(lines):
        if re.search(r'\b1\.4\.1\b', line) or re.search(r'general objective', line, re.IGNORECASE):
            start_idx = i
            break
    if start_idx is None:
        return ""
    collected: List[str] = []
    for j in range(start_idx + 1, len(lines)):
        line = lines[j].strip()
        if not line:
            if collected:
                break
            continue
        if re.search(r'\b1\.4\.2\b', line) or re.search(r'specific objectives', line, re.IGNORECASE):
            break
        collected.append(line)
    return " ".join(collected).strip()


def fallback_general_objective(topic: str, case_study: str, country: str) -> str:
    location = format_location(case_study, country)
    return f"The general objective of the study is to examine {topic} in {location}."


def fallback_objectives(topic: str, case_study: str, country: str) -> List[str]:
    location = format_location(case_study, country)
    return [
        f"To examine the key factors influencing {topic} in {location}.",
        f"To assess the main patterns and outcomes associated with {topic} in {location}.",
        f"To identify the major challenges affecting {topic} in {location}.",
        f"To propose feasible solutions for addressing the challenges of {topic} in {location}."
    ]


def normalise_objectives(objectives: List[str], user_provided: bool = False) -> List[str]:
    cleaned = [str(obj).strip() for obj in (objectives or []) if str(obj).strip()]
    limit = 5 if user_provided else 4
    return cleaned[:limit]


def _objective_to_phrase(objective: str) -> str:
    phrase = (objective or "").strip().rstrip(".")
    phrase = re.sub(r'(?i)^to\s+', '', phrase).strip()
    for verb in _OBJECTIVE_VERBS:
        phrase = re.sub(rf'(?i)^{verb}\s+', '', phrase).strip()
    return phrase


def objectives_to_questions(objectives: List[str]) -> List[str]:
    questions: List[str] = []
    for obj in objectives:
        phrase = _objective_to_phrase(obj)
        if not phrase:
            continue
        question = f"What are {phrase}"
        question = question.rstrip(".").rstrip("?") + "?"
        questions.append(question)
    return questions


def objectives_to_hypotheses(objectives: List[str]) -> List[str]:
    hypotheses: List[str] = []
    for idx, obj in enumerate(objectives, 1):
        phrase = _objective_to_phrase(obj)
        if not phrase:
            continue
        hypotheses.append(f"H0{idx}: There is no significant evidence of {phrase}.")
        hypotheses.append(f"H{idx}: There is significant evidence of {phrase}.")
    return hypotheses


def build_significance_lines(topic: str, country: str, case_study: str) -> List[str]:
    location = format_location(case_study, country)
    return [
        (
            "Policymakers: The study will inform policy choices on conflict prevention and response "
            f"for {location} by clarifying priority drivers of {topic}."
        ),
        (
            "Practitioners: The findings will guide practitioners in designing context-appropriate "
            f"programmes addressing {topic} in {location}."
        ),
        (
            f"Academics: The study will extend scholarship on {topic} by providing evidence grounded in "
            f"{location}."
        ),
        (
            "Institutions: The evidence will support institutional planning and coordination for "
            f"peacebuilding and service delivery in {location}."
        ),
        (
            "Local communities: The study will highlight community needs and practical solutions that "
            f"can reduce the effects of {topic} in {location}."
        ),
    ]
