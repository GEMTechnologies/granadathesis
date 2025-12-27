# Chapter 3 Methodology Prompt Methods - Add these to WriterSwarm class

    def _build_methodology_intro_prompt(self, section_id: str, title: str) -> str:
        """Build prompt for methodology chapter introduction."""
        return f"""Write section "{section_id} {title}" for Chapter Three: Research Methodology.

TOPIC: {self.state.topic}
CASE STUDY: {self.state.case_study}

Write 3 clear paragraphs:

**Paragraph 1**: Restate the Research Problem
- Briefly remind the reader of the core research problem being investigated
- Reference the research objectives from Chapter One

**Paragraph 2**: Chapter Purpose  
- Explain that this chapter presents the systematic approach used to address the research questions
- Emphasize the importance of methodological rigor in PhD research

**Paragraph 3**: Chapter Roadmap
- Provide a clear overview of all 11 sections (3.1 through 3.11)
- List them in order: Research Philosophy, Research Design, Target Population, Sampling Design, Sample Size, Data Collection Instruments, Validity & Reliability, Data Collection Procedures, Data Analysis, and Ethical Considerations

REQUIREMENTS:
- Academic formal tone, concise and clear
- Do NOT include citations in the introduction
- Do NOT include the section heading

Write the content now:
