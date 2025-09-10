"""
Display and formatting service for semantic search results.

Handles rich console output and result visualization.
"""

from typing import Dict, Any, List
from rich.console import Console
from rich.panel import Panel
from rich import box
from rich.columns import Columns

from ...models import PropertyListing
from ..property.models import PropertySearchResult
from ..property.common_property_display import PropertyTableDisplay, PropertyDisplayConfig
from .constants import (
    MAX_DISPLAY_RESULTS,
    TOP_MATCH_DISPLAY_COUNT,
    DEFAULT_QUERY
)


console = Console()
table_display = PropertyTableDisplay(console)


class SemanticDisplayService:
    """Service for displaying semantic search results."""
    
    @staticmethod
    def display_natural_language_results(result: PropertySearchResult) -> None:
        """Display natural language search results with rich formatting."""
        
        if not result.results:
            console.print("[yellow]No results found[/yellow]")
            return
        
        # Extract query from result description
        query_text = DEFAULT_QUERY
        if "'" in result.query_description:
            query_text = result.query_description.split("'")[1]
        
        # Use common display with semantic configuration
        config = PropertyDisplayConfig(
            table_title="🤖 Natural Language Search Results",
            show_description=True,
            show_score=True,
            show_details=True,
            score_label="Similarity"
        )
        
        table_display.display_properties(
            properties=result.results,
            config=config,
            total_hits=result.total_hits,
            execution_time_ms=result.execution_time_ms
        )
        
        # Show detailed match analysis
        console.print(f"\n[bold cyan]🔍 Why These Properties Match: '{query_text}'[/bold cyan]")
        
        # Show property descriptions with match highlighting
        for i, prop in enumerate(result.results[:TOP_MATCH_DISPLAY_COUNT], 1):
            SemanticDisplayService.display_property_match_panel(prop, i, query_text)
        
        # Add overall explanation
        SemanticDisplayService.display_semantic_search_explanation()
    
    @staticmethod
    def display_property_match_panel(prop: PropertyListing, index: int, query_text: str) -> None:
        """Display a single property match with insights."""
        desc = prop.description or 'No description available'
        
        # Generate match insights
        insights = SemanticDisplayService.generate_match_insights(query_text, desc, prop)
        
        street = prop.address.street or 'Unknown'
        panel_content = f"[bold]{street}[/bold]\n"
        panel_content += f"[yellow]${prop.price:,.0f}[/yellow] • "
        panel_content += f"{prop.bedrooms} bed / {prop.bathrooms} bath • "
        panel_content += f"{prop.square_feet:,} sq ft\n\n" if prop.square_feet else "N/A sq ft\n\n"
        panel_content += f"[bright_blue]{desc}[/bright_blue]\n\n"
        
        if insights:
            panel_content += "[bold green]Match Insights:[/bold green]\n"
            for insight in insights:
                panel_content += f"{insight}\n"
        
        panel = Panel(
            panel_content.strip(),
            title=f"Match #{index} - AI Semantic Analysis",
            border_style="green"
        )
        console.print(panel)
    
    @staticmethod
    def generate_match_insights(query_text: str, description: str, prop: PropertyListing) -> List[str]:
        """Generate insights about why a property matches the query."""
        insights = []
        query_lower = query_text.lower()
        desc_lower = description.lower() if description else ''
        
        if 'modern' in query_lower and any(word in desc_lower for word in ['modern', 'contemporary', 'updated', 'new']):
            insights.append("✓ Modern/contemporary features mentioned")
        if 'mountain' in query_lower and any(word in desc_lower for word in ['view', 'mountain', 'vista', 'scenic']):
            insights.append("✓ Views/scenic location described")  
        if 'open' in query_lower and any(word in desc_lower for word in ['open', 'spacious', 'floor plan', 'concept']):
            insights.append("✓ Open/spacious layout features")
        if 'home' in query_lower and any(word in desc_lower for word in ['family', 'home', 'residential', 'neighborhood']):
            insights.append("✓ Family-friendly/residential character")
            
        # Add score insight
        insights.append(f"🎯 Semantic similarity score: {prop.score:.3f}" if prop.score else "🎯 Semantic similarity score: 0.000")
        
        return insights
    
    @staticmethod
    def display_semantic_search_explanation() -> None:
        """Display explanation of how semantic search works."""
        explanation = Panel(
            f"[bold yellow]How Semantic Search Works:[/bold yellow]\n\n"
            f"• Query converted to 1024-dimensional vector using Voyage-3 AI model\n"
            f"• Property descriptions pre-encoded with same model during indexing\n"
            f"• Vector similarity (cosine distance) finds semantically related properties\n"
            f"• Results ranked by conceptual similarity, not just keyword matching\n"
            f"• AI understands context: 'modern home' → contemporary, updated, new construction",
            title="🧠 AI Understanding",
            border_style="yellow"
        )
        console.print(explanation)
    
    @staticmethod
    def format_property_summary(prop: PropertyListing, index: int) -> str:
        """Format a property summary for display."""
        desc = prop.description or 'No description available'
        street = prop.address.street or 'Unknown'
        
        summary = f"[bold]{index}. {street}[/bold]\n"
        summary += f"   [green]{prop.display_price}[/green] • "
        summary += f"{prop.bedrooms} bed / {prop.bathrooms} bath • "
        summary += f"[cyan]Score: {prop.score:.3f}[/cyan]\n" if prop.score else "[cyan]Score: 0.000[/cyan]\n"
        summary += f"   [dim]{desc}[/dim]\n\n"
        
        return summary
    
    @staticmethod
    def display_examples_summary_stats(num_queries: int, total_time: float, total_found: int) -> None:
        """Display summary statistics for example queries."""
        summary = Panel(
            f"[green]✓ Completed {num_queries} natural language searches[/green]\n"
            f"[yellow]Total execution time: {total_time:.0f}ms[/yellow]\n"
            f"[cyan]Total properties found: {total_found}[/cyan]\n"
            f"[magenta]Average time per query: {total_time/num_queries:.1f}ms[/magenta]",
            title="[bold green]Summary[/bold green]",
            border_style="green"
        )
        console.print(summary)
    
    @staticmethod
    def display_semantic_vs_keyword_comparison(
        result: PropertySearchResult, 
        query: str, 
        comparison: Dict[str, Any]
    ) -> None:
        """Display semantic vs keyword comparison with rich formatting."""
        
        console.print("\n[bold cyan]Semantic vs Keyword Search Comparison[/bold cyan]")
        console.print("=" * 70)
        console.print(f"\n[yellow]Query: '{query}'[/yellow]\n")
        
        # Create side-by-side comparison
        semantic_data = comparison['semantic']
        keyword_data = comparison['keyword']
        
        # Semantic Search Results Panel
        semantic_content = f"[green]Found:[/green] {semantic_data['total_hits']} properties\n"
        semantic_content += f"[yellow]Time:[/yellow] {semantic_data['execution_time_ms']:.1f}ms\n"
        semantic_content += f"[cyan]Top Score:[/cyan] {comparison['comparison']['semantic_top_score']:.3f}\n\n"
        semantic_content += "[bold]Top 3 Results:[/bold]\n"
        
        for i, prop in enumerate(semantic_data['top_results'][:3], 1):
            addr = prop.get('address', {})
            semantic_content += f"{i}. {addr.get('street', 'Unknown')}\n"
            semantic_content += f"   ${prop.get('price', 0):,.0f} • Score: {prop.get('_score', 0):.3f}\n"
        
        semantic_panel = Panel(
            semantic_content.strip(),
            title="[bold green]🤖 Semantic Search (AI Embeddings)[/bold green]",
            border_style="green"
        )
        
        # Keyword Search Results Panel  
        keyword_content = f"[green]Found:[/green] {keyword_data['total_hits']} properties\n"
        keyword_content += f"[yellow]Time:[/yellow] {keyword_data['execution_time_ms']:.1f}ms\n"
        keyword_content += f"[cyan]Top Score:[/cyan] {comparison['comparison']['keyword_top_score']:.3f}\n\n"
        keyword_content += "[bold]Top 3 Results:[/bold]\n"
        
        for i, prop in enumerate(keyword_data['top_results'][:3], 1):
            addr = prop.get('address', {})
            keyword_content += f"{i}. {addr.get('street', 'Unknown')}\n"
            keyword_content += f"   ${prop.get('price', 0):,.0f} • Score: {prop.get('_score', 0):.3f}\n"
        
        keyword_panel = Panel(
            keyword_content.strip(),
            title="[bold blue]📝 Keyword Search (BM25)[/bold blue]",
            border_style="blue"
        )
        
        # Display side by side
        columns = Columns([semantic_panel, keyword_panel], equal=True, expand=True)
        console.print(columns)
        
        # Comparison Analysis
        SemanticDisplayService.display_comparison_analysis(comparison['comparison'])
    
    @staticmethod
    def display_comparison_analysis(comp: Dict[str, Any]) -> None:
        """Display analysis of search comparison."""
        analysis = f"""[bold]Analysis:[/bold]
        
• [cyan]Result Overlap:[/cyan] {comp['overlap_count']} properties appear in both top 5 results
• [green]Unique to Semantic:[/green] {comp['unique_to_semantic']} properties found only by semantic search
• [blue]Unique to Keyword:[/blue] {comp['unique_to_keyword']} properties found only by keyword search

[bold]Key Insights:[/bold]
• Semantic search understands meaning and context beyond exact word matches
• Keyword search is faster and finds exact phrase matches effectively
• Combining both approaches can provide comprehensive search coverage"""
        
        analysis_panel = Panel(
            analysis,
            title="[bold yellow]📊 Comparison Analysis[/bold yellow]",
            border_style="yellow"
        )
        console.print(analysis_panel)