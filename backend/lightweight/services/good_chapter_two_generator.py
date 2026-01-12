"""Generate Chapter Two intro section for /good flow using real sources."""

from __future__ import annotations

import asyncio
import json
import re
from typing import List, Optional, Tuple

from core.events import events
from services.deepseek_direct import deepseek_direct
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.sources_service import sources_service
from services.workspace_service import WORKSPACES_DIR
from services.parallel_chapter_generator import ResearchResult

from services.good_chapter_one_generator import (
    _author_last_name,
    _build_citation_context,
    _build_references_section,
    _clean_text,
    _ensure_citation_density,
    _extract_keywords,
    _extract_theory_candidates,
    _format_theory_candidates,
    _link_citations_to_sources,
    _make_research_results,
    _normalise_two_author_citations,
    _paper_key,
    _replace_reused_citations,
    _select_papers,
    _strip_disallowed_citations,
    _strip_leading_heading,
    _trim_incomplete_sentences,
    _update_used_citations,
)
from services.good_objective_generator import fallback_objectives, normalise_objectives


def _needs_chapter2_regen(text: str) -> bool:
    if not text:
        return True
    lowered = text.lower()
    legacy_markers = [
        "generation pending",
        "theory 1 (general)",
        "theoretical framework 1",
        "theoretical framework 2",
        "empirical 1",
        "empirical 2",
        "empirical 3",
        "empirical 4",
        "general theory:",
        "theoretical framework:",
        "empirical review",
    ]
    if any(marker in lowered for marker in legacy_markers):
        return True
    if "# chapter two" in lowered and "literature review" in lowered and "**chapter two: literature reviews**" not in lowered:
        return True
    return False


def _extract_intro_section(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"\n#+\s*\*{0,2}2\.0\s+introduction\*{0,2}\s*\n", text, re.IGNORECASE)
    if not match:
        return ""
    start = match.end()
    next_match = re.search(r"\n#+\s*\*{0,2}2\.\d+\s+", text[start:], re.IGNORECASE)
    end = start + (next_match.start() if next_match else len(text))
    intro = text[start:end].strip()
    return intro

def _chapter_two_intro_prompt(
    topic: str,
    objectives: List[str],
    case_study: str,
    country: str,
    citation_context: str,
) -> str:
    objectives_text = "; ".join([obj.rstrip(".") for obj in objectives]) if objectives else "Not provided"
    return f"""Write ONE paragraph (5–6 sentences) introducing Chapter Two (Literature Reviews) for the study about {topic}. Integrate the study objectives: {objectives_text}. State that Chapter Two reviews theoretical and empirical literature and identifies gaps relevant to {case_study}, {country}, which form the basis for the study. Use UK English, academic tone, and avoid "we". Do not use headings or bullets.

Include 2–4 citations where evidence allows. If evidence is limited, note this briefly in the final sentence without breaking the paragraph.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

CITATION CONTEXT:
{citation_context}
"""


def _theoretical_review_intro_prompt(
    topic: str,
    objectives: List[str],
    case_study: str,
    country: str,
    citation_context: str,
) -> str:
    objectives_text = "; ".join([obj.rstrip(".") for obj in objectives]) if objectives else "Not provided"
    return f"""Write ONE paragraph (4–5 sentences) introducing the theoretical review section for the study about {topic}. State that the study will be guided by three theories: one general theory for the overall study and two theories aligned to the specific objectives. Reference the objectives briefly: {objectives_text}. Use UK English, academic tone, and avoid "we". Do not use headings or bullets.

Include 2–4 citations where evidence allows.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

CITATION CONTEXT:
{citation_context}
"""


def _theory_prompt(
    topic: str,
    case_study: str,
    country: str,
    citation_context: str,
    objectives: List[str],
    label: str,
    theory_candidates: str,
    forced_theory: Optional[Dict[str, str]],
) -> str:
    objectives_text = "; ".join([obj.rstrip(".") for obj in objectives]) if objectives else "the study objectives"
    forced_note = ""
    if forced_theory:
        forced_note = f"Use this theory: {forced_theory['name']} — {forced_theory['author']} ({forced_theory['year']})."
    return f"""Write FIVE separate paragraphs with a blank line between each paragraph (no headings, no bullets, no numbering).

Use ONE theory from the approved list below. Use the exact theory name and associated author/year. If none are available, state that evidence is limited and do not invent a theory. {forced_note}

Approved theory list:
{theory_candidates}

Paragraph 1 must start with: "The study will be guided by the [Theory Name] theory as discussed by Author (Year)." Briefly outline the historical origins and core ideas of the theory with precise in-text citations.
Paragraph 2: present studies that have applied this theory in contexts similar to {topic} or the objectives: {objectives_text}.
Paragraph 3: present critical perspectives or limitations highlighted by scholars.
Paragraph 4: explain the relevance of the theory to {label} and the current study objectives.
Paragraph 5: state gaps in the theory with reference to {case_study}, {country}.

Keep the discussion aligned to {label} and the objectives: {objectives_text}. Use UK English, academic tone, and avoid "we". Include 3–5 citations per paragraph where evidence allows.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

CITATION CONTEXT:
{citation_context}
"""


def _empirical_intro_prompt(
    topic: str,
    objectives: List[str],
    case_study: str,
    country: str,
    citation_context: str,
) -> str:
    objectives_text = "; ".join([obj.rstrip(".") for obj in objectives]) if objectives else "the study objectives"
    return f"""Write ONE paragraph (4–5 sentences) introducing the empirical review section for the study titled {topic}. State that the empirical literature will be presented in subsections aligned to the study objectives ({objectives_text}) and that study gaps relevant to {case_study}, {country} will be identified. Use UK English, academic tone, and avoid "we". Do not use headings or bullets.

Include 2–4 citations where evidence allows.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY.

CITATION CONTEXT:
{citation_context}
"""


def _empirical_section_prompt(
    objective: str,
    topic: str,
    citation_context: str,
    region_note: str,
) -> str:
    return f"""Write SIX separate paragraphs with a blank line between each paragraph (no headings, no bullets, no numbering). Each paragraph summarises ONE real empirical study that aligns with the objective: {objective}. Each paragraph must start with "Author (Year) conducted a study..." and include the study objective, location, methodology, one key finding (do NOT invent statistics if not reported; state "no quantitative results reported"), a conclusion, a recommendation, and the study gap. End each paragraph with an in-text citation in author–date format.

Use UK English and an academic tone. Avoid "we". Mention country/location only if it appears in the approved source list. {region_note}

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. If fewer than six approved studies are available, write as many as possible and state that evidence is limited rather than fabricating.

CITATION CONTEXT:
{citation_context}
"""


def _empirical_paragraph_prompt(
    objective: str,
    topic: str,
    author: str,
    year: int,
    paper_title: str,
    paper_abstract: str,
    paper_venue: str,
) -> str:
    abstract_text = (paper_abstract or "").strip()
    venue_text = (paper_venue or "").strip()
    return f"""Write ONE paragraph (5–7 sentences) summarising a single empirical study that aligns with the objective: {objective}. The study topic is {topic}.

Start EXACTLY with: "{author} ({year}) conducted a study" and then continue with the study objective, location, methodology, one key finding (do NOT invent statistics if they are not in the abstract; say "no quantitative results reported"), a conclusion, a recommendation, and the study gap. Use UK English and academic tone. Do not use headings or bullet points.

Use ONLY the study details provided below. Do NOT invent authors, locations, methods, or statistics. Do NOT add extra citations.

STUDY DETAILS:
Title: {paper_title}
Venue: {venue_text or 'Not specified'}
Abstract: {abstract_text or 'No abstract available'}
"""


def _summary_gap_prompt(
    topic: str,
    case_study: str,
    country: str,
    citation_context: str,
) -> str:
    return f"""Write ONE paragraph summarising the empirical literature and highlighting the knowledge gap for the study about {topic} in {case_study}, {country}. Do not use bullets or headings inside the paragraph. Use UK English, academic tone, and avoid "we".

Include 2–4 citations where evidence allows.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors.

CITATION CONTEXT:
{citation_context}
"""


def _paper_lead(paper: ResearchResult) -> Optional[str]:
    if not paper or not paper.authors:
        return None
    last = _author_last_name(paper.authors[0])
    if not last or len(last) < 2:
        return None
    return last


def _pick_theory_candidate(papers: List, keywords: List[str]) -> Optional[Dict[str, str]]:
    candidates = _extract_theory_candidates(papers)
    if not candidates:
        return None
    return candidates[0]


def _theory_candidate_key(candidate: Dict[str, str]) -> str:
    return f"{candidate.get('name','').lower()}|{candidate.get('author','').lower()}|{candidate.get('year','')}"


def _extract_theory_heading(text: str) -> Optional[Tuple[str, str, str]]:
    if not text:
        return None
    patterns = [
        r"The study will be guided by the\s+(?:theory of|theory)\s+(.+?)\s+(?:by|developed by|proposed by)\s+([A-Z][A-Za-z.'-]+(?:\s+(?:et al\.|and|&|[A-Z][A-Za-z.'-]+))*)\s*\((\d{4})\)",
        r"The study will be guided by the\s+(.+?)\s+theory\s+as discussed by\s+([A-Z][A-Za-z.'-]+(?:\s+(?:et al\.|and|&|[A-Z][A-Za-z.'-]+))*)\s*\((\d{4})\)",
        r"The study will be guided by\s+(.+?)\s+(?:by|developed by|proposed by)\s+([A-Z][A-Za-z.'-]+(?:\s+(?:et al\.|and|&|[A-Z][A-Za-z.'-]+))*)\s*\((\d{4})\)",
        r"The study will be guided by\s+(.+?)\s*\((\d{4})\)\s+by\s+([A-Z][A-Za-z.'-]+(?:\s+(?:et al\.|and|&|[A-Z][A-Za-z.'-]+))*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if not match:
            continue
        if len(match.groups()) == 3:
            if pattern.endswith(r"\s+by\s+([A-Z][A-Za-z.'-]+(?:\s+(?:et al\.|and|&|[A-Z][A-Za-z.'-]+))*)"):
                theory, year, author = match.group(1), match.group(2), match.group(3)
            else:
                theory, author, year = match.group(1), match.group(2), match.group(3)
            theory = (theory or "").strip().rstrip(".")
            author = re.sub(r"\s+", " ", (author or "").strip())
            year = (year or "").strip()
            if theory and author and year:
                return theory, author, year
    return None


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]


def _ensure_theory_paragraphs(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 5:
        return "\n\n".join(paragraphs)
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return text
    chunks: List[str] = []
    remaining = sentences[:]
    target = 5
    while remaining and len(chunks) < target:
        chunk_size = max(1, len(remaining) // (target - len(chunks)))
        chunk = remaining[:chunk_size]
        remaining = remaining[chunk_size:]
        chunks.append(" ".join(chunk))
    if remaining:
        chunks[-1] = f"{chunks[-1]} {' '.join(remaining)}"
    return "\n\n".join(chunks)


def _ensure_empirical_paragraphs(text: str) -> str:
    if not text:
        return text
    pattern = r"(?=\b[A-Z][A-Za-z-']+\s*\(\d{4}\)\s+conducted)"
    parts = [p.strip() for p in re.split(pattern, text) if p.strip()]
    if len(parts) >= 2:
        return "\n\n".join(parts)
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        return text
    chunks: List[str] = []
    remaining = sentences[:]
    target = 6
    while remaining and len(chunks) < target:
        chunk_size = max(1, len(remaining) // (target - len(chunks)))
        chunk = remaining[:chunk_size]
        remaining = remaining[chunk_size:]
        chunks.append(" ".join(chunk))
    if remaining:
        chunks[-1] = f"{chunks[-1]} {' '.join(remaining)}"
    return "\n\n".join(chunks)


def _objective_heading(objective: str, country: str, case_study: str) -> str:
    phrase = (objective or "").strip().rstrip(".")
    phrase = re.sub(r"(?i)^to\s+", "", phrase).strip()
    for loc in [case_study, country]:
        if loc:
            phrase = re.sub(rf"(?i)\b(in|within|at|for|across)\s+{re.escape(loc)}\b", "", phrase)
    for loc in [case_study, country]:
        if not loc:
            continue
        for token in re.split(r"[\s,]+", loc.lower()):
            token = token.strip()
            if len(token) < 3:
                continue
            phrase = re.sub(rf"(?i)\b{re.escape(token)}\b", "", phrase)
    phrase = re.sub(r"\s{2,}", " ", phrase).strip(" ,;:")
    phrase = re.sub(r"(?i)\b(in|within|at|for|across|to|into)\b[\s,]*$", "", phrase).strip(" ,;:")
    if phrase.lower().endswith(" in"):
        phrase = phrase[:-3].rstrip(" ,;:")
    if not phrase:
        return "Objective"
    return phrase[0].upper() + phrase[1:]


def _region_keywords() -> List[tuple]:
    return [
        ("Asia", ["china", "india", "pakistan", "bangladesh", "indonesia", "philippines", "malaysia", "vietnam", "thailand", "japan", "korea", "nepal", "sri lanka"]),
        ("South America", ["brazil", "argentina", "chile", "peru", "colombia", "ecuador", "bolivia", "uruguay", "paraguay", "venezuela"]),
        ("West Africa", ["nigeria", "ghana", "senegal", "mali", "niger", "burkina", "benin", "togo", "sierra leone", "liberia", "gambia", "cote d'ivoire", "ivory coast", "guinea"]),
        ("Central/Southern Africa", ["south africa", "zambia", "zimbabwe", "namibia", "botswana", "angola", "mozambique", "lesotho", "eswatini", "malawi", "congo", "drc", "democratic republic of the congo", "cameroon", "gabon", "chad", "central african", "equatorial guinea"]),
        ("East Africa", ["uganda", "kenya", "tanzania", "rwanda", "burundi", "ethiopia", "eritrea", "somalia", "south sudan", "sudan"]),
    ]


def _match_region(paper, keywords: List[str]) -> bool:
    hay = f"{paper.title} {paper.abstract}".lower()
    return any(key in hay for key in keywords)


def _select_region_papers(papers: List, country: str, used_keys: set) -> List:
    selected = []
    country_key = (country or "").lower()
    country_in_region = False
    for region, keys in _region_keywords():
        for paper in papers:
            key = _paper_key(paper)
            if not key or key in used_keys:
                continue
            if _match_region(paper, keys):
                selected.append((region, paper))
                used_keys.add(key)
                if country_key and country_key in keys:
                    country_in_region = True
                break
    if country and not country_in_region:
        for paper in papers:
            key = _paper_key(paper)
            if not key or key in used_keys:
                continue
            if country_key in f"{paper.title} {paper.abstract}".lower():
                selected.append((country, paper))
                used_keys.add(key)
                break
    return selected


def _extract_conceptual_framework(workspace_id: str) -> Optional[str]:
    chapter_path = WORKSPACES_DIR / workspace_id / "good" / "Chapter_1_Introduction.md"
    if not chapter_path.exists():
        return None
    text = chapter_path.read_text(encoding="utf-8")
    match = re.search(
        r"(?m)^##\s*\*{0,2}1\.13\s+Conceptual Framework\*{0,2}\s*$|^1\.13\s+Conceptual Framework",
        text,
    )
    if not match:
        return None
    start = match.end()
    tail = text[start:]
    end_match = re.search(r"(?m)^##\s*\*{0,2}1\.\d+\s+|^1\.\d+\s+", tail)
    end = start + (end_match.start() if end_match else len(text))
    section = text[start:end].strip()
    return section or None


async def run_good_chapter_two_intro(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
    await events.stage_started(
        job_id,
        "good_chapter_two_intro",
        {"message": "📚 Generating /good Chapter Two introduction..."},
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
    objectives = normalise_objectives(objectives, bool(user_objectives))
    objectives = normalise_objectives(objectives, bool(user_objectives))

    if not topic:
        await events.log(job_id, "⚠️ /good Chapter Two skipped: no topic provided.", session_id=session_id)
        return

    await events.log(job_id, "✍️ /good Chapter Two intro generation started...", session_id=session_id)

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    good_dir.mkdir(parents=True, exist_ok=True)
    file_path = good_dir / "Chapter_2_Literature_Review.md"

    file_path.write_text("**CHAPTER TWO: LITERATURE REVIEWS**\n\n", encoding="utf-8")
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

    selected = _select_papers(papers, keywords, count=30, used_keys=used_citations)
    context = _build_citation_context(selected, max_sources=30)

    buffer = "**CHAPTER TWO: LITERATURE REVIEWS**\n\n"
    buffer += "## **2.0 Introduction**\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    generated = ""

    async def on_chunk(chunk: str):
        nonlocal generated
        if not chunk:
            return
        generated += chunk
        file_path.write_text(buffer + generated, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    response = ""
    try:
        response = await deepseek_direct.generate_content(
            prompt=_chapter_two_intro_prompt(topic, objectives, case_study, country, context),
            system_prompt="You are an academic writing assistant.",
            temperature=0.3,
            max_tokens=900,
            stream=True,
            stream_callback=on_chunk,
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good Chapter Two intro failed: {exc}", session_id=session_id)

    section_text = (response or generated).strip()
    if not section_text:
        section_text = "Evidence is limited in the approved sources for this section."
    section_text = _trim_incomplete_sentences(section_text)
    section_text = _strip_leading_heading(section_text, "2.0 Introduction")
    section_text = _normalise_two_author_citations(section_text)
    allowed_keys = {_paper_key(p) for p in selected if _paper_key(p)}
    section_text = _strip_disallowed_citations(section_text, allowed_keys)
    section_text = _ensure_citation_density(section_text, selected, 2, 4, used_citations)
    section_text = _link_citations_to_sources(section_text, selected)
    _update_used_citations(section_text, used_citations)

    buffer = buffer + section_text + "\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    if config_id:
        update_good_status(config_id, {"chapter2_intro_done": True})

    await events.log(job_id, f"✅ /good Chapter Two intro saved: {file_path.name}", session_id=session_id)
    await events.stage_completed(job_id, "good_chapter_two_intro", {"file": file_path.name}, session_id=session_id)

    try:
        from services.good_proposal_combiner import maybe_run_good_proposal_combiner

        await maybe_run_good_proposal_combiner(job_id, workspace_id, session_id, config_id)
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good proposal combiner failed: {exc}", session_id=session_id)


async def run_good_chapter_two_theoretical_reviews(
    job_id: str,
    workspace_id: str,
    session_id: str,
    request: dict,
) -> None:
    await events.stage_started(
        job_id,
        "good_chapter_two_theory",
        {"message": "📚 Generating /good Chapter Two theoretical and empirical reviews..."},
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

    if not topic:
        await events.log(job_id, "⚠️ /good Chapter Two theoretical reviews skipped: no topic provided.", session_id=session_id)
        return

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    good_dir.mkdir(parents=True, exist_ok=True)
    file_path = good_dir / "Chapter_2_Literature_Review.md"

    existing_text = ""
    if file_path.exists():
        existing_text = file_path.read_text(encoding="utf-8")
    if not _needs_chapter2_regen(existing_text) and "## **2.1 Theoretical Reviews**" in existing_text:
        await events.log(job_id, "ℹ️ /good Chapter Two theoretical reviews already exist; skipping.", session_id=session_id)
        return

    preserved_intro = _extract_intro_section(existing_text)
    if preserved_intro and "generation pending" in preserved_intro.lower():
        preserved_intro = ""
    needs_intro = not preserved_intro
    buffer = "**CHAPTER TWO: LITERATURE REVIEWS**\n\n## **2.0 Introduction**\n\n"
    if preserved_intro:
        buffer += preserved_intro.strip() + "\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    await events.log(job_id, "✍️ /good Chapter Two theoretical reviews started...", session_id=session_id)

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

    research_meta = extra_json.get("research") or {}
    if isinstance(research_meta, str):
        try:
            research_meta = json.loads(research_meta)
        except json.JSONDecodeError:
            research_meta = {}
    objective_sources_map = research_meta.get("objective_sources") or {}
    objective_source_details = {}
    for obj, ids in (objective_sources_map or {}).items():
        if not ids:
            continue
        details = [sources_service.get_source(workspace_id, sid) for sid in ids]
        objective_source_details[obj] = [d for d in details if d]

    def objective_papers(objective: str) -> List:
        sources_for_obj = objective_source_details.get(objective) or []
        if not sources_for_obj:
            return papers
        return _make_research_results(sources_for_obj, year_from, year_to) or papers

    intro_papers = _select_papers(papers, keywords, count=25)
    intro_context = _build_citation_context(intro_papers, max_sources=25)
    if needs_intro:
        intro_generated = ""

        async def on_seed_intro_chunk(chunk: str):
            nonlocal intro_generated, buffer
            if not chunk:
                return
            intro_generated += chunk
            file_path.write_text(buffer + intro_generated, encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)

        seed_response = ""
        try:
            seed_response = await deepseek_direct.generate_content(
                prompt=_chapter_two_intro_prompt(topic, objectives, case_study, country, intro_context),
                system_prompt="You are an academic writing assistant.",
                temperature=0.3,
                max_tokens=900,
                stream=True,
                stream_callback=on_seed_intro_chunk,
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ /good Chapter Two intro seed failed: {exc}", session_id=session_id)

        seed_text = (seed_response or intro_generated).strip()
        if not seed_text:
            seed_text = "Evidence is limited in the approved sources for this section."
        seed_text = _trim_incomplete_sentences(seed_text)
        seed_text = _strip_leading_heading(seed_text, "2.0 Introduction")
        seed_text = _normalise_two_author_citations(seed_text)
        seed_text = _strip_disallowed_citations(seed_text, {_paper_key(p) for p in intro_papers if _paper_key(p)})
        seed_text = _replace_reused_citations(seed_text, intro_papers, used_citations)
        seed_text = _ensure_citation_density(seed_text, intro_papers, 2, 4, used_citations)
        seed_text = _link_citations_to_sources(seed_text, intro_papers)
        _update_used_citations(seed_text, used_citations)
        buffer = buffer + seed_text + "\n\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    buffer = file_path.read_text(encoding="utf-8").rstrip() + "\n\n"
    buffer += "## **2.1 Theoretical Reviews**\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    generated_intro = ""

    async def on_intro_chunk(chunk: str):
        nonlocal generated_intro
        if not chunk:
            return
        generated_intro += chunk
        file_path.write_text(buffer + generated_intro, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    intro_response = ""
    try:
        intro_response = await deepseek_direct.generate_content(
            prompt=_theoretical_review_intro_prompt(topic, objectives, case_study, country, intro_context),
            system_prompt="You are an academic writing assistant.",
            temperature=0.3,
            max_tokens=800,
            stream=True,
            stream_callback=on_intro_chunk,
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good theoretical review intro failed: {exc}", session_id=session_id)

    intro_text = (intro_response or generated_intro).strip()
    intro_text = _trim_incomplete_sentences(intro_text) or "Evidence is limited in the approved sources for this section."
    intro_text = _strip_leading_heading(intro_text, "2.1 Theoretical Reviews")
    intro_text = _normalise_two_author_citations(intro_text)
    intro_text = _strip_disallowed_citations(intro_text, {_paper_key(p) for p in intro_papers if _paper_key(p)})
    intro_text = _replace_reused_citations(intro_text, intro_papers, used_citations)
    intro_text = _ensure_citation_density(intro_text, intro_papers, 2, 4, used_citations)
    intro_text = _link_citations_to_sources(intro_text, intro_papers)
    _update_used_citations(intro_text, used_citations)
    buffer = buffer + intro_text + "\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    general_title = "2.1.1 General Theory"
    sections = [
        (general_title, objectives, papers),
    ]
    if objectives:
        if len(objectives) >= 2:
            sections.append(
                (
                    f"2.1.2 Theoretical Framework: {_objective_heading(objectives[0], country, case_study)}",
                    objectives[:2],
                    objective_papers(objectives[0]),
                )
            )
        if len(objectives) >= 3:
            sections.append(
                (
                    f"2.1.3 Theoretical Framework: {_objective_heading(objectives[2], country, case_study)}",
                    [objectives[2]],
                    objective_papers(objectives[2]),
                )
            )

    for title, obj_block, source_pool in sections:
        theory_papers = _select_papers(source_pool, keywords, count=30, used_keys=used_citations, require_theory=True)
        theory_context = _build_citation_context(theory_papers, max_sources=30)
        candidates = _extract_theory_candidates(theory_papers)
        candidate_list = _format_theory_candidates(candidates)
        forced_theory = _pick_theory_candidate(theory_papers, keywords)
        section_title = title
        if forced_theory:
            number = title.split()[0]
            section_title = f"{number} {forced_theory['name']} theory by {forced_theory['author']} ({forced_theory['year']})"
        else:
            number = title.split()[0]
            section_title = f"{number} Theory (evidence limited in sources)"
        section_header = f"### ***{section_title}***\n\n"
        buffer = buffer + section_header
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        generated_section = ""

        async def on_section_chunk(chunk: str):
            nonlocal generated_section, buffer
            if not chunk:
                return
            generated_section += chunk
            file_path.write_text(buffer + generated_section, encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)

        response = ""
        try:
            response = await deepseek_direct.generate_content(
                prompt=_theory_prompt(
                    topic,
                    case_study,
                    country,
                    theory_context,
                    obj_block,
                    title,
                    candidate_list,
                    forced_theory,
                ),
                system_prompt="You are an academic writing assistant.",
                temperature=0.2,
                max_tokens=1800,
                stream=True,
                stream_callback=on_section_chunk,
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ /good theoretical review failed: {title}: {exc}", session_id=session_id)

        section_text = (response or generated_section).strip()
        if not section_text:
            section_text = "Evidence is limited in the approved sources for this section."
        section_text = _trim_incomplete_sentences(section_text)
        section_text = _strip_leading_heading(section_text, title)
        section_text = _ensure_theory_paragraphs(section_text)
        section_text = _normalise_two_author_citations(section_text)
        allowed_keys = {_paper_key(p) for p in theory_papers if _paper_key(p)}
        section_text = _strip_disallowed_citations(section_text, allowed_keys)
        section_text = _replace_reused_citations(section_text, theory_papers, used_citations)
        section_text = _ensure_citation_density(section_text, theory_papers, 3, 5, used_citations)
        section_text = _link_citations_to_sources(section_text, theory_papers)
        _update_used_citations(section_text, used_citations)
        parsed_heading = _extract_theory_heading(section_text)
        allowed_keys = {_theory_candidate_key(c) for c in candidates}
        if parsed_heading:
            theory_name, author_name, year = parsed_heading
            parsed_key = f"{theory_name.lower()}|{author_name.lower()}|{year}"
            if parsed_key in allowed_keys:
                number = title.split()[0]
                heading_core = (
                    f"{theory_name} by {author_name} ({year})"
                    if "theory" in theory_name.lower()
                    else f"{theory_name} theory by {author_name} ({year})"
                )
                new_title = f"{number} {heading_core}"
                new_header = f"### ***{new_title}***\n\n"
                if section_header in buffer:
                    buffer = buffer.replace(section_header, new_header, 1)
                    section_header = new_header
        buffer = buffer + section_text + "\n\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    if not objectives:
        objectives = fallback_objectives(topic, case_study, country)

    buffer = buffer + "## **2.2 Empirical Reviews**\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    emp_intro_papers = _select_papers(papers, keywords, count=25, used_keys=used_citations)
    emp_intro_context = _build_citation_context(emp_intro_papers, max_sources=25)
    emp_intro_generated = ""

    async def on_emp_intro_chunk(chunk: str):
        nonlocal emp_intro_generated, buffer
        if not chunk:
            return
        emp_intro_generated += chunk
        file_path.write_text(buffer + emp_intro_generated, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    emp_intro_response = ""
    try:
        emp_intro_response = await deepseek_direct.generate_content(
            prompt=_empirical_intro_prompt(topic, objectives, case_study, country, emp_intro_context),
            system_prompt="You are an academic writing assistant.",
            temperature=0.3,
            max_tokens=900,
            stream=True,
            stream_callback=on_emp_intro_chunk,
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good empirical intro failed: {exc}", session_id=session_id)

    emp_intro_text = (emp_intro_response or emp_intro_generated).strip()
    if not emp_intro_text:
        emp_intro_text = "Evidence is limited in the approved sources for this section."
    emp_intro_text = _trim_incomplete_sentences(emp_intro_text)
    emp_intro_text = _strip_leading_heading(emp_intro_text, "2.2 Empirical Reviews")
    emp_intro_text = _normalise_two_author_citations(emp_intro_text)
    emp_intro_text = _strip_disallowed_citations(emp_intro_text, {_paper_key(p) for p in emp_intro_papers if _paper_key(p)})
    emp_intro_text = _replace_reused_citations(emp_intro_text, emp_intro_papers, used_citations)
    emp_intro_text = _ensure_citation_density(emp_intro_text, emp_intro_papers, 2, 4, used_citations)
    emp_intro_text = _link_citations_to_sources(emp_intro_text, emp_intro_papers)
    _update_used_citations(emp_intro_text, used_citations)
    buffer = buffer + emp_intro_text + "\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    empirical_objectives = objectives[:4]
    for idx, objective in enumerate(empirical_objectives, 1):
        section_title = f"2.2.{idx} {_objective_heading(objective, country, case_study)}"
        section_header = f"### ***{section_title}***\n\n"
        buffer = buffer + section_header
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        pool = objective_papers(objective)
        region_used_keys: set = set(used_citations)
        region_selected = _select_region_papers(pool, country, region_used_keys)
        selected_papers = [paper for _, paper in region_selected]
        if len(selected_papers) < 6:
            extra = _select_papers(
                pool,
                keywords,
                count=6 - len(selected_papers),
                used_keys=region_used_keys,
            )
            selected_papers.extend(extra)
        selected_papers = [paper for paper in selected_papers if _paper_key(paper) and _paper_lead(paper)]
        selected_papers = selected_papers[:6]

        if not selected_papers:
            emp_text = "Evidence is limited in the approved sources for this section."
            buffer = buffer + emp_text + "\n\n"
            file_path.write_text(buffer, encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)
            continue

        emp_paragraphs: List[str] = []
        for paper in selected_papers:
            author = _paper_lead(paper)
            if not author:
                continue
            para_generated = ""

            async def on_emp_para_chunk(chunk: str):
                nonlocal para_generated, buffer, emp_paragraphs
                if not chunk:
                    return
                para_generated += chunk
                live_text = "\n\n".join(emp_paragraphs + [para_generated])
                file_path.write_text(buffer + live_text, encoding="utf-8")
                await events.file_updated(job_id, str(file_path), session_id=session_id)

            para_response = ""
            try:
                para_response = await deepseek_direct.generate_content(
                    prompt=_empirical_paragraph_prompt(
                        objective,
                        topic,
                        author,
                        paper.year,
                        paper.title,
                        paper.abstract,
                        paper.venue,
                    ),
                    system_prompt="You are an academic writing assistant.",
                    temperature=0.2,
                    max_tokens=450,
                    stream=True,
                    stream_callback=on_emp_para_chunk,
                )
            except Exception as exc:
                await events.log(job_id, f"⚠️ /good empirical paragraph failed: {section_title}: {exc}", session_id=session_id)

            para_text = (para_response or para_generated).strip()
            if not para_text:
                continue
            para_text = _trim_incomplete_sentences(para_text)
            lead_phrase = f"{author} ({paper.year}) conducted a study"
            if not para_text.lower().startswith(lead_phrase.lower()):
                para_text = f"{lead_phrase} {para_text.lstrip()}"
            allowed_key = {_paper_key(paper)}
            para_text = _normalise_two_author_citations(para_text)
            para_text = _strip_disallowed_citations(para_text, allowed_key)
            para_text = _replace_reused_citations(para_text, [paper], used_citations)
            para_text = _ensure_citation_density(para_text, [paper], 1, 1, used_citations)
            para_text = _link_citations_to_sources(para_text, [paper])
            _update_used_citations(para_text, used_citations)
            emp_paragraphs.append(para_text)

        emp_text = "\n\n".join(emp_paragraphs) if emp_paragraphs else "Evidence is limited in the approved sources for this section."
        buffer = buffer + emp_text + "\n\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    buffer = buffer + "## **2.3 Conceptual Framework**\n\n"
    conceptual_section = _extract_conceptual_framework(workspace_id)
    if conceptual_section:
        buffer = buffer + conceptual_section + "\n\n"
    else:
        buffer = buffer + "Evidence is limited in the approved sources for this section.\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    buffer = buffer + "## **2.4 Summary and Knowledge Gap**\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    summary_papers = _select_papers(papers, keywords, count=20, used_keys=used_citations)
    summary_context = _build_citation_context(summary_papers, max_sources=20)
    summary_generated = ""

    async def on_summary_chunk(chunk: str):
        nonlocal summary_generated, buffer
        if not chunk:
            return
        summary_generated += chunk
        file_path.write_text(buffer + summary_generated, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    summary_response = ""
    try:
        summary_response = await deepseek_direct.generate_content(
            prompt=_summary_gap_prompt(topic, case_study, country, summary_context),
            system_prompt="You are an academic writing assistant.",
            temperature=0.3,
            max_tokens=900,
            stream=True,
            stream_callback=on_summary_chunk,
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good empirical summary failed: {exc}", session_id=session_id)

    summary_text = (summary_response or summary_generated).strip()
    if not summary_text:
        summary_text = "Evidence is limited in the approved sources for this section."
    summary_text = _trim_incomplete_sentences(summary_text)
    summary_text = _strip_leading_heading(summary_text, "2.4 Summary and Knowledge Gap")
    summary_text = _normalise_two_author_citations(summary_text)
    summary_text = _strip_disallowed_citations(summary_text, {_paper_key(p) for p in summary_papers if _paper_key(p)})
    summary_text = _replace_reused_citations(summary_text, summary_papers, used_citations)
    summary_text = _ensure_citation_density(summary_text, summary_papers, 2, 4, used_citations)
    summary_text = _link_citations_to_sources(summary_text, summary_papers)
    _update_used_citations(summary_text, used_citations)
    buffer = buffer + summary_text + "\n\n"
    file_path.write_text(buffer, encoding="utf-8")
    await events.file_updated(job_id, str(file_path), session_id=session_id)

    references = _build_references_section(buffer, "", papers)
    if references:
        buffer = buffer + "## **References for Chapter Two**\n\n" + references.strip() + "\n"
        file_path.write_text(buffer, encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    if config_id:
        update_good_status(config_id, {"chapter2_theory_done": True, "chapter2_empirical_done": True})

    await events.log(job_id, f"✅ /good Chapter Two theoretical reviews saved: {file_path.name}", session_id=session_id)
    await events.stage_completed(job_id, "good_chapter_two_theory", {"file": file_path.name}, session_id=session_id)

    try:
        from services.good_chapter_four_generator import run_good_chapter_four_generation

        await run_good_chapter_four_generation(
            job_id,
            workspace_id,
            session_id,
            {"config_id": config_id},
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good Chapter Four failed: {exc}", session_id=session_id)

    try:
        from services.good_chapter_five_generator import run_good_chapter_five_generation

        await run_good_chapter_five_generation(
            job_id,
            workspace_id,
            session_id,
            {"config_id": config_id},
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good Chapter Five failed: {exc}", session_id=session_id)

    try:
        from services.good_proposal_combiner import maybe_run_good_proposal_combiner

        await maybe_run_good_proposal_combiner(job_id, workspace_id, session_id, config_id)
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good proposal combiner failed: {exc}", session_id=session_id)
