"""
Result processing for aggregation queries.

This module transforms raw Elasticsearch aggregation responses into
structured data suitable for display or further analysis.
"""

from typing import Dict, Any, List, Optional
import logging

from ..demo_config import demo_config
from .models import (
    NeighborhoodStats,
    PriceRangeStats,
    PropertyTypeStats,
    GlobalStats,
    PropertyTypeCount
)

logger = logging.getLogger(__name__)


class AggregationResultProcessor:
    """Processor for transforming aggregation results."""
    
    @staticmethod
    def process_neighborhood_aggregations(response: Dict[str, Any]) -> List[NeighborhoodStats]:
        """
        Process neighborhood aggregation results from Elasticsearch.
        
        Extracts and structures data from terms aggregation buckets
        including all metric sub-aggregations.
        
        Args:
            response: Raw Elasticsearch response with aggregations
            
        Returns:
            List of NeighborhoodStats objects
        """
        results = []
        
        try:
            if 'aggregations' in response and 'by_neighborhood' in response['aggregations']:
                for bucket in response['aggregations']['by_neighborhood']['buckets']:
                    property_types = [
                        PropertyTypeCount(
                            type=type_bucket['key'],
                            count=type_bucket['doc_count']
                        )
                        for type_bucket in bucket['property_types']['buckets']
                    ]
                    
                    neighborhood = NeighborhoodStats(
                        neighborhood_id=bucket['key'],
                        property_count=int(bucket['property_count']['value']) if bucket['property_count']['value'] is not None else 0,
                        avg_price=round(bucket['avg_price']['value'], 2) if bucket['avg_price']['value'] else 0,
                        min_price=bucket['min_price']['value'] if bucket['min_price']['value'] is not None else 0,
                        max_price=bucket['max_price']['value'] if bucket['max_price']['value'] is not None else 0,
                        avg_bedrooms=round(bucket['avg_bedrooms']['value'], 1) if bucket['avg_bedrooms']['value'] else 0,
                        avg_square_feet=round(bucket['avg_square_feet']['value'], 0) if bucket['avg_square_feet']['value'] else 0,
                        price_per_sqft=round(bucket['price_per_sqft']['value'], 2) if bucket['price_per_sqft']['value'] else 0,
                        property_types=property_types
                    )
                    results.append(neighborhood)
                    
            logger.info(f"Processed {len(results)} neighborhood aggregations")
            
        except Exception as e:
            logger.error(f"Error processing neighborhood aggregations: {e}")
            
        return results
    
    @staticmethod
    def process_price_distribution(
        response: Dict[str, Any], 
        interval: int = None
    ) -> List[PriceRangeStats]:
        """
        Process price distribution histogram results from Elasticsearch.
        
        Extracts and structures data from histogram aggregation buckets
        including property type breakdowns.
        
        Args:
            response: Raw Elasticsearch response with histogram aggregations
            interval: Bucket width used in histogram (uses config default if None)
            
        Returns:
            List of PriceRangeStats objects
        """
        if interval is None:
            interval = demo_config.aggregation_defaults.price_interval
            
        results = []
        
        try:
            if 'aggregations' in response and 'price_histogram' in response['aggregations']:
                for bucket in response['aggregations']['price_histogram']['buckets']:
                    range_start = bucket['key']
                    range_end = range_start + interval
                    
                    # Build property type breakdown
                    property_type_breakdown = {}
                    if 'by_property_type' in bucket and 'buckets' in bucket['by_property_type']:
                        for type_bucket in bucket['by_property_type']['buckets']:
                            property_type_breakdown[type_bucket['key']] = type_bucket['doc_count']
                    
                    price_range = PriceRangeStats(
                        price_range=f"${range_start:,.0f} - ${range_end:,.0f}",
                        range_start=range_start,
                        range_end=range_end,
                        count=bucket['doc_count'],
                        property_types=property_type_breakdown,
                        avg_price=bucket['stats']['avg'] if 'stats' in bucket and bucket['stats']['avg'] else None
                    )
                    results.append(price_range)
                    
            logger.info(f"Processed {len(results)} price distribution buckets")
            
        except Exception as e:
            logger.error(f"Error processing price distribution: {e}")
            
        return results
    
    @staticmethod
    def extract_percentiles(response: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract percentile values from aggregation response.
        
        Args:
            response: Raw Elasticsearch response with percentile aggregations
            
        Returns:
            Dictionary mapping percentile labels to values
        """
        percentiles = {}
        
        try:
            if 'aggregations' in response and 'price_percentiles' in response['aggregations']:
                percentile_values = response['aggregations']['price_percentiles']['values']
                for percentile, value in percentile_values.items():
                    percentiles[f"{percentile}th percentile"] = value
                    
        except Exception as e:
            logger.error(f"Error extracting percentiles: {e}")
            
        return percentiles
    
    @staticmethod
    def extract_property_type_stats(response: Dict[str, Any]) -> List[PropertyTypeStats]:
        """
        Extract property type statistics from aggregation response.
        
        Args:
            response: Raw Elasticsearch response with property type aggregations
            
        Returns:
            List of PropertyTypeStats objects
        """
        type_stats = []
        
        try:
            if 'aggregations' in response and 'by_property_type_stats' in response['aggregations']:
                for type_bucket in response['aggregations']['by_property_type_stats']['buckets']:
                    stats = type_bucket.get('price_stats', {})
                    percentiles = type_bucket.get('price_percentiles', {}).get('values', {})
                    
                    type_stat = PropertyTypeStats(
                        property_type=type_bucket['key'],
                        count=type_bucket['doc_count'],
                        avg_price=stats.get('avg'),
                        min_price=stats.get('min'),
                        max_price=stats.get('max'),
                        median_price=percentiles.get('50.0')
                    )
                    type_stats.append(type_stat)
                    
        except Exception as e:
            logger.error(f"Error extracting property type stats: {e}")
            
        return type_stats
    
    @staticmethod
    def extract_global_stats(response: Dict[str, Any]) -> GlobalStats:
        """
        Extract global statistics from aggregation response.
        
        Args:
            response: Raw Elasticsearch response with global aggregations
            
        Returns:
            GlobalStats object
        """
        total_properties = 0
        overall_avg_price = 0.0
        
        try:
            if 'aggregations' in response:
                aggs = response['aggregations']
                
                if 'total_properties' in aggs:
                    total_properties = int(aggs['total_properties']['value'])
                    
                if 'overall_avg_price' in aggs:
                    overall_avg_price = float(aggs['overall_avg_price']['value'])
                    
        except Exception as e:
            logger.error(f"Error extracting global stats: {e}")
            
        return GlobalStats(
            total_properties=total_properties,
            overall_avg_price=overall_avg_price
        )