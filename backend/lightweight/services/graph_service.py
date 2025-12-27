"""
Graph Service - Advanced Chart and Graph Generation

Features:
- Bar, line, pie, scatter, histogram charts
- Auto-detect best chart type from data
- Save to workspace as images
- Interactive chart options

Dependencies: matplotlib, seaborn, pandas
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import json

# Data handling
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None

# Charts
try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None

# Enhanced styling
try:
    import seaborn as sns
    SEABORN_AVAILABLE = True
except ImportError:
    SEABORN_AVAILABLE = False
    sns = None


class GraphService:
    """Service for creating charts and graphs from data."""
    
    def __init__(self, workspace_dir: str = "workspaces"):
        self.workspace_dir = Path(workspace_dir)
        
        # Set style
        if SEABORN_AVAILABLE:
            sns.set_style("whitegrid")
            sns.set_palette("husl")
    
    def bar_chart(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        x: str,
        y: Union[str, List[str]],
        title: str = "Bar Chart",
        workspace_id: str = "default",
        filename: str = None,
        horizontal: bool = False,
        stacked: bool = False
    ) -> Dict[str, Any]:
        """Create a bar chart."""
        return self._create_chart(
            data, "bar", x, y, title, workspace_id, filename,
            horizontal=horizontal, stacked=stacked
        )
    
    def line_chart(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        x: str,
        y: Union[str, List[str]],
        title: str = "Line Chart",
        workspace_id: str = "default",
        filename: str = None,
        markers: bool = True
    ) -> Dict[str, Any]:
        """Create a line chart."""
        return self._create_chart(
            data, "line", x, y, title, workspace_id, filename,
            markers=markers
        )
    
    def pie_chart(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        labels: str,
        values: str,
        title: str = "Pie Chart",
        workspace_id: str = "default",
        filename: str = None,
        show_percentages: bool = True
    ) -> Dict[str, Any]:
        """Create a pie chart."""
        return self._create_chart(
            data, "pie", labels, values, title, workspace_id, filename,
            show_percentages=show_percentages
        )
    
    def scatter_plot(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        x: str,
        y: str,
        title: str = "Scatter Plot",
        workspace_id: str = "default",
        filename: str = None,
        color_by: str = None,
        size_by: str = None
    ) -> Dict[str, Any]:
        """Create a scatter plot."""
        return self._create_chart(
            data, "scatter", x, y, title, workspace_id, filename,
            color_by=color_by, size_by=size_by
        )
    
    def histogram(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        column: str,
        title: str = "Histogram",
        workspace_id: str = "default",
        filename: str = None,
        bins: int = 20
    ) -> Dict[str, Any]:
        """Create a histogram."""
        return self._create_chart(
            data, "histogram", column, None, title, workspace_id, filename,
            bins=bins
        )
    
    def _create_chart(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        chart_type: str,
        x: str,
        y: Union[str, List[str], None],
        title: str,
        workspace_id: str,
        filename: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Internal chart creation method."""
        if not MATPLOTLIB_AVAILABLE:
            return {"success": False, "error": "matplotlib not installed"}
        
        try:
            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data) if PANDAS_AVAILABLE else None
            elif isinstance(data, dict):
                df = pd.DataFrame(data) if PANDAS_AVAILABLE else None
            else:
                df = data
            
            if df is None:
                return {"success": False, "error": "pandas not available"}
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == "bar":
                kind = 'barh' if kwargs.get('horizontal') else 'bar'
                if isinstance(y, list):
                    df.plot(kind=kind, x=x, y=y, ax=ax, stacked=kwargs.get('stacked', False))
                else:
                    df.plot(kind=kind, x=x, y=y, ax=ax)
                    
            elif chart_type == "line":
                marker = 'o' if kwargs.get('markers') else None
                if isinstance(y, list):
                    for col in y:
                        ax.plot(df[x], df[col], marker=marker, label=col)
                    ax.legend()
                else:
                    ax.plot(df[x], df[y], marker=marker)
                ax.set_xlabel(x)
                ax.set_ylabel(y if isinstance(y, str) else "Values")
                
            elif chart_type == "pie":
                if kwargs.get('show_percentages'):
                    autopct = '%1.1f%%'
                else:
                    autopct = None
                ax.pie(df[y], labels=df[x], autopct=autopct)
                ax.axis('equal')
                
            elif chart_type == "scatter":
                color = None
                size = 50
                if kwargs.get('color_by') and kwargs['color_by'] in df.columns:
                    color = df[kwargs['color_by']]
                if kwargs.get('size_by') and kwargs['size_by'] in df.columns:
                    size = df[kwargs['size_by']] * 10
                
                scatter = ax.scatter(df[x], df[y], c=color, s=size, alpha=0.7)
                ax.set_xlabel(x)
                ax.set_ylabel(y)
                
                if color is not None:
                    plt.colorbar(scatter, ax=ax, label=kwargs['color_by'])
                    
            elif chart_type == "histogram":
                ax.hist(df[x], bins=kwargs.get('bins', 20), edgecolor='white')
                ax.set_xlabel(x)
                ax.set_ylabel("Frequency")
            
            ax.set_title(title)
            plt.tight_layout()
            
            # Save
            output_path = self._save_chart(fig, workspace_id, filename, chart_type)
            plt.close()
            
            return {
                "success": True,
                "path": str(output_path),
                "relative_path": f"{workspace_id}/graphs/{output_path.name}",
                "chart_type": chart_type
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _save_chart(
        self, 
        fig, 
        workspace_id: str, 
        filename: str = None,
        chart_type: str = "chart"
    ) -> Path:
        """Save chart to workspace."""
        workspace_path = self.workspace_dir / workspace_id / "graphs"
        workspace_path.mkdir(parents=True, exist_ok=True)
        
        if not filename:
            import time
            filename = f"{chart_type}_{int(time.time())}.png"
        elif not filename.endswith('.png'):
            filename += '.png'
        
        output_path = workspace_path / filename
        fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        return output_path
    
    def auto_chart(
        self,
        data: Union[List[Dict], Dict, 'pd.DataFrame'],
        workspace_id: str = "default"
    ) -> Dict[str, Any]:
        """
        Automatically detect best chart type and create charts.
        
        Returns multiple charts based on data analysis.
        """
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "pandas not installed"}
        
        try:
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                df = pd.DataFrame(data)
            else:
                df = data
            
            charts = []
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
            
            # Bar chart for categorical + numeric
            if categorical_cols and numeric_cols:
                result = self.bar_chart(
                    df, categorical_cols[0], numeric_cols[0],
                    title=f"{numeric_cols[0]} by {categorical_cols[0]}",
                    workspace_id=workspace_id,
                    filename=f"bar_{numeric_cols[0]}.png"
                )
                if result.get("success"):
                    charts.append(result)
            
            # Line chart for time-series-like data
            if len(numeric_cols) >= 2:
                result = self.line_chart(
                    df, df.columns[0], numeric_cols[:3],
                    title="Trend Analysis",
                    workspace_id=workspace_id,
                    filename="trend_line.png"
                )
                if result.get("success"):
                    charts.append(result)
            
            # Histogram for distribution
            if numeric_cols:
                result = self.histogram(
                    df, numeric_cols[0],
                    title=f"{numeric_cols[0]} Distribution",
                    workspace_id=workspace_id,
                    filename=f"histogram_{numeric_cols[0]}.png"
                )
                if result.get("success"):
                    charts.append(result)
            
            # Scatter for correlation
            if len(numeric_cols) >= 2:
                result = self.scatter_plot(
                    df, numeric_cols[0], numeric_cols[1],
                    title=f"{numeric_cols[0]} vs {numeric_cols[1]}",
                    workspace_id=workspace_id,
                    filename="correlation_scatter.png"
                )
                if result.get("success"):
                    charts.append(result)
            
            return {
                "success": True,
                "charts": charts,
                "chart_count": len(charts)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_graph_service = None

def get_graph_service() -> GraphService:
    """Get global graph service instance."""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service
