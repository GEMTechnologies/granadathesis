"""
Dataset Analyzer Service

Analyzes uploaded datasets (Excel, CSV, JSON) and extracts:
- Schema (columns, types)
- Statistical summaries
- Patterns and relationships
- Suggested operations
"""
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional
import json


class DatasetAnalyzer:
    """Intelligent dataset analysis service."""
    
    def __init__(self):
        self.supported_formats = ['xlsx', 'xls', 'csv', 'json', 'parquet']
    
    async def analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze dataset and extract comprehensive intelligence.
        
        Args:
            file_path: Path to dataset file
            
        Returns:
            Dictionary containing schema, stats, patterns, and suggestions
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Dataset not found: {file_path}")
        
        ext = file_path.suffix.lower().replace('.', '')
        
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported file format: {ext}. Supported: {self.supported_formats}")
        
        # Load dataset
        df = await self._load_dataset(file_path, ext)
        
        # Perform comprehensive analysis
        analysis = {
            "file_info": self._analyze_file_info(file_path, ext),
            "schema": self._analyze_schema(df),
            "statistics": self._analyze_statistics(df),
            "patterns": self._detect_patterns(df),
            "quality": self._analyze_quality(df),
            "samples": self._extract_samples(df),
            "suggested_operations": self._suggest_operations(df)
        }
        
        return analysis
    
    async def _load_dataset(self, file_path: Path, ext: str) -> pd.DataFrame:
        """Load dataset based on file type."""
        try:
            if ext in ['xlsx', 'xls']:
                return pd.read_excel(file_path)
            elif ext == 'csv':
                # Auto-detect delimiter
                return pd.read_csv(file_path)
            elif ext == 'json':
                return pd.read_json(file_path)
            elif ext == 'parquet':
                return pd.read_parquet(file_path)
            else:
                raise ValueError(f"Unsupported format: {ext}")
        except Exception as e:
            raise Exception(f"Error loading dataset: {e}")
    
    def _analyze_file_info(self, file_path: Path, ext: str) -> Dict[str, Any]:
        """Extract basic file information."""
        return {
            "filename": file_path.name,
            "format": ext,
            "size_bytes": file_path.stat().st_size,
            "size_mb": round(file_path.stat().st_size / (1024 * 1024), 2)
        }
    
    def _analyze_schema(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze dataset schema."""
        schema = {
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": list(df.columns),
            "dtypes": {},
            "inferred_types": {}
        }
        
        for col in df.columns:
            # Raw dtype
            schema["dtypes"][col] = str(df[col].dtype)
            
            # Inferred semantic type
            schema["inferred_types"][col] = self._infer_column_type(df[col])
        
        return schema
    
    def _infer_column_type(self, series: pd.Series) -> str:
        """Infer semantic type of column."""
        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"
        
        # Check for numeric
        if pd.api.types.is_numeric_dtype(series):
            # Check if it's an ID (sequential integers)
            if series.dtype == 'int64' and series.is_monotonic_increasing:
                return "id"
            # Check if it's categorical (low cardinality)
            if series.nunique() < len(series) * 0.05:
                return "categorical_numeric"
            return "numeric"
        
        # Check for categorical strings
        if series.dtype == 'object':
            unique_ratio = series.nunique() / len(series) if len(series) > 0 else 0
            if unique_ratio < 0.05:
                return "categorical"
            elif unique_ratio > 0.95:
                return "unique_identifier"
            else:
                return "text"
        
        return "unknown"
    
    def _analyze_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistical summaries."""
        stats = {
            "numeric": {},
            "categorical": {}
        }
        
        # Numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            desc = df[numeric_cols].describe()
            stats["numeric"] = desc.to_dict()
        
        # Categorical columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            stats["categorical"][col] = {
                "unique_count": df[col].nunique(),
                "top_values": df[col].value_counts().head(5).to_dict(),
                "mode": df[col].mode()[0] if len(df[col].mode()) > 0 else None
            }
        
        return stats
    
    def _detect_patterns(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect patterns in the dataset."""
        patterns = []
        
        # Time series detection
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        if len(datetime_cols) > 0:
            patterns.append({
                "type": "time_series",
                "description": "Dataset contains temporal data",
                "columns": list(datetime_cols)
            })
        
        # Correlation detection (numeric columns)
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr()
            high_corr = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_val = corr_matrix.iloc[i, j]
                    if abs(corr_val) > 0.7:  # Strong correlation
                        high_corr.append({
                            "col1": corr_matrix.columns[i],
                            "col2": corr_matrix.columns[j],
                            "correlation": round(corr_val, 3)
                        })
            
            if high_corr:
                patterns.append({
                    "type": "correlation",
                    "description": "Strong correlations detected",
                    "correlations": high_corr
                })
        
        # Hierarchical structure detection
        # Check if there are columns that look like hierarchies (e.g., country > city)
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 1:
            # Simple heuristic: if one column's unique count is significantly smaller
            unique_counts = {col: df[col].nunique() for col in categorical_cols}
            if len(unique_counts) > 1:
                patterns.append({
                    "type": "hierarchical_potential",
                    "description": "Potential hierarchical structure",
                    "cardinality": unique_counts
                })
        
        return patterns
    
    def _analyze_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data quality."""
        quality = {
            "completeness": {},
            "duplicates": 0,
            "issues": []
        }
        
        # Missing values
        for col in df.columns:
            null_count = df[col].isnull().sum()
            null_pct = (null_count / len(df)) * 100 if len(df) > 0 else 0
            quality["completeness"][col] = {
                "null_count": int(null_count),
                "null_percentage": round(null_pct, 2)
            }
            
            if null_pct > 50:
                quality["issues"].append(f"Column '{col}' has {null_pct:.1f}% missing values")
        
        # Duplicates
        quality["duplicates"] = int(df.duplicated().sum())
        if quality["duplicates"] > 0:
            quality["issues"].append(f"Found {quality['duplicates']} duplicate rows")
        
        return quality
    
    def _extract_samples(self, df: pd.DataFrame, n: int = 5) -> Dict[str, Any]:
        """Extract sample rows."""
        return {
            "head": df.head(n).to_dict(orient='records'),
            "random": df.sample(min(n, len(df))).to_dict(orient='records') if len(df) > 0 else []
        }
    
    def _suggest_operations(self, df: pd.DataFrame) -> List[str]:
        """Suggest possible operations based on data characteristics."""
        suggestions = []
        
        # Based on data types
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            suggestions.append("Statistical analysis (mean, median, trends)")
            suggestions.append("Aggregation and grouping")
        
        if len(numeric_cols) > 1:
            suggestions.append("Correlation analysis")
            suggestions.append("Predictive modeling")
        
        datetime_cols = df.select_dtypes(include=['datetime64']).columns
        if len(datetime_cols) > 0:
            suggestions.append("Time series analysis")
            suggestions.append("Trend forecasting")
        
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            suggestions.append("Category distribution analysis")
            suggestions.append("Segmentation")
        
        # Based on row count
        if len(df) > 10000:
            suggestions.append("Large dataset - consider sampling or aggregation")
        
        return suggestions
    
    async def analyze_with_llm(
        self,
        file_path: str,
        analysis_type: str = "comprehensive",
        job_id: str = None
    ) -> Dict[str, Any]:
        """
        Analyze dataset with LLM-powered insights.
        
        Args:
            file_path: Path to dataset
            analysis_type: Type of analysis (comprehensive, statistical, trends, quality)
            job_id: Job ID for streaming updates
            
        Returns:
            Analysis with AI-generated insights
        """
        from services.deepseek_direct import deepseek_direct_service
        from core.events import events
        
        # First do basic analysis
        basic_analysis = await self.analyze(file_path)
        
        # Prepare data summary for LLM
        schema = basic_analysis.get("schema", {})
        stats = basic_analysis.get("statistics", {})
        quality = basic_analysis.get("quality", {})
        samples = basic_analysis.get("samples", {}).get("head", [])[:3]
        
        # Create context for LLM
        context = f"""Dataset Analysis Context:
- Rows: {schema.get('rows', 0)}, Columns: {schema.get('columns', 0)}
- Column Names: {', '.join(schema.get('column_names', [])[:10])}
- Column Types: {json.dumps(schema.get('inferred_types', {}), indent=2)[:500]}
- Numeric Stats: {json.dumps(stats.get('numeric', {}), indent=2)[:500]}
- Data Quality Issues: {quality.get('issues', [])}
- Sample Data: {json.dumps(samples, indent=2)[:500]}"""

        # Analysis type specific prompts
        prompts = {
            "comprehensive": f"""Analyze this dataset comprehensively:
{context}

Provide insights on:
1. **Data Overview**: What does this data represent?
2. **Key Findings**: What are the most important patterns?
3. **Data Quality**: Any issues to address?
4. **Recommendations**: What analyses would be valuable?

Be specific and actionable. Format with markdown.""",
            
            "statistical": f"""Provide statistical analysis of this dataset:
{context}

Include:
1. **Distribution Analysis**: How is the data distributed?
2. **Central Tendency**: Key means, medians, modes
3. **Variability**: Standard deviations, ranges
4. **Outliers**: Any anomalies detected?
5. **Correlations**: Relationships between variables

Use specific numbers from the data.""",
            
            "trends": f"""Identify trends and patterns in this dataset:
{context}

Analyze:
1. **Temporal Patterns**: Any time-based trends?
2. **Growth/Decline**: Are values increasing or decreasing?
3. **Seasonality**: Cyclical patterns?
4. **Correlations**: Variables that move together?
5. **Predictions**: What might happen next?""",
            
            "quality": f"""Assess data quality for this dataset:
{context}

Evaluate:
1. **Completeness**: Missing values analysis
2. **Accuracy**: Potential errors or inconsistencies
3. **Consistency**: Data format issues
4. **Recommendations**: How to clean/improve the data"""
        }
        
        prompt = prompts.get(analysis_type, prompts["comprehensive"])
        
        if job_id:
            await events.publish(job_id, "agent_stream", {
                "agent": "analyzer",
                "content": f"🔍 **Analyzing dataset with AI...**\n\n_Analysis type: {analysis_type}_\n\n",
                "workspace_id": "default"
            })
        
        # Get LLM insights
        insights = ""
        try:
            if job_id:
                # Stream the response
                async def stream_handler(chunk):
                    nonlocal insights
                    insights += chunk
                    await events.publish(job_id, "agent_stream", {
                        "agent": "analyzer",
                        "content": chunk,
                        "workspace_id": "default",
                        "append": True
                    })
                
                await deepseek_direct_service.generate_content(
                    prompt=prompt,
                    max_tokens=2000,
                    stream=True,
                    stream_callback=stream_handler
                )
            else:
                insights = await deepseek_direct_service.generate_content(
                    prompt=prompt,
                    max_tokens=2000
                )
        except Exception as e:
            insights = f"⚠️ Analysis error: {e}"
        
        return {
            **basic_analysis,
            "ai_insights": insights,
            "analysis_type": analysis_type
        }
    
    async def analyze_streaming(
        self,
        file_path: str,
        job_id: str,
        workspace_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Full streaming analysis with real-time UI updates.
        
        Streams each analysis phase to the user as it completes.
        """
        from core.events import events
        from services.graph_service import get_graph_service
        
        results = {}
        file_path = Path(file_path)
        
        # Phase 1: Load and basic info
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": f"## 📊 Dataset Analysis\n\n**File:** `{file_path.name}`\n\n### Phase 1: Loading Data...\n",
            "workspace_id": workspace_id
        })
        
        ext = file_path.suffix.lower().replace('.', '')
        df = await self._load_dataset(file_path, ext)
        
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer", 
            "content": f"✅ Loaded **{len(df):,} rows** × **{len(df.columns)} columns**\n\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        # Phase 2: Schema Analysis
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "### Phase 2: Schema Analysis\n\n| Column | Type | Inferred |\n|--------|------|----------|\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        schema = self._analyze_schema(df)
        for col in list(schema['column_names'])[:10]:
            dtype = schema['dtypes'].get(col, 'unknown')
            inferred = schema['inferred_types'].get(col, 'unknown')
            await events.publish(job_id, "agent_stream", {
                "agent": "analyzer",
                "content": f"| {col} | {dtype} | {inferred} |\n",
                "workspace_id": workspace_id,
                "append": True
            })
        
        if len(schema['column_names']) > 10:
            await events.publish(job_id, "agent_stream", {
                "agent": "analyzer",
                "content": f"| ... | ({len(schema['column_names']) - 10} more) | ... |\n",
                "workspace_id": workspace_id,
                "append": True
            })
        
        # Phase 3: Statistics
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "\n### Phase 3: Statistical Summary\n\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        stats = self._analyze_statistics(df)
        numeric_stats = stats.get("numeric", {})
        if numeric_stats:
            first_col = list(numeric_stats.keys())[0] if numeric_stats else None
            if first_col:
                col_stats = numeric_stats[first_col]
                await events.publish(job_id, "agent_stream", {
                    "agent": "analyzer",
                    "content": f"**{first_col}**: Mean={col_stats.get('mean', 0):.2f}, "
                               f"Std={col_stats.get('std', 0):.2f}, "
                               f"Min={col_stats.get('min', 0):.2f}, "
                               f"Max={col_stats.get('max', 0):.2f}\n\n",
                    "workspace_id": workspace_id,
                    "append": True
                })
        
        # Phase 4: Quality
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "### Phase 4: Data Quality\n\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        quality = self._analyze_quality(df)
        issues = quality.get("issues", [])
        if issues:
            for issue in issues:
                await events.publish(job_id, "agent_stream", {
                    "agent": "analyzer",
                    "content": f"⚠️ {issue}\n",
                    "workspace_id": workspace_id,
                    "append": True
                })
        else:
            await events.publish(job_id, "agent_stream", {
                "agent": "analyzer",
                "content": "✅ No major quality issues detected\n",
                "workspace_id": workspace_id,
                "append": True
            })
        
        # Phase 5: Generate Charts
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "\n### Phase 5: Generating Visualizations...\n\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        try:
            graph_service = get_graph_service()
            chart_result = graph_service.auto_chart(df, workspace_id)
            if chart_result.get("success"):
                for chart in chart_result.get("charts", []):
                    path = chart.get("relative_path", "")
                    await events.publish(job_id, "agent_stream", {
                        "agent": "analyzer",
                        "content": f"📈 Generated: `{path}`\n",
                        "workspace_id": workspace_id,
                        "append": True
                    })
        except Exception as e:
            await events.publish(job_id, "agent_stream", {
                "agent": "analyzer",
                "content": f"⚠️ Chart generation skipped: {e}\n",
                "workspace_id": workspace_id,
                "append": True
            })
        
        # Phase 6: AI Insights
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "\n### Phase 6: AI-Powered Insights\n\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        # Get LLM insights with streaming
        full_analysis = await self.analyze_with_llm(
            str(file_path),
            analysis_type="comprehensive",
            job_id=job_id
        )
        
        await events.publish(job_id, "agent_stream", {
            "agent": "analyzer",
            "content": "\n\n---\n✅ **Analysis Complete**\n",
            "workspace_id": workspace_id,
            "append": True
        })
        
        return full_analysis


# Global instance
dataset_analyzer = DatasetAnalyzer()
