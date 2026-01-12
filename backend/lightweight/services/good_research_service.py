"""Background research and source digestion for /good flow."""

from __future__ import annotations

import asyncio
import re
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, List, Optional

import httpx
from core.config import settings
from core.events import events
from services.academic_search import academic_search_service
from services.good_flow_db import (
    get_good_config_by_id,
    get_latest_good_config,
    update_good_research_metadata,
    update_good_status,
)
from services.good_objective_generator import (
    format_location,
    normalise_objectives,
    strip_location_from_topic,
    fallback_objectives,
)
from services.sources_service import sources_service


_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "into", "over", "under",
    "about", "above", "below", "between", "within", "across", "among", "through",
    "are", "was", "were", "been", "being", "has", "have", "had", "will", "shall",
    "should", "could", "would", "may", "might", "must", "can", "to", "of", "in",
    "on", "at", "by", "an", "as", "is", "it", "their", "there", "these", "those",
    "its", "they", "them", "we", "our", "you", "your", "his", "her", "hers",
    "study", "research", "analysis", "effects", "effect", "impact", "role",
    "relationship", "association", "case", "case study",
}


def _extract_year(date_str: str) -> Optional[int]:
    if not date_str:
        return None
    match = re.search(r"(20\d{2})", date_str)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            return None
    return None


def _domain_author(url: str) -> str:
    if not url:
        return ""
    host = urlparse(url).netloc.lower()
    host = host.replace("www.", "")
    if not host:
        return ""
    base = host.split(".")[0]
    if not base:
        return ""
    return base.replace("-", " ").title()


async def _tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    if not settings.TAVILY_API_KEY:
        return []
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                headers={"Content-Type": "application/json"},
                json={
                    "api_key": settings.TAVILY_API_KEY,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
            return data.get("results") or []
    except Exception as exc:
        print(f"⚠️ Tavily search failed: {exc}")
        return []


async def _firecrawl_scrape(url: str) -> str:
    if not settings.FIRECRAWL_API_KEY or not url:
        return ""
    try:
        async with httpx.AsyncClient(timeout=40.0) as client:
            resp = await client.post(
                f"{settings.FIRECRAWL_URL}/v1/scrape",
                headers={
                    "Authorization": f"Bearer {settings.FIRECRAWL_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={"url": url, "formats": ["markdown"]},
            )
            if resp.status_code != 200:
                return ""
            payload = resp.json()
            return (payload.get("data", {}) or {}).get("markdown", "") or ""
    except Exception as exc:
        print(f"⚠️ Firecrawl scrape failed: {exc}")
        return ""


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_conceptual_variables(topic: str) -> Dict[str, str]:
    """Extract simple independent/dependent variables from the topic."""
    topic = _clean_text(topic)
    if not topic:
        return {}

    patterns = [
        r"(?:impact|effect|influence|role|relationship|association)\s+of\s+(.+?)\s+on\s+(.+)",
        r"(?:relationship|association|link)\s+between\s+(.+?)\s+and\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, topic, re.IGNORECASE)
        if match:
            indep = _clean_text(match.group(1))
            dep = _clean_text(match.group(2))
            return {"independent": indep, "dependent": dep}

    return {}


def _tokenise(text: str) -> List[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z-']+", text.lower())
    return [t for t in tokens if len(t) > 3 and t not in _STOPWORDS]


def extract_keywords(topic: str, objectives: List[str], case_study: str, country: str, variables: Dict[str, str]) -> List[str]:
    combined = " ".join(
        filter(
            None,
            [
                topic,
                case_study,
                country,
                variables.get("independent", ""),
                variables.get("dependent", ""),
                " ".join(objectives or []),
            ],
        )
    )
    tokens = _tokenise(combined)
    return sorted(set(tokens))[:40]


def _objective_to_query(obj: str) -> str:
    cleaned = re.sub(r"^[Tt]o\s+", "", _clean_text(obj))
    cleaned = re.sub(r"[.]+$", "", cleaned)
    words = cleaned.split()
    if len(words) > 12:
        cleaned = " ".join(words[:12])
    return cleaned


def build_search_queries(
    topic: str,
    objectives: List[str],
    case_study: str,
    country: str,
    variables: Dict[str, str],
) -> List[str]:
    queries: List[str] = []

    def add(query: Optional[str]) -> None:
        if not query:
            return
        normalized = _clean_text(query)
        if not normalized:
            return
        if normalized not in queries:
            queries.append(normalized)

    add(topic)
    add(f"{topic} {country}")
    add(f"{topic} {case_study}")
    add(f"{topic} systematic review")
    add(f"{topic} empirical study")
    add(f"{topic} challenges")
    add(f"{topic} solutions")

    indep = variables.get("independent")
    dep = variables.get("dependent")
    if indep and dep:
        add(f"{indep} {dep}")
    if indep:
        add(f"{indep} {country}")
    if dep:
        add(f"{dep} {country}")

    for obj in objectives or []:
        add(_objective_to_query(obj))

    return queries[:10]


def build_objective_query_map(objectives: List[str]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for obj in objectives or []:
        query = _objective_to_query(obj)
        if query:
            mapping[obj] = query
    return mapping


def is_relevant_paper(paper: Dict, keywords: List[str]) -> bool:
    """Check abstract/title for keyword overlap before accepting the paper."""
    if not keywords:
        return True
    abstract = (paper.get("abstract") or "").lower()
    title = (paper.get("title") or "").lower()

    if abstract:
        hits = sum(1 for kw in keywords if kw in abstract)
        if hits >= 2:
            return True
    if title:
        hits = sum(1 for kw in keywords if kw in title)
        return hits >= 1
    return True


async def run_good_background_research(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
    await events.stage_started(
        job_id,
        "good_research",
        {"message": "🔎 Running /good background research..."},
        session_id=session_id,
    )
    """Run background academic search for /good flow and save sources."""
    config_id_raw = request.get("config_id")
    config_id = None
    if config_id_raw is not None:
        try:
            config_id = int(config_id_raw)
        except (TypeError, ValueError):
            config_id = None
    topic = (request.get("topic") or "").strip()
    case_study = (request.get("case_study") or "").strip()
    country = (request.get("country") or "").strip()

    stored = get_good_config_by_id(config_id) if config_id else None
    if not stored and workspace_id:
        stored = get_latest_good_config(workspace_id)
        if stored:
            config_id = stored.get("id")
    if stored:
        topic = topic or (stored.get("topic") or "")
        case_study = case_study or (stored.get("case_study") or "")
        country = country or (stored.get("country") or "")

    if not topic:
        await events.log(job_id, "⚠️ /good research skipped: no topic provided.", session_id=session_id)
        if config_id:
            status_row = update_good_status(config_id, {"research_done": True})
            status_meta = (status_row or {}).get("extra_json") or {}
            status = status_meta.get("status") or {}
            if status.get("objectives_done") and status.get("chapter1_done") and not status.get("complete_sent"):
                update_good_status(config_id, {"complete_sent": True})
                await events.stage_completed(job_id, "complete", {"flow": "good"}, session_id=session_id)
        return

    objectives = []
    extra = stored.get("extra_json") if stored else {}
    if isinstance(extra, str):
        try:
            import json
            extra = json.loads(extra)
        except Exception:
            extra = {}
    if stored:
        objectives = stored.get("objectives") or []
    generated = extra.get("generated_objectives") or []
    if not objectives and generated:
        objectives = generated
    if not objectives and extra.get("user_objectives"):
        objectives = extra.get("user_objectives") or []

    if not objectives:
        await events.log(job_id, "ℹ️ /good research awaiting objectives; retrying shortly...", session_id=session_id)
        for _ in range(3):
            await asyncio.sleep(1.5)
            stored_retry = get_good_config_by_id(config_id) if config_id else None
            if stored_retry and stored_retry.get("objectives"):
                objectives = stored_retry.get("objectives") or []
                break
        if not objectives:
            objectives = fallback_objectives(topic, case_study, country)

    objectives = normalise_objectives(objectives, bool(extra.get("user_objectives")))

    location = format_location(case_study, country)
    topic_clean = strip_location_from_topic(topic, location) or topic

    variables = extract_conceptual_variables(topic_clean)
    keywords = extract_keywords(topic_clean, objectives, case_study, country, variables)
    queries = build_search_queries(topic_clean, objectives, case_study, country, variables)
    objective_query_map = build_objective_query_map(objectives)
    query_to_objectives: Dict[str, List[str]] = {}
    for obj, query in objective_query_map.items():
        query_to_objectives.setdefault(query, []).append(obj)
    objective_sources: Dict[str, List[str]] = {obj: [] for obj in objective_query_map}

    update_good_research_metadata(
        config_id,
        {
            "conceptual_variables": variables,
            "research_keywords": keywords,
            "research_queries": queries,
            "objective_queries": objective_query_map,
        }
    )

    await events.log(job_id, "🔍 /good background research started...", session_id=session_id)
    total_added = 0
    year_from = stored.get("literature_year_start") if stored else request.get("literature_year_start")
    year_to = stored.get("literature_year_end") if stored else request.get("literature_year_end")

    for idx, query in enumerate(queries, 1):
        await events.log(job_id, f"🔎 /good search {idx}/{len(queries)}: {query}", session_id=session_id)
        papers = await academic_search_service.search_academic_papers(
            query=query,
            max_results=15,
            year_from=year_from,
            year_to=year_to,
            job_id=job_id,
            workspace_id=workspace_id
        )
        if not papers:
            continue

        relevant = [p for p in papers if is_relevant_paper(p, keywords)]

        for paper in relevant:
            open_access_pdf = paper.get("openAccessPdf") or {}
            external_ids = paper.get("externalIds") or {}
            source_data = {
                "title": paper.get("title", "Unknown"),
                "authors": paper.get("authors", []),
                "year": paper.get("year", datetime.now().year),
                "type": "paper",
                "doi": external_ids.get("DOI", ""),
                "url": paper.get("url", ""),
                "abstract": paper.get("abstract", ""),
                "venue": paper.get("venue", ""),
                "citation_count": paper.get("citationCount", 0),
                "pdf_url": open_access_pdf.get("url", ""),
            }
            added = await sources_service.add_source(
                workspace_id=workspace_id,
                source_data=source_data,
                download_pdf=False,
                extract_text=False
            )
            total_added += 1
            if query in query_to_objectives and added:
                for obj in query_to_objectives[query]:
                    if obj not in objective_sources:
                        objective_sources[obj] = []
                    source_id = added.get("id")
                    if source_id and source_id not in objective_sources[obj]:
                        objective_sources[obj].append(source_id)

        await events.publish(
            job_id,
            "sources_updated",
            {"count": len(relevant), "scope": f"good_search_{idx}"},
            session_id=session_id
        )

    # Web research for current context and statistics
    web_added = 0
    if settings.TAVILY_API_KEY:
        web_queries = queries[:4]
        await events.log(job_id, "🌐 /good web research started (Tavily + Firecrawl)...", session_id=session_id)
        for idx, query in enumerate(web_queries, 1):
            await events.log(job_id, f"🌐 /good web search {idx}/{len(web_queries)}: {query}", session_id=session_id)
            results = await _tavily_search(query, max_results=5)
            if not results:
                continue
            for item in results:
                url = item.get("url") or ""
                if not url:
                    continue
                title = _clean_text(item.get("title") or url)
                published_date = item.get("published_date") or item.get("date") or ""
                year = _extract_year(published_date)
                if not year:
                    continue
                author = item.get("author") or item.get("source") or _domain_author(url)
                if not author:
                    continue
                snippet = _clean_text(item.get("content") or item.get("snippet") or "")
                abstract_text = snippet
                if settings.FIRECRAWL_API_KEY:
                    scraped = await _firecrawl_scrape(url)
                    if scraped:
                        abstract_text = _clean_text(scraped[:1200])
                await sources_service.add_source(
                    workspace_id=workspace_id,
                    source_data={
                        "title": title,
                        "authors": [{"name": author}],
                        "year": year,
                        "type": "web",
                        "url": url,
                        "abstract": abstract_text,
                        "venue": _domain_author(url),
                    },
                    download_pdf=False,
                    extract_text=False,
                )
                web_added += 1
            await events.publish(
                job_id,
                "sources_updated",
                {"count": len(results), "scope": f"good_web_{idx}"},
                session_id=session_id
            )
    else:
        await events.log(job_id, "⚠️ /good web research skipped: TAVILY_API_KEY not configured.", session_id=session_id)

    update_good_research_metadata(
        config_id,
        {
            "sources_added": total_added,
            "web_sources_added": web_added,
            "last_research_at": datetime.now().isoformat(),
            "objective_sources": objective_sources,
        }
    )

    await events.log(
        job_id,
        f"✅ /good background research complete: {total_added} academic + {web_added} web sources saved.",
        session_id=session_id
    )
    await events.stage_completed(job_id, "good_research", {"count": total_added}, session_id=session_id)

    if config_id:
        try:
            from services.good_chapter_two_generator import run_good_chapter_two_theoretical_reviews
            from services.good_chapter_three_generator import run_good_chapter_three_generation
            asyncio.create_task(
                run_good_chapter_two_theoretical_reviews(
                    job_id,
                    workspace_id,
                    session_id,
                    {
                        "config_id": config_id,
                        "topic": topic,
                        "case_study": case_study,
                        "country": country,
                    },
                )
            )
            asyncio.create_task(
                run_good_chapter_three_generation(
                    job_id,
                    workspace_id,
                    session_id,
                    {
                        "config_id": config_id,
                        "topic": topic,
                        "case_study": case_study,
                        "country": country,
                        "study_type": study_type,
                        "population": population,
                    },
                )
            )
        except Exception as exc:
            await events.log(job_id, f"⚠️ Failed to start /good Chapter Two theoretical reviews: {exc}", session_id=session_id)
        status_row = update_good_status(config_id, {"research_done": True})
        status_meta = (status_row or {}).get("extra_json") or {}
        status = status_meta.get("status") or {}
        if (
            status.get("objectives_done")
            and status.get("chapter1_done")
            and not status.get("complete_sent")
        ):
            update_good_status(config_id, {"complete_sent": True})
            await events.stage_completed(job_id, "complete", {"flow": "good"}, session_id=session_id)
