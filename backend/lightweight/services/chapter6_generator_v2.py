"""
Chapter 6 Generator V2 - LLM-Generated Summary, Conclusions and Recommendations

Unlike the original template-based generator, this version uses the LLM
to generate unique, contextual content for each section.

Structure:
6.0 Introduction
6.1 Summary of the Study
6.2 Summary of Key Findings (per objective)
6.3 Conclusions (per objective)
6.4 Recommendations
6.5 Contribution to Knowledge
6.6 Limitations of the Study
6.7 Suggestions for Further Research

All content is LLM-generated, not template-filled.
"""

import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


async def _generate_content(prompt: str, max_tokens: int = 1500) -> str:
    """Helper to generate content using DeepSeek."""
    from services.deepseek_direct import deepseek_direct_service
    return await deepseek_direct_service.generate_content(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.7
    )


def _extract_short_theme(objective: str, max_words: int = 5) -> str:
    """Extract a short theme from an objective for section headings."""
    # Remove common prefixes
    text = objective.lower()
    for prefix in ['to ', 'to determine ', 'to examine ', 'to assess ', 'to evaluate ', 
                   'to analyze ', 'to analyse ', 'to investigate ', 'to explore ']:
        if text.startswith(prefix):
            text = text[len(prefix):]
            break
    
    # Skip common words and get key words
    skip_words = {'the', 'and', 'for', 'with', 'from', 'that', 'this', 'which', 
                  'their', 'of', 'in', 'on', 'a', 'an', 'how', 'what', 'why', 'whether'}
    words = [w for w in text.split() if w.lower() not in skip_words and len(w) > 2]
    
    # Return first N words, title-cased
    theme = ' '.join(words[:max_words]).title()
    return theme if theme else "Key Aspects"


def _number_to_words(n: int) -> str:
    """Convert number to words for headings."""
    words = ['Zero', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten']
    return words[n] if n < len(words) else str(n)


async def generate_chapter6(
    topic: str,
    case_study: str,
    objectives: List[str],
    chapter4_content: str = "",
    chapter5_content: str = "",
    job_id: str = None,
    session_id: str = None,
    workspace_id: str = "default"
) -> str:
    """
    Generate Chapter 6 using LLM for all content.
    
    Returns complete chapter as markdown string.
    """
    from core.events import events
    from services.workspace_service import WORKSPACES_DIR
    
    # Standard workspace path
    workspace_path = WORKSPACES_DIR / (workspace_id or "default")
    
    # Try to load Golden Thread variables for context
    objective_variables = {}
    try:
        plan_path = workspace_path / "thesis_plan.json"
        if plan_path.exists():
            with open(plan_path, 'r') as f:
                plan_data = json.load(f)
                objective_variables = plan_data.get("objective_variables", {})
    except Exception:
        pass

    vars_ctx = ""
    if objective_variables:
        vars_ctx = "\nARCHITECTURAL VARIABLES (The Golden Thread):\n"
        for o_num, v_list in objective_variables.items():
            vars_ctx += f"- Objective {o_num}: {', '.join(v_list)}\n"
    
    chapter = "# CHAPTER SIX\n# SUMMARY, CONCLUSIONS AND RECOMMENDATIONS\n\n"
    
    num_objectives = len(objectives)
    
    # ========== 6.0 Introduction ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.0 Introduction..."}, session_id=session_id)
    
    intro_prompt = f"""Write the introduction section (6.0) for Chapter Six: Summary, Conclusions and Recommendations.

TOPIC: {topic}
CASE STUDY: {case_study}
NUMBER OF OBJECTIVES: {num_objectives}

**CRITICAL: Do NOT write the heading "6.0 Introduction" - it will be added automatically.**

Write 2-3 paragraphs that:
1. State that this chapter concludes the study and synthesises the entire research
2. Briefly restate the purpose - to investigate {topic} in the context of {case_study}
3. Outline what the chapter covers: summary of findings, conclusions per objective, recommendations, contribution to knowledge, limitations, and suggestions for further research

**LANGUAGE**: UK English (analyse, organisation, recognised)
**TENSE**: Past tense for findings, present for conclusions
**STYLE**: Formal academic prose, no bullet points

Write the content now:"""

    intro_content = await _generate_content(intro_prompt, max_tokens=800)
    chapter += "## 6.0 Introduction\n\n"
    chapter += intro_content.strip() + "\n\n"
    
    # ========== 6.1 Summary of the Study ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.1 Summary of the Study..."}, session_id=session_id)
    
    objectives_text = "\n".join([f"{i}. {obj}" for i, obj in enumerate(objectives, 1)])
    
    summary_prompt = f"""Write section 6.1 Summary of the Study for Chapter Six.

TOPIC: {topic}
CASE STUDY: {case_study}

RESEARCH OBJECTIVES:
{objectives_text}

**CRITICAL: Do NOT write the heading "6.1 Summary of the Study" - it will be added automatically.**

Write 4-5 substantial paragraphs covering:

1. **Research Background**: What problem this study addressed and why it was important. Do NOT repeat the full topic title - refer to it naturally (e.g., "This study investigated security sector reform during South Sudan's political transition...")

2. **Research Objectives**: Summarise what the {num_objectives} objectives sought to achieve - paraphrase them, don't copy verbatim

3. **Methodology**: Mixed-methods approach, data collection instruments (questionnaires, interviews, FGDs), sampling, and analysis techniques used

4. **Key Findings Overview**: Brief synthesis of what the study discovered - highlight 2-3 major findings without repeating per-objective details

{vars_ctx}

**LANGUAGE**: UK English
**TENSE**: Past tense throughout (was conducted, revealed, demonstrated)
**STYLE**: Flowing academic prose, synthesise don't list

Write the content now:"""

    summary_content = await _generate_content(summary_prompt, max_tokens=1500)
    chapter += "## 6.1 Summary of the Study\n\n"
    chapter += summary_content.strip() + "\n\n"
    
    # ========== 6.2 Summary of Key Findings (per objective) ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.2 Summary of Key Findings..."}, session_id=session_id)
    
    chapter += "## 6.2 Summary of Key Findings\n\n"
    
    findings_intro_prompt = f"""Write a brief introduction (1 paragraph) for the Summary of Key Findings section.

State that this section presents a summary of the key findings organised by research objective.
Mention there were {num_objectives} objectives guiding this study.

**Do NOT write any heading.**
**UK English, past tense, formal academic style.**

Write ONE paragraph only:"""

    findings_intro = await _generate_content(findings_intro_prompt, max_tokens=300)
    chapter += findings_intro.strip() + "\n\n"
    
    # Generate findings summary for each objective
    for i, objective in enumerate(objectives, 1):
        short_theme = _extract_short_theme(objective)
        obj_word = _number_to_words(i)
        
        await events.publish(job_id, "log", {"message": f"📝 Generating findings for Objective {i}..."}, session_id=session_id)
        
        finding_prompt = f"""Write the summary of key findings for Objective {i}.

OBJECTIVE {i}: {objective}
TOPIC: {topic}
CASE STUDY: {case_study}

**CRITICAL: Do NOT write any heading - it will be added automatically.**

Write 2-3 paragraphs summarising the KEY FINDINGS for this objective:
- What did the data reveal regarding this objective?
- What were the main patterns, trends, or themes identified?
- How did quantitative and qualitative findings complement each other?
- What were any notable or unexpected findings?

{vars_ctx}

**IMPORTANT**: 
- Do NOT repeat the full objective text verbatim
- Do NOT use phrases like "the phenomenon is multifaceted and context-dependent"
- Write SPECIFIC, UNIQUE findings relevant to the topic
- Use concrete language: "The findings revealed that..." "Analysis indicated..." "Respondents reported..."

**LANGUAGE**: UK English
**TENSE**: Past tense (revealed, indicated, demonstrated)

Write the content now:"""

        finding_content = await _generate_content(finding_prompt, max_tokens=800)
        chapter += f"### 6.2.{i} Findings on Objective {obj_word}: {short_theme}\n\n"
        chapter += finding_content.strip() + "\n\n"
    
    # ========== 6.3 Conclusions (per objective) ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.3 Conclusions..."}, session_id=session_id)
    
    chapter += "## 6.3 Conclusions\n\n"
    
    conclusions_intro_prompt = f"""Write a brief introduction (1 paragraph) for the Conclusions section.

State that based on the findings presented, the following conclusions are drawn in relation to each research objective.

**Do NOT write any heading.**
**UK English, formal academic style.**

Write ONE paragraph only:"""

    conclusions_intro = await _generate_content(conclusions_intro_prompt, max_tokens=300)
    chapter += conclusions_intro.strip() + "\n\n"
    
    # Generate conclusion for each objective
    for i, objective in enumerate(objectives, 1):
        short_theme = _extract_short_theme(objective)
        obj_word = _number_to_words(i)
        
        await events.publish(job_id, "log", {"message": f"📝 Generating conclusion for Objective {i}..."}, session_id=session_id)
        
        conclusion_prompt = f"""Write the conclusion for Objective {i}.

OBJECTIVE {i}: {objective}
TOPIC: {topic}
CASE STUDY: {case_study}

**CRITICAL: Do NOT write any heading - it will be added automatically.**

Write 2-3 paragraphs that:
1. State the main conclusion regarding this objective
2. Explain what this means in the context of {case_study}
3. Connect to theoretical frameworks from the literature review
4. Note any implications for understanding the broader phenomenon

**IMPORTANT**:
- Do NOT repeat generic phrases like "the phenomenon is multifaceted"
- Do NOT copy the objective verbatim - paraphrase it
- Write SPECIFIC conclusions that follow logically from the findings
- Each conclusion should be UNIQUE to this objective

**LANGUAGE**: UK English
**TENSE**: Present tense for conclusions (indicates, suggests, demonstrates)

Write the content now:"""

        conclusion_content = await _generate_content(conclusion_prompt, max_tokens=800)
        chapter += f"### 6.3.{i} Conclusion on Objective {obj_word}: {short_theme}\n\n"
        chapter += conclusion_content.strip() + "\n\n"
    
    # ========== 6.4 Recommendations ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.4 Recommendations..."}, session_id=session_id)
    
    recommendations_prompt = f"""Write section 6.4 Recommendations for Chapter Six.

TOPIC: {topic}
CASE STUDY: {case_study}

RESEARCH OBJECTIVES:
{objectives_text}

**CRITICAL: Do NOT write the heading "6.4 Recommendations" - it will be added automatically.**

Write comprehensive recommendations organised by stakeholder:

**6.4.1 Policy Recommendations** (for government/policymakers)
- 3-4 specific, actionable recommendations
- Based on the study findings
- Relevant to {case_study}

**6.4.2 Institutional/Organisational Recommendations** (for organisations involved)
- 3-4 specific recommendations for institutions
- Practical and implementable

**6.4.3 Recommendations for Practice** (for practitioners/professionals)
- 2-3 recommendations for those working in the field

**FORMAT**: Use sub-headings (### 6.4.1, ### 6.4.2, ### 6.4.3).
Under each, write flowing prose with numbered recommendations embedded.

**IMPORTANT**:
- Do NOT use numbered lists at the start (1., 2., 3.)
- Do NOT just repeat the topic title
- Write SPECIFIC recommendations relevant to the findings
- UK English (organisation, programme, recognised)

Write the content now:"""

    recommendations_content = await _generate_content(recommendations_prompt, max_tokens=2000)
    chapter += "## 6.4 Recommendations\n\n"
    chapter += recommendations_content.strip() + "\n\n"
    
    # ========== 6.5 Contribution to Knowledge ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.5 Contribution to Knowledge..."}, session_id=session_id)
    
    contribution_prompt = f"""Write section 6.5 Contribution to Knowledge for Chapter Six.

TOPIC: {topic}
CASE STUDY: {case_study}

**CRITICAL: Do NOT write the heading - it will be added automatically.**

Write 3-4 paragraphs explaining how this study contributes to:

1. **Theoretical Contribution**: How the findings extend, refine, or challenge existing theoretical frameworks discussed in the literature review

2. **Empirical Contribution**: What new empirical evidence this study provides that fills gaps in the existing literature

3. **Methodological Contribution**: Any methodological innovations or applications (if applicable)

4. **Practical Contribution**: How the findings can inform policy and practice in {case_study} and similar contexts

**UK English, formal academic style.**

Write the content now:"""

    contribution_content = await _generate_content(contribution_prompt, max_tokens=1200)
    chapter += "## 6.5 Contribution to Knowledge\n\n"
    chapter += contribution_content.strip() + "\n\n"
    
    # ========== 6.6 Limitations of the Study ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.6 Limitations..."}, session_id=session_id)
    
    limitations_prompt = f"""Write section 6.6 Limitations of the Study for Chapter Six.

TOPIC: {topic}
CASE STUDY: {case_study}

**CRITICAL: Do NOT write the heading - it will be added automatically.**

Write 3-4 paragraphs acknowledging the limitations:

1. **Scope Limitations**: Geographic/temporal boundaries - limited to {case_study}

2. **Methodological Limitations**: Sample size, sampling method, data collection constraints

3. **Practical Limitations**: Access issues, time constraints, resource limitations

4. **Generalisability**: Extent to which findings can be generalised beyond the case study

**NOTE**: Frame limitations constructively - acknowledge them but note how they were mitigated.

**UK English (generalised, recognised).**

Write the content now:"""

    limitations_content = await _generate_content(limitations_prompt, max_tokens=1000)
    chapter += "## 6.6 Limitations of the Study\n\n"
    chapter += limitations_content.strip() + "\n\n"
    
    # ========== 6.7 Suggestions for Further Research ==========
    await events.publish(job_id, "log", {"message": "📝 Generating 6.7 Suggestions for Further Research..."}, session_id=session_id)
    
    future_prompt = f"""Write section 6.7 Suggestions for Further Research for Chapter Six.

TOPIC: {topic}
CASE STUDY: {case_study}

RESEARCH OBJECTIVES:
{objectives_text}

**CRITICAL: Do NOT write the heading - it will be added automatically.**

Write 3-4 paragraphs suggesting future research directions:

1. **Extending the Scope**: Studies in other geographic contexts or time periods to test generalisability

2. **Methodological Alternatives**: Different methods (longitudinal, experimental, comparative) that could deepen understanding

3. **Unexplored Dimensions**: Aspects that emerged from this study that warrant dedicated investigation

4. **Building on Findings**: Specific research questions that flow from the conclusions

**IMPORTANT**:
- Each suggestion should be SPECIFIC and researchable
- Do NOT just say "more research is needed"
- Connect suggestions to gaps identified in this study
- UK English

Write the content now:"""

    future_content = await _generate_content(future_prompt, max_tokens=1000)
    chapter += "## 6.7 Suggestions for Further Research\n\n"
    chapter += future_content.strip() + "\n\n"
    
    await events.publish(job_id, "log", {"message": "✅ Chapter 6 generation complete!"}, session_id=session_id)
    
    return chapter


# Synchronous wrapper for compatibility
def generate_chapter6_sync(
    topic: str,
    case_study: str,
    objectives: List[str],
    chapter4_content: str = "",
    chapter5_content: str = "",
) -> str:
    """Synchronous wrapper for generate_chapter6."""
    return asyncio.run(generate_chapter6(
        topic=topic,
        case_study=case_study,
        objectives=objectives,
        chapter4_content=chapter4_content,
        chapter5_content=chapter5_content,
    ))
