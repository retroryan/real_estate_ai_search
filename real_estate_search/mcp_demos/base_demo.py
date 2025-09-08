"""Base demo class following MCP client best practices and Pydantic patterns."""

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from pydantic import ValidationError

from .client.client import get_mcp_client
from .models.hybrid_search import (
    HybridSearchRequest,
    HybridSearchResponse,
    DemoExecutionResult,
    PerformanceMetrics
)


class BaseMCPDemo(ABC):
    """
    Abstract base class for MCP hybrid search demos.
    
    Follows FastMCP client best practices:
    - Type-safe Pydantic models for all data
    - Robust error handling with structured responses
    - Performance monitoring and metrics collection
    - Clean separation of concerns
    - Rich output formatting
    """
    
    def __init__(self, demo_name: str, demo_number: int):
        """Initialize the demo with name and number."""
        self.demo_name = demo_name
        self.demo_number = demo_number
        self.console = Console()
        self.client = get_mcp_client()
        self.performance_metrics: List[PerformanceMetrics] = []
        
    async def execute_hybrid_search(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """
        Execute a hybrid search with full validation and error handling.
        
        Args:
            request: Validated Pydantic request model
            
        Returns:
            Validated Pydantic response model
            
        Raises:
            ValidationError: If request validation fails
            Exception: If MCP call fails
        """
        start_time = time.time()
        
        try:
            # Execute the MCP tool call
            # Remove include_location_extraction as it's not supported by the new API
            params = request.model_dump(exclude_none=True)
            params.pop('include_location_extraction', None)
            response_data = await self.client.call_tool(
                "search_properties_with_filters",
                params
            )
            
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            
            # Check if this is an error response
            if "error" in response_data and "results" not in response_data:
                # Handle error response - create a minimal valid response
                error_response = HybridSearchResponse(
                    properties=[],
                    total_results=0,
                    returned_results=0,
                    execution_time_ms=int(execution_time),
                    query=request.query,
                    location_extracted=None
                )
                # Log the error but return a valid response structure
                self.console.print(f"[yellow]⚠️ Server returned error: {response_data.get('error')}[/yellow]")
                return error_response
            
            # Transform PropertySearchResponse to HybridSearchResponse format
            # The new format has 'results' instead of 'properties' and 'total_hits' instead of 'total_results'
            if "results" in response_data and "properties" not in response_data:
                # Transform PropertyResult to HybridProperty format
                from .models.hybrid_search import HybridProperty, HybridPropertyAddress
                
                properties = []
                for result in response_data.get("results", []):
                    # Create HybridPropertyAddress from PropertyAddress
                    address = HybridPropertyAddress(
                        street=result["address"]["street"],
                        city=result["address"]["city"],
                        state=result["address"]["state"],
                        zip_code=result["address"]["zip_code"]
                    )
                    
                    # Create HybridProperty from PropertyResult
                    property_obj = HybridProperty(
                        listing_id=result["listing_id"],
                        property_type=result["property_type"],
                        price=result["price"],
                        bedrooms=result["bedrooms"],
                        bathrooms=result["bathrooms"],
                        square_feet=result.get("square_feet"),
                        address=address,
                        description=result["description"],
                        features=result.get("features", []),
                        score=result["score"]
                    )
                    properties.append(property_obj)
                
                # Create HybridSearchResponse with transformed data
                response = HybridSearchResponse(
                    properties=properties,
                    total_results=response_data.get("total_hits", 0),
                    returned_results=len(properties),
                    execution_time_ms=response_data.get("execution_time_ms", int(execution_time)),
                    query=request.query,
                    location_extracted=None  # The new API doesn't provide location extraction
                )
            else:
                # Try to parse as-is (for backward compatibility)
                response = HybridSearchResponse(**response_data)
            
            # Collect performance metrics
            server_time = response.execution_time_ms
            metrics = PerformanceMetrics(
                query_length=len(request.query),
                execution_time_ms=execution_time,
                server_time_ms=server_time,
                total_hits=response.total_results,
                returned_hits=response.returned_results,
                network_overhead_ms=max(0, execution_time - server_time)
            )
            self.performance_metrics.append(metrics)
            
            return response
            
        except ValidationError as e:
            self.console.print(f"[red]❌ Response validation failed: {e}[/red]")
            raise
        except Exception as e:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            self.console.print(f"[red]❌ MCP call failed ({execution_time:.1f}ms): {e}[/red]")
            raise
    
    def display_demo_header(self, subtitle: str = "") -> None:
        """Display a formatted demo header."""
        title = f"🏠 DEMO {self.demo_number}: {self.demo_name}"
        content = title
        if subtitle:
            content += f"\n[dim]{subtitle}[/dim]"
            
        self.console.print(Panel.fit(
            f"[bold cyan]{content}[/bold cyan]",
            border_style="cyan"
        ))
    
    def display_performance_summary(self) -> None:
        """Display performance metrics summary."""
        if not self.performance_metrics:
            return
            
        avg_time = sum(m.execution_time_ms for m in self.performance_metrics) / len(self.performance_metrics)
        avg_server_time = sum(m.server_time_ms for m in self.performance_metrics) / len(self.performance_metrics)
        avg_network = sum(m.network_overhead_ms for m in self.performance_metrics) / len(self.performance_metrics)
        avg_efficiency = sum(m.efficiency_ratio for m in self.performance_metrics) / len(self.performance_metrics)
        
        self.console.print(Panel.fit(
            f"[bold yellow]📈 Performance Summary[/bold yellow]\n\n"
            f"[dim]Average Total Time:[/dim] {avg_time:.1f}ms\n"
            f"[dim]Average Server Time:[/dim] {avg_server_time:.1f}ms\n"
            f"[dim]Average Network Overhead:[/dim] {avg_network:.1f}ms\n"
            f"[dim]Server Efficiency Ratio:[/dim] {avg_efficiency:.2f}\n"
            f"[dim]Queries Executed:[/dim] {len(self.performance_metrics)}",
            border_style="yellow",
            title="Performance Metrics"
        ))
    
    def display_completion_summary(self, success: bool, queries_executed: int, 
                                 queries_successful: int, error_message: Optional[str] = None) -> None:
        """Display demo completion summary."""
        success_rate = (queries_successful / queries_executed * 100) if queries_executed > 0 else 0
        
        status = "✅ Complete" if success else "❌ Failed"
        border_color = "green" if success else "red"
        
        summary_content = f"[bold {border_color}]{status}: {self.demo_name}[/bold {border_color}]\n\n"
        summary_content += f"[dim]Queries Executed:[/dim] {queries_executed}\n"
        summary_content += f"[dim]Queries Successful:[/dim] {queries_successful}\n"
        summary_content += f"[dim]Success Rate:[/dim] {success_rate:.1f}%"
        
        if error_message:
            summary_content += f"\n[dim]Error:[/dim] {error_message}"
            
        self.console.print(Panel.fit(
            summary_content,
            border_style=border_color,
            title="Demo Summary"
        ))
    
    @abstractmethod
    async def run_demo_queries(self) -> DemoExecutionResult:
        """
        Run the specific demo queries.
        
        Returns:
            DemoExecutionResult with execution details and metrics
        """
        pass
    
    async def execute(self) -> DemoExecutionResult:
        """
        Execute the complete demo with error handling and metrics collection.
        
        Returns:
            DemoExecutionResult with execution details
        """
        start_time = time.time()
        
        try:
            # Run the demo-specific queries
            result = await self.run_demo_queries()
            
            # Display performance summary
            self.display_performance_summary()
            
            # Display completion summary
            self.display_completion_summary(
                success=result.success,
                queries_executed=result.queries_executed,
                queries_successful=result.queries_successful,
                error_message=result.error_message
            )
            
            return result
            
        except Exception as e:
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000
            
            error_result = DemoExecutionResult(
                demo_name=self.demo_name,
                demo_number=self.demo_number,
                success=False,
                queries_executed=len(self.performance_metrics),
                queries_successful=0,
                total_execution_time_ms=execution_time,
                error_message=str(e)
            )
            
            self.display_completion_summary(
                success=False,
                queries_executed=len(self.performance_metrics),
                queries_successful=0,
                error_message=str(e)
            )
            
            return error_result


class ProgressTrackingMixin:
    """Mixin for demos that need progress tracking."""
    
    def create_progress_tracker(self, total_queries: int) -> Progress:
        """Create a progress tracker for query execution."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console
        )