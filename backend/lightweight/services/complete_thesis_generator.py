"""
Complete Thesis Generator with Auto-Integration.

Generates chapters using LLM and automatically creates complete thesis
with all preliminary pages, table of contents, and proper formatting.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CompleteThesisGenerator:
    """Generate complete thesis automatically."""
    
    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        from services.workspace_service import WORKSPACES_DIR
        self.workspace_path = WORKSPACES_DIR / workspace_id
        self.workspace_path.mkdir(parents=True, exist_ok=True)
        
    async def generate_complete_thesis(
        self,
        title: str,
        author_name: str,
        index_no: str,
        school: str,
        department: str,
        degree: str = "PhD",
        chapter_count: int = 6,
        include_appendices: bool = True,
        auto_generate_content: bool = True,
        llm_callback=None  # Callback to LLM for content generation
    ) -> Dict:
        """
        Generate complete thesis with all sections.
        
        If auto_generate_content=True, will call llm_callback for each section.
        Otherwise, will use placeholders.
        """
        
        try:
            # Load or create thesis metadata
            metadata_file = self.workspace_path / ".thesis_metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = {
                    "title": title,
                    "author_name": author_name,
                    "index_no": index_no,
                    "school": school,
                    "department": department,
                    "degree": degree,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "status": "in_progress"
                }
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
            
            # Generate chapters
            chapters = {}
            for chapter_num in range(1, chapter_count + 1):
                chapter_title = self._get_chapter_title(chapter_num)
                
                if auto_generate_content and llm_callback:
                    # Generate chapter content using LLM
                    try:
                        chapter_content = await llm_callback(
                            f"Write Chapter {chapter_num}: {chapter_title} for PhD thesis on '{title}'",
                            context={
                                "chapter_number": chapter_num,
                                "thesis_title": title,
                                "author": author_name,
                                "degree": degree
                            }
                        )
                    except Exception as e:
                        logger.error(f"Error generating Chapter {chapter_num}: {e}")
                        chapter_content = f"[Chapter {chapter_num}: {chapter_title} - Content to be added]"
                else:
                    chapter_content = f"[Chapter {chapter_num}: {chapter_title} - Content to be added]"
                
                chapters[chapter_num] = chapter_content
                
                # Save chapter
                self._save_chapter(chapter_num, chapter_title, chapter_content)
            
            # Generate preliminary pages
            preliminary_pages = {
                "supervisor_approval": self._generate_approval_text(author_name),
                "student_declaration": self._generate_declaration_text(author_name),
                "dedication": self._generate_dedication_text(),
                "acknowledgement": self._generate_acknowledgement_text(),
                "abstract": self._generate_abstract(title, chapters)
            }
            
            # Generate appendices
            appendices = {}
            if include_appendices:
                appendix_titles = ["Research Methodology Details", "Data Collection Instruments", "Raw Data Sample"]
                for idx, app_title in enumerate(appendix_titles, 1):
                    app_name = f"Appendix {chr(65+idx-1)}: {app_title}"
                    appendices[app_name] = f"[Content for {app_name} to be added]"
            
            # Create complete thesis using ThesisFormatter
            from ..services.thesis_formatter import ThesisFormatter
            
            formatter = ThesisFormatter(workspace_id=self.workspace_id)
            thesis_file = formatter.create_complete_thesis(
                title=title,
                author_name=author_name,
                index_no=index_no,
                school=school,
                department=department,
                degree=degree,
                chapters=chapters,
                supervisor_approval=preliminary_pages["supervisor_approval"],
                student_declaration=preliminary_pages["student_declaration"],
                dedication=preliminary_pages["dedication"],
                acknowledgement=preliminary_pages["acknowledgement"],
                abstract=preliminary_pages["abstract"],
                appendices=appendices
            )
            
            # Update metadata
            metadata["status"] = "completed"
            metadata["updated_at"] = datetime.now().isoformat()
            metadata["thesis_file"] = thesis_file
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"✅ Complete thesis generated: {thesis_file}")
            
            return {
                "success": True,
                "thesis_file": thesis_file,
                "chapters": chapters,
                "preliminary_pages": preliminary_pages,
                "appendices": appendices,
                "metadata": metadata
            }
        
        except Exception as e:
            logger.error(f"❌ Error generating complete thesis: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    def _get_chapter_title(self, chapter_num: int) -> str:
        """Get default chapter title."""
        titles = {
            1: "Introduction",
            2: "Literature Review",
            3: "Methodology",
            4: "Results",
            5: "Discussion",
            6: "Conclusion and Recommendations"
        }
        return titles.get(chapter_num, f"Chapter {chapter_num}")
    
    def _generate_approval_text(self, supervisor_name: str) -> str:
        """Generate approval page text."""
        return f"""
APPROVAL

This research proposal has been approved by the thesis supervisor(s) for submission to the 
School of {self._get_school_name()} as part of the requirements for the award of a PhD degree.

Supervisor: ____________________
Name: ___________________________
Signature: _______________________
Date: _____________________________

Cosupervisor (if applicable): __________
Name: ___________________________
Signature: _______________________
Date: _____________________________
"""
    
    def _generate_declaration_text(self, student_name: str) -> str:
        """Generate declaration page text."""
        return f"""
DECLARATION

I, {student_name}, hereby declare that this research proposal is my original work and 
has not been submitted for any award in any other university.

I confirm that all sources of information used have been duly cited and acknowledged.

_______________________________
Student Name: {student_name}
Index No: _____________________
Signature: _____________________
Date: _____________________________
"""
    
    def _generate_dedication_text(self) -> str:
        """Generate dedication page text."""
        return """
DEDICATION

This thesis is dedicated to:

[Insert personal dedication - family members, mentors, institutions, or causes that 
have influenced this research work]
"""
    
    def _generate_acknowledgement_text(self) -> str:
        """Generate acknowledgement page text."""
        return """
ACKNOWLEDGEMENT

I wish to express my sincere gratitude to:

- My supervisors for their invaluable guidance and support throughout this research
- The School of [SCHOOL NAME] for providing necessary research facilities
- My family for their encouragement and patience
- All individuals and institutions that contributed to the success of this research

[Add specific acknowledgements to funding bodies, colleagues, and other contributors]
"""
    
    def _generate_abstract(self, title: str, chapters: Dict) -> str:
        """Generate abstract from thesis content."""
        return f"""
ABSTRACT

This thesis presents a comprehensive study on "{title}".

[The abstract will be automatically generated from the introduction and conclusion chapters]

Key findings and contributions:
[To be extracted from your thesis content]

The research methodology employed:
[To be extracted from Chapter 3]

Recommendations for future work:
[To be extracted from conclusions]

Keywords: [To be updated with your thesis keywords]
"""
    
    def _save_chapter(self, chapter_num: int, title: str, content: str):
        """Save chapter to workspace."""
        chapters_dir = self.workspace_path / ".chapters"
        chapters_dir.mkdir(exist_ok=True)
        
        chapter_file = chapters_dir / f"chapter_{chapter_num:02d}_{title.replace(' ', '_').lower()}.md"
        with open(chapter_file, 'w') as f:
            f.write(f"# Chapter {chapter_num}: {title}\n\n")
            f.write(content)
    
    def _get_school_name(self) -> str:
        """Get school name from metadata."""
        metadata_file = self.workspace_path / ".thesis_metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get("school", "SCIENCE")
        return "SCIENCE"
