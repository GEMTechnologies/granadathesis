"""
Research Proposal Generator for HCR7017
Generates a detailed 5000-word research proposal with real APA 7 citations and tables.
"""
import asyncio
from typing import List, Dict, Any
from pathlib import Path
from datetime import datetime
from services.academic_search import academic_search_service
from services.deepseek_direct import deepseek_direct_service

class ResearchProposalGenerator:
    def __init__(self):
        self.topic = "Evaluating the Efficacy of a Community-Based Intervention to Improve Mental Health Service Access and Outcomes for Refugees and Asylum Seekers in the United Kingdom"
        self.short_topic = "community-based mental health intervention for refugees UK"
        self.all_citations: List[Dict[str, Any]] = []
        
    async def generate_proposal(self) -> str:
        """Orchestrate the generation of the full proposal."""
        
        # Define sections based on HCR7017 Brief
        # Tuples of (Function, Word Count)
        sections = [
            (self.generate_intro, 800),
            (self.generate_lit_review, 1500), # Increased for depth
            (self.generate_aims, 500),
            (self.generate_methods, 1200),
            (self.generate_ethics, 800),
            (self.generate_discussion, 1000),
            (self.generate_dissemination, 500),
            (self.generate_conclusion, 400)
        ]
        
        print("🚀 Starting Refined 5000-word HCR7017 Proposal Generation (APA 7 + Deep Analysis)...")
        
        # Execute in parallel 
        tasks = [func(count) for func, count in sections]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine Content
        full_content = f"""# Research Proposal: HCR7017 Research Methods

**Proposal Title**: {self.topic}
**Student Number**: [STU Number]
**Module**: HCR7017 Research Methods
**Date of Submission**: {datetime.now().strftime('%Y-%m-%d')}
**Word Count Target**: ~6000 words (Critical Deep Dive)

---

"""
        
        for i, content in enumerate(results):
            if isinstance(content, Exception):
                print(f"❌ Section {i} failed: {content}")
                full_content += f"## Section {i} Failed\n\n> Error: {content}\n\n"
            else:
                full_content += content + "\n\n"
                
        # Generate Reference List
        refs_content = self.format_references()
        full_content += refs_content
            
        return full_content

    async def _search_and_write(self, section_name: str, query: str, prompt_instructions: str, word_count: int) -> str:
        """Helper to search for papers and write a section with deep analysis."""
        print(f"🔍 Searching for terms related to {section_name}...")
        
        # 1. Search
        citations_text = ""
        citation_limit = 8 # Get more papers for depth
        
        try:
            papers = await academic_search_service.search_academic_papers(query, max_results=citation_limit)
            
            citations_list_formatted = []
            for p in papers:
                # Add to global list for bibliography
                self.all_citations.append(p)
                
                # Format for LLM context
                authors = ", ".join([a.get('name', '') for a in p.get('authors', [])])
                year = p.get('year', 'n.d.')
                title = p.get('title', 'Unknown Title')
                citations_list_formatted.append(f"- {title} by {authors} ({year}). Abstract: {p.get('abstract', '')[:200]}...")
            
            citations_text = "\n".join(citations_list_formatted)
            
        except Exception as e:
            print(f"⚠️ Search failed for {section_name}: {e}")
            citations_text = "No specific citations found. Use general academic knowledge."
        
        # 2. Write
        print(f"✍️ Writing {section_name} ({word_count} words)...")
        prompt = f"""
        You are an expert PhD-level academic researcher writing a Research Proposal (HCR7017).
        
        **SECTION**: {section_name}
        **TOPIC**: {self.topic}
        **TARGET WORD COUNT**: {word_count} words (Aim for MAX depth)
        
        **CRITICAL INSTRUCTIONS**:
        1. **STRICT APA 7 CITATIONS**: You MUST cite sources in the text using standard APA 7 format, e.g., (Smith, 2023) or "Smith (2023) argues...". Do NOT use markdown links [Author](url). The Reference List will be generated separately.
        2. **DEEP CRITICAL ANALYSIS**: Do not just describe. Critically evaluate, synthesize, and contrast findings. Discuss theoretical frameworks, methodological limitations of previous studies, and systemic issues.
        3. **NO BULLET POINTS**: Write in dense, sophisticated academic prose.
        4. **USE REAL DATA**: Use the provided sources to back up your claims with specific findings.
        5. **STRUCTURE**: Use sub-headings (###) to organize deep content if necessary.
        6. {prompt_instructions}
        
        **AVAILABLE SOURCES TO CITE**:
        {citations_text}
        """
        
        content = await deepseek_direct_service.generate_content(prompt, max_tokens=4000)
        return f"## {section_name}\n\n{content}"

    def format_references(self) -> str:
        """Format the collected references into an APA 7 Bibliography."""
        print("📚 Compiling Reference List...")
        
        # Deduplicate by Title
        unique_refs = {}
        for p in self.all_citations:
            title = p.get('title', '').strip()
            if title and title not in unique_refs:
                unique_refs[title] = p
        
        def get_author_sort_key(paper):
            authors = paper.get('authors', [])
            if authors and isinstance(authors, list) and len(authors) > 0:
                first_author = authors[0]
                if isinstance(first_author, dict):
                    return first_author.get('name', '')
                return str(first_author)
            return 'Unknown'

        sorted_refs = sorted(unique_refs.values(), key=get_author_sort_key)
        
        ref_list = "## References\n\n"
        
        for p in sorted_refs:
            # APA 7 Format Logic
            authors_list = p.get('authors', [])
            if not authors_list:
                author_text = "Unknown Author"
            elif len(authors_list) > 20:
                author_text = ", ".join([a.get('name', '') for a in authors_list[:19]]) + ", ... " + authors_list[-1].get('name', '')
            else:
                author_text = ", ".join([a.get('name', '') for a in authors_list])
            
            year = f"({p.get('year')})" if p.get('year') else "(n.d.)"
            title = f"*{p.get('title')}*"
            venue = p.get('venue', '')
            url = p.get('url', '')
            doi = p.get('externalIds', {}).get('DOI', '')
            
            # Construct entry
            entry = f"{author_text}. {year}. {title}."
            if venue:
                entry += f" {venue}."
            if doi:
                entry += f" https://doi.org/{doi}"
            elif url:
                entry += f" {url}"
            
            ref_list += f"{entry}\n\n"
            
        return ref_list

    async def generate_intro(self, wc):
        return await self._search_and_write(
            "Introduction",
            f"mental health refugees UK public health crisis statistics {datetime.now().year - 1}",
            "Introduce the contemporary public health issue with statistical severity. Critically define the target population. Explain 'need for study' referencing NHS Long Term Plan and specific gaps in current provision.",
            wc
        )

    async def generate_lit_review(self, wc):
        return await self._search_and_write(
            "Review of the Literature",
            "refugee mental health barriers UK service access community intervention efficacy systematic review",
            "Critically analyse existing literature. Organize by themes: Systemic Barriers (Hostile Environment), Cultural Barriers, and Intervention Weaknesses. Highlight the 'Evidence Gap' regarding community-based interventions.",
            wc
        )

    async def generate_aims(self, wc):
        return await self._search_and_write(
            "Aims and Objectives",
            "medical research aims objectives structure",
            "State overarching aim. Detail 4 specific objectives (Quant, Qual, Implementation, Recommendations). Ensure they are SMART and directly address the literature gaps identified.",
            wc
        )

    async def generate_methods(self, wc):
        text = await self._search_and_write(
            "Study Design and Methods",
            "mixed methods research design health refugee intervention evaluation explanatory sequential",
            "Justify the Explanatory Sequential Mixed-Methods Design (QUAN -> qual). Detail 'Participant Recruitment' (Sample power calculation, inclusion/exclusion), 'Intervention' (The manualised 12-week program details), 'Data Collection' (Measures: CORE-OM, HTQ, PHQ-9), and 'Data Analysis' (LMM, Thematic Analysis).",
            wc
        )
        # Add table manually
        table = """
### Table 1: Quantitative Outcome Measures and Assessment Schedule

| Construct | Primary/Secondary | Measurement Tool | Time Points | Description/Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Psychological Distress** | Primary Outcome | CORE-OM (34 items) | T0, T1, T2 | Global distress measure (wellbeing, symptoms, functioning) |
| **PTSD Symptoms** | Secondary Outcome | Harvard Trauma Questionnaire (HTQ) | T0, T1, T2 | Trauma exposure and PTSD symptoms (DSM-5 aligned) |
| **Depressive Symptoms** | Secondary Outcome | PHQ-9 (9 items) | T0, T1, T2 | Depression severity |
| **Quality of Life** | Secondary Outcome | WHOQOL-BREF | T0, T1, T2 | Physical, psychological, social, environmental domains |
| **Service Utilisation** | Process Outcome | Bespoke Questionnaire | T0, T1, T2 | Tracks engagement with health/social services |
"""
        return text + "\n" + table

    async def generate_ethics(self, wc):
        return await self._search_and_write(
            "Ethical Considerations",
            "ethics refugee research informed consent vulnerable populations power dynamics",
            "Discuss 'Informed Consent' (Iterative, Translated). 'Confidentiality' (GDPR, Pseudonymisation). 'Duty of Care' (Trauma-informed protocols). 'Power Dynamics' (Researcher-participant relationship).",
            wc
        )

    async def generate_discussion(self, wc):
        return await self._search_and_write(
            "Discussion",
            "community mental health intervention outcomes refugees impact policy implications",
            "Discuss potential outcomes and their theoretical implications. methodological limitations. potential policy impact (NHS commissioning).",
            wc
        )

    async def generate_dissemination(self, wc):
        return await self._search_and_write(
            "Dissemination of Research Findings",
            "research dissemination strategies public health policy impact",
            "Detail strategy for: Academic (Journals), Policy (Briefs to Home Office), and Community (Workshops, visual summaries).",
            wc
        )

    async def generate_conclusion(self, wc):
        return await self._search_and_write(
            "Conclusion",
            "refugee mental health intervention conclusion summary",
            "Synthesize the proposal's value proposition. Reiterate the urgency and potential for systemic change.",
            wc
        )

# Runner
if __name__ == "__main__":
    generator = ResearchProposalGenerator()
    content = asyncio.run(generator.generate_proposal())
    
    # Save
    import os
    
    # Path
    path = Path("/home/gemtech/Desktop/thesis/HCR7017_Research_Proposal_Refined.md")
    with open(path, "w") as f:
        f.write(content)
    print(f"✅ Created refined proposal at {path}")
