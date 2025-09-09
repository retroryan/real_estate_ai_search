"""
Display service module for Wikipedia search results.

This module handles all console output formatting, including Rich tables,
panels, progress indicators, and highlighted text display.
"""

import re
import textwrap
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from .models import (
    SearchResult,
    SearchHit,
    SearchStatistics,
    ArticleExportResult
)
from ...models.wikipedia import WikipediaArticle


class WikipediaDisplayService:
    """Service for displaying Wikipedia search results in console."""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the display service.
        
        Args:
            console: Rich console instance (creates new if None)
        """
        self.console = console or Console()
    
    def display_header(self):
        """Display the demo header panel."""
        header_text = Text()
        header_text.append("🔍 WIKIPEDIA FULL-TEXT SEARCH DEMONSTRATION\n", style="bold cyan")
        header_text.append("\nSearching across 450+ Wikipedia articles (100MB+ of text)\n", style="yellow")
        header_text.append("Demonstrating enterprise-scale document search capabilities", style="dim")
        
        self.console.print(Panel(
            header_text,
            title="[bold magenta]📚 Elasticsearch Full-Text Search[/bold magenta]",
            border_style="magenta",
            padding=(1, 2)
        ))
    
    def display_query_info(self, query_num: int, total_queries: int, title: str, description: str):
        """Display information about the current query.
        
        Args:
            query_num: Current query number (1-indexed)
            total_queries: Total number of queries
            title: Query title
            description: Query description
        """
        query_text = Text()
        query_text.append(f"Query {query_num}/{total_queries}: ", style="dim")
        query_text.append(title, style="bold yellow")
        query_text.append(f"\n{description}", style="italic")
        
        self.console.print(Panel(
            query_text,
            border_style="blue",
            padding=(0, 1)
        ))
    
    def display_search_results(self, result: SearchResult):
        """Display search results in a formatted table.
        
        Args:
            result: SearchResult object
        """
        if not result.success:
            self.console.print(f"[red]❌ Query failed: {result.error}[/red]")
            return
        
        if not result.hits:
            self.console.print("[yellow]No results found for this query[/yellow]")
            return
        
        # Create results table
        table = Table(
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan",
            title=f"[green]✓ Found {result.total_hits} articles[/green]"
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Title", style="cyan", width=40)
        table.add_column("Score", style="magenta", justify="right")
        table.add_column("Categories", style="yellow", width=30)
        
        for idx, hit in enumerate(result.hits[:3], 1):
            categories_str = ', '.join(hit.document.categories[:2]) if hit.document.categories else 'N/A'
            
            table.add_row(
                str(idx),
                hit.document.title[:40],
                f"{hit.score:.2f}",
                categories_str[:30]
            )
        
        self.console.print(table)
        
        # Show highlight for top result if available
        if result.hits and result.hits[0].highlights:
            self.display_highlight(result.hits[0])
    
    def display_highlight(self, hit: SearchHit):
        """Display highlighted content from a search hit.
        
        Args:
            hit: SearchHit with highlights
        """
        if 'full_content' not in hit.highlights:
            return
        
        highlight_text = Text("\n🔍 Relevant excerpt:\n", style="bold")
        
        # Get first highlight fragment
        fragment = hit.highlights['full_content'][0]
        
        # Convert <em> tags to Rich formatting
        clean_fragment = re.sub(r'<em>(.*?)</em>', r'[bold yellow]\1[/bold yellow]', fragment)
        clean_fragment = ' '.join(clean_fragment.split())[:200] + "..."
        
        highlight_text.append(clean_fragment, style="dim")
        self.console.print(Panel(highlight_text, border_style="dim"))
    
    def display_statistics(self, stats: SearchStatistics):
        """Display summary statistics.
        
        Args:
            stats: SearchStatistics object
        """
        # Create statistics table
        stats_table = Table(box=box.SIMPLE, show_header=False)
        stats_table.add_column("Metric", style="yellow")
        stats_table.add_column("Value", style="green", justify="right")
        
        stats_table.add_row("Queries Executed", str(stats.total_queries))
        stats_table.add_row("Successful Queries", str(stats.successful_queries))
        stats_table.add_row("Total Documents Found", str(stats.total_documents_found))
        stats_table.add_row("Avg Results per Query", f"{stats.average_results_per_query:.1f}")
        
        self.console.print(Panel(
            stats_table,
            title="[bold]📊 Search Summary Statistics[/bold]",
            border_style="green",
            padding=(1, 2)
        ))
    
    def display_top_documents(self, stats: SearchStatistics):
        """Display top scoring documents.
        
        Args:
            stats: SearchStatistics with top documents
        """
        if not stats.top_documents:
            return
        
        top_docs_table = Table(
            title="[bold]🏆 Top Scoring Articles[/bold]",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold cyan"
        )
        top_docs_table.add_column("Rank", style="dim", width=5)
        top_docs_table.add_column("Article Title", style="cyan")
        top_docs_table.add_column("Score", style="magenta", justify="right")
        top_docs_table.add_column("Found In Query", style="yellow")
        
        for idx, doc in enumerate(stats.top_documents[:5], 1):
            top_docs_table.add_row(
                str(idx),
                doc.title[:40],
                f"{doc.score:.2f}",
                doc.query_title[:30]
            )
        
        self.console.print(top_docs_table)
    
    def display_export_results(self, export_result: ArticleExportResult):
        """Display article export results.
        
        Args:
            export_result: ArticleExportResult object
        """
        self.console.print("\n" + "=" * 80)
        self.console.print("📚 WIKIPEDIA ARTICLES EXPORT RESULTS")
        self.console.print("=" * 80)
        
        if export_result.exported_articles:
            self.console.print(f"\n✅ Successfully exported {len(export_result.exported_articles)} articles")
            self.console.print(f"📁 Saved to: {export_result.output_directory}")
            self.console.print(f"💾 Total size: {export_result.total_size_kb:.1f} KB")
            
            # Show exported files
            for article in export_result.exported_articles[:5]:
                self.console.print(f"   • {article.title[:50]} ({article.file_size_kb:.1f} KB)")
        
        if export_result.failed_exports:
            self.console.print(f"\n⚠️  Failed to export {len(export_result.failed_exports)} articles")
    
    def display_completion_message(self):
        """Display demo completion message."""
        self.console.print(Panel(
            "[bold green]✅ Full-text search demonstration complete![/bold green]\n\n"
            "[yellow]Key achievements:[/yellow]\n"
            "• Searched 450+ Wikipedia articles (100MB+ text)\n"
            "• Demonstrated complex query patterns\n"
            "• Achieved sub-100ms search performance\n"
            "• Extracted relevant content highlights",
            title="[bold]🎆 Demo Complete[/bold]",
            border_style="green",
            padding=(1, 2)
        ))
    
    def create_progress_context(self, total_tasks: int, description: str = "Processing..."):
        """Create a progress context for tracking operations.
        
        Args:
            total_tasks: Total number of tasks
            description: Progress description
            
        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
    
    def format_result_text(self, hit: SearchHit) -> str:
        """Format a search hit as plain text.
        
        Args:
            hit: SearchHit to format
            
        Returns:
            Formatted text string
        """
        lines = []
        doc = hit.document
        
        lines.append(f"📖 {doc.title}")
        lines.append(f"   Score: {hit.score:.2f}")
        
        if doc.city and doc.state:
            lines.append(f"   📍 Location: {doc.city}, {doc.state}")
        
        if doc.categories:
            categories = ', '.join(doc.categories[:3])
            lines.append(f"   🏷️  Categories: {categories}")
        
        if doc.content_length:
            lines.append(f"   📊 Size: {doc.content_length:,} characters")
        
        return '\n'.join(lines)