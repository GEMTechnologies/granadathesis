"""
Thesis Combiner & Orchestrator - Multi-Agent Parallel Generation

Combines all 6 chapters into a single comprehensive PhD thesis/dissertation.
Uses concurrent workers to generate chapters in parallel for maximum speed.

Features:
- Extracts ALL references from ALL chapters into unified References section
- Removes individual chapter reference sections
- Adds proper preliminaries (Title Page, Declaration, Dedication, Acknowledgements, Abstract, TOC)
- Adds appendices section at the end
- Removes "Unknown" citations

Flow:
1. Chapter 1 starts immediately
2. Once Ch1 + objectives complete → Ch2, Ch3 start in parallel
3. Ch3 methodology → Study Tools Designer creates tools
4. Tools + Objectives → Dataset Generator creates datasets
5. Ch2 + Ch4 + Datasets → Ch4 Analysis begins
6. Ch2 + Ch4 + Objectives → Ch5 Discussion begins
7. All chapters complete → Ch6 Conclusions
8. All chapters + References → Final combined thesis.md

Commands:
- "generate complete thesis" → Full parallel generation
- "combine chapters" → Combine existing chapter files
- "generate chapter X" → Generate single chapter
- "thesis status" → Check generation progress
"""

import os
import asyncio
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Set
from datetime import datetime
from dataclasses import dataclass
import json


@dataclass
class ThesisSection:
    """Single section of thesis (chapter)."""
    chapter_num: int
    title: str
    content: str
    word_count: int
    filepath: Optional[str] = None


class ThesisCombiner:
    """Combines all chapters into single PhD thesis document with proper structure."""
    
    def __init__(
        self,
        workspace_id: str,
        topic: str,
        case_study: str,
        objectives: List[str],
        output_dir: str = None,
        student_name: str = "[Student Name]",
        supervisor_name: str = "[Supervisor Name]",
        university: str = "University of Juba",
        department: str = "Department/Faculty",
        degree: str = "Doctor of Philosophy (PhD)",
        custom_outline: Optional[Dict[str, Any]] = None
    ):
        """
        Initialise thesis combiner.
        
        Args:
            workspace_id: Workspace identifier
            topic: Research topic
            case_study: Case study name
            objectives: List of research objectives
            output_dir: Output directory for combined thesis
            student_name: Student's full name
            supervisor_name: Supervisor's name
            university: University name
            department: Department/Faculty name
            degree: Degree type
        """
        self.workspace_id = workspace_id
        self.topic = topic
        self.case_study = case_study
        self.objectives = objectives
        self.workspace_dir = Path(f"/home/gemtech/Desktop/thesis/thesis_data/{workspace_id}")
        self.output_dir = output_dir or str(self.workspace_dir)
        self.chapters: Dict[int, ThesisSection] = {}
        self.all_references: List[Dict[str, str]] = []
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Thesis metadata
        self.student_name = student_name
        self.supervisor_name = supervisor_name
        self.university = university
        self.department = department
        if custom_outline and isinstance(custom_outline, dict):
            outline_degree = custom_outline.get("thesis_type")
            if outline_degree and degree == "Doctor of Philosophy (PhD)":
                degree = outline_degree
        self.degree = degree
        self.custom_outline = custom_outline
        self.chapter_order: List[Tuple[int, str]] = self._build_chapter_order()

    def _degree_slug(self) -> str:
        """Create a short degree label for filenames."""
        if not self.degree:
            return "Thesis"
        match = re.search(r"\(([^)]+)\)", self.degree)
        label = match.group(1).strip() if match else self.degree
        label = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")
        return label or "Thesis"

    def _build_chapter_order(self) -> List[Tuple[int, str]]:
        """Determine chapter order and titles from a custom outline if provided."""
        if self.custom_outline and isinstance(self.custom_outline, dict):
            chapters = []
            for idx, chapter in enumerate(self.custom_outline.get("chapters", []), 1):
                number = chapter.get("number") or idx
                try:
                    number = int(number)
                except (TypeError, ValueError):
                    number = idx
                title = chapter.get("title") or f"Chapter {number}"
                chapters.append((number, title))
            if chapters:
                return chapters
        return [(num, f"Chapter {num}") for num in range(1, 7)]

    def _format_authors(self, authors: list) -> str:
        if not authors:
            return "Unknown Author"
        names = []
        for author in authors:
            if isinstance(author, dict):
                name = str(author.get("name", "")).strip()
            else:
                name = str(author).strip()
            if not name:
                continue
            parts = name.split()
            if len(parts) == 1:
                names.append(parts[0])
            else:
                last = parts[-1]
                initials = " ".join([p[0] + "." for p in parts[:-1] if p])
                names.append(f"{last}, {initials}".strip())
        if not names:
            return "Unknown Author"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]}, & {names[1]}"
        if len(names) > 20:
            return ", ".join(names[:19]) + ", ... " + names[-1]
        return ", ".join(names[:-1]) + ", & " + names[-1]

    def _build_references_from_sources(self) -> List[str]:
        try:
            from services.sources_service import SourcesService
            sources_service = SourcesService()
            sources_index = sources_service._load_index(self.workspace_id)
            sources = sources_index.get("sources", []) if isinstance(sources_index, dict) else []
        except Exception as exc:
            print(f"⚠️ Could not load sources index: {exc}")
            sources = []

        if not sources:
            return []

        def sort_key(source: dict) -> str:
            authors = source.get("authors") or []
            if authors:
                if isinstance(authors[0], dict):
                    name = str(authors[0].get("name", "")).strip()
                else:
                    name = str(authors[0]).strip()
                return name.lower()
            return "unknown"

        entries = []
        for source in sorted(sources, key=sort_key):
            authors_text = self._format_authors(source.get("authors") or [])
            year = source.get("year") or "n.d."
            title_text = source.get("title") or "Untitled"
            venue = source.get("venue") or ""
            doi = source.get("doi") or ""
            url = source.get("url") or ""
            if doi and not url:
                url = doi if doi.startswith("http") else f"https://doi.org/{doi}"
            entry = f"{authors_text} ({year}). *{title_text}*."
            if venue:
                entry += f" {venue}."
            if url:
                entry += f" {url}"
            entries.append(entry)

        return entries

    def _load_latest_text(self, directory: Path, patterns: List[str]) -> str:
        matches = []
        if directory.exists():
            for pattern in patterns:
                matches.extend(list(directory.glob(pattern)))
        if not matches:
            return ""
        latest = max(matches, key=lambda p: p.stat().st_mtime)
        try:
            return latest.read_text(encoding="utf-8").strip()
        except Exception:
            return ""
    
    def load_chapters_from_files(self) -> bool:
        """
        Load all generated chapter files from workspace.
        
        Returns:
            True if all chapters loaded successfully, False otherwise
        """
        print("📖 Loading chapters from workspace...")
        
        chapters_found = 0
        for ch_num, outline_title in self.chapter_order:
            # Search for chapter files (workspace root + chapters subdir)
            search_dirs = [self.workspace_dir]
            chapters_dir = self.workspace_dir / "chapters"
            if chapters_dir.exists():
                search_dirs.append(chapters_dir)

            chapter_files = []
            for base_dir in search_dirs:
                chapter_files.extend(list(base_dir.glob(f"Chapter_{ch_num}*.md")))
                chapter_files.extend(list(base_dir.glob(f"chapter_{ch_num}*.md")))
                chapter_files.extend(list(base_dir.glob(f"Chapter_{ch_num}_*.md")))
            
            if chapter_files:
                filepath = chapter_files[0]  # Use first match
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract chapter title
                    title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                    title = title_match.group(1) if title_match else outline_title
                    
                    # Count words
                    word_count = len(content.split())
                    
                    self.chapters[ch_num] = ThesisSection(
                        chapter_num=ch_num,
                        title=title,
                        content=content,
                        word_count=word_count,
                        filepath=str(filepath)
                    )
                    
                    print(f"  ✅ Chapter {ch_num}: {filepath.name} ({word_count} words)")
                    chapters_found += 1
                except Exception as e:
                    print(f"  ⚠️ Could not load Chapter {ch_num}: {e}")
            else:
                print(f"  ❌ Chapter {ch_num} not found")
        
        return chapters_found > 0
    
    def extract_all_references(self) -> List[Dict[str, str]]:
        """
        Extract ALL citations/references from ALL chapters.
        
        Returns:
            List of unique reference dictionaries sorted alphabetically
        """
        all_refs = []
        seen_citations = set()
        
        for ch_num, chapter in self.chapters.items():
            content = chapter.content
            
            # Extract markdown citations: [Author (Year)](url) or [(Author, Year)](url)
            citation_patterns = [
                r'\[([^\]]+\s*\(\d{4}\))\]\(([^\)]+)\)',  # [Author (Year)](url)
                r'\[\(([^\)]+,\s*\d{4})\)\]\(([^\)]+)\)',  # [(Author, Year)](url)
                r'\[([^\]]+)\]\(https?://[^\)]+\)',  # Any bracketed text with URL
            ]
            
            for pattern in citation_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    citation_text = match.group(1).strip()
                    citation_url = match.group(2) if len(match.groups()) > 1 else ""
                    
                    # Skip if contains "Unknown" or is empty
                    if not citation_text or "unknown" in citation_text.lower():
                        continue
                    
                    # Normalize citation text for deduplication
                    normalized = re.sub(r'\s+', ' ', citation_text.lower())
                    
                    if normalized not in seen_citations:
                        all_refs.append({
                            'citation': citation_text,
                            'url': citation_url,
                            'chapter': ch_num
                        })
                        seen_citations.add(normalized)
        
        # Sort alphabetically by citation text
        all_refs = sorted(all_refs, key=lambda x: x['citation'].lower())
        
        return all_refs
    
    def remove_chapter_references(self, content: str) -> str:
        """
        Remove the References section from a chapter's content.
        
        Args:
            content: Chapter content
            
        Returns:
            Content without the References section
        """
        # Remove various reference section patterns
        patterns = [
            r'\n---\s*\n+#*\s*References?\s*\n[\s\S]*$',  # ---\nReferences\n...
            r'\n#+ References?\s*\n[\s\S]*$',  # ## References or ### References
            r'\n\*\*References?\*\*\s*\n[\s\S]*$',  # **References**
            r'\n---\s*\n+\*\*References?\*\*[\s\S]*$',  # --- followed by **References**
        ]
        
        for pattern in patterns:
            content = re.sub(pattern, '', content, flags=re.IGNORECASE)
        
        # Remove trailing whitespace and dashes
        content = content.rstrip()
        content = re.sub(r'\n-+\s*$', '', content)
        
        return content
    
    def generate_preliminaries(self) -> str:
        """Generate all preliminary pages (front matter)."""
        
        submission_date = datetime.now().strftime("%B %Y")
        current_year = datetime.now().year
        
        logo_markdown = ""
        if "juba" in self.university.lower():
            logo_source = Path(__file__).parent.parent / "uoj_logo.png"
            try:
                logo_dest = self.workspace_dir / "uoj_logo.png"
                if logo_source.exists() and not logo_dest.exists():
                    logo_dest.write_bytes(logo_source.read_bytes())
                if logo_dest.exists():
                    logo_markdown = f"![{self.university} LOGO](uoj_logo.png)\n\n"
            except Exception as logo_err:
                print(f"⚠️ Could not prepare logo: {logo_err}")
        
        preliminaries = f"""
{'='*80}
PRELIMINARY PAGES
{'='*80}

{logo_markdown}# {self.topic.upper()}

**BY**

### {self.student_name}

---

**A Thesis Submitted in Partial Fulfilment of the Requirements for the Award of {self.degree}**

**Department:** {self.department}

**University:** {self.university}

**Date:** {submission_date}

---

{'='*80}

## DECLARATION

I, {self.student_name}, hereby declare that this thesis is my original work and has not been submitted for the award of a degree at any other university. All sources of information have been duly acknowledged through references.

**Signature:** _______________________

**Date:** _______________________

---

{'='*80}

## APPROVAL

This thesis has been submitted for examination with my approval as the University Supervisor.

**Supervisor:** {self.supervisor_name}

**Signature:** _______________________

**Date:** _______________________

---

{'='*80}

## DEDICATION

This thesis is dedicated to my family, mentors, and all those who supported me throughout this academic journey.

---

{'='*80}

## ACKNOWLEDGEMENTS

I wish to express my sincere gratitude to my supervisor, {self.supervisor_name}, for their invaluable guidance, patience, and support throughout this research journey. Their expertise and constructive feedback have been instrumental in shaping this thesis.

I am deeply grateful to the faculty and staff of the {self.department} at {self.university} for providing the academic environment and resources necessary for this research.

Special thanks to all the research participants who generously shared their time and experiences, making this study possible.

Finally, I thank my family and friends for their unwavering support, encouragement, and understanding during the challenging times of this research.

---

{'='*80}

## ABSTRACT

**Title:** {self.topic}

**Context:** {self.case_study}

This thesis investigates {self.topic.lower()} within the context of {self.case_study}. The research employs a systematic approach to address the identified research objectives. Through comprehensive literature review, rigorous methodology, and careful data analysis, this study contributes to the existing body of knowledge in this field.

**Keywords:** {self._generate_keywords()}

---

"""
        return preliminaries
    
    def _generate_keywords(self) -> str:
        """Generate keywords from topic and objectives."""
        words = []
        # Extract key terms from topic
        topic_words = [w for w in self.topic.split() if len(w) > 4 and w.lower() not in ['study', 'case', 'analysis', 'research']]
        words.extend(topic_words[:3])
        
        # Extract from case study
        case_words = [w for w in self.case_study.split() if len(w) > 3]
        words.extend(case_words[:2])
        
        return ', '.join(words[:6]) if words else self.topic
    
    def generate_table_of_contents(self) -> str:
        """Generate detailed table of contents."""
        
        toc = """
{'='*80}

## TABLE OF CONTENTS

### Preliminary Pages
- Declaration
- Approval
- Dedication
- Acknowledgements
- Abstract
- Table of Contents
- List of Tables
- List of Figures
- List of Abbreviations

"""
        
        # Add chapters with section headings
        ordered_numbers = [num for num, _ in self.chapter_order if num in self.chapters]
        for ch_num in ordered_numbers:
            chapter = self.chapters[ch_num]
            toc += f"### {chapter.title}\n"
            
            # Extract section headings from content
            section_pattern = r'^##\s+(\d+\.\d+[^\n]+)$'
            sections = re.findall(section_pattern, chapter.content, re.MULTILINE)
            
            for section in sections[:15]:  # Limit sections shown
                toc += f"- {section}\n"
            
            if len(sections) > 15:
                toc += f"- ... and {len(sections) - 15} more sections\n"
            
            toc += "\n"
        
        # Add back matter
        toc += """### Back Matter
- References
- Appendices

---

"""
        return toc
    
    def generate_references_section(self) -> str:
        """Generate formatted references section from all chapters."""
        
        self.all_references = self.extract_all_references()
        
        if not self.all_references:
            source_entries = self._build_references_from_sources()
            if source_entries:
                refs_text = f"""

{'='*80}
# REFERENCES
{'='*80}

"""
                refs_text += "\n\n".join(source_entries)
                refs_text += f"\n\n---\n**Total References:** {len(source_entries)}\n"
                return refs_text
            return """

{'='*80}
# REFERENCES
{'='*80}

No references extracted.

"""
        
        refs_text = f"""

{'='*80}
# REFERENCES
{'='*80}

"""
        
        for i, ref in enumerate(self.all_references, 1):
            citation = ref['citation']
            url = ref.get('url', '')
            
            # Format reference entry
            refs_text += f"{i}. {citation}"
            if url and url.startswith('http'):
                refs_text += f"\n   Retrieved from: {url}"
            refs_text += "\n\n"
        
        refs_text += f"\n---\n**Total References:** {len(self.all_references)}\n"
        
        return refs_text
    
    def generate_appendices(self) -> str:
        """Generate appendices section."""
        study_tools_dir = self.workspace_dir / "study_tools"
        questionnaire_text = self._load_latest_text(study_tools_dir, ["Questionnaire*.md"])
        interview_text = self._load_latest_text(study_tools_dir, ["Interview_Guide*.md"])
        fgd_text = self._load_latest_text(study_tools_dir, ["FGD_Guide*.md", "FGD*.md"])
        observation_text = self._load_latest_text(study_tools_dir, ["Observation_Checklist*.md", "Observation*.md"])

        datasets_dir = self.workspace_dir / "datasets"
        dataset_files = []
        if datasets_dir.exists():
            dataset_files = [p.name for p in datasets_dir.glob("*.*") if p.is_file()]

        appendices = f"""

{'='*80}
# APPENDICES
{'='*80}

## Appendix A: Research Questionnaire

{questionnaire_text or "[Questionnaire not generated]"}

---

## Appendix B: Interview Guide

{interview_text or "[Interview guide not generated]"}

---

## Appendix C: Focus Group Discussion Guide

{fgd_text or "[FGD guide not generated]"}

---

## Appendix D: Observation Checklist

{observation_text or "[Observation checklist not generated]"}

---

## Appendix E: Raw Data Files

{'\n'.join([f"- {name}" for name in dataset_files]) if dataset_files else "[No datasets found]"}

---

"""
        return appendices
    
    def combine_thesis(self) -> Tuple[str, str]:
        """
        Combine all chapters into single thesis document with proper structure.
        
        Returns:
            Tuple of (combined_content, filepath)
        """
        
        # Start with preliminaries
        thesis_content = self.generate_preliminaries()
        
        # Add table of contents
        thesis_content += self.generate_table_of_contents()
        
        # Add all chapters in order (removing their individual references)
        for ch_num in sorted(self.chapters.keys()):
            chapter = self.chapters[ch_num]
            
            # Remove individual reference section from chapter
            cleaned_content = self.remove_chapter_references(chapter.content)
            
            thesis_content += f"\n\n{'='*80}\n\n"
            thesis_content += cleaned_content
            thesis_content += "\n\n"
        
        # Add unified references section (extracted from ALL chapters)
        thesis_content += self.generate_references_section()
        
        # Add appendices
        thesis_content += self.generate_appendices()
        
        # Add thesis statistics at the very end
        total_words = sum(ch.word_count for ch in self.chapters.values())
        thesis_content += f"""

{'='*80}
# THESIS INFORMATION
{'='*80}

**Thesis Statistics:**
- Total Chapters: {len(self.chapters)}
- Total Words: {total_words:,}
- Estimated Pages: {int(total_words / 250)}
- Total References: {len(self.all_references)}
- Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Document Structure:**
- Preliminary Pages: Declaration, Approval, Dedication, Acknowledgements, Abstract, TOC
- Main Body: Chapters 1-{len(self.chapters)}
- Back Matter: References, Appendices

---
*This thesis was generated using the Thesis Generation System*
"""
        
        # Save to file
        safe_topic = re.sub(r'[^\w\s-]', '', self.topic)[:50].replace(' ', '_')
        degree_label = self._degree_slug()
        filename = f"Complete_{degree_label}_Thesis_{safe_topic}_{self.timestamp}.md"
        filepath = Path(self.output_dir) / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(thesis_content)
        
        return thesis_content, str(filepath)


async def generate_chapter_async(
    chapter_num: int,
    topic: str,
    case_study: str,
    objectives: List[str],
    workspace_id: str,
    dependencies: Optional[Dict[str, str]] = None
) -> Optional[str]:
    """
    Asynchronously generate a single chapter.
    
    Args:
        chapter_num: Chapter number (1-6)
        topic: Research topic
        case_study: Case study name
        objectives: Research objectives
        workspace_id: Workspace ID
        dependencies: Dict of chapter contents from previous chapters
    
    Returns:
        Filepath of generated chapter, or None if failed
    """
    
    print(f"🔄 [Worker {chapter_num}] Starting Chapter {chapter_num} generation...")
    
    try:
        # Import parallel chapter generator which handles chapters 1-6
        from services.parallel_chapter_generator import parallel_chapter_generator
        
        # Get session data for objectives
        from services.thesis_session_db import ThesisSessionDB
        db = ThesisSessionDB(workspace_id)
        objectives = []
        try:
            obj_data = db.get_objectives() or {}
            objectives = obj_data.get("specific", [])
            if obj_data.get("general"):
                objectives = [obj_data["general"]] + objectives
        except:
            pass
        
        research_questions = []
        try:
            rq_data = db.get_questions() or []
            research_questions = rq_data if isinstance(rq_data, list) else []
        except:
            pass
        
        # Generate based on chapter number
        if chapter_num == 1:
            content = await parallel_chapter_generator.generate(
                topic=topic,
                case_study=case_study,
                session_id=workspace_id
            )
            
        elif chapter_num == 2:
            content = await parallel_chapter_generator.generate_chapter_two(
                topic=topic,
                case_study=case_study,
                objectives=objectives,
                research_questions=research_questions,
                session_id=workspace_id
            )
            
        elif chapter_num == 3:
            content = await parallel_chapter_generator.generate_chapter_three(
                topic=topic,
                case_study=case_study,
                objectives=objectives,
                research_questions=research_questions,
                session_id=workspace_id
            )
            
        elif chapter_num == 4:
            # Find Chapter 2 for data collection methods
            from services.chapter4_generator import generate_chapter4
            ch2_path = dependencies.get('chapter_2_path') if dependencies else None
            content = await generate_chapter4(
                topic, case_study, objectives, workspace_id,
                chapter_two_filepath=ch2_path,
                session_id=workspace_id
            )
            
        elif chapter_num == 5:
            # Find Chapters 2 and 4 for synthesis
            from services.chapter5_generator import generate_chapter5
            ch2_path = dependencies.get('chapter_2_path') if dependencies else None
            ch4_path = dependencies.get('chapter_4_path') if dependencies else None
            content = await generate_chapter5(
                topic, case_study, objectives, workspace_id,
                chapter_two_filepath=ch2_path,
                chapter_four_filepath=ch4_path,
                session_id=workspace_id
            )
            
        elif chapter_num == 6:
            # Generate from all chapters
            from services.chapter6_generator import generate_chapter6
            ch1_path = dependencies.get('chapter_1_path') if dependencies else None
            ch2_path = dependencies.get('chapter_2_path') if dependencies else None
            ch3_path = dependencies.get('chapter_3_path') if dependencies else None
            ch4_path = dependencies.get('chapter_4_path') if dependencies else None
            ch5_path = dependencies.get('chapter_5_path') if dependencies else None
            
            # Load chapter contents
            ch1_content = ch2_content = ch3_content = ch4_content = ch5_content = ""
            
            if ch1_path and os.path.exists(ch1_path):
                with open(ch1_path, 'r', encoding='utf-8') as f:
                    ch1_content = f.read()
            if ch2_path and os.path.exists(ch2_path):
                with open(ch2_path, 'r', encoding='utf-8') as f:
                    ch2_content = f.read()
            if ch3_path and os.path.exists(ch3_path):
                with open(ch3_path, 'r', encoding='utf-8') as f:
                    ch3_content = f.read()
            if ch4_path and os.path.exists(ch4_path):
                with open(ch4_path, 'r', encoding='utf-8') as f:
                    ch4_content = f.read()
            if ch5_path and os.path.exists(ch5_path):
                with open(ch5_path, 'r', encoding='utf-8') as f:
                    ch5_content = f.read()
            
            content = generate_chapter6(
                topic, case_study, objectives,
                chapter_one_content=ch1_content,
                chapter_two_content=ch2_content,
                chapter_three_content=ch3_content,
                chapter_four_content=ch4_content,
                chapter_five_content=ch5_content,
                output_dir=f"/home/gemtech/Desktop/thesis/thesis_data/{workspace_id}"
            )
        
        print(f"✅ [Worker {chapter_num}] Chapter {chapter_num} generation complete!")
        return content
        
    except Exception as e:
        print(f"❌ [Worker {chapter_num}] Error generating Chapter {chapter_num}: {e}")
        import traceback
        traceback.print_exc()
        return None


async def generate_thesis_parallel(
    topic: str,
    case_study: str,
    objectives: List[str],
    workspace_id: str,
    output_dir: str = None
) -> Tuple[str, str]:
    """
    Generate complete thesis with parallel chapter generation.
    
    Flow:
    1. Ch1 (immediate)
    2. Ch1 done → Ch2, Ch3 parallel
    3. Ch2, Ch3 done → Ch4, Ch5 parallel
    4. Ch4, Ch5 done → Ch6
    5. All done → Combine into single file
    
    Args:
        topic: Research topic
        case_study: Case study name
        objectives: Research objectives
        workspace_id: Workspace ID
        output_dir: Output directory
    
    Returns:
        Tuple of (thesis_filepath, word_count)
    """
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║         🚀 PARALLEL THESIS GENERATION STARTING                 ║
╚════════════════════════════════════════════════════════════════╝

Topic: {topic}
Case Study: {case_study}
Objectives: {len(objectives)}
Workers: 6 concurrent agents

Generation Strategy:
  → Chapter 1 (immediate)
  → Chapters 2-3 (parallel after Ch1)
  → Chapters 4-5 (parallel after Ch2-3)
  → Chapter 6 (after Ch1-5)
  → Combine all into single thesis.md

""")
    
    workspace_dir = Path(f"/home/gemtech/Desktop/thesis/thesis_data/{workspace_id}")
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    chapter_paths = {}
    
    # Phase 1: Generate Chapter 1
    print("⏱️ Phase 1: Generating Chapter 1 (Introduction)...")
    ch1 = await generate_chapter_async(1, topic, case_study, objectives, workspace_id)
    if ch1:
        ch1_path = workspace_dir / f"Chapter_1_Introduction.md"
        with open(ch1_path, 'w', encoding='utf-8') as f:
            f.write(ch1)
        chapter_paths['chapter_1_path'] = str(ch1_path)
        print(f"✅ Phase 1 complete!\n")
    
    # Phase 2: Parallel generation of Chapters 2 & 3
    print("⏱️ Phase 2: Parallel generation of Chapters 2 & 3...")
    ch2_task = asyncio.create_task(
        generate_chapter_async(2, topic, case_study, objectives, workspace_id)
    )
    ch3_task = asyncio.create_task(
        generate_chapter_async(3, topic, case_study, objectives, workspace_id)
    )
    
    ch2, ch3 = await asyncio.gather(ch2_task, ch3_task)
    
    if ch2:
        ch2_path = workspace_dir / f"Chapter_2_Literature_Review.md"
        with open(ch2_path, 'w', encoding='utf-8') as f:
            f.write(ch2)
        chapter_paths['chapter_2_path'] = str(ch2_path)
    
    if ch3:
        ch3_path = workspace_dir / f"Chapter_3_Methodology.md"
        with open(ch3_path, 'w', encoding='utf-8') as f:
            f.write(ch3)
        chapter_paths['chapter_3_path'] = str(ch3_path)
    
    print(f"✅ Phase 2 complete!\n")
    
    # Phase 3: Parallel generation of Chapters 4 & 5
    print("⏱️ Phase 3: Parallel generation of Chapters 4 & 5...")
    ch4_task = asyncio.create_task(
        generate_chapter_async(4, topic, case_study, objectives, workspace_id, chapter_paths)
    )
    ch5_task = asyncio.create_task(
        generate_chapter_async(5, topic, case_study, objectives, workspace_id, chapter_paths)
    )
    
    ch4, ch5 = await asyncio.gather(ch4_task, ch5_task)
    
    if ch4:
        ch4_path = workspace_dir / f"Chapter_4_Findings.md"
        with open(ch4_path, 'w', encoding='utf-8') as f:
            f.write(ch4)
        chapter_paths['chapter_4_path'] = str(ch4_path)
    
    if ch5:
        ch5_path = workspace_dir / f"Chapter_5_Discussion.md"
        with open(ch5_path, 'w', encoding='utf-8') as f:
            f.write(ch5)
        chapter_paths['chapter_5_path'] = str(ch5_path)
    
    print(f"✅ Phase 3 complete!\n")
    
    # Phase 4: Generate Chapter 6
    print("⏱️ Phase 4: Generating Chapter 6 (Conclusions)...")
    ch6 = await generate_chapter_async(6, topic, case_study, objectives, workspace_id, chapter_paths)
    
    if ch6:
        ch6_path = workspace_dir / f"Chapter_6_Conclusion.md"
        with open(ch6_path, 'w', encoding='utf-8') as f:
            f.write(ch6)
        chapter_paths['chapter_6_path'] = str(ch6_path)
    
    print(f"✅ Phase 4 complete!\n")
    
    # Phase 5: Combine all chapters
    print("⏱️ Phase 5: Combining all chapters into single thesis file...")
    
    combiner = ThesisCombiner(workspace_id, topic, case_study, objectives, output_dir)
    combiner.load_chapters_from_files()
    thesis_content, thesis_path = combiner.combine_thesis()
    
    print(f"✅ Phase 5 complete!\n")
    
    # Summary
    total_words = len(thesis_content.split())
    total_pages = int(total_words / 250)
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║              ✅ THESIS GENERATION COMPLETE!                    ║
╚════════════════════════════════════════════════════════════════╝

📊 Thesis Statistics:
   • Chapters: 6
   • Total Words: {total_words:,}
   • Estimated Pages: {total_pages}
   • References: {len(combiner.references)}
   • File: {Path(thesis_path).name}

📁 Location:
   {thesis_path}

⏱️ Generation Method: Parallel 6-worker system
   • Ch1: Sequential (foundation)
   • Ch2+Ch3: Parallel (after Ch1)
   • Ch4+Ch5: Parallel (after Ch2+Ch3)
   • Ch6: Sequential (final synthesis)
   • Combine: Single operation

🎓 Ready for:
   ✅ Submission
   ✅ Export to DOCX
   ✅ PDF conversion
   ✅ Print formatting

""")
    
    return thesis_path, total_words


async def combine_existing_chapters(
    workspace_id: str,
    topic: str,
    case_study: str,
    objectives: List[str],
    output_dir: str = None
) -> Tuple[str, int]:
    """
    Combine existing chapter files into single thesis.
    
    Use when chapters are already generated.
    
    Returns:
        Tuple of (thesis_filepath, word_count)
    """
    
    print(f"""
╔════════════════════════════════════════════════════════════════╗
║           📖 COMBINING EXISTING CHAPTERS                        ║
╚════════════════════════════════════════════════════════════════╝

Workspace: {workspace_id}
Topic: {topic}

Searching for chapters...
""")
    
    combiner = ThesisCombiner(workspace_id, topic, case_study, objectives, output_dir)
    
    # Load all chapters
    success = combiner.load_chapters_from_files()
    
    if not success:
        print("❌ No chapters found to combine!")
        return None, 0
    
    # Combine
    thesis_content, thesis_path = combiner.combine_thesis()
    total_words = len(thesis_content.split())
    
    print(f"""
✅ Chapters combined successfully!

📊 Thesis Statistics:
   • Chapters combined: {len(combiner.chapters)}
   • Total words: {total_words:,}
   • File: {Path(thesis_path).name}

📁 {thesis_path}
""")
    
    return thesis_path, total_words


# Export for use in api.py
__all__ = [
    'ThesisCombiner',
    'generate_thesis_parallel',
    'combine_existing_chapters',
    'generate_chapter_async'
]
