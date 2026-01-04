"""
Analysis Intelligence System - Smart Statistical Analysis Selection

Automatically determines appropriate statistical techniques based on:
- Research objectives (keywords: examine, compare, predict, explore, etc.)
- Methodology (research design, data types, measurement scales)
- Data characteristics (sample size, variable types, distributions)

Supports:
- PCA/Factor Analysis
- ANOVA/MANOVA
- SEM (Structural Equation Modeling)
- Cluster Analysis
- Reliability Tests (Cronbach's α, KMO, Bartlett's)
- Mediation/Moderation Analysis
- Time Series Analysis
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re


class ResearchDesign(Enum):
    """Research design types"""
    EXPERIMENTAL = "experimental"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    SURVEY = "survey"
    CORRELATIONAL = "correlational"
    CASE_STUDY = "case_study"
    LONGITUDINAL = "longitudinal"
    CROSS_SECTIONAL = "cross_sectional"
    MIXED_METHODS = "mixed_methods"


class DataType(Enum):
    """Variable data types"""
    CATEGORICAL = "categorical"
    ORDINAL = "ordinal"
    CONTINUOUS = "continuous"
    LIKERT = "likert"
    BINARY = "binary"
    COUNT = "count"


class AnalysisType(Enum):
    """Available statistical analyses"""
    # Descriptive
    DESCRIPTIVE_STATS = "descriptive_statistics"
    FREQUENCY_TABLES = "frequency_tables"
    
    # Reliability & Validity
    CRONBACH_ALPHA = "cronbach_alpha"
    KMO_BARTLETT = "kmo_bartlett"
    FACTOR_ANALYSIS = "factor_analysis"
    PCA = "principal_component_analysis"
    
    # Comparison Tests
    T_TEST = "t_test"
    PAIRED_T_TEST = "paired_t_test"
    ANOVA = "anova"
    MANOVA = "manova"
    KRUSKAL_WALLIS = "kruskal_wallis"
    MANN_WHITNEY = "mann_whitney"
    CHI_SQUARE = "chi_square"
    
    # Correlation & Regression
    PEARSON_CORRELATION = "pearson_correlation"
    SPEARMAN_CORRELATION = "spearman_correlation"
    LINEAR_REGRESSION = "linear_regression"
    MULTIPLE_REGRESSION = "multiple_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    
    # Advanced Multivariate
    SEM = "structural_equation_modeling"
    PATH_ANALYSIS = "path_analysis"
    MEDIATION_ANALYSIS = "mediation_analysis"
    MODERATION_ANALYSIS = "moderation_analysis"
    
    # Clustering & Classification
    CLUSTER_ANALYSIS = "cluster_analysis"
    DISCRIMINANT_ANALYSIS = "discriminant_analysis"
    
    # Time Series
    TIME_SERIES_ANALYSIS = "time_series_analysis"
    TREND_ANALYSIS = "trend_analysis"


@dataclass
class ResearchConfig:
    """Research configuration from user input"""
    sample_size: int = 385
    research_design: ResearchDesign = ResearchDesign.SURVEY
    data_collection_methods: List[str] = None  # ['questionnaire', 'interview', 'fgd']
    measurement_scale: str = "likert"  # 'likert', 'nominal', 'ordinal', 'interval', 'ratio'
    num_objectives: int = 4
    has_hypotheses: bool = True
    has_control_group: bool = False
    is_longitudinal: bool = False
    confidence_level: float = 0.95
    
    # User preferences
    preferred_analyses: List[AnalysisType] = None
    exclude_analyses: List[AnalysisType] = None
    
    def __post_init__(self):
        if self.data_collection_methods is None:
            self.data_collection_methods = ['questionnaire']
        if self.preferred_analyses is None:
            self.preferred_analyses = []
        if self.exclude_analyses is None:
            self.exclude_analyses = []


class AnalysisIntelligence:
    """
    Intelligent analysis selection system.
    
    Reads research objectives and methodology to automatically
    determine appropriate statistical techniques.
    """
    
    def __init__(self, config: ResearchConfig):
        self.config = config
        self.selected_analyses = []
        self.analysis_rationale = {}
    
    def analyze_objectives(self, objectives: List[str]) -> Dict[str, List[AnalysisType]]:
        """
        Analyze research objectives to determine required analyses.
        
        Returns:
            Dict mapping each objective to recommended analyses
        """
        objective_analyses = {}
        
        for i, objective in enumerate(objectives, 1):
            obj_lower = objective.lower()
            analyses = []
            rationale = []
            
            # EXPLORATORY keywords → PCA, Factor Analysis, Cluster Analysis
            if any(kw in obj_lower for kw in ['explore', 'identify', 'discover', 'patterns']):
                analyses.append(AnalysisType.PCA)
                rationale.append("Exploratory objective requires dimensionality reduction")
                analyses.append(AnalysisType.CLUSTER_ANALYSIS)
                rationale.append("Pattern discovery benefits from clustering")
            
            # COMPARISON keywords → ANOVA, t-test, Mann-Whitney
            if any(kw in obj_lower for kw in ['compare', 'difference', 'differ', 'contrast', 'versus']):
                if 'two' in obj_lower or 'between' in obj_lower:
                    analyses.append(AnalysisType.T_TEST)
                    rationale.append("Comparison between two groups requires t-test")
                else:
                    analyses.append(AnalysisType.ANOVA)
                    rationale.append("Comparison across multiple groups requires ANOVA")
            
            # RELATIONSHIP keywords → Correlation, Regression
            if any(kw in obj_lower for kw in ['relationship', 'association', 'correlation', 'relate']):
                analyses.append(AnalysisType.PEARSON_CORRELATION)
                rationale.append("Relationship analysis requires correlation")
                if 'multiple' in obj_lower or len(objectives) > 2:
                    analyses.append(AnalysisType.MULTIPLE_REGRESSION)
                    rationale.append("Multiple variables require multiple regression")
            
            # PREDICTION/INFLUENCE keywords → Regression, SEM
            if any(kw in obj_lower for kw in ['predict', 'influence', 'effect', 'impact', 'determine']):
                analyses.append(AnalysisType.MULTIPLE_REGRESSION)
                rationale.append("Predictive objective requires regression analysis")
                if len(objectives) >= 3:
                    analyses.append(AnalysisType.SEM)
                    rationale.append("Complex model with multiple objectives benefits from SEM")
            
            # EVALUATION keywords → Descriptive + Inferential
            if any(kw in obj_lower for kw in ['evaluate', 'assess', 'measure', 'examine']):
                analyses.append(AnalysisType.DESCRIPTIVE_STATS)
                rationale.append("Evaluation requires comprehensive descriptive statistics")
                analyses.append(AnalysisType.PEARSON_CORRELATION)
                rationale.append("Assessment benefits from correlation analysis")
            
            # MEDIATION/MODERATION keywords
            if any(kw in obj_lower for kw in ['mediate', 'moderate', 'indirect', 'intervening']):
                analyses.append(AnalysisType.MEDIATION_ANALYSIS)
                rationale.append("Mediation/moderation effects require specialized analysis")
            
            objective_analyses[f"objective_{i}"] = {
                'analyses': analyses,
                'rationale': rationale
            }
        
        return objective_analyses
    
    def determine_required_analyses(self, objectives: List[str], 
                                     methodology_text: str = "") -> List[AnalysisType]:
        """
        Main method: Determine all required analyses based on objectives and methodology.
        
        Args:
            objectives: List of research objectives
            methodology_text: Text from Chapter 3 (methodology)
        
        Returns:
            List of recommended AnalysisType enums
        """
        analyses = set()
        
        # 1. ALWAYS include basics for survey research
        if self.config.research_design == ResearchDesign.SURVEY:
            analyses.add(AnalysisType.DESCRIPTIVE_STATS)
            analyses.add(AnalysisType.FREQUENCY_TABLES)
        
        # 2. RELIABILITY & VALIDITY for Likert scales
        if self.config.measurement_scale == "likert":
            analyses.add(AnalysisType.CRONBACH_ALPHA)
            analyses.add(AnalysisType.KMO_BARTLETT)
            analyses.add(AnalysisType.FACTOR_ANALYSIS)
            self.analysis_rationale['reliability'] = "Likert scale instruments require reliability testing"
        
        # 3. Analyze objectives
        obj_analyses = self.analyze_objectives(objectives)
        for obj_data in obj_analyses.values():
            analyses.update(obj_data['analyses'])
            for rationale in obj_data['rationale']:
                self.analysis_rationale[rationale[:30]] = rationale
        
        # 4. Sample size considerations
        if self.config.sample_size < 30:
            # Small sample → non-parametric tests
            if AnalysisType.T_TEST in analyses:
                analyses.remove(AnalysisType.T_TEST)
                analyses.add(AnalysisType.MANN_WHITNEY)
            if AnalysisType.ANOVA in analyses:
                analyses.remove(AnalysisType.ANOVA)
                analyses.add(AnalysisType.KRUSKAL_WALLIS)
        
        # 5. Add correlation for multi-objective studies
        if len(objectives) >= 2:
            analyses.add(AnalysisType.PEARSON_CORRELATION)
        
        # 6. User preferences
        if self.config.preferred_analyses:
            analyses.update(self.config.preferred_analyses)
        
        # Remove excluded analyses
        for excluded in self.config.exclude_analyses:
            analyses.discard(excluded)
        
        # Convert to sorted list
        self.selected_analyses = sorted(list(analyses), key=lambda x: x.value)
        
        return self.selected_analyses
    
    def get_visualization_recommendations(self, analysis_type: AnalysisType) -> List[str]:
        """
        Recommend appropriate visualizations for each analysis type.
        
        Returns:
            List of chart types: ['scree_plot', 'factor_loadings', 'path_diagram', etc.]
        """
        viz_map = {
            AnalysisType.PCA: ['scree_plot', 'biplot', 'variance_explained'],
            AnalysisType.FACTOR_ANALYSIS: ['scree_plot', 'factor_loadings_heatmap', 'communalities_bar'],
            AnalysisType.CLUSTER_ANALYSIS: ['dendrogram', 'cluster_scatter', 'silhouette_plot'],
            AnalysisType.ANOVA: ['box_plot', 'violin_plot', 'mean_comparison_bar'],
            AnalysisType.PEARSON_CORRELATION: ['correlation_heatmap', 'scatter_matrix'],
            AnalysisType.MULTIPLE_REGRESSION: ['residual_plot', 'qq_plot', 'predicted_vs_actual'],
            AnalysisType.SEM: ['path_diagram', 'model_fit_indices', 'standardized_estimates'],
            AnalysisType.CRONBACH_ALPHA: ['item_total_correlation', 'alpha_if_deleted'],
            AnalysisType.KMO_BARTLETT: ['kmo_bar_chart', 'correlation_matrix'],
            AnalysisType.T_TEST: ['mean_comparison_bar', 'distribution_overlay'],
            AnalysisType.CHI_SQUARE: ['mosaic_plot', 'contingency_heatmap'],
            AnalysisType.MEDIATION_ANALYSIS: ['mediation_diagram', 'indirect_effects_bar'],
        }
        
        return viz_map.get(analysis_type, ['bar_chart'])
    
    def generate_analysis_plan(self, objectives: List[str]) -> Dict[str, Any]:
        """
        Generate a complete analysis plan document.
        
        Returns:
            Dict with analysis plan details
        """
        analyses = self.determine_required_analyses(objectives)
        
        plan = {
            'research_config': {
                'sample_size': self.config.sample_size,
                'design': self.config.research_design.value,
                'measurement_scale': self.config.measurement_scale,
                'confidence_level': self.config.confidence_level
            },
            'selected_analyses': [a.value for a in analyses],
            'analysis_sequence': self._determine_analysis_sequence(analyses),
            'visualizations': {},
            'rationale': self.analysis_rationale
        }
        
        # Add visualizations for each analysis
        for analysis in analyses:
            plan['visualizations'][analysis.value] = self.get_visualization_recommendations(analysis)
        
        return plan
    
    def _determine_analysis_sequence(self, analyses: List[AnalysisType]) -> List[Dict]:
        """
        Determine the logical sequence for running analyses.
        
        Returns:
            Ordered list of analysis steps with dependencies
        """
        sequence = []
        
        # Phase 1: Data Screening & Reliability
        phase1 = []
        if AnalysisType.DESCRIPTIVE_STATS in analyses:
            phase1.append({'analysis': 'descriptive_statistics', 'purpose': 'Data screening'})
        if AnalysisType.CRONBACH_ALPHA in analyses:
            phase1.append({'analysis': 'cronbach_alpha', 'purpose': 'Reliability testing'})
        if AnalysisType.KMO_BARTLETT in analyses:
            phase1.append({'analysis': 'kmo_bartlett', 'purpose': 'Sampling adequacy'})
        
        if phase1:
            sequence.append({'phase': 'Data Screening & Reliability', 'analyses': phase1})
        
        # Phase 2: Dimensionality Reduction
        phase2 = []
        if AnalysisType.FACTOR_ANALYSIS in analyses:
            phase2.append({'analysis': 'factor_analysis', 'purpose': 'Construct validation'})
        if AnalysisType.PCA in analyses:
            phase2.append({'analysis': 'pca', 'purpose': 'Dimensionality reduction'})
        
        if phase2:
            sequence.append({'phase': 'Dimensionality Reduction', 'analyses': phase2})
        
        # Phase 3: Inferential Statistics
        phase3 = []
        if AnalysisType.PEARSON_CORRELATION in analyses:
            phase3.append({'analysis': 'correlation', 'purpose': 'Bivariate relationships'})
        if AnalysisType.T_TEST in analyses or AnalysisType.ANOVA in analyses:
            phase3.append({'analysis': 'group_comparison', 'purpose': 'Mean differences'})
        if AnalysisType.MULTIPLE_REGRESSION in analyses:
            phase3.append({'analysis': 'regression', 'purpose': 'Predictive modeling'})
        
        if phase3:
            sequence.append({'phase': 'Inferential Statistics', 'analyses': phase3})
        
        # Phase 4: Advanced Multivariate
        phase4 = []
        if AnalysisType.SEM in analyses:
            phase4.append({'analysis': 'sem', 'purpose': 'Structural modeling'})
        if AnalysisType.MEDIATION_ANALYSIS in analyses:
            phase4.append({'analysis': 'mediation', 'purpose': 'Indirect effects'})
        if AnalysisType.CLUSTER_ANALYSIS in analyses:
            phase4.append({'analysis': 'clustering', 'purpose': 'Pattern discovery'})
        
        if phase4:
            sequence.append({'phase': 'Advanced Multivariate Analysis', 'analyses': phase4})
        
        return sequence


def parse_research_command(command: str) -> ResearchConfig:
    """
    Parse user command to extract research configuration.
    
    Example:
        /uoj_phd n=500 design=survey analyses=pca,anova,sem exclude=cluster
    
    Returns:
        ResearchConfig object
    """
    config = ResearchConfig()
    
    # Extract sample size
    n_match = re.search(r'n[=\s]+(\d+)', command, re.IGNORECASE)
    if n_match:
        config.sample_size = int(n_match.group(1))
    
    # Extract research design
    design_match = re.search(r'design[=\s]+(\w+)', command, re.IGNORECASE)
    if design_match:
        design_str = design_match.group(1).lower()
        for design in ResearchDesign:
            if design.value in design_str or design_str in design.value:
                config.research_design = design
                break
    
    # Extract preferred analyses
    analyses_match = re.search(r'analyses?[=\s]+([\w,]+)', command, re.IGNORECASE)
    if analyses_match:
        analysis_names = analyses_match.group(1).split(',')
        config.preferred_analyses = []
        for name in analysis_names:
            name = name.strip().lower()
            for analysis_type in AnalysisType:
                if name in analysis_type.value or analysis_type.value.startswith(name):
                    config.preferred_analyses.append(analysis_type)
                    break
    
    # Extract excluded analyses
    exclude_match = re.search(r'exclude[=\s]+([\w,]+)', command, re.IGNORECASE)
    if exclude_match:
        exclude_names = exclude_match.group(1).split(',')
        config.exclude_analyses = []
        for name in exclude_names:
            name = name.strip().lower()
            for analysis_type in AnalysisType:
                if name in analysis_type.value:
                    config.exclude_analyses.append(analysis_type)
                    break
    
    # Extract measurement scale
    scale_match = re.search(r'scale[=\s]+(\w+)', command, re.IGNORECASE)
    if scale_match:
        config.measurement_scale = scale_match.group(1).lower()
    
    return config


# Example usage
if __name__ == "__main__":
    # Test the system
    objectives = [
        "To examine the institutional framework governing security sector reform",
        "To analyze the key factors influencing security sector reform",
        "To evaluate the effectiveness of current security sector reform initiatives",
        "To assess the relationship between reform progress and political stability"
    ]
    
    # Parse command
    command = "/uoj_phd n=385 design=survey analyses=pca,factor,anova scale=likert"
    config = parse_research_command(command)
    
    # Create intelligence system
    ai = AnalysisIntelligence(config)
    
    # Generate plan
    plan = ai.generate_analysis_plan(objectives)
    
    print("=" * 80)
    print("ANALYSIS PLAN")
    print("=" * 80)
    print(f"\nSample Size: {plan['research_config']['sample_size']}")
    print(f"Design: {plan['research_config']['design']}")
    print(f"\nSelected Analyses ({len(plan['selected_analyses'])}):")
    for analysis in plan['selected_analyses']:
        print(f"  - {analysis}")
    
    print(f"\nAnalysis Sequence:")
    for phase in plan['analysis_sequence']:
        print(f"\n  {phase['phase']}:")
        for analysis in phase['analyses']:
            print(f"    - {analysis['analysis']}: {analysis['purpose']}")
    
    print(f"\nVisualizations:")
    for analysis, viz_list in plan['visualizations'].items():
        print(f"  {analysis}: {', '.join(viz_list)}")
