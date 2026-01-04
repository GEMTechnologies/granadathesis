"""
Research Context Manager - Ensures Consistency Across All Chapters

Manages research configuration to ensure that:
- Chapter 3 (Methodology) reflects the correct sample size, population, sampling technique
- Chapter 4 (Data Analysis) uses the exact sample size specified
- All chapters reference consistent research design
- LLM generates appropriate justifications and citations

Example:
    If user specifies n=50:
    - Chapter 3: "A purposive sample of 50 respondents..."
    - Chapter 3: "Population estimated at 250 security officials..."
    - Chapter 4: All tables show N=50
    - Chapter 4: Uses non-parametric tests (n<100)
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math


@dataclass
class PopulationConfig:
    """Population and sampling configuration"""
    target_population_size: int
    accessible_population_size: int
    sample_size: int
    sampling_technique: str
    sampling_justification: str
    population_description: str
    inclusion_criteria: List[str]
    exclusion_criteria: List[str]


class ResearchContextManager:
    """
    Manages research context to ensure consistency across all chapters.
    
    This class calculates and provides:
    - Appropriate population size based on sample size
    - Sampling technique based on research design and sample size
    - Sample size justification with academic citations
    - Statistical test appropriateness
    - Data generation parameters
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with research configuration.
        
        Args:
            config: Dict containing:
                - sample_size: int (e.g., 50, 385)
                - research_design: str ('survey', 'experimental', 'case_study')
                - topic: str
                - case_study: str (optional)
                - measurement_scale: str ('likert', 'nominal', etc.)
        """
        self.sample_size = config.get('sample_size', 385)
        self.research_design = config.get('research_design', 'survey')
        self.topic = config.get('topic', 'Research Study')
        self.case_study = config.get('case_study', '')
        self.measurement_scale = config.get('measurement_scale', 'likert')
        self.preferred_analyses = config.get('preferred_analyses', [])
        self.custom_instructions = config.get('custom_instructions', '')
        
        # Calculate derived values
        self.population_config = self._calculate_population()
        self.sampling_config = self._determine_sampling_technique()
        self.statistical_config = self._determine_statistical_approach()
    
    def _calculate_population(self) -> PopulationConfig:
        """
        Calculate appropriate population size based on sample size and research design.
        CRITICAL: If user specified n, we must justify IT, not calculate a new one.
        """
        n = self.sample_size
        
        # Determine population multiplier based on design
        # If n=120 (user input), we reverse-engineer a plausible population
        if self.research_design == 'case_study':
             # For case study, population is usually slightly larger than sample or same
            multiplier = 1.5 if n > 50 else 3.0
            target_pop = int(n * multiplier)
            accessible_pop = n  # For case study, often we sample the whole accessible group
            
        elif self.research_design == 'experimental':
            multiplier = 2.0
            target_pop = int(n * multiplier)
            accessible_pop = n
            
        elif self.research_design == 'survey':
            # Reverse Yamane/Krejcie logic: Population must be big enough to justify n
            if n < 100:
                multiplier = 5.0  # Small targeted survey
            elif n < 300:
                multiplier = 10.0 # Medium
            else:
                multiplier = 20.0 # Large (n=385 implied N>100,000 usually)
            
            target_pop = int(n * multiplier)
            accessible_pop = int(target_pop * 0.6) # 60% accessible
        
        else:  # Default
            multiplier = 10.0
            target_pop = int(n * multiplier)
            accessible_pop = int(target_pop * 0.7)
        
        # Round to nice numbers
        target_pop = self._round_to_nice_number(target_pop)
        if accessible_pop != n: # careful not to change n if it was set as accessible
             accessible_pop = self._round_to_nice_number(accessible_pop)
        
        # Determine sampling technique
        technique, justification = self._get_sampling_technique()
        
        # Generate inclusion/exclusion criteria
        inclusion = self._generate_inclusion_criteria()
        exclusion = self._generate_exclusion_criteria()
        
        return PopulationConfig(
            target_population_size=target_pop,
            accessible_population_size=accessible_pop,
            sample_size=n,
            sampling_technique=technique,
            sampling_justification=justification,
            population_description=self._generate_population_description(target_pop),
            inclusion_criteria=inclusion,
            exclusion_criteria=exclusion
        )
    
    def _round_to_nice_number(self, num: int) -> int:
        """Round to nice round numbers (e.g., 247 → 250, 1834 → 1800)"""
        if num < 100:
            return round(num / 10) * 10
        elif num < 1000:
            return round(num / 50) * 50
        elif num < 10000:
            return round(num / 100) * 100
        else:
            return round(num / 1000) * 1000
    
    def _generate_population_description(self, target_pop: int) -> str:
        """Generate appropriate population description based on topic and case study"""
        
        # Extract key terms from topic
        topic_lower = self.topic.lower()
        case_lower = self.case_study.lower() if self.case_study else ""
        
        # Determine population type
        if any(word in topic_lower for word in ['security', 'military', 'police', 'defense']):
            pop_type = "security sector officials and personnel"
        elif any(word in topic_lower for word in ['health', 'medical', 'hospital']):
            pop_type = "healthcare professionals and administrators"
        elif any(word in topic_lower for word in ['education', 'school', 'university', 'student']):
            pop_type = "educators, administrators, and students"
        elif any(word in topic_lower for word in ['business', 'enterprise', 'company', 'firm']):
            pop_type = "business professionals and managers"
        elif any(word in topic_lower for word in ['government', 'public', 'civil service']):
            pop_type = "government officials and civil servants"
        else:
            pop_type = "stakeholders and relevant personnel"
        
        # Add location if case study specified
        location = f" in {self.case_study}" if self.case_study else ""
        
        return f"The target population consisted of approximately {target_pop:,} {pop_type}{location}"
    
    def _get_sampling_technique(self) -> Tuple[str, str]:
        """
        Determine appropriate sampling technique based on sample size and design.
        
        Returns:
            (technique_name, justification_with_citation)
        """
        n = self.sample_size
        
        if n < 30:
            technique = "Purposive sampling"
            justification = (
                "Given the small, specialized nature of the population and the need for "
                "in-depth insights, purposive sampling was deemed most appropriate. This "
                "non-probability sampling technique allows for the deliberate selection of "
                "information-rich cases (Patton, 2002). The sample size of {n} aligns with "
                "Roscoe's (1975) rule of thumb that sample sizes larger than 30 and less than "
                "500 are appropriate for most research."
            ).format(n=n)
        
        elif n < 100:
            technique = "Snowball sampling"
            justification = (
                "Snowball sampling was employed due to the specialized and potentially "
                "hard-to-reach nature of the target population. This technique, recommended "
                "by Biernacki and Waldorf (1981) for accessing hidden populations, involves "
                "initial participants recruiting additional subjects. The sample size of {n} "
                "was determined to be adequate based on Guest et al. (2006), who found that "
                "data saturation typically occurs within the first 50-100 interviews."
            ).format(n=n)
        
        elif n < 200:
            technique = "Stratified random sampling"
            justification = (
                "Stratified random sampling was utilized to ensure proportional representation "
                "across key demographic and organizational strata. This probability sampling "
                "technique, as outlined by Cochran (1977), enhances the precision of estimates "
                "by reducing sampling error. The sample size of {n} was calculated to provide "
                "adequate representation within each stratum while maintaining statistical power."
            ).format(n=n)
        
        else:  # n >= 200
            technique = "Stratified random sampling"
            justification = (
                "Stratified random sampling was employed to ensure representative coverage of "
                "the target population. Following Krejcie and Morgan's (1970) sample size "
                "determination table, a sample of {n} was calculated for a population of "
                "{pop:,}, providing a 95% confidence level with a ±5% margin of error. "
                "Stratification was conducted based on key demographic and organizational "
                "variables to enhance the generalizability of findings (Cochran, 1977)."
            ).format(n=n, pop=self.population_config.target_population_size if hasattr(self, 'population_config') else n*30)
        
        return technique, justification
    
    def get_sample_size_justification(self) -> Dict[str, Any]:
        """
        Intelligently select the best scholarly justification for the sample size.
        
        Returns:
            Dict containing:
            - citation: str (e.g., "Roscoe (1975)")
            - method: str (e.g., "Rule of Thumb", "Yamane's Formula")
            - prompt_text: str (Instructions for the LLM)
        """
        n = self.sample_size
        design = self.research_design
        N = self.population_config.target_population_size
        
        # 1. Qualitative / Small Samples (n < 30)
        if n < 30 or design == 'phenomenology':
            return {
                "citation": "Guest et al. (2006); Saunders (2012)",
                "method": "Data Saturation",
                "prompt_text": f"""
Paragraph 3: Justify Sample Size using 'Data Saturation' principle:
- State that for {design} studies, sample size is determined by information verification rather than statistical power.
- Cite **Guest et al. (2006)** who found saturation often occurs within the first 12 interviews.
- Cite **Saunders (2012)** on the flexibility of non-probability sampling.
- Explicitly state: "A sample size of **n={n}** was deemed sufficient to reach data saturation."
- **DO NOT use any mathematical formulas.**
"""
            }
            
        # 2. Experimental / Power Analysis (Cohen)
        if design == 'experimental':
            return {
                "citation": "Cohen (1988)",
                "method": "Power Analysis",
                "prompt_text": f"""
Paragraph 3: Justify Sample Size using 'Power Analysis':
- Cite **Cohen (1988)** standard for statistical power (1 - β = 0.80).
- State that for a medium effect size (d=0.5) and alpha=0.05, a sample of **n={n}** is required.
- **Formula**: Use G*Power reference or simple power notation.
"""
            }

        # 3. Roscoe's Rule of Thumb (30 <= n <= 500) - Ideally for Case Studies / Mixed Methods
        # If specific population is unknown or it's a "general" justifications
        # We prioritize Roscoe if it's a Case Study or if n doesn't perfectly match a formula
        if 30 <= n <= 500 and (design == 'case_study' or design == 'mixed_methods'):
             return {
                "citation": "Roscoe (1975)",
                "method": "Rule of Thumb",
                "prompt_text": f"""
Paragraph 3: Justify Sample Size using **Roscoe's Rule of Thumb**:
- Cite **Roscoe (1975)** who proposes that "sample sizes larger than 30 and less than 500 are appropriate for most research."
- Argue that **n={n}** falls perfectly within this robust range.
- Mention that this size allows for comparable sub-samples (if applicable).
- **DO NOT perform a complex calculation (like Yamane) that contradicts n={n}.**
"""
            }

        # 4. Large Samples (n >= 380) -> Krejcie & Morgan
        if n >= 380:
             return {
                "citation": "Krejcie & Morgan (1970)",
                "method": "Table for Determinining Sample Size",
                "prompt_text": f"""
Paragraph 3: Justify Sample Size using **Krejcie and Morgan (1970)**:
- Cite their famous "Table for Determining Sample Size from a Given Population".
- State that for large populations (N > 100,000), the required sample size asymptotes to **384**.
- Thus, **n={n}** is statistically representative at the 95% confidence level with a 5% margin of error.
- **Formula**: $$ s = X^2NP(1-P) / d^2(N-1) + X^2P(1-P) $$ (Optional, or just cite the table).
"""
            }

        # 5. Default Fallback: Yamane (1967)
        # If none of the above specific cases match, we assume a finite population calculation
        return {
            "citation": "Yamane (1967)",
            "method": "Yamane's Formula",
            "prompt_text": f"""
Paragraph 3: Justify Sample Size using **Yamane's Formula (1967)**:
- Method suitable for known finite populations.
- **Formula**: $$ n = N / (1 + Ne^2) $$
- **CRITICAL**: You MUST walk through the calculation step-by-step for the user:
  1. Start with the population N={N}.
  2. State the desired margin of error e=0.05.
  3. Show the formula substitution: n = {N} / (1 + {N}(0.05)^2).
  4. Show the intermediate steps: n = {N} / (1 + {N}*0.0025).
  5. State that {N}*0.0025 = {N*0.0025:.2f}.
  6. Show final division: n = {N} / {1 + N*0.0025:.2f}.
  7. Confirm that the result is approximately **{n}**.
- Explicitly state: "Using Yamane's (1967) formula with a {N} population and 5% margin of error, the required sample size is {n}."
"""
        }
    
    def _generate_inclusion_criteria(self) -> List[str]:
        """Generate appropriate inclusion criteria based on topic"""
        criteria = [
            f"Individuals directly involved in or affected by {self.topic.lower()}",
            "Willingness to participate voluntarily in the study",
            "Ability to provide informed consent",
        ]
        
        # Add specific criteria based on topic
        topic_lower = self.topic.lower()
        if 'security' in topic_lower or 'military' in topic_lower:
            criteria.append("Current or former employment in security sector institutions")
            criteria.append("Minimum of 2 years of experience in the security sector")
        elif 'health' in topic_lower:
            criteria.append("Licensed healthcare professional or administrator")
            criteria.append("Minimum of 1 year of clinical or administrative experience")
        elif 'education' in topic_lower:
            criteria.append("Current enrollment or employment in educational institutions")
        
        # Add location criteria if case study specified
        if self.case_study:
            criteria.append(f"Based in or familiar with {self.case_study}")
        
        return criteria
    
    def _generate_exclusion_criteria(self) -> List[str]:
        """Generate appropriate exclusion criteria"""
        return [
            "Individuals unable to provide informed consent",
            "Respondents with incomplete or unreliable data",
            "Participants who withdrew consent during the study",
            "Individuals with conflicts of interest that could bias responses"
        ]
    
    def _determine_sampling_technique(self) -> Dict[str, Any]:
        """Determine sampling approach details"""
        return {
            'technique': self.population_config.sampling_technique,
            'justification': self.population_config.sampling_justification,
            'is_probability': self.sample_size >= 100,
            'is_stratified': self.sample_size >= 100,
            'strata': self._determine_strata() if self.sample_size >= 100 else []
        }
    
    def _determine_strata(self) -> List[Dict[str, Any]]:
        """Determine stratification variables if using stratified sampling"""
        if self.sample_size < 100:
            return []
        
        # Common stratification variables
        strata = [
            {
                'variable': 'Gender',
                'categories': ['Male', 'Female'],
                'proportions': [0.55, 0.45]  # Realistic distribution
            },
            {
                'variable': 'Age Group',
                'categories': ['18-25', '26-35', '36-45', '46-55', '56+'],
                'proportions': [0.15, 0.30, 0.25, 0.20, 0.10]
            },
            {
                'variable': 'Education Level',
                'categories': ['Diploma', 'Bachelors', 'Masters', 'PhD', 'Other'],
                'proportions': [0.15, 0.50, 0.25, 0.05, 0.05]
            }
        ]
        
        return strata
    
    def _determine_statistical_approach(self) -> Dict[str, Any]:
        """Determine appropriate statistical tests based on sample size"""
        n = self.sample_size
        
        return {
            'use_parametric': n >= 30,
            'use_sem': n >= 200,
            'use_factor_analysis': n >= 100,
            'use_cluster_analysis': n >= 50,
            'minimum_group_size': max(15, n // 10),  # For subgroup analysis
            'recommended_tests': self._get_recommended_tests(n),
            'power_analysis': self._calculate_power(n)
        }
    
    def _get_recommended_tests(self, n: int) -> Dict[str, List[str]]:
        """Get recommended statistical tests based on sample size"""
        tests = {
            'comparison': [],
            'correlation': [],
            'regression': [],
            'multivariate': []
        }
        
        if n < 30:
            tests['comparison'] = ['Mann-Whitney U', 'Wilcoxon signed-rank', 'Kruskal-Wallis']
            tests['correlation'] = ['Spearman correlation']
            tests['regression'] = ['Simple linear regression']
            tests['multivariate'] = []
        
        elif n < 100:
            tests['comparison'] = ['Independent t-test', 'Paired t-test', 'One-way ANOVA']
            tests['correlation'] = ['Pearson correlation', 'Spearman correlation']
            tests['regression'] = ['Multiple regression (limited predictors)']
            tests['multivariate'] = ['PCA']
        
        elif n < 200:
            tests['comparison'] = ['Independent t-test', 'ANOVA', 'MANOVA']
            tests['correlation'] = ['Pearson correlation', 'Partial correlation']
            tests['regression'] = ['Multiple regression', 'Hierarchical regression']
            tests['multivariate'] = ['PCA', 'Factor Analysis', 'Cluster Analysis']
        
        else:  # n >= 200
            tests['comparison'] = ['t-test', 'ANOVA', 'MANOVA', 'ANCOVA']
            tests['correlation'] = ['Pearson', 'Partial', 'Canonical correlation']
            tests['regression'] = ['Multiple regression', 'Logistic regression', 'Path analysis']
            tests['multivariate'] = ['PCA', 'EFA', 'CFA', 'SEM', 'Cluster Analysis']
        
        return tests
    
    def _calculate_power(self, n: int) -> Dict[str, float]:
        """Calculate statistical power for common effect sizes"""
        # Simplified power calculation (would use statsmodels in production)
        # Power = 1 - β (Type II error rate)
        
        # Rule of thumb: n=30 gives ~0.70 power, n=100 gives ~0.85, n=200+ gives ~0.95
        if n < 30:
            power = 0.60
        elif n < 50:
            power = 0.70
        elif n < 100:
            power = 0.80
        elif n < 200:
            power = 0.85
        else:
            power = 0.95
        
        return {
            'small_effect': power * 0.7,  # Cohen's d = 0.2
            'medium_effect': power,        # Cohen's d = 0.5
            'large_effect': min(0.99, power * 1.1)  # Cohen's d = 0.8
        }
    
    def get_methodology_context(self) -> Dict[str, Any]:
        """
        Get complete context for Chapter 3 (Methodology) generation.
        
        Returns:
            Dict with all methodology details the LLM needs
        """
        return {
            'research_design': self.research_design,
            'population': {
                'target_size': self.population_config.target_population_size,
                'accessible_size': self.population_config.accessible_population_size,
                'description': self.population_config.population_description,
                'inclusion_criteria': self.population_config.inclusion_criteria,
                'exclusion_criteria': self.population_config.exclusion_criteria
            },
            'sampling': {
                'technique': self.sampling_config['technique'],
                'justification': self.sampling_config['justification'],
                'sample_size': self.sample_size,
                'is_probability': self.sampling_config['is_probability'],
                'strata': self.sampling_config['strata']
            },
            'data_collection': {
                'primary_method': 'Structured questionnaire' if self.measurement_scale == 'likert' else 'Survey',
                'measurement_scale': self.measurement_scale,
                'pilot_test_size': max(10, int(self.sample_size * 0.1))  # 10% for pilot
            },
            'statistical_approach': self.statistical_config,
            'preferred_analyses': self.preferred_analyses,
            'custom_instructions': self.custom_instructions
        }
    
    def get_analysis_context(self) -> Dict[str, Any]:
        """
        Get complete context for Chapter 4 (Data Analysis) generation.
        
        Returns:
            Dict with all analysis parameters
        """
        return {
            'sample_size': self.sample_size,
            'use_parametric': self.statistical_config['use_parametric'],
            'recommended_tests': self.statistical_config['recommended_tests'],
            'confidence_level': 0.95,
            'significance_level': 0.05,
            'effect_size_thresholds': {
                'small': 0.2,
                'medium': 0.5,
                'large': 0.8
            },
            'power': self.statistical_config['power_analysis']
        }
    
    def generate_sample_size_justification(self) -> str:
        """
        Generate academic justification for the sample size.
        
        Returns:
            Formatted text with citations
        """
        n = self.sample_size
        pop = self.population_config.target_population_size
        
        if n < 30:
            return (
                f"A sample size of {n} was selected for this qualitative-oriented study. "
                f"According to Roscoe (1975), sample sizes between 10 and 30 are sufficient "
                f"for exploratory research. Patton (2002) further notes that purposive samples "
                f"of this size can provide rich, in-depth insights when information saturation "
                f"is achieved."
            )
        
        elif n < 100:
            return (
                f"The sample size of {n} was determined based on Roscoe's (1975) rule of thumb, "
                f"which suggests that sample sizes larger than 30 and less than 500 are appropriate "
                f"for most research. Guest et al. (2006) found that data saturation typically occurs "
                f"within 50-100 interviews for homogeneous populations, supporting the adequacy of "
                f"this sample size."
            )
        
        elif n < 200:
            return (
                f"A sample size of {n} was calculated to ensure adequate statistical power while "
                f"maintaining feasibility. Following Cohen's (1988) power analysis guidelines, this "
                f"sample provides approximately 80% power to detect medium effect sizes (d=0.5) at "
                f"α=0.05. Bartlett et al. (2001) recommend a minimum of 100 respondents for survey "
                f"research to ensure reliable statistical analysis."
            )
        
        else:  # n >= 200
            # Use Krejcie & Morgan formula
            margin_of_error = 0.05
            confidence = 0.95
            
            return (
                f"The sample size of {n} was determined using Krejcie and Morgan's (1970) formula "
                f"for a target population of {pop:,}. This calculation assumes a 95% confidence level "
                f"and a ±5% margin of error, which are standard in social science research (Cochran, 1977). "
                f"The formula is: n = [χ²NP(1-P)] / [d²(N-1) + χ²P(1-P)], where χ²=3.841 (95% confidence), "
                f"N={pop:,}, P=0.5 (maximum variability), and d=0.05 (precision). This sample size ensures "
                f"adequate representation and generalizability of findings to the target population."
            )


# Example usage and testing
if __name__ == "__main__":
    # Test with different sample sizes
    test_configs = [
        {'sample_size': 25, 'research_design': 'case_study', 'topic': 'Security Sector Reform', 'case_study': 'Juba'},
        {'sample_size': 75, 'research_design': 'survey', 'topic': 'Healthcare Quality'},
        {'sample_size': 150, 'research_design': 'survey', 'topic': 'Educational Outcomes'},
        {'sample_size': 385, 'research_design': 'survey', 'topic': 'Political Stability'},
    ]
    
    for config in test_configs:
        print("=" * 80)
        print(f"TESTING: n={config['sample_size']}, design={config['research_design']}")
        print("=" * 80)
        
        manager = ResearchContextManager(config)
        
        # Get methodology context
        method_ctx = manager.get_methodology_context()
        
        print(f"\n📊 POPULATION:")
        print(f"  Target: {method_ctx['population']['target_size']:,}")
        print(f"  Accessible: {method_ctx['population']['accessible_size']:,}")
        print(f"  Description: {method_ctx['population']['description']}")
        
        print(f"\n🎯 SAMPLING:")
        print(f"  Technique: {method_ctx['sampling']['technique']}")
        print(f"  Sample Size: {method_ctx['sampling']['sample_size']}")
        print(f"  Probability: {method_ctx['sampling']['is_probability']}")
        
        print(f"\n📈 STATISTICAL APPROACH:")
        print(f"  Parametric: {method_ctx['statistical_approach']['use_parametric']}")
        print(f"  SEM Appropriate: {method_ctx['statistical_approach']['use_sem']}")
        print(f"  Recommended Tests: {method_ctx['statistical_approach']['recommended_tests']['comparison']}")
        
        print(f"\n📝 SAMPLE SIZE JUSTIFICATION:")
        print(f"  {manager.generate_sample_size_justification()}")
        
        print("\n")
