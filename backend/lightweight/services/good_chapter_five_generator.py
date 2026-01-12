"""Generate Chapter Five (Discussion, Conclusions, Recommendations) for /good flow."""

from __future__ import annotations

import json
import re
from itertools import cycle
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from core.events import events
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.workspace_service import WORKSPACES_DIR
from services.good_chapter_one_generator import _clean_text
from services.good_objective_generator import normalise_objectives


def _pick_latest(path: Path, pattern: str) -> Optional[Path]:
    files = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    return files[-1] if files else None


def _extract_citations(content: str) -> List[str]:
    citations: List[str] = []
    patterns = [
        r"\[([^\]]+\s*\(\d{4}\))\]\(([^\)]+)\)",
        r"\[\(([^\)]+,\s*\d{4})\)\]\(([^\)]+)\)",
        r"\[([^\]]+,\s*\d{4})\]\(([^\)]+)\)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content or ""):
            text = (match.group(1) or "").strip()
            url = (match.group(2) or "").strip()
            if not text:
                continue
            formatted = f"[{text}]({url})" if url else f"({text})"
            if formatted not in citations:
                citations.append(formatted)
    return citations


def _load_chapter2_citations(workspace_id: str) -> List[str]:
    chapter2_path = WORKSPACES_DIR / workspace_id / "good" / "Chapter_2_Literature_Review.md"
    if not chapter2_path.exists():
        return []
    content = chapter2_path.read_text(encoding="utf-8")
    return _extract_citations(content)


def _objective_title(objective: str) -> str:
    text = (objective or "").strip().rstrip(".")
    return text if text else "Objective"


def _objective_stats(df: pd.DataFrame, variables: List[str]) -> Dict[str, float]:
    if not variables:
        return {"mean": 0.0, "min": 0.0, "max": 0.0}
    subset = df[variables]
    mean_val = float(subset.mean().mean())
    min_val = float(subset.min().min())
    max_val = float(subset.max().max())
    return {"mean": mean_val, "min": min_val, "max": max_val}


def _discussion_block(objective: str, stats: Dict[str, float], citation_iter) -> List[str]:
    mean_val = stats.get("mean", 0.0)
    min_val = stats.get("min", 0.0)
    max_val = stats.get("max", 0.0)

    paragraphs = []
    paragraphs.append(
        f"The findings for {_objective_title(objective).lower()} indicated an overall mean score of {mean_val:.2f}, "
        f"with responses ranging from {min_val:.0f} to {max_val:.0f} on the measurement scale. "
        "This pattern suggested a concentrated distribution of views across respondents."
    )
    paragraphs.append(
        "The results were interpreted as evidence of the prevailing conditions linked to the study variables, "
        "showing how respondent perceptions aligned with the objective and the local context."
    )
    citation = next(citation_iter, "")
    paragraphs.append(
        f"Comparable patterns were reported in the literature, where similar indicators were linked to the study focus {citation}."
    )
    paragraphs.append(
        "Overall, the findings underscored the importance of the objective within the study area and provided "
        "a basis for the subsequent conclusions and recommendations."
    )
    return paragraphs


async def run_good_chapter_five_generation(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
    config_id_raw = request.get("config_id")
    config_id = None
    if config_id_raw is not None:
        try:
            config_id = int(config_id_raw)
        except (TypeError, ValueError):
            config_id = None

    config = get_good_config_by_id(config_id) if config_id else None
    if not config:
        config = get_latest_good_config(workspace_id)
        config_id = config.get("id") if config else None
    config = config or {}

    topic = _clean_text(config.get("topic") or "")
    if not topic:
        await events.log(job_id, "⚠️ /good Chapter Five skipped: no topic provided.", session_id=session_id)
        return

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    chapter4_path = good_dir / "Chapter_4_Data_Analysis.md"
    if not chapter4_path.exists():
        await events.log(job_id, "ℹ️ /good Chapter Five awaiting Chapter Four; will retry later.", session_id=session_id)
        return

    await events.stage_started(
        job_id,
        "good_chapter_five",
        {"message": "🧭 Generating /good Chapter Five (Discussion & Recommendations)..."},
        session_id=session_id,
    )

    datasets_dir = good_dir / "datasets"
    data_path = _pick_latest(datasets_dir, "questionnaire_data_*.csv")
    mapping_path = _pick_latest(datasets_dir, "*_variable_mapping.json")
    if not data_path or not mapping_path:
        await events.log(job_id, "⚠️ /good Chapter Five skipped: dataset missing.", session_id=session_id)
        return

    df = pd.read_csv(data_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))

    objectives = config.get("objectives") or []
    if isinstance(objectives, str):
        try:
            objectives = json.loads(objectives)
        except json.JSONDecodeError:
            objectives = []
    objectives = [obj for obj in objectives if str(obj).strip()]
    extra = config.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    user_objectives = extra.get("user_objectives") or []
    objectives = normalise_objectives(objectives, bool(user_objectives))

    likert_items = mapping.get("likert_items") or {}
    objective_map: Dict[str, List[str]] = {}
    for variable, item in likert_items.items():
        objective = item.get("section_title") or ""
        objective_map.setdefault(objective, []).append(variable)

    citations = _load_chapter2_citations(workspace_id)
    citation_iter = cycle(citations) if citations else cycle([""])
    scale = mapping.get("likert_scale")
    if not isinstance(scale, int) or scale not in (3, 5, 7):
        scale = 5

    lines: List[str] = []
    lines.append("CHAPTER FIVE: DISCUSSIONS, CONCLUSIONS AND RECOMMENDATIONS OF FINDINGS")
    lines.append("")
    lines.append("## 5.0 Introduction")
    lines.append(
        f"This chapter presented the discussion, conclusions, and recommendations for the study on {topic}. "
        "The discussion summarised the findings in relation to each objective, while the conclusions and "
        "recommendations drew directly from the empirical evidence."
    )
    lines.append("")

    lines.append("## 5.1 Discussion/Summary of Findings")
    lines.append(
        "The discussion was presented in accordance with the findings for each study objective as outlined below."
    )
    lines.append("")

    for idx, objective in enumerate(objectives, 1):
        objective_title = _objective_title(objective)
        lines.append(f"### 5.1.{idx} Discussion/Summary for {objective_title}")
        variables = objective_map.get(objective, [])
        stats = _objective_stats(df, variables)
        for paragraph in _discussion_block(objective, stats, citation_iter):
            lines.append(paragraph)
        lines.append("")

    lines.append("## 5.2 Conclusions")
    conclusions_text = (
        "The study concluded that the research questions were addressed through the empirical evidence, "
        "with results indicating clear patterns in the variables under investigation. "
    )
    for idx, objective in enumerate(objectives, 1):
        variables = objective_map.get(objective, [])
        mean_val = _objective_stats(df, variables).get("mean", 0.0)
        midpoint = (scale + 1) / 2
        decision = "supported" if mean_val >= midpoint else "not supported"
        conclusions_text += (
            f"For objective {idx}, the hypothesis was {decision} based on the observed mean score of "
            f"{mean_val:.2f}. "
        )
    conclusions_text += "The conclusions reflected the relationships between the study objectives and the analysed variables."
    lines.append(conclusions_text)
    lines.append("")

    lines.append("## 5.3 Recommendations")
    lines.append(
        "Based on the findings, the study recommended targeted interventions aligned to the identified challenges. "
        "Priority was placed on evidence-informed policies, institutional strengthening, and practical programmes "
        "that can address the factors highlighted in the objectives. These recommendations were anchored in the "
        "empirical patterns observed within the study area."
    )
    lines.append("")

    lines.append("## 5.4 Suggestions for Further Studies")
    lines.append(
        "Future studies could examine longitudinal trends in the study variables, the effectiveness of specific "
        "policy interventions, comparative analyses across similar settings, and deeper qualitative exploration "
        "of community perspectives related to the study objectives."
    )
    lines.append("")

    chapter_path = good_dir / "Chapter_5_Discussion.md"
    chapter_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(chapter_path),
            "full_path": str(chapter_path),
            "type": "file",
            "workspace_id": workspace_id,
            "filename": chapter_path.name,
        },
        session_id=session_id,
    )
    await events.file_updated(job_id, str(chapter_path), session_id=session_id)

    if config_id:
        update_good_status(config_id, {"chapter5_done": True})

    await events.stage_completed(
        job_id,
        "good_chapter_five",
        {"message": f"✅ /good Chapter Five saved: {chapter_path.name}"},
        session_id=session_id,
    )
