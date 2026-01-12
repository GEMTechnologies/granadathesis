"""Generate Chapter Three (Methodology) for /good flow using real sources when available."""

from __future__ import annotations

import asyncio
import json
import math
import re
from typing import Dict, List, Optional

from core.events import events
from services.deepseek_direct import deepseek_direct
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.sources_service import sources_service
from services.workspace_service import WORKSPACES_DIR

from services.good_chapter_one_generator import (
    _clean_text,
    _extract_keywords,
    _make_research_results,
    _select_papers,
    _build_citation_context,
    _build_references_section,
    _trim_incomplete_sentences,
    _strip_leading_heading,
    _normalise_two_author_citations,
    _strip_disallowed_citations,
    _replace_reused_citations,
    _ensure_citation_density,
    _link_citations_to_sources,
    _update_used_citations,
    _paper_key,
)
from services.good_objective_generator import fallback_objectives, normalise_objectives


def _needs_chapter3_regen(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    if "generation pending" in lowered:
        return True
    required_headings = [
        "## 3.0 Introduction",
        "## 3.1 Study Area",
        "## 3.5 Sample and Sampling Procedures",
        "## 3.10 Ethical Considerations",
        "## 3.13 Chapter Summary",
    ]
    if any(heading not in text for heading in required_headings):
        return True
    if re.search(r"(?m)^\s*\*{2,}\s*3\.\d+", text):
        return True
    return False


def _strip_title_prefix(text: str, title: str) -> str:
    cleaned = (text or "").lstrip()
    if not cleaned:
        return cleaned
    pattern = rf"^(?:#+\s*)?\*{{0,3}}{re.escape(title)}\*{{0,3}}\s*[:\-–]?\s*"
    while True:
        updated = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
        if updated == cleaned:
            break
        cleaned = updated.lstrip()
    return cleaned.lstrip()


def _strip_repeated_heading(text: str, title: str) -> str:
    if not text:
        return text
    cleaned = text.strip()
    cleaned = re.sub(r"(?i)^chapter\s+three[:\s]+research\s+methodology\s*", "", cleaned).strip()
    heading_pattern = rf"^\s*{re.escape(title)}\s*[:\-–]?\s*"
    cleaned = re.sub(heading_pattern, "", cleaned, flags=re.IGNORECASE).lstrip()
    return cleaned


def _format_sampling_steps(text: str) -> str:
    cleaned = text or ""
    if not cleaned:
        return cleaned
    cleaned = re.sub(r"\s*(Yamane[^\n\.]*\.)", r"\1\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*(Step\s+\d+:)", r"\n\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(Step\s+\d+:[^\n]*?)(?=\s+Step\s+\d+:)", r"\1\n", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace(". Step", ".\nStep")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _ensure_min_paragraphs(text: str, min_paragraphs: int = 2) -> str:
    if not text:
        return text
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= min_paragraphs:
        return "\n\n".join(paragraphs)
    lines = text.splitlines()
    table_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("|") and line.count("|") >= 2:
            table_idx = idx
            break
    text_block = "\n".join(lines[:table_idx]) if table_idx is not None else text
    tail_block = "\n".join(lines[table_idx:]) if table_idx is not None else ""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_block) if s.strip()]
    if len(sentences) >= 2:
        split_at = max(1, len(sentences) // 2)
        first = " ".join(sentences[:split_at]).strip()
        rest = " ".join(sentences[split_at:]).strip()
        rebuilt = f"{first}\n\n{rest}".strip()
    else:
        words = text_block.split()
        if len(words) < 12:
            return text
        split_at = max(1, len(words) // 2)
        first = " ".join(words[:split_at]).strip()
        rest = " ".join(words[split_at:]).strip()
        rebuilt = f"{first}\n\n{rest}".strip()
    if tail_block:
        rebuilt = f"{rebuilt}\n\n{tail_block}".strip()
    return rebuilt


def _ensure_sample_table(text: str) -> str:
    if not text:
        return text
    if "|" in text:
        return text
    table = (
        "\n\nTable 3.1: Sample Distribution (Placeholder)\n"
        "| Stratum | Population | Sample Allocation |\n"
        "| --- | --- | --- |\n"
        "| Age 18–25 | To be determined | To be determined |\n"
        "| Age 26–35 | To be determined | To be determined |\n"
        "| Age 36–45 | To be determined | To be determined |\n"
        "| Age 46+ | To be determined | To be determined |\n"
        "| Education level | To be determined | To be determined |\n"
        "| Gender | To be determined | To be determined |\n"
    )
    return f"{text.strip()}{table}"


def _ensure_reliability_table(text: str) -> str:
    if not text:
        return text
    if "|" in text:
        return text
    table = (
        "\n\nTable 3.2: Reliability Analysis (Placeholder)\n"
        "| Scale/Construct | Number of Items | Cronbach’s Alpha (α) |\n"
        "| --- | --- | --- |\n"
        "| Perceived economic impact | To be determined | To be calculated |\n"
        "| Employment challenges | To be determined | To be calculated |\n"
    )
    return f"{text.strip()}{table}"


def _parse_population(population_text: str) -> Optional[int]:
    if not population_text:
        return None
    matches = re.findall(r"\b\d{2,9}\b", population_text.replace(",", ""))
    if not matches:
        return None
    try:
        return int(matches[0])
    except ValueError:
        return None


def _study_profile(study_type: str) -> Dict[str, str]:
    st = (study_type or "").lower()
    if "qualitative" in st:
        return {
            "paradigm": "Interpretivism",
            "design": "qualitative case study",
            "instruments": "semi-structured interviews, focus group discussions, and observation",
            "analysis": "thematic analysis using NVivo or manual coding",
            "sampling": "purposive and snowball sampling",
            "reliability": "trustworthiness (credibility, dependability, confirmability, transferability)",
        }
    if "mixed" in st:
        return {
            "paradigm": "Pragmatism",
            "design": "convergent mixed methods",
            "instruments": "questionnaires and interviews",
            "analysis": "descriptive statistics (SPSS/Excel) and thematic analysis (NVivo)",
            "sampling": "stratified sampling for quantitative and purposive sampling for qualitative",
            "reliability": "Cronbach’s alpha for quantitative items and trustworthiness for qualitative data",
        }
    return {
        "paradigm": "Positivism",
        "design": "descriptive cross-sectional design",
        "instruments": "structured questionnaire",
        "analysis": "descriptive and inferential statistics using SPSS or Excel",
        "sampling": "stratified or simple random sampling",
        "reliability": "Cronbach’s alpha for internal consistency",
    }


def _section_prompt(
    title: str,
    topic: str,
    country: str,
    case_study: str,
    objectives: List[str],
    population_text: str,
    profile: Dict[str, str],
    sampling_calc: str,
    citation_context: str,
) -> str:
    objective_text = "; ".join([obj.rstrip(".") for obj in objectives]) if objectives else "Not provided"
    definition_note = ""
    extra_instructions = ""
    if title.startswith("3.0"):
        extra_instructions = "Write 4–5 sentences outlining the chapter contents and linking to the study topic."
    elif title.startswith("3.1"):
        definition_note = "Begin with 1–2 sentences defining the study area (cite if available)."
        extra_instructions = "Describe location, context, and include population statistics if available from sources."
    elif title.startswith("3.2"):
        definition_note = "Begin with 1–2 sentences defining research paradigms (cite if available)."
        extra_instructions = f"Justify why {profile['paradigm']} fits the study and its data type."
    elif title.startswith("3.3"):
        definition_note = "Begin with 1–2 sentences defining research design (cite if available)."
        extra_instructions = f"Justify the selected {profile['design']} in relation to the objectives and data."
    elif title.startswith("3.4"):
        definition_note = "Begin with 1–2 sentences defining target population (cite if available)."
        extra_instructions = "Describe the groups included and why; include a short strata table only if groups are provided."
    elif title.startswith("3.5"):
        definition_note = "Begin with 1–2 sentences defining sample and sampling (cite if available)."
        extra_instructions = (
            "Explain sampling technique(s) and include Yamane’s formula with step-by-step calculation. "
            "Use the provided sampling calculation lines exactly as given and keep each step on its own line. "
            "Include a small sample distribution table; if strata are not provided, note this and present a placeholder table with 'To be determined' values."
        )
    elif title.startswith("3.6"):
        definition_note = "Begin with 1–2 sentences defining research instruments (cite if available)."
        extra_instructions = f"Describe each research instrument in its own paragraph and link each to relevant objectives. Use instruments: {profile['instruments']}."
    elif title.startswith("3.7 "):
        definition_note = "Begin with 1–2 sentences defining validity and reliability (cite if available)."
        extra_instructions = "Explain how data quality will be ensured."
    elif title.startswith("3.7.1"):
        definition_note = "Begin with 1–2 sentences defining piloting or pretesting (cite if available)."
        extra_instructions = "Explain piloting/pretesting and how tools were refined."
    elif title.startswith("3.7.2"):
        definition_note = "Begin with 1–2 sentences defining validity (cite if available)."
        extra_instructions = "Explain validity checks (content/construct) and expert review where applicable."
    elif title.startswith("3.7.3"):
        definition_note = "Begin with 1–2 sentences defining reliability (cite if available)."
        extra_instructions = (
            "Explain reliability and include Cronbach’s alpha formula and a short reliability table if quantitative items apply; "
            "if qualitative, state that reliability is addressed through trustworthiness."
        )
    elif title.startswith("3.8"):
        definition_note = "Begin with 1–2 sentences defining data collection (cite if available)."
        extra_instructions = "Provide step-by-step data collection procedures, including permissions, access, and tool administration."
    elif title.startswith("3.9"):
        definition_note = "Begin with 1–2 sentences defining data analysis (cite if available)."
        extra_instructions = f"Explain analysis techniques and tools aligned to {profile['analysis']}."
    elif title.startswith("3.10"):
        definition_note = "Begin with 1–2 sentences defining research ethics (cite if available)."
        extra_instructions = "Cover informed consent, confidentiality, voluntary participation, and protection of vulnerable groups."
    elif title.startswith("3.11"):
        definition_note = "Begin with 1–2 sentences defining research limitations (cite if available)."
        extra_instructions = "Provide 3–6 concise limitations and mitigation strategies."
    elif title.startswith("3.12"):
        definition_note = "Begin with 1–2 sentences defining research assumptions (cite if available)."
        extra_instructions = "State 3–5 concise study assumptions and why they are reasonable in this context."
    elif title.startswith("3.13"):
        extra_instructions = "Summarise the chapter in 3–4 sentences and link to Chapter Four."
    base = f"""Write the section titled "{title}" for Chapter Three (Research Methodology) for the study about {topic} in {case_study}, {country}. Use UK English, academic tone, and avoid "we". Use future tense throughout (e.g., "will", "shall", "is expected"). Do not repeat the section title in the body. Do not use markdown bold/italics inside the body. Do not use bullets unless the section explicitly requires a table or formula.

Study objectives: {objective_text}
Study type guidance: paradigm={profile['paradigm']}, design={profile['design']}, instruments={profile['instruments']}, analysis={profile['analysis']}, sampling={profile['sampling']}, reliability={profile['reliability']}.
Population info (if provided): {population_text or 'Not provided'}
Sampling calculation (if available, keep each step on its own line):
{sampling_calc or 'Not available'}
Additional requirements: {definition_note} {extra_instructions}

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Use citations only where evidence is clearly relevant; if evidence is limited, state that briefly without inventing sources. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

CITATION CONTEXT:
{citation_context}
"""
    return base


def _sampling_calc_block(population_n: Optional[int]) -> str:
    if not population_n or population_n <= 0:
        return "\n".join(
            [
                "Yamane’s formula: n = N / (1 + N(e^2)).",
                "Step 1: N = not provided.",
                "Step 2: e = 0.05.",
                "Step 3: n will be computed once the population frame is confirmed.",
            ]
        )
    e = 0.05
    denom = 1 + population_n * (e ** 2)
    n = population_n / denom
    n_rounded = max(1, math.ceil(n))
    return "\n".join(
        [
            "Yamane’s formula: n = N / (1 + N(e^2)).",
            f"Step 1: N = {population_n}.",
            "Step 2: e = 0.05.",
            "Step 3: e^2 = 0.0025.",
            f"Step 4: 1 + N(e^2) = 1 + {population_n} × 0.0025 = {denom:.4f}.",
            f"Step 5: n = {population_n} / {denom:.4f} = {n:.2f}.",
            f"Step 6: n ≈ {n_rounded}.",
        ]
    )


async def run_good_chapter_three_generation(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
    await events.stage_started(
        job_id,
        "good_chapter_three",
        {"message": "🧪 Generating /good Chapter Three (Methodology)..."},
        session_id=session_id,
    )
    config_id_raw = request.get("config_id")
    config_id = None
    if config_id_raw is not None:
        try:
            config_id = int(config_id_raw)
        except (TypeError, ValueError):
            config_id = None

    config = get_good_config_by_id(config_id) if config_id else None
    if not config and workspace_id:
        config = get_latest_good_config(workspace_id)
        if config:
            config_id = config.get("id")
    config = config or {}
    topic = _clean_text(request.get("topic") or config.get("topic") or "")
    country = _clean_text(request.get("country") or config.get("country") or "South Sudan")
    case_study = _clean_text(request.get("case_study") or config.get("case_study") or "")
    study_type = _clean_text(request.get("study_type") or config.get("study_type") or "")
    population_text = _clean_text(request.get("population") or config.get("population") or "")

    extra_json = config.get("extra_json") or {}
    if isinstance(extra_json, str):
        try:
            extra_json = json.loads(extra_json)
        except json.JSONDecodeError:
            extra_json = {}
    objectives = config.get("objectives") or []
    user_objectives = extra_json.get("user_objectives") or []
    generated_objectives = extra_json.get("generated_objectives") or []
    if user_objectives:
        objectives = user_objectives
    elif not objectives and generated_objectives:
        objectives = generated_objectives
    if not objectives:
        objectives = fallback_objectives(topic, case_study, country)
    objectives = normalise_objectives(objectives, bool(user_objectives))

    if not topic:
        await events.log(job_id, "⚠️ /good Chapter Three skipped: no topic provided.", session_id=session_id)
        return

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    good_dir.mkdir(parents=True, exist_ok=True)
    file_path = good_dir / "Chapter_3_Research_Methodology.md"

    existing_text = ""
    if file_path.exists():
        existing_text = file_path.read_text(encoding="utf-8")
    if not _needs_chapter3_regen(existing_text) and "## 3.0 Introduction" in existing_text:
        await events.log(job_id, "ℹ️ /good Chapter Three already exists; skipping.", session_id=session_id)
        return

    await events.log(job_id, "🧪 /good Chapter Three generation started...", session_id=session_id)

    sources = sources_service.list_sources(workspace_id)
    for _ in range(10):
        if sources:
            break
        await asyncio.sleep(1.5)
        sources = sources_service.list_sources(workspace_id)

    year_from = config.get("literature_year_start") or 2020
    year_to = config.get("literature_year_end") or 2026
    papers = _make_research_results(sources, year_from, year_to)
    keywords = _extract_keywords(topic, country, case_study, " ".join(objectives or []))
    used_citations: set = set()
    selected = _select_papers(papers, keywords, count=25, used_keys=used_citations)
    context = _build_citation_context(selected, max_sources=25)

    profile = _study_profile(study_type)
    population_n = _parse_population(population_text)
    sampling_calc = _sampling_calc_block(population_n)

    buffer = "# CHAPTER THREE: RESEARCH METHODOLOGY\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(file_path),
            "full_path": str(file_path),
            "type": "file",
            "workspace_id": workspace_id,
            "filename": file_path.name,
        },
        session_id=session_id,
    )
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    sections = [
        ("3.0 Introduction", 2, 3),
        ("3.1 Study Area", 1, 2),
        ("3.2 Philosophical Paradigm", 1, 2),
        ("3.3 Research Design", 1, 2),
        ("3.4 Target Population", 1, 2),
        ("3.5 Sample and Sampling Procedures", 1, 2),
        ("3.6 Research Instruments", 1, 2),
        ("3.7 Measurement of Validity and Reliability", 0, 2),
        ("3.7.1 Piloting", 0, 2),
        ("3.7.2 Validity", 0, 2),
        ("3.7.3 Reliability", 0, 2),
        ("3.8 Data Collection Procedures", 1, 2),
        ("3.9 Data Analysis Techniques", 1, 2),
        ("3.10 Ethical Considerations", 1, 2),
        ("3.11 Limitations of the Study", 0, 2),
        ("3.12 Assumptions of the Study", 0, 1),
        ("3.13 Chapter Summary", 0, 1),
    ]

    min_paragraphs_map = {
        "3.0": 2,
        "3.1": 2,
        "3.2": 2,
        "3.3": 2,
        "3.4": 2,
        "3.5": 2,
        "3.6": 2,
        "3.7": 2,
        "3.7.1": 2,
        "3.7.2": 2,
        "3.7.3": 2,
        "3.8": 2,
        "3.9": 2,
        "3.10": 2,
        "3.11": 2,
        "3.12": 2,
        "3.13": 1,
    }

    for title, min_cites, max_cites in sections:
        heading = f"## {title}\n\n" if not title.startswith("3.7.") else f"### {title}\n\n"
        buffer = buffer + heading
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        generated = ""

        async def on_chunk(chunk: str):
            nonlocal generated, buffer
            if not chunk:
                return
            generated += chunk
            file_path.write_text(buffer + generated, encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)

        response = ""
        try:
            response = await deepseek_direct.generate_content(
                prompt=_section_prompt(
                    title,
                    topic,
                    country,
                    case_study,
                    objectives,
                    population_text,
                    profile,
                    sampling_calc if title.startswith("3.5") else "",
                    context,
                ),
                system_prompt="You are an academic writing assistant.",
                temperature=0.3,
                max_tokens=1200,
                stream=True,
                stream_callback=on_chunk,
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ /good Chapter Three section failed: {title}: {exc}", session_id=session_id)

        section_text = (response or generated).strip()
        if not section_text:
            section_text = "Evidence is limited in the approved sources for this section."
        section_text = _trim_incomplete_sentences(section_text)
        section_text = _strip_leading_heading(section_text, title)
        section_text = _strip_title_prefix(section_text, title)
        section_text = _strip_repeated_heading(section_text, title)
        section_text = _normalise_two_author_citations(section_text)
        allowed_keys = {_paper_key(p) for p in selected if _paper_key(p)}
        section_text = _strip_disallowed_citations(section_text, allowed_keys)
        section_text = _replace_reused_citations(section_text, selected, used_citations)
        section_text = _ensure_citation_density(section_text, selected, min_cites, max_cites, used_citations)
        section_text = _link_citations_to_sources(section_text, selected)
        _update_used_citations(section_text, used_citations)
        min_paras = min_paragraphs_map.get(title.split()[0], 2)
        section_text = _ensure_min_paragraphs(section_text, min_paras)
        if title.startswith("3.5"):
            section_text = _format_sampling_steps(section_text)
            if sampling_calc and ("Yamane" not in section_text or "Step 1" not in section_text):
                section_text = f"{section_text}\n\n{sampling_calc}"
            section_text = _ensure_sample_table(section_text)
        if title.startswith("3.7.3"):
            section_text = _ensure_reliability_table(section_text)
        buffer = buffer + section_text + "\n\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    references = _build_references_section(buffer, "", papers)
    if references:
        buffer = buffer + "## References for Chapter Three\n\n" + references.strip() + "\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    if config_id:
        update_good_status(config_id, {"chapter3_done": True})

    await events.log(job_id, f"✅ /good Chapter Three saved: {file_path.name}", session_id=session_id)
    await events.stage_completed(job_id, "good_chapter_three", {"file": file_path.name}, session_id=session_id)

    try:
        from services.good_proposal_combiner import maybe_run_good_proposal_combiner

        await maybe_run_good_proposal_combiner(job_id, workspace_id, session_id, config_id)
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good proposal combiner failed: {exc}", session_id=session_id)
