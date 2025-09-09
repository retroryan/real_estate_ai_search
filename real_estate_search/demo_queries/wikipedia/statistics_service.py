"""
Statistics service module for Wikipedia search results.

This module handles calculation and aggregation of search metrics,
including performance statistics and result analysis.
"""

from typing import List, Dict, Set
from .models import (
    SearchResult,
    SearchStatistics,
    TopDocument
)


class WikipediaStatisticsService:
    """Service for calculating statistics from Wikipedia search results."""
    
    def calculate_statistics(
        self,
        search_results: List[SearchResult]
    ) -> SearchStatistics:
        """Calculate comprehensive statistics from search results.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            SearchStatistics with calculated metrics
        """
        total_queries = len(search_results)
        successful_queries = sum(1 for r in search_results if r.success and r.total_hits > 0)
        total_documents_found = sum(r.total_hits for r in search_results)
        
        # Calculate average results per query
        average_results = 0.0
        if total_queries > 0:
            average_results = round(total_documents_found / total_queries, 1)
        
        # Find top scoring documents
        top_documents = self._find_top_documents(search_results)
        
        return SearchStatistics(
            total_queries=total_queries,
            successful_queries=successful_queries,
            total_documents_found=total_documents_found,
            average_results_per_query=average_results,
            top_documents=top_documents
        )
    
    def _find_top_documents(
        self,
        search_results: List[SearchResult],
        max_documents: int = 5
    ) -> List[TopDocument]:
        """Find the top scoring unique documents across all results.
        
        Args:
            search_results: List of SearchResult objects
            max_documents: Maximum number of top documents to return
            
        Returns:
            List of TopDocument objects
        """
        # Collect all documents with scores
        all_docs = []
        
        for result in search_results:
            if not result.success:
                continue
                
            for hit in result.hits:
                doc = hit.document
                if doc.page_id and doc.title:
                    all_docs.append({
                        "title": doc.title,
                        "page_id": str(doc.page_id),
                        "score": hit.score,
                        "query_title": result.query.title
                    })
        
        # Sort by score and deduplicate by title
        sorted_docs = sorted(all_docs, key=lambda x: x['score'], reverse=True)
        
        seen_titles: Set[str] = set()
        top_documents = []
        
        for doc in sorted_docs:
            if doc['title'] not in seen_titles:
                seen_titles.add(doc['title'])
                top_documents.append(TopDocument(
                    title=doc['title'],
                    page_id=doc['page_id'],
                    score=doc['score'],
                    query_title=doc['query_title']
                ))
                
                if len(top_documents) >= max_documents:
                    break
        
        return top_documents
    
    def calculate_query_performance(
        self,
        search_results: List[SearchResult]
    ) -> Dict[str, float]:
        """Calculate performance metrics for queries.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Dictionary with performance metrics
        """
        execution_times = [
            r.execution_time_ms 
            for r in search_results 
            if r.execution_time_ms is not None
        ]
        
        if not execution_times:
            return {
                "avg_execution_time_ms": 0.0,
                "min_execution_time_ms": 0.0,
                "max_execution_time_ms": 0.0
            }
        
        return {
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "min_execution_time_ms": min(execution_times),
            "max_execution_time_ms": max(execution_times)
        }
    
    def calculate_hit_distribution(
        self,
        search_results: List[SearchResult]
    ) -> Dict[str, int]:
        """Calculate distribution of hits across queries.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Dictionary with hit distribution metrics
        """
        hit_counts = [r.total_hits for r in search_results if r.success]
        
        if not hit_counts:
            return {
                "queries_with_no_results": len(search_results),
                "queries_with_1_10_results": 0,
                "queries_with_11_100_results": 0,
                "queries_with_100_plus_results": 0
            }
        
        return {
            "queries_with_no_results": sum(1 for c in hit_counts if c == 0),
            "queries_with_1_10_results": sum(1 for c in hit_counts if 1 <= c <= 10),
            "queries_with_11_100_results": sum(1 for c in hit_counts if 11 <= c <= 100),
            "queries_with_100_plus_results": sum(1 for c in hit_counts if c > 100)
        }
    
    def calculate_category_distribution(
        self,
        search_results: List[SearchResult]
    ) -> Dict[str, int]:
        """Calculate distribution of categories in results.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            Dictionary with category counts
        """
        category_counts: Dict[str, int] = {}
        
        for result in search_results:
            if not result.success:
                continue
                
            for hit in result.hits:
                for category in hit.document.categories:
                    category_counts[category] = category_counts.get(category, 0) + 1
        
        # Sort by count and return top categories
        sorted_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return dict(sorted_categories[:10])
    
    def get_summary_text(self, stats: SearchStatistics) -> str:
        """Generate a text summary of the statistics.
        
        Args:
            stats: SearchStatistics object
            
        Returns:
            Formatted summary text
        """
        lines = [
            f"Search Execution Summary:",
            f"  • Queries executed: {stats.total_queries}",
            f"  • Successful queries: {stats.successful_queries}",
            f"  • Total documents found: {stats.total_documents_found}",
            f"  • Average results per query: {stats.average_results_per_query}"
        ]
        
        if stats.top_documents:
            lines.append("\nTop Scoring Documents:")
            for idx, doc in enumerate(stats.top_documents[:3], 1):
                lines.append(f"  {idx}. {doc.title} (Score: {doc.score:.2f})")
        
        return '\n'.join(lines)