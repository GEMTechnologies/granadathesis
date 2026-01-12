"""Generate Chapter One sections for /good flow using real sources."""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from core.events import events
from services.deepseek_direct import deepseek_direct
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.good_objective_generator import normalise_objectives
from services.sources_service import sources_service
from services.workspace_service import WORKSPACES_DIR
from services.parallel_chapter_generator import ResearchResult


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _author_last_name(author) -> str:
    if isinstance(author, dict):
        name = author.get("name") or author.get("family") or author.get("given") or ""
    else:
        name = str(author or "")
    name = name.strip()
    if not name:
        return ""
    if "," in name:
        return name.split(",")[0].strip()
    parts = name.split()
    if parts and parts[-1].lower().strip(".") in {"jr", "sr"} and len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else name


def _paper_key(paper: ResearchResult) -> str:
    last = _author_last_name(paper.authors[0]) if paper.authors else ""
    if not last or len(last) < 2:
        return ""
    return f"{last.lower()}:{paper.year}" if last else ""


def _paper_citation_text(paper: ResearchResult) -> str:
    last = _author_last_name(paper.authors[0]) if paper.authors else ""
    if not last or len(last) < 2:
        return ""
    return f"{last}, {paper.year}" if last else ""


def _extract_keywords(*texts: str) -> List[str]:
    stop = {
        "about", "after", "again", "against", "among", "between", "context", "during",
        "study", "studies", "research", "the", "and", "with", "from", "this", "that",
        "into", "over", "under", "within", "where", "which", "their", "there", "these",
        "those", "case", "state", "states", "country", "countries", "region", "regions",
        "area", "areas", "south", "north", "east", "west", "central", "africa", "sudan",
    }
    words: List[str] = []
    for text in texts:
        for token in re.findall(r"[a-z]{4,}", (text or "").lower()):
            if token in stop:
                continue
            words.append(token)
    return list(dict.fromkeys(words))


def _score_paper(paper: ResearchResult, keywords: List[str]) -> int:
    if not keywords:
        return 0
    hay = f"{paper.title} {paper.abstract}".lower()
    return sum(1 for kw in keywords if kw in hay)


def _select_papers(
    papers: List[ResearchResult],
    keywords: List[str],
    count: int,
    used_keys: Optional[set] = None,
    require_theory: bool = False,
) -> List[ResearchResult]:
    used_keys = used_keys or set()
    filtered = [p for p in papers if _paper_key(p) not in used_keys]
    if require_theory:
        theory_keys = ["theory", "theoretical", "framework", "model"]
        filtered = [
            p for p in filtered
            if any(key in f"{p.title} {p.abstract}".lower() for key in theory_keys)
        ]
    ranked = sorted(filtered, key=lambda p: _score_paper(p, keywords), reverse=True)
    selected = ranked[:count]
    if len(selected) < count:
        fallback = [p for p in papers if p not in selected]
        selected.extend(fallback[: max(0, count - len(selected))])
    return selected


def _make_research_results(sources: List[Dict], year_from: int, year_to: int) -> List[ResearchResult]:
    results: List[ResearchResult] = []
    seen_keys: set = set()
    for source in sources:
        year = source.get("year")
        if isinstance(year, str) and year.isdigit():
            year = int(year)
        if not isinstance(year, int):
            continue
        if year < year_from or year > year_to:
            continue
        authors = source.get("authors") or []
        if not authors:
            continue
        first_author = _author_last_name(authors[0])
        if (
            not first_author
            or len(first_author) < 2
            or first_author.lower() in ["unknown", "anonymous", "n/a"]
        ):
            continue
        doi = source.get("doi", "") or ""
        url = source.get("url", "") or (f"https://doi.org/{doi}" if doi else "")
        if not url:
            continue
        candidate = ResearchResult(
            title=source.get("title", "Untitled"),
            authors=authors,
            year=year,
            doi=doi,
            url=url,
            abstract=(source.get("abstract") or "")[:1200],
            source="good",
            venue=source.get("venue", ""),
        )
        key = _paper_key(candidate)
        if key and key in seen_keys:
            continue
        if key:
            seen_keys.add(key)
        results.append(candidate)
    return results


def _build_citation_context(papers: List[ResearchResult], max_sources: int = 60) -> str:
    if not papers:
        return "No approved sources available. Do not add citations; explicitly state evidence is limited."

    context = [
        "APPROVED CITATION SOURCES:",
        "Cite ONLY from this list. Do NOT invent authors or studies.",
        "",
    ]

    for idx, paper in enumerate(papers[:max_sources], 1):
        apa = paper.to_apa()
        if not apa:
            continue
        url = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
        if not url:
            continue
        context.append(f"{idx}. {apa} - \"{paper.title}\"")
        if paper.abstract:
            context.append(f"   Abstract: {paper.abstract[:1200]}...")
        context.append(f"   URL for citation: {url}")
        context.append("")

    context.append("⚠️ END OF APPROVED SOURCES. Any citation not from this list is PROHIBITED.")
    return "\n".join(context)


def _link_citations_to_sources(content: str, papers: List[ResearchResult]) -> str:
    if not content or not papers:
        return content

    url_map: Dict[str, str] = {}
    for paper in papers:
        if not paper.authors:
            continue
        url = paper.url or (f"https://doi.org/{paper.doi}" if paper.doi else "")
        if not url:
            continue
        last_name = _author_last_name(paper.authors[0])
        if not last_name:
            continue
        url_map[f"{last_name.lower()}:{paper.year}"] = url

    if not url_map:
        return content

    def link_part(part: str) -> str:
        if "](" in part:
            return part
        match = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?\s*,\s*(\d{4})", part)
        if not match:
            return part
        last = match.group(1)
        if len(last) < 2:
            return part
        year = match.group(2)
        url = url_map.get(f"{last.lower()}:{year}")
        if not url:
            return part
        return part.replace(match.group(0), f"[{match.group(0)}]({url})", 1)

    def replace_group(match: re.Match) -> str:
        inner = match.group(1)
        if "](" in inner:
            return match.group(0)
        parts = [p.strip() for p in inner.split(";")]
        linked_parts = [link_part(p) for p in parts]
        return "(" + "; ".join(linked_parts) + ")"

    content = re.sub(r"\(([^()]*\d{4}[^()]*)\)", replace_group, content)

    def replace_narrative(match: re.Match) -> str:
        name = match.group(1)
        year = match.group(2)
        key_match = re.search(r"([A-Za-z][A-Za-z-']+)", name)
        if not key_match:
            return match.group(0)
        last = key_match.group(1)
        if len(last) < 2:
            return match.group(0)
        url = url_map.get(f"{last.lower()}:{year}")
        if not url:
            return match.group(0)
        return f"[{name} ({year})]({url})"

    content = re.sub(r"(?<!\[)(\b[A-Z][A-Za-z-']+(?:\s+et al\.)?)\s*\((\d{4})\)", replace_narrative, content)
    return content


def _trim_incomplete_sentences(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return cleaned
    if re.search(r"[.!?][\"')\]]?\s*$", cleaned):
        return cleaned
    matches = list(re.finditer(r"[.!?][\"')\]]?", cleaned))
    if not matches:
        return cleaned + "."
    cut = matches[-1].end()
    return cleaned[:cut].strip()


def _normalise_two_author_citations(text: str) -> str:
    if not text:
        return text
    text = re.sub(
        r"([A-Z][A-Za-z-']+)\s*(?:&|and)\s*[A-Z][A-Za-z-']+\.?\s*,\s*(\d{4})",
        r"\1 et al., \2",
        text,
    )
    text = re.sub(
        r"([A-Z][A-Za-z-']+)\s*(?:&|and)\s*[A-Z][A-Za-z-']+\.?\s*\((\d{4})\)",
        r"\1 et al. (\2)",
        text,
    )
    return text


def _strip_leading_heading(text: str, section_title: str) -> str:
    if not text:
        return text
    title = section_title.lower()
    lines = text.splitlines()
    while lines:
        first = lines[0].strip()
        if not first:
            lines.pop(0)
            continue
        if re.match(r"(?i)^chapter\s+one", first):
            lines.pop(0)
            continue
        if first.lower().startswith(title):
            lines.pop(0)
            continue
        if re.match(r"^\s*1\.\d+", first) and first.lower().split()[0] in title:
            lines.pop(0)
            continue
        break
    return "\n".join(lines).strip()


def _strip_disallowed_citations(text: str, allowed_keys: set) -> str:
    if not text or not allowed_keys:
        return text

    def filter_group(match: re.Match) -> str:
        inner = match.group(1)
        parts = [p.strip() for p in inner.split(";")]
        kept = []
        seen = set()
        for part in parts:
            ref = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
            if not ref:
                continue
            key = f"{ref.group(1).lower()}:{ref.group(2)}"
            if key in allowed_keys and key not in seen:
                kept.append(part)
                seen.add(key)
        if not kept:
            return ""
        return "(" + "; ".join(kept) + ")"

    text = re.sub(r"\(([^()]*\d{4}[^()]*)\)", filter_group, text)

    def filter_narrative(match: re.Match) -> str:
        name = match.group(1)
        year = match.group(2)
        key = f"{name.lower()}:{year}"
        if key in allowed_keys:
            return match.group(0)
        return name

    text = re.sub(r"\b([A-Z][A-Za-z-']+)\s*\((\d{4})\)", filter_narrative, text)
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text


def _cleanup_inline_citation_formatting(text: str) -> str:
    if not text:
        return text
    # Remove link wrappers or markdown emphasis inside parenthetical citations.
    text = re.sub(r"\(\[([^\]]+?)\]\([^)]+?\)\)", r"(\1)", text)
    text = re.sub(r"\(\*\*([^\*]+)\*\*\)", r"(\1)", text)
    text = re.sub(r"\(\*([^\*]+)\*\)", r"(\1)", text)
    text = re.sub(r"\(\s+", "(", text)
    text = re.sub(r"\s+\)", ")", text)
    return text


def _dedupe_citation_groups(text: str) -> str:
    if not text:
        return text

    def dedupe_group(match: re.Match) -> str:
        inner = match.group(1)
        parts = [p.strip() for p in inner.split(";") if p.strip()]
        seen = set()
        kept = []
        for part in parts:
            ref = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
            if not ref:
                continue
            key = f"{ref.group(1).lower()}:{ref.group(2)}"
            if key in seen:
                continue
            seen.add(key)
            kept.append(part)
        if not kept:
            return ""
        return "(" + "; ".join(kept) + ")"

    return re.sub(r"\(([^()]*\d{4}[^()]*)\)", dedupe_group, text)


def _replace_reused_citations(
    text: str,
    allowed_papers: List[ResearchResult],
    used_keys: set,
) -> str:
    if not text or not allowed_papers:
        return text

    available = [p for p in allowed_papers if _paper_key(p) and _paper_key(p) not in used_keys]
    if not available:
        return _dedupe_citation_groups(text)

    local_used = set(used_keys)

    def pick_replacement() -> str:
        for paper in available:
            key = _paper_key(paper)
            if not key or key in local_used:
                continue
            local_used.add(key)
            citation = _paper_citation_text(paper)
            if citation:
                return citation
        return ""

    def replace_group(match: re.Match) -> str:
        inner = match.group(1)
        parts = [p.strip() for p in inner.split(";") if p.strip()]
        kept = []
        seen = set()
        for part in parts:
            ref = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
            if not ref:
                continue
            key = f"{ref.group(1).lower()}:{ref.group(2)}"
            if key in seen:
                continue
            seen.add(key)
            if key in used_keys:
                replacement = pick_replacement()
                kept.append(replacement or part)
            else:
                kept.append(part)
        if not kept:
            return ""
        return "(" + "; ".join(kept) + ")"

    text = re.sub(r"\(([^()]*\d{4}[^()]*)\)", replace_group, text)
    return _dedupe_citation_groups(text)


def _ensure_citation_density(
    text: str,
    allowed_papers: List[ResearchResult],
    min_citations: int,
    max_citations: int,
    used_keys: set,
) -> str:
    if not text:
        return text
    paragraphs = [p for p in text.split("\n") if p.strip()]
    allowed_keys = {_paper_key(p) for p in allowed_papers if _paper_key(p)}
    pool = [p for p in allowed_papers if _paper_key(p) in allowed_keys]
    for idx, paragraph in enumerate(paragraphs):
        word_count = len(re.findall(r"\b\w+\b", paragraph))
        if word_count < 8 and not re.search(r"[.!?]\s*$", paragraph.strip()):
            continue
        citations = re.findall(r"\(([^\)]*\d{4}[^\)]*)\)", paragraph)
        present = set()
        for group in citations:
            for part in group.split(";"):
                ref = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
                if ref:
                    present.add(f"{ref.group(1).lower()}:{ref.group(2)}")
        count = len(present)
        if count >= min_citations:
            continue
        available = [p for p in pool if _paper_key(p) not in present and _paper_key(p) not in used_keys]
        needed = min(max_citations, min_citations) - count
        if len(available) < needed:
            fallback = [p for p in pool if _paper_key(p) not in present]
            for paper in fallback:
                if paper in available:
                    continue
                available.append(paper)
        chosen = available[: max(0, needed)]
        if not chosen:
            continue
        cite_text = "; ".join(_paper_citation_text(p) for p in chosen if _paper_citation_text(p))
        if not cite_text:
            continue
        if paragraph.endswith("."):
            paragraph = paragraph[:-1] + f" ({cite_text})."
        else:
            paragraph = paragraph + f" ({cite_text})."
        for paper in chosen:
            key = _paper_key(paper)
            if key:
                used_keys.add(key)
        paragraphs[idx] = paragraph
    return "\n".join(paragraphs)


def _update_used_citations(text: str, used_keys: set) -> None:
    if not text:
        return
    for group in re.findall(r"\(([^\)]*\d{4}[^\)]*)\)", text):
        for part in group.split(";"):
            ref = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
            if ref:
                used_keys.add(f"{ref.group(1).lower()}:{ref.group(2)}")
    for match in re.finditer(r"\b([A-Z][A-Za-z-']+(?:\s+et al\.)?)\s*\((\d{4})\)", text):
        used_keys.add(f"{match.group(1).split()[0].lower()}:{match.group(2)}")


def _build_references_section(body_text: str, post_text: str, papers: List[ResearchResult]) -> str:
    if not papers:
        return ""
    combined = f"{body_text}\n{post_text}"
    combined = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", combined)
    citations = re.findall(r"\(([^\)]+?\d{4}[^\)]*?)\)", combined)
    narrative = re.findall(r"\b([A-Z][A-Za-z-']+(?:\s+et al\.)?)\s*\((\d{4})\)", combined)
    cited_keys = set()
    for group in citations:
        parts = [part.strip() for part in group.split(";")]
        for part in parts:
            match = re.search(r"([A-Za-z][A-Za-z-']+)(?:\s+et al\.)?,\s*(\d{4})", part)
            if not match:
                continue
            cited_keys.add(f"{match.group(1).lower()}:{match.group(2)}")
    for name, year in narrative:
        key_match = re.search(r"[A-Za-z][A-Za-z-']+", name)
        if key_match:
            cited_keys.add(f"{key_match.group(0).lower()}:{year}")
    if not cited_keys:
        return ""
    references = []
    for paper in papers:
        if not paper.authors:
            continue
        last_name = _author_last_name(paper.authors[0])
        if not last_name or len(last_name) < 2:
            continue
        key = f"{last_name.lower()}:{paper.year}"
        if key not in cited_keys:
            continue
        apa = paper.to_apa_full()
        if not apa:
            continue
        apa = apa.replace("*", "")
        references.append(apa)
    if not references:
        return ""
    return "\n".join(sorted(set(references)))


def _intro_prompt(topic: str, country: str, case_study: str, citation_context: str) -> str:
    return f"""Write a brief Introduction about {topic} in {country} and specifically in {case_study} with enough in-text citations. Write three short paragraphs for the introduction and conclude the fourth paragraph by outlining the Chapter One contents (historical background, problem statement, purpose, objectives, questions and hypotheses, significance, scope, methodology, limitations and delimitation, assumptions, definition of key terms, and summary). Keep each paragraph to 3–4 sentences. Include 1–2 citations per paragraph where evidence allows. NOTE THAT THE CURRENT YEAR WE ARE IN IS 2026 and citations need to be between June of 2020 and June of 2026.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use UK English. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats. Do not use headings or bullets. Never say "we"; use "the study" or "the researcher".

CITATION CONTEXT:
{citation_context}
"""


def _background_prompt(topic: str, country: str, case_study: str, citation_context: str) -> str:
    return f"""Write a historical Background of the study about {topic} in multiple SINGLE paragraphs (no subheadings, no bullets). Use strong academic tone, UK English, and avoid "we". Keep each paragraph to 3–4 sentences. Use ONLY sources from the CITATION CONTEXT below. If a region is not covered by approved sources, state that evidence is limited and do not invent citations. Do not fabricate authors or studies. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

GLOBAL SECTION (five single paragraphs):
1) One paragraph giving a global historical overview of {topic}.
2) One paragraph covering the Americas (mention sample countries/states).
3) One paragraph covering Asia (mention sample countries/states).
4) One paragraph covering Australia/Oceania (mention sample countries/states).
5) One paragraph covering Europe (mention sample countries/states).

AFRICAN SECTION (five single paragraphs):
6) One paragraph giving an Africa-wide historical overview of {topic}.
7) One paragraph covering North Africa/Arab African countries (e.g., Egypt, Libya, Tunisia, Morocco, Sudan) using only approved sources.
8) One paragraph covering Southern Africa.
9) One paragraph covering Central Africa.
10) One paragraph covering West Africa.

EAST AFRICA SECTION (two single paragraphs):
11) One paragraph giving an East African overview.
12) One paragraph mentioning sample districts/villages/places in East African countries, and include local place names where sources allow.

COUNTRY + LOCAL SECTION (two single paragraphs):
13) One paragraph giving a {country}-level historical background with local place names where sources allow.
14) One paragraph giving the past-to-present situation of {topic} in {case_study}, then conclude that it is upon the above background that this study aims to examine {topic} in {case_study}, {country}.

NOTE: The current year is 2026; use sources dated June 2020 to June 2026 where available in the approved list.

CITATION CONTEXT:
{citation_context}
"""


def _problem_prompt(
    topic: str,
    country: str,
    case_study: str,
    citation_context: str,
    objectives: List[str],
    conceptual_vars: Dict[str, str],
) -> str:
    objectives_text = "\n".join(f"- {obj}" for obj in objectives) if objectives else "- Not provided"
    indep = conceptual_vars.get("independent") or "Not specified"
    dep = conceptual_vars.get("dependent") or "Not specified"
    return f"""Write a concise problem statement for the study about {topic} in {case_study}, {country}. Use UK English and an academic tone. Do not use bullets or headings. Never say "we". Write ONE or TWO short paragraphs only (2–3 sentences each).

The problem statement must be data-informed and link the background to the study objectives and the core variables. Explicitly connect the problem to the objectives and to the independent/dependent variables listed below. Include at least one numeric or statistical reference if it exists in the approved sources; if no statistics are available, state that clearly without inventing data.

Use ONLY sources from the CITATION CONTEXT below. Do not fabricate studies or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

OBJECTIVES:
{objectives_text}

CONCEPTUAL VARIABLES:
Independent: {indep}
Dependent: {dep}

CITATION CONTEXT:
{citation_context}
"""


def _background_part_prompt(topic: str, country: str, case_study: str, citation_context: str, focus: str, note: str = "") -> str:
    note_clause = f" {note}" if note else ""
    return f"""Write ONE historical background paragraph (3–4 sentences) about {topic}. Focus: {focus}.{note_clause} Include 3–5 citations within the paragraph where evidence allows.

Use strong academic tone, UK English, and avoid "we". If evidence is limited in the approved sources, state that clearly in a complete sentence and do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats. Do not use headings or bullets.

    CITATION CONTEXT:
{citation_context}
"""


def _extract_theory_candidates(papers: List[ResearchResult]) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    seen = set()
    if not papers:
        return candidates
    patterns = [
        re.compile(r"([A-Z][A-Za-z0-9\- ]+?\b(?:theory|model|framework))", re.IGNORECASE),
    ]
    for paper in papers:
        text = f"{paper.title} {paper.abstract}".strip()
        if not text:
            continue
        matches = []
        for pattern in patterns:
            matches.extend(pattern.findall(text))
        if not matches:
            continue
        name = matches[0].strip().rstrip(".")
        if len(name) < 5:
            continue
        if name.lower() in {"theoretical framework", "conceptual framework", "theory", "model", "framework"}:
            continue
        author = _author_last_name(paper.authors[0]) if paper.authors else ""
        year = str(paper.year) if paper.year else ""
        if not author or not year:
            continue
        key = f"{name.lower()}|{author.lower()}|{year}"
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"name": name, "author": author, "year": year})
    return candidates


def _format_theory_candidates(candidates: List[Dict[str, str]]) -> str:
    if not candidates:
        return "- None available in approved sources."
    lines = []
    for cand in candidates[:8]:
        lines.append(f"- {cand['name']} — {cand['author']} ({cand['year']})")
    return "\n".join(lines)


def _theoretical_framework_prompt(
    topic: str,
    country: str,
    case_study: str,
    citation_context: str,
    theory_candidates: str,
    forced_theory: Optional[Dict[str, str]],
) -> str:
    forced_note = ""
    if forced_theory:
        forced_note = f"Use this theory: {forced_theory['name']} — {forced_theory['author']} ({forced_theory['year']})."
    return f"""Generate a detailed theoretical framework for the study about {topic}. Write FIVE separate paragraphs with a blank line between each paragraph (no headings, no bullets, no numbering).

Use ONE theory from the approved list below. Use the exact theory name and associated author/year. If none are available, state that evidence is limited and do not invent a theory. {forced_note}

Approved theory list:
{theory_candidates}

Paragraph 1 must start with: "The study will be guided by the [Theory Name] theory as discussed by Author (Year)." Briefly outline the historical origins and core ideas of the theory with precise in-text citations.
Paragraph 2: present studies that have applied this theory in contexts similar to {topic}, highlighting how it has been used.
Paragraph 3: present critical perspectives or limitations highlighted by scholars.
Paragraph 4: explain the relevance of the theory to the current study and its objectives.
Paragraph 5: state gaps in the theory with reference to {case_study}, {country}.

Use UK English, academic tone, and avoid "we". Include 3–5 citations per paragraph where evidence allows.

Use ONLY sources from the CITATION CONTEXT below. Do not invent citations or authors. Avoid placeholder names (e.g., Smith, Johnson, Lee) unless they appear in the approved source list. Use author–date citations in parentheses using LAST NAMES ONLY (e.g., (Surname, 2023) or (Surname et al., 2024)). Avoid two-author formats.

CITATION CONTEXT:
{citation_context}
"""


def _ensure_theory_paragraphs(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paragraphs) >= 5:
        return "\n\n".join(paragraphs)
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]
    if len(sentences) <= 1:
        return text
    target = 5
    chunks: List[str] = []
    remaining = sentences[:]
    while remaining and len(chunks) < target:
        chunk_size = max(1, len(remaining) // (target - len(chunks)))
        chunk = remaining[:chunk_size]
        remaining = remaining[chunk_size:]
        chunks.append(" ".join(chunk))
    if remaining:
        chunks[-1] = f"{chunks[-1]} {' '.join(remaining)}"
    return "\n\n".join(chunks)


async def run_good_chapter_one_generation(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
    await events.stage_started(
        job_id,
        "good_chapter_one",
        {"message": "📝 Generating /good Chapter One..."},
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
    generated_objectives = extra_json.get("generated_objectives") or []
    user_objectives = extra_json.get("user_objectives") or []
    if user_objectives:
        objectives = user_objectives
    elif not objectives and generated_objectives:
        objectives = generated_objectives
    objectives = normalise_objectives(objectives, bool(user_objectives))

    conceptual_vars = extra_json.get("conceptual_variables") or {}
    if isinstance(conceptual_vars, str):
        try:
            conceptual_vars = json.loads(conceptual_vars)
        except json.JSONDecodeError:
            conceptual_vars = {}
    if not conceptual_vars:
        try:
            from services.good_research_service import extract_conceptual_variables
            conceptual_vars = extract_conceptual_variables(topic)
        except Exception:
            conceptual_vars = {}

    if not topic:
        await events.log(job_id, "⚠️ /good Chapter One skipped: no topic provided.", session_id=session_id)
        return

    await events.log(job_id, "✍️ /good Chapter One generation started...", session_id=session_id)

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    good_dir.mkdir(parents=True, exist_ok=True)
    file_path = good_dir / "Chapter_1_Introduction.md"
    file_exists = file_path.exists()
    existing_text = file_path.read_text(encoding="utf-8") if file_exists else ""
    tail = ""
    if existing_text:
        match = re.search(
            r"(?m)^##\s*\*\*1\.4 Objectives of the Study\*\*|^1\.4 Objectives of the Study",
            existing_text,
        )
        if match:
            tail = existing_text[match.start():].lstrip()

    file_path.write_text("**CHAPTER ONE: INTRODUCTION**\n\n", encoding="utf-8")
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

    # Wait for sources to be available (up to ~20 seconds)
    sources = sources_service.list_sources(workspace_id)
    for _ in range(12):
        if sources:
            break
        await asyncio.sleep(1.5)
        sources = sources_service.list_sources(workspace_id)

    year_from = config.get("literature_year_start") or 2020
    year_to = config.get("literature_year_end") or 2026
    papers = _make_research_results(sources, year_from, year_to)
    base_keywords = _extract_keywords(topic, country, case_study, " ".join(objectives or []))
    used_citations: set = set()

    buffer = "**CHAPTER ONE: INTRODUCTION**\n\n"

    def _compose_text(main_text: str, tail_text: str, post_text: str = "") -> str:
        parts = [main_text]
        if tail_text:
            parts.append(tail_text.strip() + "\n\n")
        if post_text:
            parts.append(post_text)
        return "".join(parts)

    def _section_context(section_keywords: List[str], count: int = 40, require_theory: bool = False) -> tuple:
        keywords = list(dict.fromkeys(base_keywords + section_keywords))
        selected = _select_papers(
            papers,
            keywords,
            count=count,
            used_keys=used_citations,
            require_theory=require_theory,
        )
        context = _build_citation_context(selected, max_sources=min(count, 60))
        return selected, context, keywords

    async def generate_section(
        section_title: str,
        prompt: str,
        allowed_papers: List[ResearchResult],
        min_citations: int,
        max_citations: int,
        max_tokens: int = 1200,
    ) -> str:
        section_header = f"## **{section_title}**\n\n"
        nonlocal buffer
        buffer = f"{buffer}{section_header}"
        file_path.write_text(_compose_text(buffer, tail), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        generated = ""

        async def on_chunk(chunk: str):
            nonlocal generated
            if not chunk:
                return
            generated += chunk
            file_path.write_text(_compose_text(buffer + generated, tail), encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)

        response = ""
        try:
            response = await deepseek_direct.generate_content(
                prompt=prompt,
                system_prompt="You are an academic writing assistant.",
                temperature=0.3,
                max_tokens=max_tokens,
                stream=True,
                stream_callback=on_chunk
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ /good section failed: {section_title}: {exc}", session_id=session_id)

        section_text = (response or generated).strip()
        if not section_text:
            section_text = "Evidence is limited in the approved sources for this section."
        section_text = _trim_incomplete_sentences(section_text)
        section_text = _strip_leading_heading(section_text, section_title)
        section_text = _strip_leading_heading(section_text, section_title)
        section_text = _normalise_two_author_citations(section_text)
        allowed_papers = allowed_papers or papers
        allowed_keys = {_paper_key(p) for p in allowed_papers if _paper_key(p)}
        section_text = _strip_disallowed_citations(section_text, allowed_keys)
        section_text = _replace_reused_citations(section_text, allowed_papers, used_citations)
        section_text = _ensure_citation_density(
            section_text,
            allowed_papers,
            min_citations,
            max_citations,
            used_citations,
        )
        section_text = _link_citations_to_sources(section_text, allowed_papers)
        _update_used_citations(section_text, used_citations)
        buffer = f"{buffer}{section_text}\n\n"
        file_path.write_text(_compose_text(buffer, tail), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)
        return section_text

    async def generate_section_parts(section_title: str, parts: List[Dict], max_tokens: int = 700) -> str:
        section_header = f"## **{section_title}**\n\n"
        nonlocal buffer
        buffer = f"{buffer}{section_header}"
        file_path.write_text(_compose_text(buffer, tail), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        for part in parts:
            focus = part.get("focus")
            note = part.get("note", "")
            prompt = part.get("prompt")
            allowed_papers = part.get("allowed_papers")
            if focus and not prompt:
                part_keywords = _extract_keywords(focus, note, topic, case_study, country)
                part_papers, part_ctx, _ = _section_context(part_keywords, count=35)
                allowed_papers = part_papers
                prompt = _background_part_prompt(topic, country, case_study, part_ctx, focus, note)
            prompt = prompt or ""
            allowed_papers = allowed_papers or papers
            min_citations = part.get("min_citations", 3)
            max_citations = part.get("max_citations", 5)
            generated = ""

            async def on_chunk(chunk: str):
                nonlocal generated
                if not chunk:
                    return
                generated += chunk
                file_path.write_text(_compose_text(buffer + generated, tail), encoding="utf-8")
                await events.file_updated(job_id, str(file_path), session_id=session_id)

            response = ""
            try:
                response = await deepseek_direct.generate_content(
                    prompt=prompt,
                    system_prompt="You are an academic writing assistant.",
                    temperature=0.3,
                    max_tokens=max_tokens,
                    stream=True,
                    stream_callback=on_chunk
                )
            except Exception as exc:
                await events.log(job_id, f"⚠️ /good background segment failed: {exc}", session_id=session_id)

            section_text = (response or generated).strip()
            if not section_text:
                section_text = "Evidence is limited in the approved sources for this section."
            section_text = _trim_incomplete_sentences(section_text)
            section_text = _strip_leading_heading(section_text, section_title)
            section_text = _normalise_two_author_citations(section_text)
            allowed_keys = {_paper_key(p) for p in allowed_papers if _paper_key(p)}
            section_text = _strip_disallowed_citations(section_text, allowed_keys)
            section_text = _replace_reused_citations(section_text, allowed_papers, used_citations)
            section_text = _ensure_citation_density(
                section_text,
                allowed_papers,
                min_citations,
                max_citations,
                used_citations,
            )
            section_text = _link_citations_to_sources(section_text, allowed_papers)
            _update_used_citations(section_text, used_citations)
            if section_text:
                buffer = f"{buffer}{section_text}\n\n"
                file_path.write_text(_compose_text(buffer, tail), encoding="utf-8")
                await events.file_updated(job_id, str(file_path), session_id=session_id)

        return buffer

    post_buffer = ""

    async def generate_post_section(
        section_title: str,
        prompt: str,
        allowed_papers: List[ResearchResult],
        min_citations: int,
        max_citations: int,
        max_tokens: int = 1400,
    ) -> str:
        nonlocal post_buffer
        section_header = f"## **{section_title}**\n\n"
        post_buffer = f"{post_buffer}{section_header}"
        file_path.write_text(_compose_text(buffer, tail, post_buffer), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

        generated = ""

        async def on_chunk(chunk: str):
            nonlocal generated
            if not chunk:
                return
            generated += chunk
            file_path.write_text(_compose_text(buffer, tail, post_buffer + generated), encoding="utf-8")
            await events.file_updated(job_id, str(file_path), session_id=session_id)

        response = ""
        try:
            response = await deepseek_direct.generate_content(
                prompt=prompt,
                system_prompt="You are an academic writing assistant.",
                temperature=0.3,
                max_tokens=max_tokens,
                stream=True,
                stream_callback=on_chunk
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ /good section failed: {section_title}: {exc}", session_id=session_id)

        section_text = (response or generated).strip()
        if not section_text:
            section_text = "Evidence is limited in the approved sources for this section."
        section_text = _trim_incomplete_sentences(section_text)
        section_text = _normalise_two_author_citations(section_text)
        allowed_papers = allowed_papers or papers
        allowed_keys = {_paper_key(p) for p in allowed_papers if _paper_key(p)}
        section_text = _strip_disallowed_citations(section_text, allowed_keys)
        section_text = _replace_reused_citations(section_text, allowed_papers, used_citations)
        section_text = _ensure_citation_density(
            section_text,
            allowed_papers,
            min_citations,
            max_citations,
            used_citations,
        )
        section_text = _link_citations_to_sources(section_text, allowed_papers)
        _update_used_citations(section_text, used_citations)
        if section_title == "1.12 Theoretical Framework of the Study":
            section_text = _ensure_theory_paragraphs(section_text)
        if section_title == "1.15 Definition of Key Terms":
            section_text = _format_key_terms_lines(section_text)
        if section_title == "1.13 Conceptual Framework":
            section_text = _format_conceptual_framework_list(section_text)
        post_buffer = f"{post_buffer}{section_text}\n\n"
        file_path.write_text(_compose_text(buffer, tail, post_buffer), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)
        return section_text

    intro_papers, intro_ctx, _ = _section_context(_extract_keywords("introduction", topic), count=30)
    await generate_section(
        "1.0 Introduction to the Study",
        _intro_prompt(topic, country, case_study, intro_ctx),
        intro_papers,
        min_citations=1,
        max_citations=2,
        max_tokens=1400,
    )

    background_parts: List[Dict] = []
    background_focuses = [
        ("global historical overview", ""),
        ("the Americas", "Mention sample countries or states."),
        ("Asia", "Mention sample countries or states."),
        ("Australia and Oceania", "Mention sample countries or states."),
        ("Europe", "Mention sample countries or states."),
        ("Africa-wide historical overview", ""),
        (
            "North Africa or Arab Africa",
            "Mention countries such as Egypt, Libya, Tunisia, Morocco, or Sudan where supported.",
        ),
        ("Southern Africa", ""),
        ("Central Africa", ""),
        ("West Africa", ""),
        ("East Africa overview", ""),
        ("East Africa local districts, villages, or places", "Include local place names where sources allow."),
        (f"{country}-level historical background", "Include local place names where sources allow."),
        (
            f"past-to-present situation in {case_study}",
            f"Conclude that it is upon this background that the study examines {topic} in {case_study}, {country}.",
        ),
    ]
    for focus, note in background_focuses:
        background_parts.append(
            {
                "focus": focus,
                "note": note,
                "min_citations": 3,
                "max_citations": 5,
            }
        )

    await generate_section_parts(
        "1.1 Background of the Study",
        background_parts,
        max_tokens=650,
    )

    problem_papers, problem_ctx, _ = _section_context(_extract_keywords("problem statement", topic), count=30)
    await generate_section(
        "1.2 Problem Statement",
        _problem_prompt(topic, country, case_study, problem_ctx, objectives, conceptual_vars),
        problem_papers,
        min_citations=2,
        max_citations=4,
        max_tokens=1400,
    )

    theory_papers, theory_ctx, _ = _section_context(
        _extract_keywords("theoretical framework theory model", topic),
        count=30,
        require_theory=True,
    )
    theory_candidate_list = _extract_theory_candidates(theory_papers)
    theory_candidates = _format_theory_candidates(theory_candidate_list)
    forced_theory = theory_candidate_list[0] if theory_candidate_list else None
    await generate_post_section(
        "1.12 Theoretical Framework of the Study",
        _theoretical_framework_prompt(topic, country, case_study, theory_ctx, theory_candidates, forced_theory),
        theory_papers,
        min_citations=3,
        max_citations=5,
        max_tokens=2000,
    )

    conceptual_papers, conceptual_ctx, _ = _section_context(
        _extract_keywords("conceptual framework variables", topic, case_study),
        count=25,
    )
    await generate_post_section(
        "1.13 Conceptual Framework",
        _conceptual_framework_prompt(topic, country, case_study, conceptual_ctx),
        conceptual_papers,
        min_citations=2,
        max_citations=4,
        max_tokens=1600,
    )

    definitions_papers, definitions_ctx, _ = _section_context(
        _extract_keywords("definitions key terms", topic, case_study),
        count=20,
    )
    await generate_post_section(
        "1.15 Definition of Key Terms",
        _definitions_prompt(topic, country, case_study, definitions_ctx),
        definitions_papers,
        min_citations=1,
        max_citations=2,
        max_tokens=1400,
    )

    await generate_post_section(
        "1.16 Organization of the Study",
        _organisation_prompt(topic, country, case_study),
        allowed_papers=[],
        min_citations=0,
        max_citations=0,
        max_tokens=900,
    )

    references = _build_references_section(buffer, post_buffer, papers)
    if references:
        post_buffer = f"{post_buffer}## **References for Chapter One**\n\n{references}\n"
        file_path.write_text(_compose_text(buffer, tail, post_buffer), encoding="utf-8")
        await events.file_updated(job_id, str(file_path), session_id=session_id)

    if config_id:
        status_row = update_good_status(config_id, {"chapter1_done": True})
        status_meta = (status_row or {}).get("extra_json") or {}
        status = status_meta.get("status") or {}
        if status.get("objectives_done") and status.get("research_done") and not status.get("complete_sent"):
            update_good_status(config_id, {"complete_sent": True})
            await events.stage_completed(job_id, "complete", {"flow": "good"}, session_id=session_id)

    await events.log(job_id, f"✅ /good Chapter One saved: {file_path.name}", session_id=session_id)
    await events.stage_completed(job_id, "good_chapter_one", {"file": file_path.name}, session_id=session_id)

    try:
        from services.good_proposal_combiner import maybe_run_good_proposal_combiner

        await maybe_run_good_proposal_combiner(job_id, workspace_id, session_id, config_id)
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good proposal combiner failed: {exc}", session_id=session_id)


def _conceptual_framework_prompt(topic: str, country: str, case_study: str, citation_context: str) -> str:
    return f"""Produce a conceptual framework section for the study about {topic} in {case_study}, {country}. You MUST include the variable lists even if citations are limited.

First, list the variables using bullet points only: list 10 Independent Variables, 5 Dependent Variables, and 4 Intervening Variables. Use the labels "Independent Variables", "Dependent Variables", and "Intervening Variables" as plain lines, then list the variables as bullet points underneath each label. Do not include citations in the variable lists. Do not draw ASCII diagrams. After the lists, write "Figure 1.1: Conceptual Framework" on its own line, then "Designed and Molded by Researcher (2026)" on its own line.

Then write two to three detailed paragraphs discussing how the independent, dependent, and intervening variables relate to one another in the context of {topic} and the study objectives, with in-text citations. Use UK English, academic tone, and avoid "we". Include 2–4 citations per paragraph where evidence allows. Use ONLY sources from the CITATION CONTEXT below. If evidence is limited, note that in ONE sentence within the discussion but do not stop after that.

    CITATION CONTEXT:
{citation_context}
"""


def _format_conceptual_framework_list(text: str) -> str:
    if not text:
        return text
    labels = {
        "independent variables",
        "dependent variables",
        "intervening variables",
    }
    lines = text.splitlines()
    new_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            new_lines.append("")
            continue
        lower = stripped.lower().rstrip(":")
        if lower in labels:
            in_list = True
            cleaned = re.sub(r"\s*\([^)]*\)", "", stripped).rstrip(":").strip()
            new_lines.append(cleaned)
            continue
        if in_list:
            if re.match(r"(?i)^figure\s+1\.1", stripped) or re.match(r"(?i)^designed and molded", stripped):
                in_list = False
                new_lines.append(stripped)
                continue
            cleaned = re.sub(r"\s*\([^)]*\d{4}[^)]*\)", "", stripped)
            cleaned = re.sub(r"^[-*\d\.\)]\s*", "", cleaned).strip()
            if cleaned:
                new_lines.append(f"- {cleaned}")
            continue
        new_lines.append(line)
    return "\n".join(new_lines).strip()


def _definitions_prompt(topic: str, country: str, case_study: str, citation_context: str) -> str:
    return f"""Write definitions of key terms for the study about {topic} in {case_study}, {country}. Present each term on its own line in the format "**Term**: definition." Do not use bullets or numbering. Use UK English and an academic tone; avoid "we". Define 7–10 key terms. ALWAYS provide the definitions even if citations are limited; only cite when evidence exists in the sources.

CITATION CONTEXT:
{citation_context}
"""


def _organisation_prompt(topic: str, country: str, case_study: str) -> str:
    return f"""Write the organisation of the study in five chapters for {topic} in {case_study}, {country}. Use five separate lines (no bullets, no numbering), one per chapter, in the format "Chapter One ...", "Chapter Two ...", etc. Use UK English and avoid "we".
"""


def _format_key_terms_lines(text: str) -> str:
    if not text:
        return text
    if "\n" not in text:
        text = re.sub(r"(?<!^)(\*\*[^*]+\*\*:)", r"\n\1", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)
