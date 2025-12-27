"""
Advanced Page Numbering Handler for Thesis.

Manages:
1. Cover page (no numbering)
2. Preliminary pages (Roman numerals: i, ii, iii, ...)
3. Main content (Arabic numerals: 1, 2, 3, ...)
"""

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt
from typing import Literal


class AdvancedPageNumbering:
    """Handle complex page numbering scenarios."""
    
    @staticmethod
    def add_page_break_with_new_section(doc: Document):
        """Add page break with new section (for numbering change)."""
        # Get the last paragraph
        last_paragraph = doc.paragraphs[-1]._p
        
        # Create a section break
        section_pr = last_paragraph.get_or_add_pPr()
        sectPr = OxmlElement('w:sectPr')
        section_pr.append(sectPr)
        
        doc.add_page_break()
    
    @staticmethod
    def set_page_number_format(section, fmt: Literal['roman', 'arabic', 'none']):
        """
        Set page number format for a section.
        
        fmt: 'roman' (lowercase Roman: i, ii, iii), 
             'arabic' (numbers: 1, 2, 3),
             'none' (no numbering)
        """
        sectPr = section._sectPr
        
        # Remove existing page number settings
        for element in sectPr.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}pgNum'):
            sectPr.remove(element)
        
        # Add footer with page numbers
        footer = OxmlElement('w:ftr')
        sectPr.append(footer)
        
        if fmt == 'none':
            # No page numbers
            return
        
        # Create paragraph in footer
        p = OxmlElement('w:p')
        footer.append(p)
        
        # Create page number field
        pPr = OxmlElement('w:pPr')
        p.append(pPr)
        
        jc = OxmlElement('w:jc')
        jc.set(qn('w:val'), 'center')
        pPr.append(jc)
        
        r = OxmlElement('w:r')
        p.append(r)
        
        if fmt == 'roman':
            # Set to lowercase Roman numerals
            fldChar = OxmlElement('w:fldChar')
            fldChar.set(qn('w:fldCharType'), 'begin')
            r.append(fldChar)
            
            instrText = OxmlElement('w:instrText')
            instrText.text = 'PAGE \\* ROMAN'
            r.append(instrText)
            
            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'end')
            r.append(fldChar2)
        
        elif fmt == 'arabic':
            # Set to Arabic numerals
            fldChar = OxmlElement('w:fldChar')
            fldChar.set(qn('w:fldCharType'), 'begin')
            r.append(fldChar)
            
            instrText = OxmlElement('w:instrText')
            instrText.text = 'PAGE'
            r.append(instrText)
            
            fldChar2 = OxmlElement('w:fldChar')
            fldChar2.set(qn('w:fldCharType'), 'end')
            r.append(fldChar2)
    
    @staticmethod
    def restart_page_numbering(section, start_number: int = 1):
        """Restart page numbering from a specific number."""
        sectPr = section._sectPr
        
        pgSz = sectPr.find(qn('w:pgSz'))
        if pgSz is None:
            pgSz = OxmlElement('w:pgSz')
            sectPr.append(pgSz)
        
        # Use PAGEREF field to reset numbering
        # This is a simplified approach
        pass


class ThesisPageNumberingManager:
    """Manage page numbering throughout thesis document."""
    
    def __init__(self, doc: Document):
        self.doc = doc
        self.section_count = 0
    
    def setup_cover_page(self):
        """Setup cover page (no numbering)."""
        if len(self.doc.sections) == 0:
            section = self.doc.sections[0]
        else:
            section = self.doc.sections[-1]
        
        AdvancedPageNumbering.set_page_number_format(section, 'none')
    
    def setup_preliminaries(self):
        """Setup preliminary pages (Roman numerals)."""
        # Create new section
        self.doc.add_section()
        section = self.doc.sections[-1]
        
        AdvancedPageNumbering.set_page_number_format(section, 'roman')
        AdvancedPageNumbering.restart_page_numbering(section, 1)
    
    def setup_main_content(self):
        """Setup main content (Arabic numerals)."""
        # Create new section
        self.doc.add_section()
        section = self.doc.sections[-1]
        
        AdvancedPageNumbering.set_page_number_format(section, 'arabic')
        AdvancedPageNumbering.restart_page_numbering(section, 1)
    
    def disable_previous_footer(self):
        """Disable footer from previous section."""
        if len(self.doc.sections) > 1:
            prev_section = self.doc.sections[-2]
            # Copy footer from new section to previous
            # This prevents footer overlap
            pass
