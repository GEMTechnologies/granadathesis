"""
University of Juba Chapter 1 Generator
Generates Chapter 1 following UoJ Bachelor's thesis template with 16 sections.
"""
from typing import Dict, Any
from services.deepseek_direct import deepseek_direct_service
from services.objective_generator import normalize_objectives
from core.events import events
from services.chapter_state import ChapterState
from services.plan_tracker import ensure_plan_file, mark_plan_item
from services.workspace_service import WORKSPACES_DIR


async def generate_chapter_one_uoj(
    topic: str,
    case_study: str,
    country: str,
    job_id: str,
    session_id: str,
    workspace_id: str,
    objectives: Dict[str, Any],
    thesis_type: str = "general"
) -> str:
    """
    Generate Chapter 1 for University of Juba thesis (General or PhD).
    Follows exact UoJ template with 16 sections.
    """
    
    await events.publish(job_id, "log", {"message": "📖 Generating UoJ Chapter 1 (16 sections)..."}, session_id=session_id)
    
    if not isinstance(objectives, dict):
        objectives = normalize_objectives(objectives or [], topic, case_study)
    general_objective = objectives.get("general", "")
    specific_objectives = objectives.get("specific", [])
    chapter_one_outline_sentence = (
        "Due to the above introduction, chapter one of this study will focus on historical "
        "background, problem statement, purpose of the study, objectives of the study outlining "
        "the general and specific objectives, research questions and hypothesis, significance of "
        "the study, scope of the study, brief methodology of the study, anticipated limitations and "
        "delimitation, assumptions of the study, definition of key terms, and summary of chapter one."
    )
    custom_outline = None
    try:
        from services.outline_parser import outline_parser
        from services.workspace_service import WORKSPACES_DIR

        outline_path = WORKSPACES_DIR / workspace_id / "outline.json"
        if outline_path.exists():
            custom_outline = outline_parser.load_outline(workspace_id)
            chapter_one_outline = outline_parser.get_chapter_structure(custom_outline, 1)
            section_list = []
            if chapter_one_outline and chapter_one_outline.get("sections"):
                section_list = [
                    section for section in chapter_one_outline.get("sections", [])
                    if isinstance(section, str) and section.strip()
                ]
            if section_list:
                section_text = ", ".join(section_list)
                chapter_one_outline_sentence = (
                    "Due to the above introduction, chapter one of this study will focus on "
                    f"{section_text}."
                )
    except Exception as e:
        print(f"⚠️ Could not load custom outline for introduction: {e}")

    plan_outline = custom_outline
    try:
        if not plan_outline:
            outline_path = WORKSPACES_DIR / workspace_id / "outline.json"
            if outline_path.exists():
                from services.outline_parser import outline_parser
                plan_outline = outline_parser.load_outline(workspace_id)
    except Exception as e:
        print(f"⚠️ Could not load outline for planner: {e}")

    plan_path, _ = ensure_plan_file(workspace_id, plan_outline, thesis_type)

    async def _update_plan_section(label: str):
        if not label:
            return
        if mark_plan_item(workspace_id, label, cascade=False):
            await events.publish(
                job_id,
                "file_updated",
                {
                    "path": str(plan_path.relative_to(WORKSPACES_DIR / workspace_id)),
                    "full_path": str(plan_path),
                    "filename": plan_path.name,
                    "workspace_id": workspace_id,
                    "type": "markdown"
                },
                session_id=session_id
            )

    async def announce(section_id: str, title: str):
        await events.publish(
            job_id,
            "agent_activity",
            {
                "agent": "uoj_writer",
                "agent_name": "UoJ Writer",
                "status": "running",
                "action": f"Writing §{section_id}: {title}",
                "icon": "✍️",
                "type": "chapter_generator"
            },
            session_id=session_id
        )
    
    # ================================================================
    # SECTION 1.0: INTRODUCTION TO THE STUDY
    # ================================================================
    await announce("1.0", "Introduction to the Study")
    intro_prompt = f"""Write a brief Introduction about {topic} in {country} and specifically in {case_study}.

Make about three paragraphs for this Introduction with enough in-text citations (2020-2025, APA style).

Fourth paragraph: outline the structure of chapter one, saying "{chapter_one_outline_sentence}"

NOTE: Current year is 2025. Citations must be between June 2020 to June 2025, APA 7 style.
**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Use hypothetical but realistic citations (avoid Smith, Johnson, Lee).
For local content, use local names from {country}.
Don't bullet or number. Present in big detailed paragraphs in academic tone.
Never say "we" - say "the study" or "the researcher".
Be brief but comprehensive."""

    section_1_0 = await deepseek_direct_service.generate_content(
        prompt=intro_prompt,
        temperature=0.7,
        max_tokens=800
    )
    await _update_plan_section("1.0 Introduction to the Study")
    
    # ================================================================
    # SECTION 1.1: BACKGROUND OF THE STUDY
    # ================================================================
    await announce("1.1", "Background of the Study")
    background_prompt = f"""Write historical Background of the study about {topic}.

Structure (all in ONE paragraph each):
1. **Global Perspective**: Summarize global trends, mentioning specific countries/places in America, Asia, Australia, Europe. One paragraph.
2. **African Perspective**: Summarize African trends, mentioning countries in North Africa, South Africa, Central Africa, West Africa. One paragraph.
3. **East African Perspective**: Summarize East African trends, mentioning specific districts/villages/places in East African countries. One paragraph.
4. **{country} Perspective**: Detailed background in {country}, mentioning States, Payams, Bomas, Villages. Then write a very detailed past and current situation of {topic} in {case_study}.

Conclude: "It is upon the above background that this study aims to {general_objective} in {case_study}, {country}."

NOTE: Current year is 2025. Citations must be between June 2020 to June 2025, APA 7 style (e.g., [Dennis, 2020](https://doi.org/xxxxx) or [Dennis et al., 2020](https://doi.org/xxxxx)).
**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Use hypothetical but realistic citations. For {country} content, use local names.
Don't bullet or number. Present in big detailed paragraphs. Never say "we".
Be comprehensive with citations at the end of each line/sentence."""

    section_1_1 = await deepseek_direct_service.generate_content(
        prompt=background_prompt,
        temperature=0.7,
        max_tokens=1500
    )
    await _update_plan_section("1.1 Background of the Study")
    
    # ================================================================
    # SECTION 1.2: PROBLEM STATEMENT
    # ================================================================
    await announce("1.2", "Problem Statement")
    problem_prompt = f"""Write a standard problem Statement in APA style for the study about {topic} in {case_study}, {country}.

Organize in this format (one paragraph per point):
1. Problem is current
2. Population affected
3. Has wide magnitude justified by data
4. Effects on the individuals, community, or health service providers
5. Plausible factors contributing to the problem
6. Attempts taken to solve this problem (including studies, their problems, and gaps)
7. Where information is missing

**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Use hypothetical but realistic citations (avoid Smith, Johnson, Lee).
Don't bullet or number. Present in big detailed paragraphs in academic tone.
Never say "we" - say "the study" or "the researcher"."""

    section_1_2 = await deepseek_direct_service.generate_content(
        prompt=problem_prompt,
        temperature=0.7,
        max_tokens=1200
    )
    await _update_plan_section("1.2 Problem Statement")
    
    # ================================================================
    # SECTION 1.3: PURPOSE OF THE STUDY
    # ================================================================
    await announce("1.3", "Purpose of the Study")
    purpose_prompt = f"""Write the purpose of the study about {topic} in {case_study}, {country}.

Let it be precise and very summarized. Only the purpose of the study, don't add anything else.
Write in academic and professional tone. Be brief."""

    section_1_3 = await deepseek_direct_service.generate_content(
        prompt=purpose_prompt,
        temperature=0.6,
        max_tokens=200
    )
    await _update_plan_section("1.3 Purpose of the Study")
    
    # ================================================================
    # SECTIONS 1.4-1.6: OBJECTIVES, QUESTIONS, HYPOTHESIS
    # ================================================================
    # Format objectives
    objectives_text = f"**General Objective:**\n{general_objective}\n\n**Specific Objectives:**\n"
    for i, obj in enumerate(specific_objectives, 1):
        objectives_text += f"{i}. {obj}\n"
    
    # Generate research questions
    questions_prompt = f"""Convert these objectives into research question form:

{objectives_text}

Return ONLY the questions, numbered 1-{len(specific_objectives)+1}. Be brief."""

    await announce("1.5", "Study Questions")
    section_1_5 = await deepseek_direct_service.generate_content(
        prompt=questions_prompt,
        temperature=0.5,
        max_tokens=400
    )
    await _update_plan_section("1.5 Study Questions")
    
    # Generate hypotheses
    hypothesis_prompt = f"""Convert these objectives into hypothesis statements:

{objectives_text}

Format as:
H1: [hypothesis for objective 1]
H01: [null hypothesis for objective 1]
H2: [hypothesis for objective 2]
H02: [null hypothesis for objective 2]
... and so on.

Return ONLY the hypotheses. Be brief."""

    await announce("1.6", "Research Hypothesis")
    section_1_6 = await deepseek_direct_service.generate_content(
        prompt=hypothesis_prompt,
        temperature=0.5,
        max_tokens=600
    )
    await _update_plan_section("1.6 Research Hypothesis")
    
    # ================================================================
    # SECTION 1.7: SIGNIFICANCE OF THE STUDY
    # ================================================================
    await announce("1.7", "Significance of the Study")
    significance_prompt = f"""State the Significance of the study about {topic} in {country} and {case_study}.

Format:
**Beneficiary 1:** [State the significance for this beneficiary]
**Beneficiary 2:** [State the significance for this beneficiary]
... (at least 4 beneficiaries)

Be detailed and specific to {case_study}."""

    section_1_7 = await deepseek_direct_service.generate_content(
        prompt=significance_prompt,
        temperature=0.7,
        max_tokens=600
    )
    await _update_plan_section("1.7 Significance of the Study")
    
    # ================================================================
    # SECTION 1.8: SCOPE OF THE STUDY
    # ================================================================
    await announce("1.8", "Scope of the Study")
    scope_prompt = f"""State the Scope of the study about {topic} in {case_study}, {country} in terms of:

1. **Content Scope**: What the study will cover
2. **Time Scope**: Note that we are in 2025 and studies take three months period
3. **Geographical Scope**: Write the geography of {case_study}, its longitude and latitude, its directions and neighbouring places/villages/Payams/Bomas/Districts

Don't bullet or number. Write in detailed paragraphs."""

    section_1_8 = await deepseek_direct_service.generate_content(
        prompt=scope_prompt,
        temperature=0.7,
        max_tokens=800
    )
    await _update_plan_section("1.8 Scope of the Study")
    
    # ================================================================
    # SECTION 1.9: LIMITATIONS OF THE STUDY
    # ================================================================
    await announce("1.9", "Limitations of the Study")
    limitations_prompt = f"""State the Limitations of the Study about {topic} in {case_study}, {country}.

Explain each limitation in detail and talk in future tense. For each, tell us how you could mitigate it in a few sentences.
Make 4 to 7 limitations.

Don't bullet or number. Write in detailed paragraphs."""

    section_1_9 = await deepseek_direct_service.generate_content(
        prompt=limitations_prompt,
        temperature=0.7,
        max_tokens=800
    )
    await _update_plan_section("1.9 Limitations of the Study")
    
    # ================================================================
    # SECTION 1.11: DELIMITATIONS OF THE STUDY
    # ================================================================
    await announce("1.11", "Delimitations of the Study")
    delimitations_prompt = f"""State and explain the Delimitation(s) of the study about {topic} in {case_study}, {country}.

Present all in ONE paragraph. Write in academic language."""

    section_1_11 = await deepseek_direct_service.generate_content(
        prompt=delimitations_prompt,
        temperature=0.7,
        max_tokens=400
    )
    await _update_plan_section("1.11 Delimitations of the Study")
    
    # ================================================================
    # SECTION 1.12: THEORETICAL FRAMEWORK
    # ================================================================
    await announce("1.12", "Theoretical Framework of the Study")
    theoretical_prompt = f"""Generate one theory by a scholar or scholars for a study about {topic}.

Structure:
1. State the theory name and author(year)
2. State what the theory says with precise in-text citations (4 citations, 2020-2025)
3. State two authors who oppose the theory and what they say (each in a specific paragraph)
4. State two authors who agree with the theory and what they say (each in a specific paragraph)
5. State the importance of the theory in the context of {topic}
6. State the importance of the theory in {case_study}
7. State the gaps in the theory referring to {case_study}

**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Everything must be academically well cited. Use hypothetical but realistic citations.
Don't bullet or number. Present in big detailed paragraphs. Never say "we".
Be very very detailed."""

    section_1_12 = await deepseek_direct_service.generate_content(
        prompt=theoretical_prompt,
        temperature=0.7,
        max_tokens=1500
    )
    await _update_plan_section("1.12 Theoretical Framework of the Study")
    
    # ================================================================
    # SECTION 1.13: CONCEPTUAL FRAMEWORK
    # ================================================================
    await announce("1.13", "Conceptual Framework")
    conceptual_prompt = f"""State Independent and dependent Variables for the study about {topic}.

List:
- 10 independent variables
- 5 dependent variables
- 4 intervening variables

Then make a discussion on how each of the Independent, dependent and intervening Variables relates to another with the concept of {general_objective}, or {topic} with in-text citations.

**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Be detailed in discussions and in context of {case_study}.

Format as:
**Independent Variables:**
1. [Variable 1]
2. [Variable 2]
...

**Dependent Variables:**
1. [Variable 1]
...

**Intervening Variables:**
1. [Variable 1]
...

**Discussion:**
[Detailed discussion with citations]

Then add:
**Figure 1.1: Conceptual Framework**
Designed and Molded by Researcher (2025)"""

    section_1_13 = await deepseek_direct_service.generate_content(
        prompt=conceptual_prompt,
        temperature=0.7,
        max_tokens=1200
    )
    await _update_plan_section("1.13 Conceptual Framework")
    
    # ================================================================
    # SECTION 1.15: DEFINITION OF KEY TERMS
    # ================================================================
    await announce("1.15", "Definition of Key Terms")
    definitions_prompt = f"""Write definition of key terms on the study about {topic} in {case_study}.

**CRITICAL**: Format ALL citations as clickable markdown hyperlinks: [Author et al., Year](https://doi.org/xxxxx)
Present with citations where appropriate. Use hypothetical but realistic citations.
Don't bullet or number. Present in big detailed paragraphs.
Where you can't get real good citations, don't cite."""

    section_1_15 = await deepseek_direct_service.generate_content(
        prompt=definitions_prompt,
        temperature=0.7,
        max_tokens=800
    )
    await _update_plan_section("1.15 Definition of Key Terms")
    
    # ================================================================
    # SECTION 1.16: ORGANIZATION OF THE STUDY
    # ================================================================
    await announce("1.16", "Organization of the Study")
    is_phd = thesis_type in ["phd", "uoj_phd"]
    ch_outline = "six chapters" if is_phd else "five chapters"
    chapter_lines = []

    try:
        if custom_outline and custom_outline.get("chapters"):
            for chapter in custom_outline.get("chapters", []):
                ch_num = chapter.get("number")
                ch_title = chapter.get("title")
                if ch_num and ch_title:
                    chapter_lines.append(f"- Chapter {ch_num}: {ch_title}")
    except Exception as e:
        print(f"⚠️ Could not load custom outline for organisation section: {e}")

    if not chapter_lines:
        ch6_text = "- Chapter six: Conclusions, recommendations, suggestions for future studies" if is_phd else ""
        ch5_text = "- Chapter five: Discussions, summary, conclusions, recommendations, suggestions for future studies" if not is_phd else "- Chapter five: Discussions"
        chapter_lines = [
            "- Chapter one: Introduction",
            "- Chapter two: Literature review",
            "- Chapter three: Methodology",
            "- Chapter four: Data analysis, presentation and interpretations of findings",
            ch5_text,
            ch6_text
        ]
        chapter_lines = [line for line in chapter_lines if line]

    organization_prompt = f"""Write Organisation of the study which will be guided in {ch_outline}:
{chr(10).join(chapter_lines)}

Write in context of {topic} in {case_study}.
Be brief and academic."""

    section_1_16 = await deepseek_direct_service.generate_content(
        prompt=organization_prompt,
        temperature=0.6,
        max_tokens=400
    )
    await _update_plan_section("1.16 Organization of the Study")
    
    # ================================================================
    # ASSEMBLE CHAPTER 1
    # ================================================================
    chapter_one_content = f"""# CHAPTER ONE: INTRODUCTION

## 1.0 Introduction to the Study
{section_1_0}

## 1.1 Background of the Study
{section_1_1}

## 1.2 Problem Statement
{section_1_2}

## 1.3 Purpose of the Study
{section_1_3}

## 1.4 Objectives of the Study
The study will be guided by both a general objective and a list of specific objectives as presented below:

### 1.4.1 General Objective of the Study
{general_objective}

### 1.4.2 Specific Objectives
{chr(10).join([f"{i}. {obj}" for i, obj in enumerate(specific_objectives, 1)])}

## 1.5 Study Questions
{section_1_5}

## 1.6 Research Hypothesis
{section_1_6}

## 1.7 Significance of the Study
{section_1_7}

## 1.8 Scope of the Study
{section_1_8}

## 1.9 Limitations of the Study
{section_1_9}

## 1.11 Delimitations of the Study
{section_1_11}

## 1.12 Theoretical Framework of the Study
{section_1_12}

## 1.13 Conceptual Framework
{section_1_13}

## 1.15 Definition of Key Terms
{section_1_15}

## 1.16 Organization of the Study
{section_1_16}
"""
    
    # Save to file
    from services.workspace_service import WORKSPACES_DIR
    import os
    workspace_path = WORKSPACES_DIR / workspace_id
    os.makedirs(workspace_path, exist_ok=True)
    chapter_path = workspace_path / "Chapter_1_Introduction_UoJ.md"
    with open(chapter_path, "w", encoding="utf-8") as f:
        f.write(chapter_one_content)

    await events.publish(
        job_id,
        "file_created",
        {
            "path": str(chapter_path),
            "filename": chapter_path.name,
            "type": "markdown",
            "auto_open": True,
            "content_preview": chapter_one_content[:500]
        },
        session_id=session_id
    )
    
    await events.publish(job_id, "log", {"message": f"✅ UoJ Chapter 1 complete ({len(chapter_one_content.split())} words)"}, session_id=session_id)
    
    return chapter_one_content
