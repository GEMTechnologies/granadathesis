"""
Chapter 5 Generator V2 - Results and Discussion

Generates Chapter 5 that synthesizes:
- Chapter 2: Literature Review (theories and previous studies)
- Chapter 4: Data Analysis (research findings)

Structure (NO sub-sub-headings):
5.0 Introduction
5.1 Discussion of Objective One: [objective text]
5.2 Discussion of Objective Two: [objective text]
...
5.N Discussion of Objective N: [objective text]

Each section is pure flowing academic prose with NO sub-headings inside.
"""

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


def _strip_subheadings(text: str) -> str:
    """Remove any accidental sub-headings the LLM might have added."""
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        # Skip any markdown heading lines (# ## ### ####)
        if stripped.startswith('#'):
            continue
        # Skip numbered sub-section headings like "5.0.1 Title", "5.1.2 Something", etc.
        if re.match(r'^\d+\.\d+\.\d+', stripped):
            continue
        # Skip lines that look like headers: "5.0.1 Purpose and Scope"
        if re.match(r'^[\*]*\d+\.\d+\.\d+\s+[A-Z]', stripped):
            continue
        # Skip bold-only lines that look like headers: "**Overview of Findings**"
        if re.match(r'^\*\*[A-Za-z\s]+\*\*$', stripped):
            continue
        # Skip lines like "### Overview" or "#### Comparison"
        if re.match(r'^#{1,6}\s+', stripped):
            continue
        clean_lines.append(line)
    
    # Join and clean up excessive newlines
    result = '\n'.join(clean_lines)
    result = re.sub(r'\n{4,}', '\n\n\n', result)  # Max 3 newlines
    return result.strip()


async def generate_chapter5_v2(
    topic: str,
    case_study: str,
    objectives: List[str],
    chapter_two_filepath: str = None,
    chapter_three_filepath: str = None,
    chapter_four_filepath: str = None,
    output_dir: str = None,
    job_id: str = None,
    session_id: str = None,
    workspace_id: str = "default",
    sample_size: int = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate Chapter 5 using LLM with Chapter 2 and 4 content.
    
    Structure:
    5.0 Introduction
    5.1 Discussion of Objective One: [text]
    5.2 Discussion of Objective Two: [text]
    ... (one section per objective, no sub-headings inside)
    """
    from services.deepseek_direct import deepseek_direct_service
    from core.events import events
    
    from services.workspace_service import WORKSPACES_DIR
    
    # Standard output dir logic
    if not output_dir or "default" in str(output_dir):
        output_dir = str(WORKSPACES_DIR / "default")
    
    # Define all possible search directories based on WORKSPACES_DIR
    search_dirs = [
        Path(output_dir),
        Path(output_dir) / "chapters",
        WORKSPACES_DIR / "default",
        WORKSPACES_DIR / "default" / "chapters",
    ]
    
    # ============ LOAD CHAPTER 2 CONTENT ============
    chapter_two_content = ""
    ch2_search_paths = [chapter_two_filepath] if chapter_two_filepath else []
    for d in search_dirs:
        if d.exists():
            ch2_search_paths.extend(list(d.glob("Chapter_2*.md")))
            ch2_search_paths.extend(list(d.glob("chapter_2*.md")))
    
    for path in ch2_search_paths:
        if path and isinstance(path, (str, Path)):
            p = Path(path) if isinstance(path, str) else path
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    chapter_two_content = f.read()
                print(f"✓ Loaded Chapter 2: {p}")
                if job_id and session_id:
                    await events.publish(job_id, "log", {"message": f"📖 Loaded Chapter 2: {p.name}"}, session_id=session_id)
                break
    
                if job_id and session_id:
                    await events.publish(job_id, "log", {"message": f"📖 Loaded Chapter 2: {p.name}"}, session_id=session_id)
                break
    
    # ============ LOAD CHAPTER 3 CONTENT ============
    chapter_three_content = ""
    ch3_search_paths = [chapter_three_filepath] if chapter_three_filepath else []
    for d in search_dirs:
        if d.exists():
            ch3_search_paths.extend(list(d.glob("Chapter_3*.md")))
            ch3_search_paths.extend(list(d.glob("chapter_3*.md")))
            
    for path in ch3_search_paths:
        if path and isinstance(path, (str, Path)):
            p = Path(path) if isinstance(path, str) else path
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    chapter_three_content = f.read()
                print(f"✓ Loaded Chapter 3: {p}")
                if job_id and session_id:
                    await events.publish(job_id, "log", {"message": f"🔬 Loaded Chapter 3: {p.name}"}, session_id=session_id)
                break

    # ============ LOAD CHAPTER 4 CONTENT ============
    chapter_four_content = ""
    ch4_search_paths = [chapter_four_filepath] if chapter_four_filepath else []
    for d in search_dirs:
        if d.exists():
            ch4_search_paths.extend(list(d.glob("Chapter_4*.md")))
            ch4_search_paths.extend(list(d.glob("chapter_4*.md")))
    
    for path in ch4_search_paths:
        if path and isinstance(path, (str, Path)):
            p = Path(path) if isinstance(path, str) else path
            if p.exists():
                with open(p, 'r', encoding='utf-8') as f:
                    chapter_four_content = f.read()
                print(f"✓ Loaded Chapter 4: {p}")
                if job_id and session_id:
                    await events.publish(job_id, "log", {"message": f"📊 Loaded Chapter 4: {p.name}"}, session_id=session_id)
                break
    
    # ============ GENERATE CHAPTER 5 ============
    chapter_content = "# CHAPTER FIVE\n\n# RESULTS AND DISCUSSION\n\n"
    
    # --- 5.0 Introduction ---
    # Try to load Golden Thread variables for context
    objective_variables = {}
    try:
        plan_path = Path(output_dir) / "thesis_plan.json"
        if plan_path.exists():
            import json
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
            
    # --- 5.0 Introduction ---
    if job_id and session_id:
        await events.publish(job_id, "log", {"message": "✍️ Generating 5.0 Introduction..."}, session_id=session_id)
    
    intro_prompt = f"""Write section "5.0 Introduction" for Chapter 5 (Results and Discussion) of a PhD thesis.

TOPIC: {topic}
CASE STUDY: {case_study}
SAMPLE SIZE: {sample_size if sample_size else 385} respondents

OBJECTIVES OF THE STUDY:
{chr(10).join([f'{i+1}. {obj}' for i, obj in enumerate(objectives)])}

METHODOLOGY SUMMARY (from Chapter 3):
{chapter_three_content[:2000] if chapter_three_content else "Quantitative study using questionnaires."}

{vars_ctx}

Write 4-5 substantial paragraphs (about 800 words total) that:
1. State the purpose of this chapter - to discuss and interpret the findings from Chapter 4 in relation to the literature reviewed in Chapter 2
2. Briefly restate the research problem and objectives
3. Explain how this chapter is organized (one section per objective)
4. Emphasize that findings will be compared with existing literature to identify confirmations, contradictions, and contributions to knowledge

CRITICAL REQUIREMENTS:
- Write in formal academic English (UK spelling)
- ABSOLUTELY NO sub-headings like "5.0.1", "5.0.2", "Purpose", "Scope", "Organisation" etc.
- ABSOLUTELY NO headings starting with # or ##
- Write ONLY flowing paragraphs - pure prose
- Do NOT include the section heading "5.0 Introduction" - just the content paragraphs
- Do NOT use bullet points or numbered lists in the prose
- Do NOT repeat the full topic title in sentences - use "this study" or "the research" instead"""

    intro_content = await deepseek_direct_service.generate_content(
        prompt=intro_prompt,
        system_prompt="You are an expert PhD thesis writer. Write formal academic prose in UK English. CRITICAL: Output ONLY paragraphs - absolutely NO headings (no #, no ##, no ###), NO numbered sections like 5.0.1, NO bullet points. Pure flowing academic prose only.",
        temperature=0.7,
        max_tokens=2000
    )
    
    # Strip any accidental headings the LLM might have added
    intro_content = _strip_subheadings(intro_content)
    
    chapter_content += f"## 5.0 Introduction\n\n{intro_content}\n\n"
    
    if job_id and session_id:
        await events.publish(job_id, "response_chunk", {
            "chunk": f"## 5.0 Introduction\n\n{intro_content}\n\n",
            "accumulated": chapter_content
        }, session_id=session_id)
    
    # --- 5.1, 5.2, ... Discussion of each Objective ---
    for i, objective in enumerate(objectives):
        section_num = f"5.{i+1}"
        obj_num_word = ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight"][i] if i < 8 else str(i+1)
        
        if job_id and session_id:
            await events.publish(job_id, "log", {"message": f"✍️ Generating {section_num} Discussion of Objective {obj_num_word}..."}, session_id=session_id)
        
        # Extract relevant literature excerpts for this objective
        lit_excerpt = _extract_relevant_literature(chapter_two_content, objective)
        
        # Extract relevant findings from Chapter 4 for this objective
        findings_excerpt = _extract_relevant_findings(chapter_four_content, objective, i+1)
        
        discussion_prompt = f"""Write section "{section_num} Discussion of Objective {obj_num_word}" for Chapter 5 of a PhD thesis.

TOPIC: {topic}
CASE STUDY: {case_study}
SAMPLE SIZE: {sample_size if sample_size else 385} respondents
OBJECTIVE BEING DISCUSSED: {objective}

METHODOLOGY CONTEXT:
{chapter_three_content[:1500] if chapter_three_content else "Quantitative survey based study."}

RELEVANT LITERATURE FROM CHAPTER 2:
{lit_excerpt[:8000] if lit_excerpt else "Use general academic literature on this topic."}

RELEVANT FINDINGS FROM CHAPTER 4:
{findings_excerpt[:8000] if findings_excerpt else "Discuss findings related to this objective based on typical research patterns."}

{vars_ctx}

Write 8-10 substantial paragraphs (about 2000 words) that:

1. Summarize the key findings from Chapter 4 related to this objective
2. Compare findings with what previous researchers found (cite authors from Chapter 2)
3. Identify where findings CONFIRM existing literature - explain why this confirmation is significant
4. Identify where findings CONTRADICT or DIFFER from existing literature - provide possible explanations for differences
5. Explain how findings relate to the theoretical frameworks discussed in Chapter 2
6. Discuss the implications of these findings for theory and practice
7. Highlight the unique contribution of this study regarding this objective

CITATION FORMAT (APA 7 - Last names only):
- Smith (2024) found that...
- This aligns with Jones & Brown (2023) who reported...
- Similar patterns were observed by Williams et al. (2022)...

CRITICAL REQUIREMENTS:
- Write in formal academic English (UK spelling: analyse, organisation, behaviour)
- ABSOLUTELY NO sub-headings like "5.1.1", "5.1.2", "Overview", "Comparison", "Theoretical Framework" etc.
- ABSOLUTELY NO headings starting with # or ## or ###
- Write ONLY flowing paragraphs - pure prose without any structural markers
- NO bullet points, NO numbered lists
- Do NOT include the section heading - just the content paragraphs
- Do NOT repeat the full objective text verbatim in every paragraph - paraphrase or use "this objective"
- Make specific comparisons: "While Smith (2024) found X, this study found Y, which suggests..."
- Use connectives: Furthermore, Moreover, Conversely, In contrast, Similarly, Consequently"""

        discussion_content = await deepseek_direct_service.generate_content(
            prompt=discussion_prompt,
            system_prompt="You are an expert PhD thesis writer. Write formal academic prose in UK English. CRITICAL: Output ONLY paragraphs - absolutely NO headings (no #, no ##, no ###), NO numbered sections like 5.1.1, NO bullet points, NO bold headers. Pure flowing academic prose with citations only.",
            temperature=0.7,
            max_tokens=4000
        )
        
        # Strip any accidental headings the LLM might have added
        discussion_content = _strip_subheadings(discussion_content)
        
        section_heading = f"## {section_num} Discussion of Objective {obj_num_word}: {objective}"
        chapter_content += f"{section_heading}\n\n{discussion_content}\n\n"
        
        if job_id and session_id:
            await events.publish(job_id, "response_chunk", {
                "chunk": f"{section_heading}\n\n{discussion_content}\n\n",
                "accumulated": chapter_content
            }, session_id=session_id)
    
    # ============ SAVE FILE ============
    safe_topic = re.sub(r'[^\w\s-]', '', topic)[:50].replace(' ', '_')
    filename = f"Chapter_5_Results_Discussion_{safe_topic}.md"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(chapter_content)
    
    print(f"✅ Chapter 5 generated: {filepath}")
    print(f"   - Sections: 5.0 Introduction + {len(objectives)} objective discussions")
    print(f"   - Word count: ~{len(chapter_content.split())} words")
    
    if job_id and session_id:
        await events.publish(job_id, "file_created", {
            "path": filepath,
            "filename": filename,
            "type": "markdown",
            "auto_open": True
        }, session_id=session_id)
    
    return {
        'filepath': filepath,
        'objectives_discussed': len(objectives),
        'word_count': len(chapter_content.split()),
        'citations_integrated': chapter_content.count('(20'),  # Count year citations
        'status': 'success'
    }


def _extract_relevant_literature(chapter_two_content: str, objective: str) -> str:
    """Extract sections of Chapter 2 most relevant to this objective."""
    if not chapter_two_content:
        return ""
    
    # Get keywords from objective
    keywords = [w.lower() for w in objective.split() if len(w) > 4]
    
    # Split Chapter 2 into paragraphs
    paragraphs = chapter_two_content.split('\n\n')
    
    # Score each paragraph by keyword matches
    scored = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for kw in keywords if kw in para_lower)
        if score > 0:
            scored.append((score, para))
    
    # Return top relevant paragraphs (up to 3000 words)
    scored.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    word_count = 0
    for score, para in scored[:15]:
        words = len(para.split())
        if word_count + words > 3000:
            break
        result.append(para)
        word_count += words
    
    return '\n\n'.join(result)


def _extract_relevant_findings(chapter_four_content: str, objective: str, obj_num: int) -> str:
    """Extract sections of Chapter 4 most relevant to this objective."""
    if not chapter_four_content:
        return ""
    
    # Look for objective-specific sections in Chapter 4
    patterns = [
        rf'4\.{obj_num}[^0-9].*?(?=\n##|\n#|$)',  # Section 4.1, 4.2, etc.
        rf'[Oo]bjective\s*{obj_num}.*?(?=\n##|\n#|$)',
        rf'[Oo]bjective\s*[Oo]ne.*?(?=\n##|\n#|$)' if obj_num == 1 else '',
    ]
    
    for pattern in patterns:
        if pattern:
            match = re.search(pattern, chapter_four_content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(0)[:4000]
    
    # Fallback: get keywords from objective and find relevant paragraphs
    keywords = [w.lower() for w in objective.split() if len(w) > 4]
    
    paragraphs = chapter_four_content.split('\n\n')
    
    scored = []
    for para in paragraphs:
        para_lower = para.lower()
        score = sum(1 for kw in keywords if kw in para_lower)
        if score > 0:
            scored.append((score, para))
    
    scored.sort(key=lambda x: x[0], reverse=True)
    
    result = []
    word_count = 0
    for score, para in scored[:10]:
        words = len(para.split())
        if word_count + words > 2000:
            break
        result.append(para)
        word_count += words
    
    return '\n\n'.join(result)


# Backwards compatibility - alias the old function name
async def generate_chapter5(
    topic: str,
    case_study: str,
    objectives: List[str],
    chapter_two_filepath: str = None,
    chapter_four_filepath: str = None,
    output_dir: str = None,
    job_id: str = None,
    session_id: str = None
) -> Dict[str, Any]:
    """Wrapper for backwards compatibility."""
    return await generate_chapter5_v2(
        topic=topic,
        case_study=case_study,
        objectives=objectives,
        chapter_two_filepath=chapter_two_filepath,
        chapter_four_filepath=chapter_four_filepath,
        output_dir=output_dir,
        job_id=job_id,
        session_id=session_id,
        sample_size=kwargs.get('sample_size')
    )
