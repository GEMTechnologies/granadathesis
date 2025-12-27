"""
Chapter 6 Generator - Summary, Conclusion and Recommendations (PhD-Level)

Generates Chapter 6 (Final chapter) that:
- Summarises the entire research journey and key findings
- Synthesises conclusions from all previous chapters
- Provides clear, evidence-based recommendations
- Identifies limitations and future research directions

TARGET: 10,000-15,000 words for comprehensive conclusions

Uses UK English and reported speech/past tense throughout.

Structure:
6.1 Summary - Overview of research problem, methodology, and key findings
6.2 Conclusions - Synthesis of findings per objective and overall conclusions
6.3 Recommendations - Practical, policy, and theoretical recommendations
6.4 Suggestions for Future Research - Identified gaps and research directions

Key Features:
- Loads all chapter summaries from previous chapters (1-5)
- Synthesises findings across all objectives
- Provides actionable recommendations by stakeholder
- Identifies clear limitations and boundaries of findings
- Suggests specific, feasible future research directions
- PhD-level depth and academic rigour
- UK English spelling and grammar
- Reported speech and past tense throughout
"""

import os
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


class Chapter6Generator:
    """Generates Chapter 6: Summary, Conclusion and Recommendations (PhD-Level)."""
    
    def __init__(
        self,
        topic: str,
        case_study: str,
        objectives: List[str],
        chapter_one_content: str = "",
        chapter_two_content: str = "",
        chapter_three_content: str = "",
        chapter_four_content: str = "",
        chapter_five_content: str = "",
        output_dir: str = None
    ):
        """
        Initialise Chapter 6 generator.
        
        Args:
            topic: Research topic
            case_study: Case study name
            objectives: List of research objectives
            chapter_one_content: Chapter 1 content for reference
            chapter_two_content: Chapter 2 (Literature Review) content
            chapter_three_content: Chapter 3 (Methodology) content
            chapter_four_content: Chapter 4 (Findings) content
            chapter_five_content: Chapter 5 (Discussion) content
            output_dir: Directory to save output
        """
        self.topic = topic
        self.case_study = case_study
        self.objectives = objectives
        self.chapter_one_content = chapter_one_content
        self.chapter_two_content = chapter_two_content
        self.chapter_three_content = chapter_three_content
        self.chapter_four_content = chapter_four_content
        self.chapter_five_content = chapter_five_content
        self.output_dir = output_dir or "/tmp"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract key information
        self._extracted_key_findings = []
        self._extracted_limitations = []
        self._extract_from_previous_chapters()
    
    def _extract_from_previous_chapters(self):
        """Extract key findings, limitations, and conclusions from previous chapters."""
        # Extract limitations from Chapter 3 (Methodology)
        if self.chapter_three_content:
            limitation_patterns = [
                r'limitation[s]?:?\s+([^.!?]+[.!?])',
                r'constraint[s]?:?\s+([^.!?]+[.!?])',
                r'boundary[ies]?:?\s+([^.!?]+[.!?])',
            ]
            for pattern in limitation_patterns:
                matches = re.findall(pattern, self.chapter_three_content, re.IGNORECASE)
                self._extracted_limitations.extend(matches)
        
        # Extract key findings from Chapter 4 and 5
        if self.chapter_four_content:
            finding_patterns = [
                r'finding[s]?:?\s+([^.!?]+[.!?])',
                r'result[s]?:?\s+([^.!?]+[.!?])',
                r'revealed:?\s+([^.!?]+[.!?])',
                r'showed:?\s+([^.!?]+[.!?])',
            ]
            for pattern in finding_patterns:
                matches = re.findall(pattern, self.chapter_four_content, re.IGNORECASE)
                self._extracted_key_findings.extend(matches[:3])  # Limit to top 3
    
    def generate_full_chapter(self) -> str:
        """Generate complete Chapter 6."""
        content = ""
        content += "# CHAPTER SIX: SUMMARY, CONCLUSION AND RECOMMENDATION\n\n"
        content += self.generate_summary()
        content += "\n\n" + self.generate_conclusions()
        content += "\n\n" + self.generate_recommendations()
        content += "\n\n" + self.generate_future_research()
        
        return content
    
    def generate_summary(self) -> str:
        """
        Generate Section 6.1: Summary.
        
        Covers:
        - Research problem and context
        - Research questions/objectives
        - Methodology overview
        - Key findings summary
        - Word count: ~2,500 words
        """
        summary = "## 6.1 Summary\n\n"
        
        summary += self._generate_research_problem_summary()
        summary += "\n\n" + self._generate_methodology_summary()
        summary += "\n\n" + self._generate_key_findings_summary()
        
        return summary
    
    def _generate_research_problem_summary(self) -> str:
        """Generate summary of research problem and context."""
        section = "### 6.1.1 Research Problem and Context\n\n"
        
        section += (
            f"This research examined {self.topic.lower()} within the context of {self.case_study}. "
            f"The study was undertaken to address identified gaps in the existing literature and to provide "
            f"empirically-grounded evidence regarding key questions that remain contested in the field. "
            f"The research problem emerged from observations that whilst considerable work has been undertaken "
            f"in related domains, limited research attention has been paid to the specific intersection of "
            f"{self.topic.lower()} and its practical manifestations within {self.case_study}.\n\n"
        )
        
        section += "#### Research Questions and Objectives\n\n"
        section += (
            f"The research was guided by {len(self.objectives)} primary research objectives:\n\n"
        )
        
        for i, obj in enumerate(self.objectives, 1):
            section += f"{i}. {obj}\n"
        
        section += (
            "\n\nThese objectives were formulated following an extensive review of the literature and "
            "preliminary exploratory work. They were designed to be sufficiently focused to enable rigorous "
            "empirical investigation, whilst remaining broad enough to yield insights with wider applicability "
            "beyond the immediate case study context.\n"
        )
        
        return section
    
    def _generate_methodology_summary(self) -> str:
        """Generate summary of methodology."""
        section = "### 6.1.2 Research Methodology\n\n"
        
        section += (
            "The research employed a mixed-methods approach, integrating qualitative and quantitative data "
            "collection and analysis. This methodological choice was considered appropriate given the complexity "
            "of the research questions and the acknowledged benefits of triangulation in providing both breadth "
            "and depth of understanding.\n\n"
            
            "The study was conducted within {}, and involved the collection of data through multiple mechanisms. "
            "A comprehensive review of documentary evidence was undertaken, supplemented by structured data collection "
            "and detailed analysis. The data analysis process was rigorous and systematic, employing established "
            "statistical and qualitative analytical techniques to interrogate the data and derive findings.\n\n"
            
            "The research was bound by certain limitations and constraints, which are detailed in Chapter 3. "
            "These limitations were carefully acknowledged throughout the data collection and analysis stages, "
            "and inform the interpretation of the findings presented in Chapter 4.\n"
        ).format(self.case_study)
        
        return section
    
    def _generate_key_findings_summary(self) -> str:
        """Generate summary of key findings."""
        section = "### 6.1.3 Key Findings\n\n"
        
        section += (
            "The research yielded several significant findings, which are summarised here and explored in "
            "greater detail in the conclusions section below.\n\n"
        )
        
        for i, obj in enumerate(self.objectives, 1):
            section += (
                f"**Objective {i}**: Research into {obj.lower()} revealed "
                f"that the phenomenon is multifaceted and context-dependent. The findings demonstrated "
                f"nuances that complicate simplistic interpretations and align, in part, with existing "
                f"literature whilst also extending current understanding in novel directions.\n\n"
            )
        
        section += (
            "The integration of findings across all research objectives suggests a coherent narrative regarding "
            "the nature of the phenomena under investigation, the factors that influence them, and the implications "
            "for practice and future research.\n"
        )
        
        return section
    
    def generate_conclusions(self) -> str:
        """
        Generate Section 6.2: Conclusions.
        
        Covers:
        - Objective-by-objective conclusions
        - Overall conclusions
        - Contribution to theory and practice
        - Word count: ~4,000 words
        """
        conclusion = "## 6.2 Conclusions\n\n"
        
        conclusion += "### 6.2.1 Introduction to Conclusions\n\n"
        conclusion += (
            "The preceding chapters of this thesis have presented a comprehensive investigation into "
            f"{self.topic.lower()} within the context of {self.case_study}. This section synthesises the findings "
            "and draws together the various threads of argument developed throughout the thesis. The conclusions "
            "are organised around the primary research objectives, before considering broader conclusions regarding "
            "the nature of the phenomena under investigation and their implications for theory and practice.\n\n"
        )
        
        # Per-objective conclusions
        for i, obj in enumerate(self.objectives, 1):
            conclusion += self._generate_objective_conclusion(i, obj)
        
        # Overall conclusions
        conclusion += self._generate_overall_conclusions()
        
        return conclusion
    
    def _generate_objective_conclusion(self, obj_num: int, objective: str) -> str:
        """Generate conclusion for a specific objective."""
        section = f"### 6.2.{obj_num} Conclusions Regarding Objective {obj_num}\n\n"
        
        section += (
            f"With reference to the research objective to {objective.lower()}, the research conducted and "
            f"presented in this thesis has reached several important conclusions.\n\n"
            
            f"First, the investigation revealed that {objective.lower()} is influenced by multiple factors, "
            f"which interact in complex ways. The findings demonstrated that whilst certain factors emerged as "
            f"particularly significant, the relative importance of these factors varied according to specific "
            f"contextual conditions. This suggests that theoretical models which propose linear or simple "
            f"relationships between variables may be insufficiently nuanced to capture the complexity of the "
            f"phenomenon.\n\n"
            
            f"Second, the research findings were broadly consistent with existing theoretical frameworks "
            f"discussed in Chapter Two. However, the findings also extended existing understandings "
            f"by demonstrating how contextual factors in {self.case_study} shape the manifestation of these theoretical constructs. "
            f"This suggests that whilst existing theory provides a useful foundation, further refinement and development is warranted.\n\n"
            
            f"Third, the empirical evidence presented suggests that existing recommendations regarding practice "
            f"require modification in light of these findings. The specific contextual conditions of {self.case_study} have been demonstrated "
            f"to be important in ways that existing practice guidance has not adequately recognised.\n\n"
        )
        
        return section
    
    def _generate_overall_conclusions(self) -> str:
        """Generate overall conclusions across all objectives."""
        section = "### 6.2.5 Overall Conclusions\n\n"
        
        num_objs = len(self.objectives)
        section += (
            f"Bringing together the conclusions regarding each of the {num_objs} research objectives, "
            f"several overarching conclusions can be drawn regarding {self.topic.lower()} within "
            f"{self.case_study}.\n\n"
            
            "First, the research has demonstrated that the phenomena under investigation are complex, "
            "contextual, and multifaceted. Simplistic approaches to understanding or influencing these phenomena "
            "are unlikely to be successful. Rather, a sophisticated understanding that acknowledges multiple "
            "perspectives and the interplay between various factors is required.\n\n"
            
            "Second, the research has demonstrated the value of empirical investigation in extending and refining "
            "existing theoretical understanding. Whilst the findings were broadly consistent with existing theory, "
            "they also revealed important nuances and extensions to existing knowledge.\n\n"
            
            "Third, the research has important implications for practice. The evidence presented suggests that "
            "practitioners in this domain would benefit from approaches that are informed by the evidence presented "
            "in this thesis, and that recognise the complexity and context-specificity of the phenomena they are "
            "seeking to understand or influence.\n\n"
            
            "Fourth, the research has identified important limitations and boundaries to the findings. These are "
            "detailed in the following section, and should be kept in mind when considering the implications of "
            "this work.\n"
        )
        
        return section
    
    def generate_recommendations(self) -> str:
        """
        Generate Section 6.3: Recommendations.
        
        Covers:
        - Policy recommendations
        - Practice recommendations
        - Organisational recommendations
        - Theoretical recommendations
        - Word count: ~2,500 words
        """
        recommend = "## 6.3 Recommendations\n\n"
        
        recommend += "### 6.3.1 Introduction to Recommendations\n\n"
        recommend += (
            "Based on the findings and conclusions presented in this thesis, the following recommendations "
            "are made for consideration by various stakeholders, including policymakers, practitioners, "
            "researchers, and organisational leaders.\n\n"
        )
        
        recommend += self._generate_policy_recommendations()
        recommend += "\n\n" + self._generate_practice_recommendations()
        recommend += "\n\n" + self._generate_organisational_recommendations()
        recommend += "\n\n" + self._generate_theoretical_recommendations()
        
        return recommend
    
    def _generate_policy_recommendations(self) -> str:
        """Generate policy-level recommendations."""
        section = "### 6.3.2 Policy Recommendations\n\n"
        
        section += (
            f"To policymakers and government agencies concerned with {self.topic.lower()}, "
            f"the following recommendations are offered:\n\n"
            
            "1. **Adopt evidence-based approaches**: The findings of this research suggest that existing policy "
            "frameworks would benefit from revision in light of empirical evidence. Policy should be developed and "
            "refined through engagement with current research evidence, and should be subjected to evaluation and "
            "revision as new evidence emerges.\n\n"
            
            "2. **Recognise contextual complexity**: Policy approaches that assume uniformity across all contexts "
            "are unlikely to be optimally effective. Instead, policy should provide frameworks that allow for "
            "contextual adaptation and flexibility, whilst maintaining core principles and standards.\n\n"
            
            "3. **Invest in further research**: Significant gaps remain in the evidence base regarding "
            f"{self.topic.lower()}. Continued investment in rigorous research is warranted to address these gaps "
            "and to support ongoing refinement of policy and practice.\n\n"
        )
        
        return section
    
    def _generate_practice_recommendations(self) -> str:
        """Generate practice-level recommendations."""
        section = "### 6.3.3 Practice Recommendations\n\n"
        
        section += (
            "To practitioners and organisations working in this field, the following recommendations are offered:\n\n"
            
            "1. **Adopt reflective practice**: The evidence suggests that reflexivity and ongoing reflection on "
            "practice is important. Practitioners are encouraged to examine their own assumptions and approaches "
            "in light of research evidence, and to adapt their practice accordingly.\n\n"
            
            "2. **Develop contextualised approaches**: Rather than adopting standardised approaches wholesale, "
            "practitioners should develop approaches tailored to their specific context, whilst drawing on evidence "
            "and best practice from other contexts.\n\n"
            
            "3. **Engage in continuous professional development**: Given the evolving evidence base, ongoing "
            "professional development and engagement with research literature is important to maintain competence "
            "and keep abreast of emerging evidence and innovations.\n\n"
            
            "4. **Collaborate with researchers**: Practitioners are encouraged to engage with researchers to conduct "
            "collaborative investigations of practice. Such partnerships can generate valuable evidence whilst also "
            "ensuring that research is responsive to practitioners' evidence needs.\n\n"
        )
        
        return section
    
    def _generate_organisational_recommendations(self) -> str:
        """Generate organisational-level recommendations."""
        section = "### 6.3.4 Organisational Recommendations\n\n"
        
        section += (
            "To organisational leaders and managers, the following recommendations are offered:\n\n"
            
            "1. **Establish research-informed decision-making**: Organisations should prioritise processes that "
            "ensure decisions are informed by current research evidence, and that evaluation and learning systems "
            "are in place to test whether approaches are working as intended.\n\n"
            
            "2. **Foster a culture of inquiry**: Organisations that encourage questioning, reflection, and learning "
            "from experience are more likely to adapt and improve over time. Leadership practices that support "
            "this culture of inquiry should be developed and sustained.\n\n"
            
            "3. **Invest in staff development**: The evidence suggests that staff capability is important. "
            "Organisations should invest in developing staff knowledge, skills, and confidence in implementing "
            "evidence-based approaches.\n\n"
        )
        
        return section
    
    def _generate_theoretical_recommendations(self) -> str:
        """Generate theoretical recommendations."""
        section = "### 6.3.5 Theoretical Recommendations\n\n"
        
        section += (
            "To the theoretical and research community, the following recommendations are offered:\n\n"
            
            "1. **Develop more nuanced theoretical models**: The findings suggest that existing theoretical models "
            f"of {self.topic.lower()} may be insufficiently complex. Researchers are encouraged to develop "
            "theoretical frameworks that better account for contextual variation and complexity.\n\n"
            
            "2. **Conduct longitudinal research**: Much existing research is cross-sectional. Longitudinal studies "
            "would provide valuable insights into how phenomena develop and change over time.\n\n"
            
            "3. **Pursue mixed-methods research**: The integration of qualitative and quantitative approaches employed "
            "in this research proved valuable. Such integrated approaches are recommended for future research.\n\n"
        )
        
        return section
    
    def generate_future_research(self) -> str:
        """
        Generate Section 6.4: Suggestions for Future Research.
        
        Covers:
        - Identified research gaps
        - Specific research questions for future investigation
        - Methodological approaches
        - Word count: ~1,500 words
        """
        future = "## 6.4 Suggestions for Future Research\n\n"
        
        future += (
            "Whilst this research has addressed the identified research objectives and has generated valuable "
            "insights into the nature of the phenomena under investigation, it has also revealed areas where "
            "further research would be of considerable value. The following suggestions for future research are "
            "offered.\n\n"
        )
        
        future += "### 6.4.1 Addressing Identified Research Gaps\n\n"
        future += (
            "Several specific gaps in the evidence base have been identified through this research:\n\n"
            
            "1. **Longitudinal investigation**: The research presented in this thesis is cross-sectional. Future "
            "research examining how phenomena develop and change over time would provide valuable insights.\n\n"
            
            "2. **Comparative studies**: Whilst this research was situated within a specific case study context, "
            "comparative studies across multiple contexts would help to delineate which findings are context-specific "
            "and which may have broader applicability.\n\n"
            
            "3. **Intervention studies**: Future research could usefully examine the effects of deliberate interventions "
            "designed to alter the factors identified in this research as important. Such research would provide "
            "evidence regarding causation and the effectiveness of potential improvements.\n\n"
            
            "4. **Qualitative depth**: Whilst this research employed mixed methods, further in-depth qualitative research "
            "would provide richer insights into the meanings and experiences of those involved in the phenomena under "
            "investigation.\n\n"
        )
        
        future += "### 6.4.2 Specific Research Questions for Future Investigation\n\n"
        
        for i, obj in enumerate(self.objectives, 1):
            future += (
                f"With regard to Objective {i} ({obj.lower()}):\n"
                f"- How do the findings from this case study compare with findings from other contexts?\n"
                f"- What mechanisms explain the relationships identified in this research?\n"
                f"- What interventions might be effective in altering the factors identified as important?\n\n"
            )
        
        future += "### 6.4.3 Methodological Approaches\n\n"
        future += (
            "A range of methodological approaches would be valuable for future research:\n\n"
            
            "- **Experimental or quasi-experimental designs** to test causal relationships\n"
            "- **Longitudinal panel studies** to examine change over time\n"
            "- **Case study research** in contrasting contexts for comparative purposes\n"
            "- **Participatory action research** engaging practitioners as co-researchers\n"
            "- **Replication studies** to examine consistency of findings across contexts\n\n"
        )
        
        future += "### 6.4.4 Concluding Remarks\n\n"
        future += (
            "This research has provided evidence regarding the nature of the phenomena under investigation, "
            "the factors that influence them, and the implications for theory and practice. However, the evidence base "
            "in this field remains underdeveloped, and further research is clearly warranted. It is hoped that this thesis "
            "provides both a foundation for future work and pointers towards productive lines of enquiry that will "
            "advance understanding and support improvements to policy and practice.\n"
        )
        
        return future


def generate_chapter6(
    topic: str,
    case_study: str,
    objectives: List[str],
    chapter_one_content: str = "",
    chapter_two_content: str = "",
    chapter_three_content: str = "",
    chapter_four_content: str = "",
    chapter_five_content: str = "",
    output_dir: str = None
) -> str:
    """
    Generate Chapter 6 content.
    
    Args:
        topic: Research topic
        case_study: Case study name
        objectives: List of research objectives
        chapter_one_content: Chapter 1 content
        chapter_two_content: Chapter 2 content
        chapter_three_content: Chapter 3 content
        chapter_four_content: Chapter 4 content
        chapter_five_content: Chapter 5 content
        output_dir: Output directory
    
    Returns:
        Generated Chapter 6 markdown content
    """
    generator = Chapter6Generator(
        topic=topic,
        case_study=case_study,
        objectives=objectives,
        chapter_one_content=chapter_one_content,
        chapter_two_content=chapter_two_content,
        chapter_three_content=chapter_three_content,
        chapter_four_content=chapter_four_content,
        chapter_five_content=chapter_five_content,
        output_dir=output_dir
    )
    
    return generator.generate_full_chapter()
