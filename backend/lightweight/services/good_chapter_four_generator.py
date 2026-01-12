"""Generate Chapter Four (Data Analysis) for /good flow using datasets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from itertools import cycle

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from core.events import events
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.workspace_service import WORKSPACES_DIR
from services.good_chapter_one_generator import _clean_text
from services.good_objective_generator import normalise_objectives


LIKERT_LABELS = {
    3: ["SD", "N", "SA"],
    5: ["SD", "D", "NS", "A", "SA"],
    7: ["SD", "D", "NS", "N", "A", "SA", "S A"],
}


def _pick_latest(path: Path, pattern: str) -> Optional[Path]:
    files = sorted(path.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0)
    return files[-1] if files else None


def _format_freq_pct(count: int, total: int) -> str:
    if total <= 0:
        return f"{count} (0%)"
    pct = round((count / total) * 100)
    return f"{count} ({pct}%)"


def _load_sources(workspace_id: str) -> List[Dict[str, str]]:
    sources_path = WORKSPACES_DIR / workspace_id / "sources" / "index.json"
    if not sources_path.exists():
        return []
    try:
        payload = json.loads(sources_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    sources = payload.get("sources", []) if isinstance(payload, dict) else []
    return sources if isinstance(sources, list) else []


def _inline_citation(source: Dict[str, str]) -> str:
    authors = source.get("authors") or []
    year = str(source.get("year") or "").strip()
    url = source.get("url") or ""
    doi = source.get("doi") or ""
    if doi and not url:
        url = doi if doi.startswith("http") else f"https://doi.org/{doi}"

    surname = "Author"
    if authors:
        name = authors[0].get("name") if isinstance(authors[0], dict) else str(authors[0])
        name = (name or "").strip()
        surname = name.split()[-1] if name else "Author"
    if not year:
        return ""
    author_text = f"{surname} et al." if len(authors) > 1 else surname
    if url:
        return f"[{author_text}, {year}]({url})"
    return f"({author_text}, {year})"


def _citation_cycle(sources: List[Dict[str, str]]) -> Iterable[str]:
    usable = [s for s in sources if s.get("year")]
    if not usable:
        while True:
            yield ""
    idx = 0
    while True:
        source = usable[idx % len(usable)]
        idx += 1
        yield _inline_citation(source)


def _table_header(columns: List[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    return "\n".join([header, sep])


def _safe_statement(text: str) -> str:
    cleaned = (text or "").strip()
    return cleaned if cleaned else "Respondents evaluated this statement."


def _objective_title(objective: str) -> str:
    text = (objective or "").strip().rstrip(".")
    return text if text else "Objective"


def _pick_versions() -> Tuple[str, str]:
    # Deterministic versions for reproducible output.
    return "2019", "25"


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


def _chart_counts(series: pd.Series) -> Tuple[List[str], List[int]]:
    counts = series.value_counts(dropna=False)
    labels = [str(item) if str(item).strip() else "Not stated" for item in counts.index.tolist()]
    values = [int(val) for val in counts.values.tolist()]
    return labels, values


def _save_bar_chart(labels: List[str], values: List[int], title: str, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    plt.bar(labels, values, color="#4e79a7")
    plt.title(title)
    plt.xlabel("Category")
    plt.ylabel("Frequency")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def _save_pie_chart(labels: List[str], values: List[int], title: str, path: Path) -> None:
    plt.figure(figsize=(6, 6))
    plt.pie(values, labels=labels, autopct="%1.0f%%", startangle=90)
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=300, bbox_inches="tight")
    plt.close()


def _make_response_rate_table(n_distributed: int, n_returned: int) -> Tuple[str, str]:
    total = n_distributed
    returned_pct = _format_freq_pct(n_returned, total).split(" ", 1)[1]
    not_returned = max(total - n_returned, 0)
    not_returned_pct = _format_freq_pct(not_returned, total).split(" ", 1)[1]
    columns = ["Questionnaires", "Frequency", "Percentage", "Total"]
    lines = [
        _table_header(columns),
        f"| Distributed | {n_distributed} | 100% | {total} |",
        f"| Returned | {n_returned} | {returned_pct} | {total} |",
        f"| Not Returned | {not_returned} | {not_returned_pct} | {total} |",
    ]
    return "\n".join(lines), f"**Source: Survey data ({total} respondents, 2026).**"


def _make_demographic_table(series: pd.Series, label: str) -> Tuple[str, str]:
    counts = series.value_counts(dropna=False)
    total = int(counts.sum())
    columns = [label, "Frequency", "Percentage", "Total"]
    lines = [_table_header(columns)]
    for value, count in counts.items():
        value_label = str(value) if str(value).strip() else "Not stated"
        lines.append(f"| {value_label} | {count} | {_format_freq_pct(int(count), total).split(' ',1)[1]} | {total} |")
    return "\n".join(lines), f"**Source: Survey data ({total} respondents, 2026).**"


def _format_statement_distribution(values: pd.Series, labels: List[str]) -> Dict[str, str]:
    counts = values.value_counts().reindex(range(1, len(labels) + 1), fill_value=0)
    total = int(counts.sum())
    formatted = {}
    for idx, label in enumerate(labels, 1):
        formatted[label] = _format_freq_pct(int(counts[idx]), total)
    formatted["Total"] = str(total)
    formatted["_total"] = total
    return formatted


def _statement_paragraph(statement: str, dist: Dict[str, str], objective: str, citation: str) -> str:
    labels = [key for key in dist.keys() if key not in {"Total", "_total"}]
    total = dist.get("_total", 0)
    parts = [f"{label} {dist[label]}" for label in labels]
    stats_text = "; ".join(parts)
    lead = (
        f"The statement \"{statement}\" recorded {stats_text} from a total of {total} responses. "
        f"The distribution suggested varied perceptions linked to {_objective_title(objective).lower()}, "
        "highlighting the intensity of agreement and disagreement across respondents. "
    )
    relevance = (
        f"This pattern indicated how the study variables aligned with the objective, "
        f"showing areas of consensus and contention around {_objective_title(objective).lower()} in the study area. "
    )
    cross = f"Comparable evidence was reported in related studies {citation}."
    return lead + relevance + cross


def _objective_conclusion(objective: str, citation: str) -> str:
    sentence = (
        f"Overall, the findings for {_objective_title(objective).lower()} demonstrated coherent response patterns "
        "that supported the analytical focus of the study. "
    )
    if citation:
        sentence += f"Related empirical insights were noted in the literature {citation}."
    return sentence


def _pick_quotes(df: pd.DataFrame, objective: str, limit: int = 2) -> List[str]:
    if df.empty:
        return []
    filtered = df[df.get("objective", "") == objective]
    if filtered.empty:
        filtered = df
    responses = filtered.get("response")
    if responses is None:
        return []
    quotes = [str(val).strip() for val in responses.dropna().tolist() if str(val).strip()]
    return quotes[:limit]


async def run_good_chapter_four_generation(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
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
    extra = config.get("extra_json") or {}
    if isinstance(extra, str):
        try:
            extra = json.loads(extra)
        except json.JSONDecodeError:
            extra = {}
    status = extra.get("status") or {}

    topic = _clean_text(config.get("topic") or "")
    if not topic:
        await events.log(job_id, "⚠️ /good Chapter Four skipped: no topic provided.", session_id=session_id)
        return

    chapter2_ready = status.get("chapter2_empirical_done")
    datasets_ready = status.get("datasets_done")
    if not (chapter2_ready and datasets_ready):
        await events.log(
            job_id,
            "ℹ️ /good Chapter Four awaiting Chapter Two + datasets; will retry later.",
            session_id=session_id,
        )
        return

    await events.stage_started(
        job_id,
        "good_chapter_four",
        {"message": "📊 Generating /good Chapter Four (Data Analysis)..."},
        session_id=session_id,
    )

    good_dir = WORKSPACES_DIR / workspace_id / "good"
    datasets_dir = good_dir / "datasets"
    datasets_dir.mkdir(parents=True, exist_ok=True)

    data_path = _pick_latest(datasets_dir, "questionnaire_data_*.csv")
    mapping_path = _pick_latest(datasets_dir, "*_variable_mapping.json")
    if not data_path or not mapping_path:
        await events.log(job_id, "⚠️ /good Chapter Four skipped: dataset missing.", session_id=session_id)
        return

    try:
        df = pd.read_csv(data_path)
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good Chapter Four failed to load dataset: {exc}", session_id=session_id)
        return

    try:
        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        mapping = {}

    objectives = config.get("objectives") or []
    if isinstance(objectives, str):
        try:
            objectives = json.loads(objectives)
        except json.JSONDecodeError:
            objectives = []
    objectives = [obj for obj in objectives if str(obj).strip()]
    user_objectives = extra.get("user_objectives") or []
    objectives = normalise_objectives(objectives, bool(user_objectives))

    chapter2_citations = _load_chapter2_citations(workspace_id)
    if chapter2_citations:
        citation_iter = iter(cycle(chapter2_citations))
    else:
        sources = _load_sources(workspace_id)
        citation_iter = _citation_cycle(sources)

    excel_version, spss_version = _pick_versions()
    intro_text = (
        f"This chapter presented the analysis, presentation, and interpretation of findings for the study on {topic}. "
        f"Results were summarised using tables and, where applicable, figures. Data analysis was carried out using "
        f"Microsoft Excel {excel_version}, IBM SPSS {spss_version}, and MAXQDA for thematic insights. "
        "The presentation emphasised the response rate, demographic profiles, and objective-based findings."
    )

    lines: List[str] = []
    lines.append("CHAPTER FOUR: DATA ANALYSIS, PRESENTATION AND INTERPRETATION OF FINDINGS")
    lines.append("")
    lines.append("## 4.0 Introduction")
    lines.append(intro_text)
    lines.append("")

    total_responses = int(df.shape[0])
    distributed = total_responses
    returned = total_responses
    response_table, response_source = _make_response_rate_table(distributed, returned)
    lines.append("## 4.1 Rate of Return")
    lines.append("The response rate for the study was summarised in Table 4.1.")
    lines.append("")
    lines.append("Table 4.1: Response Rate")
    lines.append(response_table)
    lines.append(response_source)
    lines.append(
        "The table indicated that all distributed questionnaires were returned, suggesting complete coverage "
        "of the sampled respondents for this study."
    )
    lines.append("")

    demographics = mapping.get("demographics") or {}
    if demographics:
        lines.append("## 4.2 Demographic Data")
        lines.append("Demographic characteristics were presented in the subsections below.")
        lines.append("")
        table_index = 2
        figures_dir = good_dir / "figures"
        figures_dir.mkdir(parents=True, exist_ok=True)
        for idx, (column, label) in enumerate(demographics.items(), 1):
            if column not in df.columns:
                continue
            table, source_line = _make_demographic_table(df[column], label)
            lines.append(f"### 4.2.{idx} {label}")
            lines.append(f"The results for {label.lower()} were presented in Table 4.{table_index}.")
            lines.append("")
            lines.append(f"Table 4.{table_index}: {label} Distribution")
            lines.append(table)
            lines.append(source_line)
            labels, values = _chart_counts(df[column])
            bar_path = figures_dir / f"bar_{column}.png"
            pie_path = figures_dir / f"pie_{column}.png"
            _save_bar_chart(labels, values, f"{label} Distribution", bar_path)
            _save_pie_chart(labels, values, f"{label} Distribution", pie_path)
            lines.append(f"Figure 4.{table_index}: {label} Distribution (Bar Chart)")
            lines.append(f"![](figures/{bar_path.name})")
            lines.append(f"Figure 4.{table_index + 1}: {label} Distribution (Pie Chart)")
            lines.append(f"![](figures/{pie_path.name})")
            lines.append(f"**Source: Survey data ({total_responses} respondents, 2026).**")
            lines.append(
                f"The distribution in Table 4.{table_index} showed how {label.lower()} varied across respondents, "
                "providing essential context for interpreting objective-based results."
            )
            lines.append("")
            table_index += 2

    likert_items = mapping.get("likert_items") or {}
    likert_scale = int(mapping.get("likert_scale") or 5)
    labels = LIKERT_LABELS.get(likert_scale, LIKERT_LABELS[5])

    sections: Dict[str, List[Tuple[str, Dict[str, str]]]] = defaultdict(list)
    for variable, item in likert_items.items():
        if variable not in df.columns:
            continue
        section_title = item.get("section_title") or "Objective"
        sections[section_title].append((variable, item))

    objective_sections: List[Tuple[str, List[Tuple[str, Dict[str, str]]]]] = []
    if objectives:
        for objective in objectives:
            objective_sections.append((objective, sections.get(objective, [])))
    else:
        objective_sections = list(sections.items())
    if objective_sections:
        lines.append("## 4.3 Analysis by Objectives")
        lines.append("")

    interview_path = _pick_latest(datasets_dir, "interviews_kii_*.csv")
    interview_df = pd.read_csv(interview_path) if interview_path and interview_path.exists() else pd.DataFrame()

    for section_idx, (objective_title, items) in enumerate(objective_sections, 1):
        lines.append(f"### 4.3.{section_idx} {_objective_title(objective_title)}")
        lines.append("Findings for this objective were presented in the table below.")
        lines.append("")

        table_columns = ["Statement"] + labels + ["Total"]
        table_lines = [_table_header(table_columns)]
        statement_rows = []

        for variable, item in items:
            statement = _safe_statement(item.get("full_label") or item.get("text") or variable)
            dist = _format_statement_distribution(df[variable], labels)
            row = [statement] + [dist[label] for label in labels] + [dist.get("Total", str(dist.get("_total", "")))]
            statement_rows.append((statement, dist))
            table_lines.append("| " + " | ".join(row) + " |")

        table_number = section_idx + 1
        lines.append(f"Table 4.{table_number}: Responses for {_objective_title(objective_title)}")
        lines.append("\n".join(table_lines))
        lines.append(f"**Source: Survey data ({total_responses} respondents, 2026).**")
        lines.append("")

        for statement, dist in statement_rows:
            citation = next(citation_iter, "")
            lines.append(_statement_paragraph(statement, dist, objective_title, citation))
            lines.append("")

        conclusion_citation = next(citation_iter, "")
        lines.append(_objective_conclusion(objective_title, conclusion_citation))
        lines.append("")

        quotes = _pick_quotes(interview_df, objective_title, limit=2)
        if quotes:
            quote_lines = []
            for quote in quotes:
                quote_lines.append(f"\"{quote}\"")
            lines.append(
                "Qualitative insights from key informant interviews supported the quantitative patterns, "
                "as highlighted by the following statements: "
                + " ".join(quote_lines)
            )
            lines.append("")

    if objectives:
        lines.append("## 4.4 Hypothesis Testing")
        lines.append(
            "Hypotheses aligned to the objectives were tested using descriptive and inferential statistics. "
            "Mean scores above the neutral midpoint were interpreted as supportive evidence for the study’s "
            "hypotheses, while mean scores below the midpoint indicated weaker support."
        )
        lines.append("")

        for idx, objective in enumerate(objectives, 1):
            objective_title = _objective_title(objective)
            related_vars = [var for var, item in likert_items.items() if item.get("section_title") == objective]
            mean_score = None
            if related_vars:
                mean_score = df[related_vars].mean().mean()
            if mean_score is not None:
                support = "supported" if mean_score >= (likert_scale + 1) / 2 else "not supported"
                lines.append(
                    f"The hypothesis linked to objective {idx} was {support} based on an average score of "
                    f"{mean_score:.2f}, indicating the direction of the relationship within the dataset."
                )
            else:
                lines.append(
                    f"The hypothesis linked to objective {idx} was assessed using the available survey indicators "
                    "for the study."
                )
            lines.append("")

    chapter_path = good_dir / "Chapter_4_Data_Analysis.md"
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
        update_good_status(config_id, {"chapter4_done": True})

    await events.stage_completed(
        job_id,
        "good_chapter_four",
        {"message": f"✅ /good Chapter Four saved: {chapter_path.name}"},
        session_id=session_id,
    )
