"""
Outline Rewriter - Reformat generated thesis content to a custom outline.

Uses the LLM to reorganize existing chapter content into the user's outline.
"""

from typing import Dict, Any, List, Tuple

from services.deepseek_direct import deepseek_direct_service


def _build_source_map(outline_chapters: List[Dict[str, Any]], source_chapters: Dict[int, str]) -> Dict[int, str]:
    """Map source chapter content to outline chapter numbers, merging trailing chapters if needed."""
    if not outline_chapters:
        return {}

    outline_numbers = []
    for idx, chapter in enumerate(outline_chapters, 1):
        number = chapter.get("number") or idx
        try:
            number = int(number)
        except (TypeError, ValueError):
            number = idx
        outline_numbers.append(number)

    source_numbers = sorted([num for num in source_chapters.keys() if isinstance(num, int)])
    if not source_numbers:
        return {}

    outline_count = len(outline_numbers)
    source_count = len(source_numbers)
    source_map: Dict[int, str] = {}

    for index, outline_num in enumerate(outline_numbers, 1):
        if outline_num in source_chapters:
            source_map[outline_num] = source_chapters[outline_num]
            continue

        if index == outline_count and source_count >= outline_count:
            merged = []
            for src_num in source_numbers:
                if src_num >= outline_count:
                    merged.append(source_chapters[src_num])
            if merged:
                source_map[outline_num] = "\n\n".join(merged)
                continue

        if source_numbers:
            closest = source_numbers[min(index - 1, source_count - 1)]
            source_map[outline_num] = source_chapters.get(closest, "")

    return source_map


async def rewrite_thesis_to_outline(
    outline: Dict[str, Any],
    source_chapters: Dict[int, str],
    topic: str,
    case_study: str,
    thesis_type: str = "phd"
) -> Dict[int, str]:
    """Rewrite chapters to match the custom outline."""
    outline_chapters = outline.get("chapters", []) if outline else []
    if not outline_chapters:
        return source_chapters

    source_map = _build_source_map(outline_chapters, source_chapters)
    rewritten: Dict[int, str] = {}

    for idx, chapter in enumerate(outline_chapters, 1):
        chapter_number = chapter.get("number") or idx
        try:
            chapter_number = int(chapter_number)
        except (TypeError, ValueError):
            chapter_number = idx

        chapter_title = chapter.get("title") or f"Chapter {chapter_number}"
        sections = [
            section.strip()
            for section in (chapter.get("sections") or [])
            if isinstance(section, str) and section.strip()
        ]
        if not sections:
            sections = ["Introduction", "Main Discussion", "Summary"]

        source_material = source_map.get(chapter_number, "")
        if len(source_material) > 12000:
            source_material = source_material[:12000] + "\n\n[TRUNCATED SOURCE MATERIAL]"

        outline_block = "\n".join([f"## {section}" for section in sections])
        prompt = f"""You are rewriting an existing {thesis_type.upper()} thesis chapter to match a new outline.

Topic: {topic}
Case study: {case_study}

Reformat the source material into the outline below. Use UK English and academic tone.
Use markdown headings exactly in this order:

# CHAPTER {chapter_number}: {chapter_title}
{outline_block}

Rules:
- Only use information present in the source material.
- Do NOT invent citations, facts, or references.
- Keep existing citations/hyperlinks as-is.
- If a section is not covered in the source material, write a short paragraph stating it is not covered.
- Do not add extra sections beyond the outline.

SOURCE MATERIAL:
<<<
{source_material}
>>>

Return ONLY the rewritten chapter with the exact headings.
"""

        rewritten_content = await deepseek_direct_service.generate_content(
            prompt=prompt,
            temperature=0.4,
            max_tokens=2200
        )
        rewritten[chapter_number] = rewritten_content

    return rewritten

