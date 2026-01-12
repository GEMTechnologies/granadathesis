"""Combine /good proposal chapters with references and appendices."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.events import events
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.workspace_service import WORKSPACES_DIR


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _remove_references_section(content: str) -> str:
    patterns = [
        r"\n---\s*\n+#*\s*References?\s*\n[\s\S]*$",
        r"\n#+ References?\s*\n[\s\S]*$",
        r"\n\*\*References?\*\*\s*\n[\s\S]*$",
        r"\n---\s*\n+\*\*References?\*\*[\s\S]*$",
    ]
    cleaned = content or ""
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
    return cleaned.rstrip()


def _extract_citations(content: str) -> List[Dict[str, str]]:
    citations: List[Dict[str, str]] = []
    seen = set()
    patterns = [
        r"\[([^\]]+\s*\(\d{4}\))\]\(([^\)]+)\)",
        r"\[\(([^\)]+,\s*\d{4})\)\]\(([^\)]+)\)",
        r"\[([^\]]+)\]\(https?://[^\)]+\)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, content or ""):
            citation_text = (match.group(1) or "").strip()
            citation_url = match.group(2) if len(match.groups()) > 1 else ""
            if not citation_text:
                continue
            normalized = re.sub(r"\s+", " ", citation_text.lower())
            if normalized in seen:
                continue
            seen.add(normalized)
            citations.append({"citation": citation_text, "url": citation_url})
    citations.sort(key=lambda item: item["citation"].lower())
    return citations


def _format_authors(authors: list) -> str:
    if not authors:
        return "Unknown Author"
    names: List[str] = []
    for author in authors:
        if isinstance(author, dict):
            name = str(author.get("name", "")).strip()
        else:
            name = str(author).strip()
        if not name:
            continue
        parts = name.split()
        if len(parts) == 1:
            names.append(parts[0])
        else:
            last = parts[-1]
            initials = " ".join([p[0] + "." for p in parts[:-1] if p])
            names.append(f"{last}, {initials}".strip())
    if not names:
        return "Unknown Author"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]}, & {names[1]}"
    if len(names) > 20:
        return ", ".join(names[:19]) + ", ... " + names[-1]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def _load_sources_index(workspace_id: str) -> List[Dict[str, str]]:
    sources_path = WORKSPACES_DIR / workspace_id / "sources" / "index.json"
    if not sources_path.exists():
        return []
    try:
        payload = json.loads(sources_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    sources = payload.get("sources", []) if isinstance(payload, dict) else []
    return sources if isinstance(sources, list) else []


def _citation_key(citation: str) -> Tuple[str, Optional[str]]:
    year_match = re.search(r"\b(19|20)\d{2}\b", citation)
    year = year_match.group(0) if year_match else None
    prefix = citation.split("(")[0]
    prefix = prefix.split(",")[0]
    prefix = prefix.split("&")[0].strip()
    surname = re.sub(r"[^A-Za-z-]", "", prefix).lower()
    return surname, year


def _match_source(citation: str, sources: List[Dict[str, str]]) -> Optional[Dict[str, str]]:
    surname, year = _citation_key(citation)
    if not surname or not year:
        return None
    for source in sources:
        source_year = str(source.get("year") or "").strip()
        if source_year != year:
            continue
        authors = source.get("authors") or []
        for author in authors:
            name = author.get("name") if isinstance(author, dict) else str(author)
            if surname and surname in (name or "").lower():
                return source
    return None


def _build_apa_entry(source: Dict[str, str]) -> str:
    authors_text = _format_authors(source.get("authors") or [])
    year = source.get("year") or "n.d."
    title = source.get("title") or "Untitled"
    venue = source.get("venue") or ""
    doi = source.get("doi") or ""
    url = source.get("url") or ""
    if doi and not url:
        url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
    entry = f"{authors_text} ({year}). *{title}*."
    if venue:
        entry += f" {venue}."
    if url:
        entry += f" {url}"
    return entry


def _build_references(citations: List[Dict[str, str]], sources: List[Dict[str, str]]) -> List[str]:
    if citations:
        entries: List[str] = []
        used = set()
        for item in citations:
            citation_text = item.get("citation") or ""
            url = item.get("url") or ""
            normalized = citation_text.lower()
            if normalized in used:
                continue
            used.add(normalized)
            source = _match_source(citation_text, sources)
            if source:
                entries.append(_build_apa_entry(source))
                continue
            entry = citation_text.strip()
            if url:
                entry = f"{entry}. {url}"
            entries.append(entry)
        return entries

    return [_build_apa_entry(source) for source in sources]


def _introductory_letter(topic: str, case_study: str, country: str) -> str:
    return "\n".join(
        [
            "Appendix A: Introductory Letter to Respondents",
            "",
            "Dear Respondent,",
            "",
            f"You are invited to participate in a study titled \"{topic}\" focusing on {case_study}, {country}. The study seeks to collect information that will inform the research objectives and improve understanding of the study area.",
            "",
            "The study uses AI-assisted tools to help design and organise the data collection instruments. All responses will be reviewed by the researcher, and no automated decisions will be made about participants. Your participation is voluntary, and you may withdraw at any time without penalty.",
            "",
            "All information provided will be treated as confidential and used strictly for academic purposes. No personal identifiers will be disclosed in the final report.",
            "",
            "If you have any questions about this study, please contact the researcher using the details provided on the questionnaire.",
            "",
            "Thank you for your time and cooperation.",
            "",
            "Sincerely,",
            "The Researcher",
        ]
    )


def _load_appendix(path: Path, fallback: str) -> str:
    if not path.exists():
        return fallback
    try:
        return path.read_text(encoding="utf-8").strip()
    except Exception:
        return fallback


async def maybe_run_good_proposal_combiner(job_id: str, workspace_id: str, session_id: str, config_id: Optional[int]) -> None:
    config = get_good_config_by_id(config_id) if config_id else None
    if not config:
        config = get_latest_good_config(workspace_id)
        config_id = config.get("id") if config else None
    config = config or {}
    extra = config.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    status = extra.get("status") or {}

    if status.get("proposal_combined"):
        return

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    chapter_one = good_dir / "Chapter_1_Introduction.md"
    chapter_two = good_dir / "Chapter_2_Literature_Review.md"
    chapter_three = good_dir / "Chapter_3_Research_Methodology.md"
    appendices_dir = good_dir / "appendices"
    questionnaire_path = appendices_dir / "Appendix_II_Questionnaire.md"

    chapter_one_ready = chapter_one.exists() and chapter_one.stat().st_size > 0
    chapter_two_ready = chapter_two.exists() and chapter_two.stat().st_size > 0
    chapter_three_ready = chapter_three.exists() and chapter_three.stat().st_size > 0
    if chapter_two_ready:
        chapter_two_text = chapter_two.read_text(encoding="utf-8")
        chapter_two_ready = "2.1 Theoretical Reviews" in chapter_two_text and "2.2 Empirical Reviews" in chapter_two_text
    study_tools_ready = questionnaire_path.exists() and questionnaire_path.stat().st_size > 0

    required_flags = [
        status.get("chapter1_done"),
        status.get("chapter2_intro_done"),
        status.get("chapter2_theory_done"),
        status.get("chapter2_empirical_done"),
        status.get("chapter3_done"),
        status.get("study_tools_done"),
    ]
    if not all(required_flags):
        if not (chapter_one_ready and chapter_two_ready and chapter_three_ready and study_tools_ready):
            return
        if config_id:
            update_good_status(
                config_id,
                {
                    "chapter1_done": chapter_one_ready,
                    "chapter2_intro_done": chapter_two_ready,
                    "chapter2_theory_done": chapter_two_ready,
                    "chapter2_empirical_done": chapter_two_ready,
                    "chapter3_done": chapter_three_ready,
                    "study_tools_done": study_tools_ready,
                },
            )

    await events.stage_started(
        job_id,
        "good_proposal_combining",
        {"message": "📑 Combining /good proposal chapters, references, and appendices..."},
        session_id=session_id,
    )

    topic = _clean_text(config.get("topic") or "")
    case_study = _clean_text(config.get("case_study") or "")
    country = _clean_text(config.get("country") or "South Sudan")

    ch1_text = _remove_references_section(_load_appendix(chapter_one, ""))
    ch2_text = _remove_references_section(_load_appendix(chapter_two, ""))
    ch3_text = _remove_references_section(_load_appendix(chapter_three, ""))

    citations = []
    citations.extend(_extract_citations(ch1_text))
    citations.extend(_extract_citations(ch2_text))
    citations.extend(_extract_citations(ch3_text))
    sources = _load_sources_index(workspace_id)
    references = _build_references(citations, sources)

    appendix_letter = _load_appendix(
        appendices_dir / "Appendix_I_Introductory_Letter.md",
        _introductory_letter(topic, case_study, country),
    )
    questionnaire_text = _load_appendix(appendices_dir / "Appendix_II_Questionnaire.md", "[Questionnaire not generated]")
    kii_text = _load_appendix(appendices_dir / "Appendix_III_KII_Guide.md", "[KII guide not generated]")
    fgd_text = _load_appendix(appendices_dir / "Appendix_IV_FGD_Guide.md", "[FGD guide not generated]")
    observation_text = _load_appendix(appendices_dir / "Appendix_V_Observation_Checklist.md", "[Observation checklist not generated]")
    document_text = _load_appendix(appendices_dir / "Appendix_VI_Document_Review.md", "[Document review checklist not generated]")
    datasets_dir = good_dir / "datasets"
    dataset_files = []
    if datasets_dir.exists():
        dataset_files = [p.name for p in datasets_dir.glob("*.*") if p.is_file()]
    dataset_lines = [
        "Appendix F: Raw Data",
        "",
        "The generated datasets and transcripts are stored in the datasets folder:",
        "",
    ]
    if dataset_files:
        dataset_lines.extend([f"- {name}" for name in dataset_files])
    else:
        dataset_lines.append("[No datasets found]")
    dataset_text = "\n".join(dataset_lines)

    combined = "\n\n".join(
        [
            "# Research Proposal",
            "",
            ch1_text,
            "",
            ch2_text,
            "",
            ch3_text,
            "",
            "# References",
            "\n".join([f"{idx}. {entry}" for idx, entry in enumerate(references, 1)]) if references else "No references extracted.",
            "",
            "# Appendices",
            appendix_letter,
            "",
            questionnaire_text,
            "",
            kii_text,
            "",
            fgd_text,
            "",
            observation_text,
            "",
            document_text,
            "",
            dataset_text,
            "",
        ]
    ).strip() + "\n"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r"[^\w\s-]", "", topic)[:50].replace(" ", "_") or "Proposal"
    combined_path = good_dir / f"Research_Proposal_{safe_topic}_{timestamp}.md"
    combined_path.write_text(combined, encoding="utf-8")

    update_good_status(config_id, {"proposal_combined": True})

    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(combined_path),
            "full_path": str(combined_path),
            "type": "markdown",
            "workspace_id": workspace_id,
            "filename": combined_path.name,
        },
        session_id=session_id,
    )
    await events.stage_completed(
        job_id,
        "good_proposal_combining",
        {"file": combined_path.name},
        session_id=session_id,
    )
    await events.stage_completed(
        job_id,
        "complete",
        {"flow": "good", "file": combined_path.name},
        session_id=session_id,
    )
