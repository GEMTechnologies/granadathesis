"""
Plan Tracker - Create and update a markdown planner checklist per workspace.
"""

from pathlib import Path
import re
from typing import Any, Dict, List, Tuple, Optional

from services.workspace_service import WORKSPACES_DIR


def _get_objectives_for_plan(workspace_id: str) -> List[str]:
    try:
        from services.thesis_session_db import ThesisSessionDB
        db = ThesisSessionDB(workspace_id)
        objectives = db.get_objectives() or {}
        specific = objectives.get("specific") or []
        return [obj for obj in specific if isinstance(obj, str) and obj.strip()]
    except Exception:
        return []


def _short_objective_label(objective: str, max_words: int = 8) -> str:
    cleaned = re.sub(
        r'^(to|To)\s+(assess|examine|analyze|analyse|evaluate|investigate|determine|study|explore)\s+',
        '',
        objective or ''
    ).strip()
    if not cleaned:
        cleaned = (objective or '').strip()
    words = cleaned.split()
    if len(words) > max_words:
        return " ".join(words[:max_words]) + "..."
    return cleaned


def _should_expand_empirical_sections(sections: List[Any]) -> bool:
    for section in sections:
        if isinstance(section, dict):
            title = str(section.get("title") or "")
            sec_id = str(section.get("id") or "")
        else:
            title = str(section or "")
            sec_id = ""
        lower = title.lower()
        if "objective" in lower:
            return False
        if re.search(r"\d+\.\d+\.\d+", title) or re.search(r"\d+\.\d+\.\d+", sec_id):
            return False
    return True

PLAN_FILENAME = "planner.md"
UOJ_DEFAULT_SECTIONS = {
    1: [
        "1.0 Introduction to the Study",
        "1.1 Background of the Study",
        "1.2 Problem Statement",
        "1.3 Purpose of the Study",
        "1.4 Objectives of the Study",
        "1.5 Study Questions",
        "1.6 Research Hypothesis",
        "1.7 Significance of the Study",
        "1.8 Scope of the Study",
        "1.9 Limitations of the Study",
        "1.11 Delimitations of the Study",
        "1.12 Theoretical Framework of the Study",
        "1.13 Conceptual Framework",
        "1.15 Definition of Key Terms",
        "1.16 Organization of the Study"
    ],
    2: [
        "2.1 Introduction",
        "2.2 Theoretical Literature Review",
        "2.3 Empirical Literature Review",
        "2.4 Conceptual Framework",
        "2.5 Research Gap",
        "2.6 Chapter Two Summary"
    ],
    3: [
        "3.1 Introduction",
        "3.2 Research Design",
        "3.3 Study Area",
        "3.4 Target Population",
        "3.5 Sample Size and Sampling Techniques",
        "3.6 Data Sources",
        "3.7 Data Collection Methods and Instruments",
        "3.8 Validity and Reliability of Research Instruments",
        "3.9 Data Analysis Techniques",
        "3.10 Ethical Considerations",
        "3.11 Chapter Three Summary"
    ],
    4: [
        "4.1 Introduction",
        "4.2 Response Rate",
        "4.3 Demographic Characteristics of Respondents",
        "4.4 Data Analysis and Findings",
        "4.5 Discussion of Findings",
        "4.6 Chapter Four Summary"
    ],
    5: [
        "5.1 Introduction",
        "5.2 Summary of the Study",
        "5.3 Conclusions",
        "5.4 Recommendations",
        "5.5 Suggestions for Further Research",
        "5.6 Chapter Five Summary"
    ]
}


def get_plan_chapter_labels(outline: Optional[Dict[str, Any]], thesis_type: str) -> List[Tuple[int, str]]:
    """Return ordered chapter labels for the planner."""
    if outline and isinstance(outline, dict) and outline.get("chapters"):
        labels = []
        for idx, chapter in enumerate(outline.get("chapters", []), 1):
            number = chapter.get("number") or idx
            try:
                number = int(number)
            except (TypeError, ValueError):
                number = idx
            title = chapter.get("title") or f"Chapter {number}"
            labels.append((number, f"Chapter {number}: {title}"))
        if labels:
            return labels

    if thesis_type in ("general", "uoj_general"):
        return [
            (1, "Chapter 1: Introduction"),
            (2, "Chapter 2: Literature Review"),
            (3, "Chapter 3: Research Methodology"),
            (4, "Chapter 4: Data Presentation, Analysis and Discussion"),
            (5, "Chapter 5: Summary, Conclusions and Recommendations")
        ]
    return [
        (1, "Chapter 1: Introduction"),
        (2, "Chapter 2: Literature Review"),
        (3, "Chapter 3: Research Methodology"),
        (4, "Chapter 4: Data Analysis"),
        (5, "Chapter 5: Discussion"),
        (6, "Chapter 6: Conclusion")
    ]


def build_plan_markdown(outline: Optional[Dict[str, Any]], thesis_type: str, workspace_id: Optional[str] = None) -> str:
    """Build a markdown checklist plan."""
    lines = [
        "# Thesis Planner",
        "",
        "Use this checklist to track progress. You can edit the items as needed.",
        ""
    ]

    planner_outline = outline
    if not planner_outline and thesis_type not in ("general", "uoj_general"):
        try:
            from services.outline_parser import outline_parser
            planner_outline = outline_parser.get_default_outline("phd_dissertation")
        except Exception:
            planner_outline = None

    objectives = _get_objectives_for_plan(workspace_id or "") if workspace_id else []

    if planner_outline and isinstance(planner_outline, dict) and planner_outline.get("chapters"):
        for idx, chapter in enumerate(planner_outline.get("chapters", []), 1):
            number = chapter.get("number") or idx
            try:
                number = int(number)
            except (TypeError, ValueError):
                number = idx
            title = chapter.get("title") or f"Chapter {number}"
            lines.append(f"- [ ] Chapter {number}: {title}")

            sections = chapter.get("sections") or []
            expand_empirical = bool(objectives) and _should_expand_empirical_sections(sections) and number == 2
            for section in sections:
                label = ""
                if isinstance(section, dict):
                    label = section.get("title") or section.get("id") or ""
                elif isinstance(section, str):
                    label = section.strip()
                if not label:
                    continue
                lines.append(f"  - [ ] {label}")
                if expand_empirical and "empirical" in label.lower():
                    for obj_idx, obj in enumerate(objectives, 1):
                        short_label = _short_objective_label(obj)
                        lines.append(f"    - [ ] Empirical Review for Objective {obj_idx}: {short_label}")
    else:
        for ch_num, label in get_plan_chapter_labels(None, thesis_type):
            lines.append(f"- [ ] {label}")
            if thesis_type in ("general", "uoj_general"):
                sections = UOJ_DEFAULT_SECTIONS.get(ch_num, [])
                for section in sections:
                    lines.append(f"  - [ ] {section}")

    return "\n".join(lines) + "\n"


def ensure_plan_file(workspace_id: str, outline: Optional[Dict[str, Any]], thesis_type: str) -> Tuple[Path, bool]:
    """Ensure a planner file exists. Returns (path, created)."""
    workspace_path = WORKSPACES_DIR / workspace_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    plan_path = workspace_path / PLAN_FILENAME

    if plan_path.exists():
        existing = plan_path.read_text(encoding="utf-8")
        has_checkboxes = "- [ ]" in existing or "- [x]" in existing
        has_nested = bool(re.search(r"^\s{2,}- \[[ xX]\]\s+\S", existing, flags=re.MULTILINE))
        if not has_checkboxes or not has_nested:
            plan_path.write_text(build_plan_markdown(outline, thesis_type, workspace_id=workspace_id), encoding="utf-8")
            return plan_path, True
        return plan_path, False

    plan_path.write_text(build_plan_markdown(outline, thesis_type, workspace_id=workspace_id), encoding="utf-8")
    return plan_path, True


def mark_plan_item(workspace_id: str, label: str, cascade: bool = False) -> bool:
    """Mark a checklist item as done. Returns True if updated."""
    plan_path = WORKSPACES_DIR / workspace_id / PLAN_FILENAME
    if not plan_path.exists():
        return False

    lines = plan_path.read_text(encoding="utf-8").splitlines()
    updated = False

    checkbox_re = re.compile(r"^(?P<indent>\s*)-\s*\[[ xX]\]\s*(?P<label>.+)$")

    for idx, line in enumerate(lines):
        match = checkbox_re.match(line)
        if not match:
            continue
        current_label = match.group("label").strip()
        if current_label != label:
            continue

        indent = match.group("indent")
        lines[idx] = f"{indent}- [x] {current_label}"
        updated = True

        if cascade:
            indent_len = len(indent)
            for j in range(idx + 1, len(lines)):
                sub_match = checkbox_re.match(lines[j])
                if not sub_match:
                    continue
                sub_indent = sub_match.group("indent")
                if len(sub_indent) <= indent_len:
                    break
                sub_label = sub_match.group("label").strip()
                lines[j] = f"{sub_indent}- [x] {sub_label}"
        break

    if updated:
        plan_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return updated
