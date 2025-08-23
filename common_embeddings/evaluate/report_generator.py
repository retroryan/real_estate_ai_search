"""
Report generator for evaluation results.

Generates HTML and text reports from evaluation metrics.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from .metrics_calculator import AggregateMetrics


class ReportGenerator:
    """Generates evaluation reports."""
    
    def generate(
        self,
        metrics: AggregateMetrics,
        queries_json: Path,
        articles_json: Path,
        output_dir: Path
    ) -> Path:
        """
        Generate evaluation report.
        
        Args:
            metrics: Calculated metrics
            queries_json: Path to queries JSON
            articles_json: Path to articles JSON
            output_dir: Output directory
            
        Returns:
            Path to generated report
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate text report
        text_report = self._generate_text_report(metrics)
        text_path = output_dir / "evaluation_report.txt"
        with open(text_path, 'w') as f:
            f.write(text_report)
        
        # Generate HTML report
        html_report = self._generate_html_report(
            metrics, queries_json, articles_json
        )
        html_path = output_dir / "evaluation_report.html"
        with open(html_path, 'w') as f:
            f.write(html_report)
        
        return html_path
    
    def _generate_text_report(self, metrics: AggregateMetrics) -> str:
        """
        Generate text format report.
        
        Args:
            metrics: Calculated metrics
            
        Returns:
            Text report string
        """
        from ..evaluate.metrics_calculator import MetricsCalculator
        calculator = MetricsCalculator()
        return calculator.format_metrics(metrics)
    
    def _generate_html_report(
        self,
        metrics: AggregateMetrics,
        queries_json: Path,
        articles_json: Path
    ) -> str:
        """
        Generate HTML format report.
        
        Args:
            metrics: Calculated metrics
            queries_json: Path to queries JSON
            articles_json: Path to articles JSON
            
        Returns:
            HTML report string
        """
        # Load query and article data for context
        with open(queries_json) as f:
            queries_data = json.load(f)
        
        with open(articles_json) as f:
            articles_data = json.load(f)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Wikipedia Embeddings Evaluation Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #666;
            margin-top: 30px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .category-section {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
        }}
        .timestamp {{
            color: #999;
            font-size: 0.9em;
            text-align: right;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Wikipedia Embeddings Evaluation Report</h1>
        
        <h2>Overall Metrics</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Precision</div>
                <div class="metric-value">{metrics.overall_precision:.1%}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Recall</div>
                <div class="metric-value">{metrics.overall_recall:.1%}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">F1 Score</div>
                <div class="metric-value">{metrics.overall_f1:.1%}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Mean Average Precision</div>
                <div class="metric-value">{metrics.mean_map:.1%}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Mean Reciprocal Rank</div>
                <div class="metric-value">{metrics.mean_mrr:.1%}</div>
            </div>
        </div>
        
        <h2>Performance at Different K Values</h2>
        <table>
            <tr>
                <th>K</th>
                <th>Precision@K</th>
                <th>Recall@K</th>
                <th>F1@K</th>
                <th>NDCG@K</th>
            </tr>
"""
        
        for k in sorted(metrics.mean_precision_at_k.keys()):
            html += f"""
            <tr>
                <td>{k}</td>
                <td>{metrics.mean_precision_at_k[k]:.1%}</td>
                <td>{metrics.mean_recall_at_k[k]:.1%}</td>
                <td>{metrics.mean_f1_at_k[k]:.1%}</td>
                <td>{metrics.mean_ndcg_at_k[k]:.1%}</td>
            </tr>
"""
        
        html += """
        </table>
        
        <h2>Category-wise Performance</h2>
"""
        
        for category, cat_metrics in metrics.category_metrics.items():
            html += f"""
        <div class="category-section">
            <h3>{category.title()}</h3>
            <table>
                <tr>
"""
            for metric_name, value in cat_metrics.items():
                metric_display = metric_name.replace('_', ' ').title()
                html += f"""
                    <td><strong>{metric_display}:</strong></td>
                    <td>{value:.1%}</td>
"""
            html += """
                </tr>
            </table>
        </div>
"""
        
        html += f"""
        <h2>Evaluation Details</h2>
        <ul>
            <li><strong>Total Articles:</strong> {len(articles_data['articles'])}</li>
            <li><strong>Total Queries:</strong> {len(queries_data['queries'])}</li>
            <li><strong>Query Categories:</strong> {', '.join(queries_data.get('categories', {{}}).keys())}</li>
        </ul>
        
        <div class="timestamp">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
        
        return html