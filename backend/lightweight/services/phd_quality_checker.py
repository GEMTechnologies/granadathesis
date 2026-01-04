"""
PhD-Level Quality Assurance System

This module provides comprehensive quality checks for thesis chapters to ensure
they meet PhD-level academic standards.

Checks include:
- Academic rigor and depth
- Citation density and quality
- Methodological soundness
- Statistical appropriateness
- Writing quality and coherence
- Formatting and structure
"""

from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import re


@dataclass
class QualityIssue:
    """Represents a quality issue found in the thesis"""
    severity: str  # 'critical', 'major', 'minor'
    category: str  # 'citations', 'methodology', 'statistics', 'writing', 'structure'
    issue: str
    location: str
    suggestion: str


class PhDQualityChecker:
    """
    Comprehensive quality checker for PhD-level thesis chapters.
    
    Evaluates:
    - Academic rigor
    - Citation quality
    - Methodological soundness
    - Statistical appropriateness
    - Writing quality
    """
    
    def __init__(self):
        self.issues: List[QualityIssue] = []
        self.scores: Dict[str, float] = {}
    
    def check_chapter(self, content: str, chapter_number: int, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Comprehensive quality check for a chapter.
        
        Args:
            content: Chapter content (markdown)
            chapter_number: Chapter number (1-6)
            metadata: Additional metadata (sample_size, objectives, etc.)
        
        Returns:
            Quality report with scores and issues
        """
        self.issues = []
        self.scores = {}
        
        # Run all checks
        self._check_citations(content, chapter_number)
        self._check_structure(content, chapter_number)
        self._check_writing_quality(content)
        
        if chapter_number == 3:
            self._check_methodology(content, metadata)
        elif chapter_number == 4:
            self._check_statistics(content, metadata)
        
        # Calculate overall score
        overall_score = sum(self.scores.values()) / len(self.scores) if self.scores else 0
        
        # Determine quality level
        if overall_score >= 90:
            quality_level = "Excellent - PhD Level"
        elif overall_score >= 80:
            quality_level = "Good - Meets PhD Standards"
        elif overall_score >= 70:
            quality_level = "Acceptable - Minor Revisions Needed"
        elif overall_score >= 60:
            quality_level = "Fair - Major Revisions Needed"
        else:
            quality_level = "Poor - Substantial Rework Required"
        
        return {
            'overall_score': overall_score,
            'quality_level': quality_level,
            'category_scores': self.scores,
            'issues': [
                {
                    'severity': issue.severity,
                    'category': issue.category,
                    'issue': issue.issue,
                    'location': issue.location,
                    'suggestion': issue.suggestion
                }
                for issue in self.issues
            ],
            'critical_issues': len([i for i in self.issues if i.severity == 'critical']),
            'major_issues': len([i for i in self.issues if i.severity == 'major']),
            'minor_issues': len([i for i in self.issues if i.severity == 'minor'])
        }
    
    def _check_citations(self, content: str, chapter_number: int):
        """Check citation quality and density"""
        # Count citations
        apa_citations = len(re.findall(r'\([A-Z][a-z]+(?:\s+(?:&|et al\.))?.*?\d{4}\)', content))
        
        # Count paragraphs
        paragraphs = [p for p in content.split('\n\n') if len(p.strip()) > 50]
        num_paragraphs = len(paragraphs)
        
        if num_paragraphs == 0:
            self.scores['citations'] = 0
            return
        
        # Calculate citation density
        citations_per_paragraph = apa_citations / num_paragraphs if num_paragraphs > 0 else 0
        
        # Expected citation density by chapter
        expected_density = {
            1: 2.0,  # Chapter 1: 2+ citations per paragraph
            2: 3.0,  # Chapter 2: 3+ citations per paragraph (literature review)
            3: 2.5,  # Chapter 3: 2.5+ citations per paragraph (methodology)
            4: 1.5,  # Chapter 4: 1.5+ citations per paragraph (data analysis)
            5: 2.0,  # Chapter 5: 2+ citations per paragraph (discussion)
            6: 1.5   # Chapter 6: 1.5+ citations per paragraph (conclusion)
        }
        
        expected = expected_density.get(chapter_number, 2.0)
        
        if citations_per_paragraph >= expected:
            score = 100
        elif citations_per_paragraph >= expected * 0.8:
            score = 85
            self.issues.append(QualityIssue(
                severity='minor',
                category='citations',
                issue=f'Citation density ({citations_per_paragraph:.1f} per paragraph) is slightly below PhD standard ({expected:.1f})',
                location='Throughout chapter',
                suggestion=f'Add {int((expected - citations_per_paragraph) * num_paragraphs)} more citations to meet PhD standards'
            ))
        elif citations_per_paragraph >= expected * 0.6:
            score = 70
            self.issues.append(QualityIssue(
                severity='major',
                category='citations',
                issue=f'Citation density ({citations_per_paragraph:.1f} per paragraph) is below PhD standard ({expected:.1f})',
                location='Throughout chapter',
                suggestion=f'Add {int((expected - citations_per_paragraph) * num_paragraphs)} more citations. Each paragraph should have {expected:.0f}+ citations.'
            ))
        else:
            score = 50
            self.issues.append(QualityIssue(
                severity='critical',
                category='citations',
                issue=f'Citation density ({citations_per_paragraph:.1f} per paragraph) is significantly below PhD standard ({expected:.1f})',
                location='Throughout chapter',
                suggestion=f'Substantially increase citations. Add {int((expected - citations_per_paragraph) * num_paragraphs)} more citations minimum.'
            ))
        
        self.scores['citations'] = score
    
    def _check_structure(self, content: str, chapter_number: int):
        """Check structural elements"""
        score = 100
        
        # Check for proper headings
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        
        if len(headings) < 5:
            score -= 20
            self.issues.append(QualityIssue(
                severity='major',
                category='structure',
                issue=f'Only {len(headings)} headings found. PhD chapters should have 8-12 sections.',
                location='Chapter structure',
                suggestion='Add more subsections to provide comprehensive coverage'
            ))
        
        # Check for tables and figures
        tables = len(re.findall(r'Table \d+\.\d+:', content))
        figures = len(re.findall(r'Figure \d+\.\d+:', content))
        
        if chapter_number in [3, 4] and tables == 0:
            score -= 15
            self.issues.append(QualityIssue(
                severity='major',
                category='structure',
                issue='No tables found in methodology/analysis chapter',
                location='Chapter content',
                suggestion='Add tables to present data, demographics, or analysis results'
            ))
        
        self.scores['structure'] = score
    
    def _check_writing_quality(self, content: str):
        """Check writing quality"""
        score = 100
        
        # Check for passive voice (appropriate for academic writing)
        passive_markers = len(re.findall(r'\b(?:was|were|is|are|be|been|being)\s+\w+ed\b', content))
        words = len(content.split())
        
        if words > 0:
            passive_ratio = passive_markers / words
            
            # Academic writing should have 20-40% passive voice
            if passive_ratio < 0.15:
                score -= 10
                self.issues.append(QualityIssue(
                    severity='minor',
                    category='writing',
                    issue='Low use of passive voice for academic writing',
                    location='Throughout chapter',
                    suggestion='Use more passive constructions (e.g., "was conducted", "were analyzed") for academic tone'
                ))
        
        # Check for informal language
        informal_words = ['gonna', 'wanna', 'gotta', 'kinda', 'sorta', 'yeah', 'ok', 'okay']
        for word in informal_words:
            if word in content.lower():
                score -= 20
                self.issues.append(QualityIssue(
                    severity='critical',
                    category='writing',
                    issue=f'Informal language detected: "{word}"',
                    location='Throughout chapter',
                    suggestion='Replace with formal academic language'
                ))
        
        self.scores['writing'] = score
    
    def _check_methodology(self, content: str, metadata: Dict[str, Any] = None):
        """Check methodology chapter quality"""
        score = 100
        
        # Check for essential methodology sections
        required_sections = [
            ('research design', 'Research Design'),
            ('population', 'Target Population'),
            ('sample|sampling', 'Sampling'),
            ('data collection', 'Data Collection'),
            ('validity|reliability', 'Validity and Reliability'),
            ('ethical', 'Ethical Considerations')
        ]
        
        for pattern, section_name in required_sections:
            if not re.search(pattern, content, re.IGNORECASE):
                score -= 15
                self.issues.append(QualityIssue(
                    severity='critical',
                    category='methodology',
                    issue=f'Missing essential section: {section_name}',
                    location='Chapter 3',
                    suggestion=f'Add a section on {section_name} with appropriate citations'
                ))
        
        # Check for sample size justification
        if metadata and 'sample_size' in metadata:
            n = metadata['sample_size']
            if not re.search(r'(?:Krejcie|Morgan|Yamane|Roscoe|Guest|Cohen)', content):
                score -= 10
                self.issues.append(QualityIssue(
                    severity='major',
                    category='methodology',
                    issue='No academic citation for sample size determination',
                    location='Sample Size section',
                    suggestion='Cite Krejcie & Morgan (1970), Roscoe (1975), or Cohen (1988) for sample size justification'
                ))
        
        self.scores['methodology'] = score
    
    def _check_statistics(self, content: str, metadata: Dict[str, Any] = None):
        """Check statistical analysis quality"""
        score = 100
        
        # Check for appropriate statistical tests
        if metadata and 'sample_size' in metadata:
            n = metadata['sample_size']
            
            # Check for parametric vs non-parametric appropriateness
            if n < 30:
                # Should use non-parametric
                if re.search(r'\b(?:t-test|ANOVA|Pearson)\b', content, re.IGNORECASE):
                    score -= 15
                    self.issues.append(QualityIssue(
                        severity='major',
                        category='statistics',
                        issue=f'Using parametric tests with small sample (n={n})',
                        location='Statistical Analysis',
                        suggestion='Use non-parametric tests (Mann-Whitney, Kruskal-Wallis, Spearman) for n<30'
                    ))
            
            # Check for SEM with small sample
            if n < 200 and re.search(r'\b(?:SEM|structural equation)', content, re.IGNORECASE):
                score -= 20
                self.issues.append(QualityIssue(
                    severity='critical',
                    category='statistics',
                    issue=f'Using SEM with insufficient sample size (n={n}, minimum=200)',
                    location='Statistical Analysis',
                    suggestion='Remove SEM or increase sample size to 200+'
                ))
        
        # Check for reliability testing
        if 'Likert' in content or 'questionnaire' in content.lower():
            if not re.search(r'(?:Cronbach|alpha|reliability)', content, re.IGNORECASE):
                score -= 15
                self.issues.append(QualityIssue(
                    severity='major',
                    category='statistics',
                    issue='No reliability testing for Likert scale data',
                    location='Data Analysis',
                    suggestion="Add Cronbach's alpha reliability test for questionnaire data"
                ))
        
        self.scores['statistics'] = score
    
    def generate_report(self) -> str:
        """Generate a formatted quality report"""
        report = "# PhD-Level Quality Assessment Report\n\n"
        
        report += f"## Overall Score: {self.scores.get('overall_score', 0):.1f}/100\n"
        report += f"**Quality Level**: {self.scores.get('quality_level', 'Unknown')}\n\n"
        
        report += "## Category Scores\n\n"
        for category, score in self.scores.items():
            if category not in ['overall_score', 'quality_level']:
                report += f"- **{category.title()}**: {score:.1f}/100\n"
        
        report += "\n## Issues Found\n\n"
        
        # Group by severity
        critical = [i for i in self.issues if i.severity == 'critical']
        major = [i for i in self.issues if i.severity == 'major']
        minor = [i for i in self.issues if i.severity == 'minor']
        
        if critical:
            report += "### 🔴 Critical Issues\n\n"
            for issue in critical:
                report += f"- **{issue.category.title()}**: {issue.issue}\n"
                report += f"  - *Suggestion*: {issue.suggestion}\n\n"
        
        if major:
            report += "### 🟡 Major Issues\n\n"
            for issue in major:
                report += f"- **{issue.category.title()}**: {issue.issue}\n"
                report += f"  - *Suggestion*: {issue.suggestion}\n\n"
        
        if minor:
            report += "### 🟢 Minor Issues\n\n"
            for issue in minor:
                report += f"- **{issue.category.title()}**: {issue.issue}\n"
                report += f"  - *Suggestion*: {issue.suggestion}\n\n"
        
        if not self.issues:
            report += "*No issues found - Excellent work!*\n"
        
        return report


# Example usage
if __name__ == "__main__":
    checker = PhDQualityChecker()
    
    # Test with sample content
    sample_chapter3 = """
    # Chapter 3: Research Methodology
    
    ## 3.1 Introduction
    
    This chapter outlines the research methodology employed in this study. The research design, population, sampling procedures, data collection instruments, and data analysis methods are described.
    
    ## 3.2 Research Design
    
    A survey research design was adopted for this study (Creswell, 2014). This design is appropriate for collecting data from a large population (Mugenda & Mugenda, 2003).
    
    ## 3.3 Target Population
    
    The target population consisted of 12,000 stakeholders (Kothari, 2004).
    
    ## 3.4 Sample Size
    
    Using Krejcie and Morgan's (1970) formula, a sample of 385 was determined.
    """
    
    result = checker.check_chapter(
        sample_chapter3,
        chapter_number=3,
        metadata={'sample_size': 385}
    )
    
    print(f"Overall Score: {result['overall_score']:.1f}/100")
    print(f"Quality Level: {result['quality_level']}")
    print(f"\nIssues: {result['critical_issues']} critical, {result['major_issues']} major, {result['minor_issues']} minor")
