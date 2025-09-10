#!/usr/bin/env python3
"""
Demo Validation Script - Phase 2: Systematic Execution and Analysis
Executes all demos sequentially and captures results for analysis.
"""

import subprocess
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class DemoExecutionResult(BaseModel):
    """Result of executing a single demo."""
    demo_number: int
    demo_name: str
    success: bool
    total_hits: Optional[int] = None
    returned_hits: Optional[int] = None
    execution_time_ms: Optional[int] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = None  # data_missing, query_error, index_issue, api_error
    output_sample: Optional[str] = None
    
    
class DemoValidationReport(BaseModel):
    """Complete validation report for all demos."""
    execution_date: str
    elasticsearch_status: str
    total_demos: int
    successful_demos: int
    failed_demos: int
    zero_result_demos: List[int] = Field(default_factory=list)
    error_demos: List[int] = Field(default_factory=list)
    results: List[DemoExecutionResult] = Field(default_factory=list)
    failure_categories: Dict[str, List[int]] = Field(default_factory=dict)
    

class DemoValidator:
    """Validates all demos in the Real Estate AI Search system."""
    
    def __init__(self):
        self.demos = self._get_demo_registry()
        self.report = DemoValidationReport(
            execution_date=datetime.now().isoformat(),
            elasticsearch_status="unknown",
            total_demos=28,
            successful_demos=0,
            failed_demos=0
        )
        
    def _get_demo_registry(self) -> Dict[int, str]:
        """Get the registry of all demos."""
        return {
            1: "Basic Property Search",
            2: "Property Filter Search",
            3: "Geographic Distance Search",
            4: "Neighborhood Statistics",
            5: "Price Distribution Analysis",
            6: "Semantic Similarity Search",
            7: "Multi-Entity Combined Search",
            8: "Wikipedia Article Search",
            9: "Wikipedia Full-Text Search",
            10: "Property Relationships via Denormalized Index",
            11: "Natural Language Semantic Search",
            12: "Natural Language Examples",
            13: "Semantic vs Keyword Comparison",
            14: "Rich Real Estate Listing",
            15: "Hybrid Search with RRF",
            16: "Location Understanding",
            17: "Location-Aware: Waterfront Luxury",
            18: "Location-Aware: Family Schools",
            19: "Location-Aware: Urban Modern",
            20: "Location-Aware: Recreation Mountain",
            21: "Location-Aware: Historic Urban",
            22: "Location-Aware: Beach Proximity",
            23: "Location-Aware: Investment Market",
            24: "Location-Aware: Luxury Urban Views",
            25: "Location-Aware: Suburban Architecture",
            26: "Location-Aware: Neighborhood Character",
            27: "Location-Aware Search Showcase",
            28: "Wikipedia Location Search"
        }
    
    def check_elasticsearch(self) -> bool:
        """Check if Elasticsearch is running and healthy."""
        try:
            result = subprocess.run(
                ["./es-manager.sh", "health"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if "Elasticsearch is healthy" in result.stdout:
                self.report.elasticsearch_status = "healthy"
                return True
            else:
                self.report.elasticsearch_status = "unhealthy"
                return False
                
        except Exception as e:
            self.report.elasticsearch_status = f"error: {str(e)}"
            return False
    
    def execute_demo(self, demo_number: int) -> DemoExecutionResult:
        """Execute a single demo and capture results."""
        demo_name = self.demos.get(demo_number, "Unknown")
        
        print(f"\n[{demo_number}/28] Executing: {demo_name}")
        print("-" * 60)
        
        result = DemoExecutionResult(
            demo_number=demo_number,
            demo_name=demo_name,
            success=False
        )
        
        try:
            # Execute the demo
            cmd_result = subprocess.run(
                ["./es-manager.sh", "demo", str(demo_number)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = cmd_result.stdout
            error_output = cmd_result.stderr
            
            # Store sample output (first 500 chars)
            result.output_sample = output[:500] if output else None
            
            # Parse the output for key metrics
            if cmd_result.returncode == 0:
                result.success = self._parse_demo_output(output, result)
                
                # Check for zero results
                if result.total_hits == 0 or result.returned_hits == 0:
                    result.success = False
                    result.error_type = "zero_results"
                    result.error_message = "Demo returned zero results"
                    
            else:
                result.success = False
                result.error_message = error_output or "Demo execution failed"
                result.error_type = self._categorize_error(error_output or output)
                
        except subprocess.TimeoutExpired:
            result.success = False
            result.error_message = "Demo execution timeout (>30s)"
            result.error_type = "timeout"
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            result.error_type = "execution_error"
        
        # Print summary
        if result.success:
            print(f"✅ SUCCESS - Hits: {result.total_hits}, Returned: {result.returned_hits}")
        else:
            print(f"❌ FAILED - {result.error_type}: {result.error_message}")
            
        return result
    
    def _parse_demo_output(self, output: str, result: DemoExecutionResult) -> bool:
        """Parse demo output to extract metrics."""
        try:
            # Look for execution metrics
            exec_time_match = re.search(r'Execution Time:\s*(\d+)ms', output)
            if exec_time_match:
                result.execution_time_ms = int(exec_time_match.group(1))
            
            # Look for hit counts
            total_hits_match = re.search(r'Total Hits:\s*(\d+)', output)
            if total_hits_match:
                result.total_hits = int(total_hits_match.group(1))
            
            returned_hits_match = re.search(r'Returned:\s*(\d+)', output)
            if returned_hits_match:
                result.returned_hits = int(returned_hits_match.group(1))
            
            # Check for various success indicators
            success_indicators = [
                "Demo completed successfully",
                "✅",
                "TOP PROPERTIES",
                "TOP WIKIPEDIA ARTICLES",
                "AGGREGATION RESULTS",
                "SEARCH RESULTS"
            ]
            
            for indicator in success_indicators:
                if indicator in output:
                    return True
            
            # Check for error indicators
            error_indicators = [
                "Error executing demo",
                "❌",
                "No results found",
                "0 results"
            ]
            
            for indicator in error_indicators:
                if indicator in output:
                    return False
                    
            # Default to success if no clear indicators
            return True
            
        except Exception:
            return False
    
    def _categorize_error(self, error_text: str) -> str:
        """Categorize the type of error."""
        error_text_lower = error_text.lower()
        
        if "index" in error_text_lower and "not found" in error_text_lower:
            return "index_missing"
        elif "connection" in error_text_lower or "refused" in error_text_lower:
            return "connection_error"
        elif "api" in error_text_lower or "key" in error_text_lower:
            return "api_error"
        elif "field" in error_text_lower or "mapping" in error_text_lower:
            return "mapping_error"
        elif "query" in error_text_lower or "syntax" in error_text_lower:
            return "query_error"
        elif "no results" in error_text_lower or "0 results" in error_text_lower:
            return "zero_results"
        else:
            return "unknown_error"
    
    def run_validation(self):
        """Run the complete validation of all demos."""
        print("=" * 80)
        print("DEMO VALIDATION REPORT - Phase 2: Systematic Execution")
        print("=" * 80)
        
        # Check Elasticsearch first
        print("\n📊 Checking Elasticsearch health...")
        if not self.check_elasticsearch():
            print("❌ Elasticsearch is not healthy. Please ensure it's running.")
            return
        
        print("✅ Elasticsearch is healthy and ready.")
        
        # Execute all demos
        print(f"\n🚀 Executing {self.report.total_demos} demos sequentially...")
        
        for demo_num in range(1, 29):
            result = self.execute_demo(demo_num)
            self.report.results.append(result)
            
            if result.success:
                self.report.successful_demos += 1
            else:
                self.report.failed_demos += 1
                
                if result.error_type == "zero_results":
                    self.report.zero_result_demos.append(demo_num)
                else:
                    self.report.error_demos.append(demo_num)
                
                # Categorize failure
                error_type = result.error_type or "unknown"
                if error_type not in self.report.failure_categories:
                    self.report.failure_categories[error_type] = []
                self.report.failure_categories[error_type].append(demo_num)
        
        # Generate and save report
        self._generate_report()
    
    def _generate_report(self):
        """Generate the final validation report."""
        print("\n" + "=" * 80)
        print("VALIDATION SUMMARY")
        print("=" * 80)
        
        print(f"\n📊 Overall Results:")
        print(f"  Total Demos: {self.report.total_demos}")
        print(f"  ✅ Successful: {self.report.successful_demos}")
        print(f"  ❌ Failed: {self.report.failed_demos}")
        
        if self.report.zero_result_demos:
            print(f"\n⚠️ Demos with Zero Results: {self.report.zero_result_demos}")
        
        if self.report.error_demos:
            print(f"\n❌ Demos with Errors: {self.report.error_demos}")
        
        if self.report.failure_categories:
            print(f"\n📋 Failure Categories:")
            for category, demos in self.report.failure_categories.items():
                print(f"  {category}: {demos}")
        
        # Save detailed report
        report_path = Path("demo_validation_report.json")
        with open(report_path, "w") as f:
            json.dump(self.report.model_dump(), f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_path}")
        
        # Create markdown summary
        self._create_markdown_summary()
    
    def _create_markdown_summary(self):
        """Create a markdown summary of the validation results."""
        summary_path = Path("DEMO_VALIDATION_SUMMARY.md")
        
        with open(summary_path, "w") as f:
            f.write("# Demo Validation Summary - Phase 2\n\n")
            f.write(f"**Execution Date**: {self.report.execution_date}\n\n")
            f.write(f"**Elasticsearch Status**: {self.report.elasticsearch_status}\n\n")
            
            f.write("## Overall Results\n\n")
            f.write(f"- **Total Demos**: {self.report.total_demos}\n")
            f.write(f"- **Successful**: {self.report.successful_demos}\n")
            f.write(f"- **Failed**: {self.report.failed_demos}\n\n")
            
            f.write("## Demo Results\n\n")
            f.write("| Demo # | Name | Status | Hits | Error Type |\n")
            f.write("|--------|------|--------|------|------------|\n")
            
            for result in self.report.results:
                status = "✅" if result.success else "❌"
                hits = f"{result.total_hits}/{result.returned_hits}" if result.total_hits else "N/A"
                error = result.error_type or "-"
                f.write(f"| {result.demo_number} | {result.demo_name} | {status} | {hits} | {error} |\n")
            
            if self.report.failure_categories:
                f.write("\n## Failure Analysis\n\n")
                for category, demos in self.report.failure_categories.items():
                    f.write(f"### {category}\n")
                    f.write(f"Demos: {demos}\n\n")
        
        print(f"📝 Markdown summary saved to: {summary_path}")


if __name__ == "__main__":
    validator = DemoValidator()
    validator.run_validation()