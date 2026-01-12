"""Generate study tools (questionnaire, KII, FGD) for /good flow."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from core.events import events
from services.deepseek_direct import deepseek_direct
from services.good_flow_db import get_good_config_by_id, get_latest_good_config, update_good_status
from services.workspace_service import WORKSPACES_DIR
from services.data_collection_worker import generate_research_dataset

from services.good_chapter_one_generator import _clean_text
from services.good_objective_generator import fallback_objectives, normalise_objectives


def _normalise_study_type(study_type: str) -> str:
    st = (study_type or "").lower()
    if "qual" in st:
        return "qualitative"
    if "mixed" in st:
        return "mixed"
    return "quantitative"


def _safe_json_list(text: str, expected: int) -> List[str]:
    if not text:
        return []
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    cleaned = [str(item).strip() for item in data if str(item).strip()]
    if expected and len(cleaned) >= expected:
        return cleaned[:expected]
    return cleaned


async def _generate_statements(objective: str, count: int = 10) -> List[str]:
    prompt = f"""Generate {count} concise Likert-scale statements aligned to this study objective:
{objective}

Return ONLY a JSON array of {count} strings. Keep statements short, specific, and suitable for a 5-point Likert scale (SD, D, NS, A, SA)."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=600,
        stream=False,
    )
    statements = _safe_json_list(response or "", count)
    if len(statements) < count:
        base = objective.rstrip(".")
        statements = [
            f"Respondents report aspects of {base.lower()} relevant to the study."
            for _ in range(count)
        ]
    return statements


async def _generate_open_questions(objective: str, count: int = 2) -> List[str]:
    prompt = f"""Generate {count} concise open-ended questions aligned to this study objective:
{objective}

Return ONLY a JSON array of {count} strings. Keep each question short and direct."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=300,
        stream=False,
    )
    questions = _safe_json_list(response or "", count)
    if len(questions) < count:
        base = objective.rstrip(".")
        questions = [f"What further information can be provided about {base.lower()}?"] * count
    return questions


async def _generate_kii_questions(objectives: List[str], count: int = 8) -> List[str]:
    objectives_text = "; ".join(obj.rstrip(".") for obj in objectives)
    prompt = f"""Generate {count} key informant interview questions aligned to these objectives:
{objectives_text}

Return ONLY a JSON array of {count} strings. Questions should be open-ended and suitable for expert informants."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=600,
        stream=False,
    )
    questions = _safe_json_list(response or "", count)
    if len(questions) < count:
        questions = [f"Please describe your experience related to {objectives_text.lower()}."]
        questions = questions * count
    return questions[:count]


async def _generate_fgd_prompts(objectives: List[str], count: int = 6) -> List[str]:
    objectives_text = "; ".join(obj.rstrip(".") for obj in objectives)
    prompt = f"""Generate {count} focus group discussion prompts aligned to these objectives:
{objectives_text}

Return ONLY a JSON array of {count} strings. Prompts should encourage discussion among participants."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=500,
        stream=False,
    )
    prompts = _safe_json_list(response or "", count)
    if len(prompts) < count:
        prompts = [f"Discuss experiences and perceptions related to {objectives_text.lower()}."]
        prompts = prompts * count
    return prompts[:count]


async def _generate_observation_items(objectives: List[str], count: int = 8) -> List[str]:
    objectives_text = "; ".join(obj.rstrip(".") for obj in objectives)
    prompt = f"""Generate {count} observation checklist items aligned to these objectives:
{objectives_text}

Return ONLY a JSON array of {count} strings. Each item should be an observable indicator."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=400,
        stream=False,
    )
    items = _safe_json_list(response or "", count)
    if len(items) < count:
        items = [f"Observable indicators related to {objectives_text.lower()} are present."] * count
    return items[:count]


async def _generate_document_items(objectives: List[str], count: int = 8) -> List[str]:
    objectives_text = "; ".join(obj.rstrip(".") for obj in objectives)
    prompt = f"""Generate {count} document review checklist items aligned to these objectives:
{objectives_text}

Return ONLY a JSON array of {count} strings. Each item should indicate a document attribute to review."""
    response = await deepseek_direct.generate_content(
        prompt=prompt,
        system_prompt="You are a research assistant.",
        temperature=0.4,
        max_tokens=400,
        stream=False,
    )
    items = _safe_json_list(response or "", count)
    if len(items) < count:
        items = [f"Document evidence related to {objectives_text.lower()} is recorded."] * count
    return items[:count]


def _demographic_section() -> str:
    return "\n".join(
        [
            "SECTION A: DEMOGRAPHICS OF RESPONDENTS",
            "1. What is your gender?",
            "A. Male (   )",
            "B. Female (   )",
            "",
            "2. What is your age group?",
            "A. 18-24 (   )",
            "B. 25-34 (   )",
            "C. 35-44 (   )",
            "D. 45-54 (   )",
            "E. 55+ (   )",
            "",
            "3. What is your highest level of education?",
            "A. Primary (   )",
            "B. Secondary (   )",
            "C. Diploma/Certificate (   )",
            "D. Bachelor’s (   )",
            "E. Postgraduate (   )",
            "",
            "4. What is your marital status?",
            "A. Single (   )",
            "B. Married (   )",
            "C. Separated/divorced (   )",
            "D. Widowed (   )",
            "",
            "5. What is your current employment status?",
            "A. Employed (   )",
            "B. Self-employed (   )",
            "C. Unemployed (   )",
            "D. Student (   )",
            "",
            "6. How long have you lived/worked in the study area?",
            "A. Less than 1 year (   )",
            "B. 1-3 years (   )",
            "C. 4-6 years (   )",
            "D. 7-10 years (   )",
            "E. More than 10 years (   )",
            "",
            "7. What is your primary role/position?",
            "A. Community member (   )",
            "B. Local leader/official (   )",
            "C. Service provider (   )",
            "D. NGO/CSO staff (   )",
            "E. Other (specify) __________",
        ]
    )


def _likert_table(statements: List[str]) -> str:
    header = "| No. | Statement | SD | D | NS | A | SA |"
    sep = "| --- | --- | --- | --- | --- | --- | --- |"
    rows = []
    for idx, stmt in enumerate(statements, 1):
        rows.append(f"| {idx} | {stmt} |  |  |  |  |  |")
    return "\n".join([header, sep] + rows)


def _open_question_block(questions: List[str]) -> str:
    lines: List[str] = []
    for idx, question in enumerate(questions, 1):
        lines.append(f"{idx}. {question}")
        lines.append("__________")
        lines.append("__________")
        lines.append("__________")
        lines.append("")
    return "\n".join(lines).strip()


async def run_good_study_tools_generation(job_id: str, workspace_id: str, session_id: str, request: dict) -> None:
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
    case_study = _clean_text(request.get("case_study") or config.get("case_study") or "")
    country = _clean_text(request.get("country") or config.get("country") or "South Sudan")
    study_type = _clean_text(request.get("study_type") or config.get("study_type") or "")

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
        await events.log(job_id, "⚠️ /good study tools skipped: no topic provided.", session_id=session_id)
        return

    tools_dir = WORKSPACES_DIR / workspace_id / "good" / "appendices"
    tools_dir.mkdir(parents=True, exist_ok=True)

    letter_path = tools_dir / "Appendix_I_Introductory_Letter.md"
    questionnaire_path = tools_dir / "Appendix_II_Questionnaire.md"

    await events.stage_started(
        job_id,
        "good_study_tools",
        {"message": "📋 Generating /good study tools (questionnaire, interview, FGD, checklists)..."},
        session_id=session_id,
    )
    await events.log(job_id, "📋 /good study tools generation started...", session_id=session_id)

    # Create a placeholder questionnaire immediately so it appears in the UI early.
    if not questionnaire_path.exists():
        questionnaire_path.write_text(
            "\n".join(
                [
                    "Appendix II: Questionnaires",
                    f"Study Title: {topic}",
                    "",
                    "[Questionnaire is being generated. Please wait...]",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        await events.publish(
            job_id,
            "file_created",
            {
                "path": str(questionnaire_path),
                "full_path": str(questionnaire_path),
                "type": "file",
                "workspace_id": workspace_id,
                "filename": questionnaire_path.name,
            },
            session_id=session_id,
        )
    await events.file_updated(job_id, str(questionnaire_path), session_id=session_id)

    study_header = "\n".join(
        [
            "Appendix II: Questionnaires",
            f"Study Title: {topic}",
            "Objectives:",
            "\n".join([f"{idx}. {obj}" for idx, obj in enumerate(objectives, 1)]),
            "",
        ]
    )

    letter_text = "\n".join(
        [
            "Appendix I: Introductory Letter to Respondents",
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
    letter_path.write_text(letter_text + "\n", encoding="utf-8")

    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(letter_path),
            "full_path": str(letter_path),
            "type": "file",
            "workspace_id": workspace_id,
            "filename": letter_path.name,
        },
        session_id=session_id,
    )
    await events.file_updated(job_id, str(letter_path), session_id=session_id)

    content_lines = [study_header, _demographic_section(), ""]

    sections = []
    for idx, objective in enumerate(objectives, 1):
        letter = chr(ord("B") + idx - 1)
        sections.append((f"### SECTION {letter}: {objective}", objective))

    for idx, (label, objective) in enumerate(sections, 1):
        statements = await _generate_statements(objective, 10)
        open_questions = await _generate_open_questions(objective, 2)
        content_lines.append(label)
        content_lines.append(f"Objective {idx}: {objective}")
        content_lines.append("Instruction: Indicate your level of agreement with each statement below.")
        content_lines.append("KEY: SD, D, NS, A, SA")
        content_lines.append("")
        content_lines.append(_likert_table(statements))
        content_lines.append("")
        content_lines.append("Open-ended questions")
        content_lines.append(_open_question_block(open_questions))
        content_lines.append("")

    questionnaire_text = "\n".join(content_lines).strip() + "\n"
    questionnaire_path.write_text(questionnaire_text, encoding="utf-8")

    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(questionnaire_path),
            "full_path": str(questionnaire_path),
            "type": "file",
            "workspace_id": workspace_id,
            "filename": questionnaire_path.name,
        },
        session_id=session_id,
    )
    await events.file_updated(job_id, str(questionnaire_path), session_id=session_id)

    normalized_type = _normalise_study_type(study_type)
    if normalized_type in {"qualitative", "mixed"}:
        kii_path = tools_dir / "Appendix_III_KII_Guide.md"
        fgd_path = tools_dir / "Appendix_IV_FGD_Guide.md"

        if not kii_path.exists():
            kii_path.write_text(
                "\n".join(
                    [
                        "Appendix III: Key Informant Interview (KII) Guide",
                        f"Study Title: {topic}",
                        "",
                        "[KII guide is being generated. Please wait...]",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            await events.publish(
                job_id,
                "file_created",
                {
                    "path": str(kii_path),
                    "full_path": str(kii_path),
                    "type": "file",
                    "workspace_id": workspace_id,
                    "filename": kii_path.name,
                },
                session_id=session_id,
            )
        await events.file_updated(job_id, str(kii_path), session_id=session_id)

        if not fgd_path.exists():
            fgd_path.write_text(
                "\n".join(
                    [
                        "Appendix IV: Focus Group Discussion (FGD) Guide",
                        f"Study Title: {topic}",
                        "",
                        "[FGD guide is being generated. Please wait...]",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            await events.publish(
                job_id,
                "file_created",
                {
                    "path": str(fgd_path),
                    "full_path": str(fgd_path),
                    "type": "file",
                    "workspace_id": workspace_id,
                    "filename": fgd_path.name,
                },
                session_id=session_id,
            )
        await events.file_updated(job_id, str(fgd_path), session_id=session_id)

        kii_questions = await _generate_kii_questions(objectives, 8)
        fgd_prompts = await _generate_fgd_prompts(objectives, 6)

        kii_text = "\n".join(
            [
                "Appendix III: Key Informant Interview (KII) Guide",
                f"Study Title: {topic}",
                "Instructions: Please answer the following questions based on your experience.",
                "",
                "\n".join([f"{idx}. {q}" for idx, q in enumerate(kii_questions, 1)]),
                "",
            ]
        )
        kii_path.write_text(kii_text, encoding="utf-8")
        await events.publish(
            job_id,
            "file_created",
            {
                "path": str(kii_path),
                "full_path": str(kii_path),
                "type": "file",
                "workspace_id": workspace_id,
                "filename": kii_path.name,
            },
            session_id=session_id,
        )
        await events.file_updated(job_id, str(kii_path), session_id=session_id)

        fgd_text = "\n".join(
            [
                "Appendix IV: Focus Group Discussion (FGD) Guide",
                f"Study Title: {topic}",
                "Instructions: Use the prompts below to guide group discussion.",
                "",
                "\n".join([f"{idx}. {p}" for idx, p in enumerate(fgd_prompts, 1)]),
                "",
            ]
        )
        fgd_path.write_text(fgd_text, encoding="utf-8")
        await events.publish(
            job_id,
            "file_created",
            {
                "path": str(fgd_path),
                "full_path": str(fgd_path),
                "type": "file",
                "workspace_id": workspace_id,
                "filename": fgd_path.name,
            },
            session_id=session_id,
        )
        await events.file_updated(job_id, str(fgd_path), session_id=session_id)

    if normalized_type in {"qualitative", "mixed"}:
        observation_path = tools_dir / "Appendix_V_Observation_Checklist.md"
        document_path = tools_dir / "Appendix_VI_Document_Review.md"

        if not observation_path.exists():
            observation_path.write_text(
                "\n".join(
                    [
                        "Appendix V: Observation Checklist",
                        f"Study Title: {topic}",
                        "",
                        "[Observation checklist is being generated. Please wait...]",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            await events.publish(
                job_id,
                "file_created",
                {
                    "path": str(observation_path),
                    "full_path": str(observation_path),
                    "type": "file",
                    "workspace_id": workspace_id,
                    "filename": observation_path.name,
                },
                session_id=session_id,
            )
        await events.file_updated(job_id, str(observation_path), session_id=session_id)

        if not document_path.exists():
            document_path.write_text(
                "\n".join(
                    [
                        "Appendix VI: Document Review Checklist",
                        f"Study Title: {topic}",
                        "",
                        "[Document review checklist is being generated. Please wait...]",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            await events.publish(
                job_id,
                "file_created",
                {
                    "path": str(document_path),
                    "full_path": str(document_path),
                    "type": "file",
                    "workspace_id": workspace_id,
                    "filename": document_path.name,
                },
                session_id=session_id,
            )
        await events.file_updated(job_id, str(document_path), session_id=session_id)

        observation_items = await _generate_observation_items(objectives, 8)
        document_items = await _generate_document_items(objectives, 8)

        observation_text = "\n".join(
            [
                "Appendix V: Observation Checklist",
                f"Study Title: {topic}",
                "Instructions: Tick the indicators observed.",
                "",
                "\n".join([f"{idx}. {item} (   )" for idx, item in enumerate(observation_items, 1)]),
                "",
            ]
        )
        observation_path.write_text(observation_text, encoding="utf-8")
        await events.publish(
            job_id,
            "file_created",
            {
                "path": str(observation_path),
                "full_path": str(observation_path),
                "type": "file",
                "workspace_id": workspace_id,
                "filename": observation_path.name,
            },
            session_id=session_id,
        )
        await events.file_updated(job_id, str(observation_path), session_id=session_id)

        document_text = "\n".join(
            [
                "Appendix VI: Document Review Checklist",
                f"Study Title: {topic}",
                "Instructions: Use the checklist items below to guide document review.",
                "",
                "\n".join([f"{idx}. {item} (   )" for idx, item in enumerate(document_items, 1)]),
                "",
            ]
        )
        document_path.write_text(document_text, encoding="utf-8")
        await events.publish(
            job_id,
            "file_created",
            {
                "path": str(document_path),
                "full_path": str(document_path),
                "type": "file",
                "workspace_id": workspace_id,
                "filename": document_path.name,
            },
            session_id=session_id,
        )
        await events.file_updated(job_id, str(document_path), session_id=session_id)

    if config_id:
        update_good_status(config_id, {"study_tools_done": True})

    await events.log(job_id, "✅ /good study tools saved in appendices.", session_id=session_id)
    await events.stage_completed(job_id, "good_study_tools", {"dir": str(tools_dir)}, session_id=session_id)

    try:
        datasets_dir = WORKSPACES_DIR / workspace_id / "good" / "datasets"
        datasets_dir.mkdir(parents=True, exist_ok=True)
        methodology_path = WORKSPACES_DIR / workspace_id / "good" / "Chapter_3_Research_Methodology.md"
        await events.stage_started(
            job_id,
            "good_datasets",
            {"message": "🎲 Generating /good synthetic datasets..."},
            session_id=session_id,
        )
        dataset_result = await generate_research_dataset(
            topic=topic,
            case_study=case_study,
            questionnaire_path=str(questionnaire_path),
            methodology_path=str(methodology_path) if methodology_path.exists() else None,
            objectives=objectives,
            job_id=job_id,
            session_id=session_id,
            output_dir=str(datasets_dir),
        )
        for dataset_path in dataset_result.get("files", []) if dataset_result else []:
            await events.publish(
                job_id,
                "file_created",
                {
                    "path": str(dataset_path),
                    "full_path": str(dataset_path),
                    "type": "file",
                    "workspace_id": workspace_id,
                    "filename": os.path.basename(str(dataset_path)),
                },
                session_id=session_id,
            )
            await events.file_updated(job_id, str(dataset_path), session_id=session_id)
        if config_id:
            update_good_status(config_id, {"datasets_done": True})
        await events.stage_completed(
            job_id,
            "good_datasets",
            {"dir": str(datasets_dir), "files": dataset_result.get("files", []) if dataset_result else []},
            session_id=session_id,
        )
    except Exception as exc:
        await events.log(job_id, f"⚠️ /good dataset generation failed: {exc}", session_id=session_id)

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
