"""Type-safe demo registry using Pydantic models"""

from typing import Callable, Dict, Optional, Protocol
from pathlib import Path
from pydantic import BaseModel, Field
from enum import Enum


class DemoType(str, Enum):
    """Enum for demo types"""
    SIMPLE = "simple"  # Uses SimpleDemoRunner
    MODULE = "module"  # Uses dynamic module loading


class DemoEntryPoint(str, Enum):
    """Enum for demo entry point functions"""
    MAIN = "main"
    RUN = "run"
    RUN_DEMO = "run_demo"
    RUN_COMPLETE_MARKET_INTELLIGENCE_DEMO = "run_complete_market_intelligence_demo"
    RUN_WIKIPEDIA_DEMO = "run_wikipedia_demo"
    RUN_VECTOR_SEARCH_DEMO = "run_vector_search_demo"
    RUN_PURE_VECTOR_SEARCH_DEMO = "run_pure_vector_search_demo"
    RUN_WIKIPEDIA_ENHANCED_DEMO = "run_wikipedia_enhanced_demo"


class DemoProtocol(Protocol):
    """Protocol defining the expected demo module interface"""
    def main(self) -> None: ...
    def run(self) -> None: ...
    def run_demo(self) -> None: ...
    def run_complete_market_intelligence_demo(self) -> None: ...


class DemoDefinition(BaseModel):
    """Type-safe definition of a demo"""
    
    demo_number: int = Field(..., ge=1, le=7, description="Demo number")
    title: str = Field(..., description="Demo title")
    description: str = Field(..., description="Demo description")
    demo_type: DemoType = Field(..., description="Type of demo execution")
    
    # For MODULE type demos
    file_name: Optional[str] = Field(None, description="Demo file name (for MODULE type)")
    entry_point: Optional[DemoEntryPoint] = Field(None, description="Entry point function name")
    
    class Config:
        """Pydantic configuration"""
        use_enum_values = True
        validate_assignment = True


class DemoRegistry(BaseModel):
    """Registry of all available demos"""
    
    demos: Dict[int, DemoDefinition] = Field(default_factory=dict, description="Demo definitions by number")
    
    def register(self, demo: DemoDefinition) -> None:
        """Register a demo in the registry"""
        self.demos[demo.demo_number] = demo
    
    def get(self, demo_number: int) -> Optional[DemoDefinition]:
        """Get a demo definition by number"""
        return self.demos.get(demo_number)
    
    def validate_demo_exists(self, demo_number: int) -> bool:
        """Check if a demo exists"""
        return demo_number in self.demos
    
    class Config:
        """Pydantic configuration"""
        validate_assignment = True


def create_demo_registry() -> DemoRegistry:
    """Create and populate the demo registry with all available demos"""
    registry = DemoRegistry()
    
    # Demo 1: Simple demo runner (no file needed)
    registry.register(DemoDefinition(
        demo_number=1,
        title="Basic Graph Queries",
        description="Running basic Neo4j graph queries without external dependencies",
        demo_type=DemoType.SIMPLE
    ))
    
    # Demo 2: Hybrid Search Simple
    registry.register(DemoDefinition(
        demo_number=2,
        title="Hybrid Search Simple",
        description="Simple hybrid search combining graph and vector embeddings",
        demo_type=DemoType.MODULE,
        file_name="demo_1_hybrid_search_simple.py",
        entry_point=DemoEntryPoint.MAIN
    ))
    
    # Demo 3: Hybrid Search Advanced
    registry.register(DemoDefinition(
        demo_number=3,
        title="Hybrid Search Advanced",
        description="Advanced hybrid search with complex graph relationships",
        demo_type=DemoType.MODULE,
        file_name="demo_1_hybrid_search.py",
        entry_point=DemoEntryPoint.MAIN
    ))
    
    # Demo 4: Graph Analysis
    registry.register(DemoDefinition(
        demo_number=4,
        title="Graph Analysis",
        description="Deep graph analysis and network insights",
        demo_type=DemoType.MODULE,
        file_name="demo_2_graph_analysis.py",
        entry_point=DemoEntryPoint.MAIN
    ))
    
    # Demo 5: Market Intelligence
    registry.register(DemoDefinition(
        demo_number=5,
        title="Market Intelligence",
        description="Advanced market intelligence using graph relationships and vector embeddings",
        demo_type=DemoType.MODULE,
        file_name="demo_3_market_intelligence.py",
        entry_point=DemoEntryPoint.RUN_COMPLETE_MARKET_INTELLIGENCE_DEMO
    ))
    
    # Demo 6: Wikipedia Enhanced
    registry.register(DemoDefinition(
        demo_number=6,
        title="Wikipedia Enhanced",
        description="Wikipedia-enhanced property search and analysis",
        demo_type=DemoType.MODULE,
        file_name="demo_4_wikipedia_enhanced.py",
        entry_point=DemoEntryPoint.RUN_WIKIPEDIA_ENHANCED_DEMO
    ))
    
    # Demo 7: Pure Vector Search
    registry.register(DemoDefinition(
        demo_number=7,
        title="Pure Vector Search",
        description="Pure vector similarity search without graph relationships",
        demo_type=DemoType.MODULE,
        file_name="demo_5_pure_vector_search.py",
        entry_point=DemoEntryPoint.RUN_PURE_VECTOR_SEARCH_DEMO
    ))
    
    return registry


# Create a singleton registry instance
DEMO_REGISTRY = create_demo_registry()