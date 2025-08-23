"""
Statistics API endpoints.

Provides comprehensive statistics and metrics about ingested data including
property distributions, geographic coverage, and data quality metrics.
"""

import statistics
from collections import Counter, defaultdict
from typing import Dict, List, Any
from pathlib import Path
from decimal import Decimal

from fastapi import APIRouter, HTTPException, Request

from ...utils.logger import setup_logger
from ..dependencies import PropertyLoaderDep, NeighborhoodLoaderDep, WikipediaLoaderDep
from ..schemas.stats import (
    StatsSummaryResponse,
    PropertyStatsResponse, 
    NeighborhoodStatsResponse,
    WikipediaStatsResponse,
    CoverageStatsResponse,
    EnrichmentStatsResponse,
    DataSummaryStats,
    PropertyStats,
    NeighborhoodStats,
    WikipediaStats,
    CoverageStats,
    EnrichmentStats
)

logger = setup_logger(__name__)
router = APIRouter()


def _safe_statistics_mean(values: List[float]) -> float:
    """Safely calculate mean, return 0.0 if no values."""
    return statistics.mean(values) if values else 0.0


def _safe_statistics_median(values: List[float]) -> float:
    """Safely calculate median, return 0.0 if no values."""
    return statistics.median(values) if values else 0.0


def _calculate_price_stats(prices: List[Decimal]) -> Dict[str, Decimal]:
    """Calculate comprehensive price statistics."""
    if not prices:
        return {"min": Decimal("0"), "max": Decimal("0"), "avg": Decimal("0"), "median": Decimal("0")}
    
    price_floats = [float(p) for p in prices]
    return {
        "min": min(prices),
        "max": max(prices), 
        "avg": Decimal(str(round(_safe_statistics_mean(price_floats), 2))),
        "median": Decimal(str(round(_safe_statistics_median(price_floats), 2)))
    }


def _calculate_numeric_stats(values: List[float]) -> Dict[str, float]:
    """Calculate basic numeric statistics."""
    if not values:
        return {"min": 0.0, "max": 0.0, "avg": 0.0}
    
    return {
        "min": min(values),
        "max": max(values),
        "avg": round(_safe_statistics_mean(values), 2)
    }


def _calculate_score_distribution(scores: List[float], ranges: List[tuple]) -> Dict[str, int]:
    """Calculate distribution of scores across ranges."""
    distribution = {}
    for range_start, range_end, label in ranges:
        count = sum(1 for score in scores if range_start <= score < range_end)
        distribution[label] = count
    return distribution


def _calculate_completeness(data_list: List[Any], fields: List[str]) -> Dict[str, float]:
    """Calculate data completeness percentages for specified fields."""
    if not data_list:
        return {field: 0.0 for field in fields}
    
    total_count = len(data_list)
    completeness = {}
    
    for field in fields:
        complete_count = 0
        for item in data_list:
            value = getattr(item, field, None)
            if value is not None:
                # Handle different field types
                if isinstance(value, str) and value.strip():
                    complete_count += 1
                elif isinstance(value, (int, float)) and value > 0:
                    complete_count += 1
                elif isinstance(value, list) and len(value) > 0:
                    complete_count += 1
                elif hasattr(value, '__dict__'):  # Complex objects like Address
                    complete_count += 1
        
        completeness[field] = round((complete_count / total_count) * 100, 1)
    
    return completeness


@router.get("/summary", response_model=StatsSummaryResponse)
async def get_data_summary(
    request: Request,
    property_loader: PropertyLoaderDep = None,
    neighborhood_loader: NeighborhoodLoaderDep = None,
    wikipedia_loader: WikipediaLoaderDep = None
):
    """
    Get overall data summary statistics.
    
    Provides high-level overview of all data sources including counts,
    geographic coverage, and key metrics across properties, neighborhoods,
    and Wikipedia content.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating data summary statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Load all data
        properties = property_loader.load_all()
        neighborhoods = neighborhood_loader.load_all()
        
        # Wikipedia data (handle potential unavailability)
        articles = []
        summaries = []
        if hasattr(wikipedia_loader, 'database_path') and Path(wikipedia_loader.database_path).exists():
            try:
                articles = wikipedia_loader.load_all()
                summaries = wikipedia_loader.load_summaries()
            except Exception as e:
                logger.warning(f"Could not load Wikipedia data: {e}", extra={"correlation_id": correlation_id})
        
        # Calculate geographic coverage
        all_cities = set()
        all_states = set()
        
        # Add cities/states from properties
        all_cities.update(prop.address.city for prop in properties)
        all_states.update(prop.address.state for prop in properties)
        
        # Add cities/states from neighborhoods
        all_cities.update(neighborhood.city for neighborhood in neighborhoods)
        all_states.update(neighborhood.state for neighborhood in neighborhoods)
        
        # Calculate price range
        prices = [prop.price for prop in properties]
        price_stats = _calculate_price_stats(prices)
        
        # Build summary statistics
        summary_stats = DataSummaryStats(
            total_properties=len(properties),
            total_neighborhoods=len(neighborhoods),
            total_wikipedia_articles=len(articles),
            total_wikipedia_summaries=len(summaries),
            unique_cities=len(all_cities),
            unique_states=len(all_states),
            price_range=price_stats
        )
        
        logger.info(
            f"Generated summary: {len(properties)} properties, {len(neighborhoods)} neighborhoods, "
            f"{len(articles)} articles across {len(all_cities)} cities",
            extra={"correlation_id": correlation_id}
        )
        
        return StatsSummaryResponse(
            data=summary_stats,
            metadata={
                "source": "common_ingest_loaders",
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate summary statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate summary statistics")


@router.get("/properties", response_model=PropertyStatsResponse)
async def get_property_statistics(
    request: Request,
    property_loader: PropertyLoaderDep = None
):
    """
    Get detailed property statistics and distributions.
    
    Provides comprehensive analysis of property data including type distributions,
    price statistics, geographic breakdown, and feature analysis.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating property statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Load property data
        properties = property_loader.load_all()
        
        if not properties:
            # Return empty statistics if no properties
            empty_stats = PropertyStats(
                total_count=0,
                by_type={},
                by_city={},
                by_state={},
                price_stats={"min": Decimal("0"), "max": Decimal("0"), "avg": Decimal("0"), "median": Decimal("0")},
                bedroom_stats={"min": 0.0, "max": 0.0, "avg": 0.0},
                features_analysis={},
                amenities_analysis={},
                data_completeness={}
            )
            
            return PropertyStatsResponse(
                data=empty_stats,
                metadata={"source": "common_ingest_loaders", "correlation_id": correlation_id}
            )
        
        # Calculate distributions
        type_counter = Counter(prop.property_type.value if hasattr(prop.property_type, 'value') else str(prop.property_type) for prop in properties)
        city_counter = Counter(prop.address.city for prop in properties)
        state_counter = Counter(prop.address.state for prop in properties)
        
        # Calculate price statistics
        prices = [prop.price for prop in properties]
        price_stats = _calculate_price_stats(prices)
        
        # Calculate bedroom statistics  
        bedrooms = [float(prop.bedrooms) for prop in properties if prop.bedrooms is not None]
        bedroom_stats = _calculate_numeric_stats(bedrooms)
        
        # Analyze features and amenities
        all_features = []
        all_amenities = []
        
        for prop in properties:
            if prop.features:
                all_features.extend(prop.features)
            if prop.amenities:
                all_amenities.extend(prop.amenities)
        
        # Get top 10 most common features and amenities
        feature_counter = Counter(all_features)
        amenity_counter = Counter(all_amenities)
        
        # Calculate data completeness
        completeness_fields = ['square_feet', 'year_built', 'lot_size', 'features', 'amenities']
        data_completeness = _calculate_completeness(properties, completeness_fields)
        
        # Build property statistics
        property_stats = PropertyStats(
            total_count=len(properties),
            by_type=dict(type_counter),
            by_city=dict(city_counter),
            by_state=dict(state_counter),
            price_stats=price_stats,
            bedroom_stats=bedroom_stats,
            features_analysis=dict(feature_counter.most_common(10)),
            amenities_analysis=dict(amenity_counter.most_common(10)),
            data_completeness=data_completeness
        )
        
        logger.info(
            f"Generated property stats: {len(properties)} properties across {len(city_counter)} cities",
            extra={"correlation_id": correlation_id}
        )
        
        return PropertyStatsResponse(
            data=property_stats,
            metadata={
                "source": "common_ingest_loaders",
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate property statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate property statistics")


@router.get("/neighborhoods", response_model=NeighborhoodStatsResponse)
async def get_neighborhood_statistics(
    request: Request,
    neighborhood_loader: NeighborhoodLoaderDep = None
):
    """
    Get detailed neighborhood statistics and distributions.
    
    Provides comprehensive analysis of neighborhood data including geographic
    distribution, POI statistics, and characteristic analysis.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating neighborhood statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Load neighborhood data
        neighborhoods = neighborhood_loader.load_all()
        
        if not neighborhoods:
            # Return empty statistics if no neighborhoods
            empty_stats = NeighborhoodStats(
                total_count=0,
                by_city={},
                by_state={},
                poi_stats={"min": 0.0, "max": 0.0, "avg": 0.0},
                characteristics_analysis={},
                data_completeness={}
            )
            
            return NeighborhoodStatsResponse(
                data=empty_stats,
                metadata={"source": "common_ingest_loaders", "correlation_id": correlation_id}
            )
        
        # Calculate distributions
        city_counter = Counter(neighborhood.city for neighborhood in neighborhoods)
        state_counter = Counter(neighborhood.state for neighborhood in neighborhoods)
        
        # Calculate POI statistics
        poi_counts = [float(neighborhood.poi_count) for neighborhood in neighborhoods if neighborhood.poi_count is not None]
        poi_stats = _calculate_numeric_stats(poi_counts)
        
        # Analyze characteristics
        all_characteristics = []
        for neighborhood in neighborhoods:
            if neighborhood.characteristics:
                all_characteristics.extend(neighborhood.characteristics)
        
        characteristic_counter = Counter(all_characteristics)
        
        # Calculate data completeness
        completeness_fields = ['boundaries', 'center_point', 'demographics', 'characteristics']
        data_completeness = _calculate_completeness(neighborhoods, completeness_fields)
        
        # Build neighborhood statistics
        neighborhood_stats = NeighborhoodStats(
            total_count=len(neighborhoods),
            by_city=dict(city_counter),
            by_state=dict(state_counter),
            poi_stats=poi_stats,
            characteristics_analysis=dict(characteristic_counter.most_common(10)),
            data_completeness=data_completeness
        )
        
        logger.info(
            f"Generated neighborhood stats: {len(neighborhoods)} neighborhoods across {len(city_counter)} cities",
            extra={"correlation_id": correlation_id}
        )
        
        return NeighborhoodStatsResponse(
            data=neighborhood_stats,
            metadata={
                "source": "common_ingest_loaders", 
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate neighborhood statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate neighborhood statistics")


@router.get("/wikipedia", response_model=WikipediaStatsResponse)
async def get_wikipedia_statistics(
    request: Request,
    wikipedia_loader: WikipediaLoaderDep = None
):
    """
    Get detailed Wikipedia data statistics and quality metrics.
    
    Provides analysis of Wikipedia articles and summaries including confidence
    distributions, relevance scores, and geographic coverage.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating Wikipedia statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Check if Wikipedia database exists
        if not hasattr(wikipedia_loader, 'database_path') or not Path(wikipedia_loader.database_path).exists():
            # Return empty statistics if no Wikipedia database
            empty_stats = WikipediaStats(
                total_articles=0,
                total_summaries=0,
                relevance_distribution={},
                confidence_distribution={},
                geographic_coverage={},
                quality_metrics={"avg_relevance": 0.0, "avg_confidence": 0.0}
            )
            
            return WikipediaStatsResponse(
                data=empty_stats,
                metadata={
                    "source": "wikipedia_database_unavailable",
                    "correlation_id": correlation_id
                }
            )
        
        # Load Wikipedia data
        articles = wikipedia_loader.load_all()
        summaries = wikipedia_loader.load_summaries()
        
        # Calculate relevance score distribution for articles
        relevance_scores = [article.relevance_score for article in articles if article.relevance_score is not None]
        relevance_ranges = [
            (0.0, 0.3, "Low (0.0-0.3)"),
            (0.3, 0.6, "Medium (0.3-0.6)"),
            (0.6, 0.8, "High (0.6-0.8)"),
            (0.8, 1.0, "Very High (0.8-1.0)")
        ]
        relevance_distribution = _calculate_score_distribution(relevance_scores, relevance_ranges)
        
        # Calculate confidence score distribution for summaries  
        confidence_scores = [summary.overall_confidence for summary in summaries if summary.overall_confidence is not None]
        confidence_ranges = [
            (0.0, 0.5, "Low (0.0-0.5)"),
            (0.5, 0.7, "Medium (0.5-0.7)"),
            (0.7, 0.85, "High (0.7-0.85)"),
            (0.85, 1.0, "Very High (0.85-1.0)")
        ]
        confidence_distribution = _calculate_score_distribution(confidence_scores, confidence_ranges)
        
        # Calculate geographic coverage
        geographic_coverage = defaultdict(lambda: defaultdict(int))
        
        # Add coverage from summaries with location data
        for summary in summaries:
            if summary.best_state:
                state = summary.best_state
                if summary.best_city:
                    geographic_coverage[state][summary.best_city] += 1
                else:
                    geographic_coverage[state]["_state_only"] += 1
        
        # Convert to regular dict for JSON serialization
        geographic_coverage = {state: dict(cities) for state, cities in geographic_coverage.items()}
        
        # Calculate quality metrics
        avg_relevance = _safe_statistics_mean(relevance_scores)
        avg_confidence = _safe_statistics_mean(confidence_scores)
        
        # Build Wikipedia statistics
        wikipedia_stats = WikipediaStats(
            total_articles=len(articles),
            total_summaries=len(summaries),
            relevance_distribution=relevance_distribution,
            confidence_distribution=confidence_distribution,
            geographic_coverage=geographic_coverage,
            quality_metrics={
                "avg_relevance": round(avg_relevance, 3),
                "avg_confidence": round(avg_confidence, 3)
            }
        )
        
        logger.info(
            f"Generated Wikipedia stats: {len(articles)} articles, {len(summaries)} summaries",
            extra={"correlation_id": correlation_id}
        )
        
        return WikipediaStatsResponse(
            data=wikipedia_stats,
            metadata={
                "source": "wikipedia_database",
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate Wikipedia statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate Wikipedia statistics")


@router.get("/coverage", response_model=CoverageStatsResponse)
async def get_coverage_statistics(
    request: Request,
    property_loader: PropertyLoaderDep = None,
    neighborhood_loader: NeighborhoodLoaderDep = None,
    wikipedia_loader: WikipediaLoaderDep = None
):
    """
    Get geographic coverage and data distribution metrics.
    
    Shows how data is distributed across different locations and identifies
    the most data-rich cities and states.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating coverage statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Load all data
        properties = property_loader.load_all()
        neighborhoods = neighborhood_loader.load_all()
        
        # Wikipedia data (handle potential unavailability)
        summaries = []
        if hasattr(wikipedia_loader, 'database_path') and Path(wikipedia_loader.database_path).exists():
            try:
                summaries = wikipedia_loader.load_summaries()
            except Exception as e:
                logger.warning(f"Could not load Wikipedia summaries: {e}", extra={"correlation_id": correlation_id})
        
        # Calculate coverage by city
        city_coverage = defaultdict(lambda: {"properties": 0, "neighborhoods": 0, "wikipedia": 0})
        
        for prop in properties:
            city_coverage[prop.address.city]["properties"] += 1
            
        for neighborhood in neighborhoods:
            city_coverage[neighborhood.city]["neighborhoods"] += 1
            
        for summary in summaries:
            if summary.best_city:
                city_coverage[summary.best_city]["wikipedia"] += 1
        
        # Calculate coverage by state
        state_coverage = defaultdict(lambda: {"properties": 0, "neighborhoods": 0, "wikipedia": 0})
        
        for prop in properties:
            state_coverage[prop.address.state]["properties"] += 1
            
        for neighborhood in neighborhoods:
            state_coverage[neighborhood.state]["neighborhoods"] += 1
            
        for summary in summaries:
            if summary.best_state:
                state_coverage[summary.best_state]["wikipedia"] += 1
        
        # Calculate top cities by total data points
        city_totals = []
        for city, counts in city_coverage.items():
            total = counts["properties"] + counts["neighborhoods"] + counts["wikipedia"]
            city_totals.append({
                "city": city,
                "total_data_points": total,
                "properties": counts["properties"],
                "neighborhoods": counts["neighborhoods"],
                "wikipedia": counts["wikipedia"]
            })
        
        # Sort by total data points and take top 10
        top_cities = sorted(city_totals, key=lambda x: x["total_data_points"], reverse=True)[:10]
        
        # Calculate coverage summary
        coverage_summary = {
            "total_cities": len(city_coverage),
            "total_states": len(state_coverage),
            "cities_with_properties": sum(1 for counts in city_coverage.values() if counts["properties"] > 0),
            "cities_with_neighborhoods": sum(1 for counts in city_coverage.values() if counts["neighborhoods"] > 0),
            "cities_with_wikipedia": sum(1 for counts in city_coverage.values() if counts["wikipedia"] > 0)
        }
        
        # Build coverage statistics
        coverage_stats = CoverageStats(
            by_city={city: dict(counts) for city, counts in city_coverage.items()},
            by_state={state: dict(counts) for state, counts in state_coverage.items()},
            coverage_summary=coverage_summary,
            top_cities_by_data=top_cities
        )
        
        logger.info(
            f"Generated coverage stats: {len(city_coverage)} cities, {len(state_coverage)} states",
            extra={"correlation_id": correlation_id}
        )
        
        return CoverageStatsResponse(
            data=coverage_stats,
            metadata={
                "source": "common_ingest_loaders",
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate coverage statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate coverage statistics")


@router.get("/enrichment", response_model=EnrichmentStatsResponse)
async def get_enrichment_statistics(
    request: Request,
    property_loader: PropertyLoaderDep = None,
    neighborhood_loader: NeighborhoodLoaderDep = None,
    wikipedia_loader: WikipediaLoaderDep = None
):
    """
    Get data enrichment success rates and quality metrics.
    
    Shows how effectively data enrichment processes are working including
    address expansion, feature normalization, and coordinate availability.
    """
    correlation_id = getattr(request.state, 'correlation_id', 'unknown')
    
    logger.info("Generating enrichment statistics", extra={"correlation_id": correlation_id})
    
    try:
        # Load all data
        properties = property_loader.load_all()
        neighborhoods = neighborhood_loader.load_all()
        
        # Wikipedia data (handle potential unavailability) 
        summaries = []
        if hasattr(wikipedia_loader, 'database_path') and Path(wikipedia_loader.database_path).exists():
            try:
                summaries = wikipedia_loader.load_summaries()
            except Exception as e:
                logger.warning(f"Could not load Wikipedia summaries: {e}", extra={"correlation_id": correlation_id})
        
        # Calculate address enrichment success rates
        total_properties = len(properties)
        total_neighborhoods = len(neighborhoods)
        
        # Check for expanded city names (length > 2 indicates expansion)
        expanded_property_cities = sum(1 for prop in properties if len(prop.address.city) > 2)
        expanded_neighborhood_cities = sum(1 for neighborhood in neighborhoods if len(neighborhood.city) > 2)
        
        # Check for expanded state names (length > 2 indicates expansion)
        expanded_property_states = sum(1 for prop in properties if len(prop.address.state) > 2)
        expanded_neighborhood_states = sum(1 for neighborhood in neighborhoods if len(neighborhood.state) > 2)
        
        address_enrichment = {
            "property_city_expansion": round((expanded_property_cities / total_properties * 100) if total_properties > 0 else 0, 1),
            "property_state_expansion": round((expanded_property_states / total_properties * 100) if total_properties > 0 else 0, 1),
            "neighborhood_city_expansion": round((expanded_neighborhood_cities / total_neighborhoods * 100) if total_neighborhoods > 0 else 0, 1),
            "neighborhood_state_expansion": round((expanded_neighborhood_states / total_neighborhoods * 100) if total_neighborhoods > 0 else 0, 1)
        }
        
        # Calculate feature normalization success (assuming normalization means lists exist and are not empty)
        properties_with_features = sum(1 for prop in properties if prop.features and len(prop.features) > 0)
        properties_with_amenities = sum(1 for prop in properties if prop.amenities and len(prop.amenities) > 0)
        neighborhoods_with_characteristics = sum(1 for neighborhood in neighborhoods if neighborhood.characteristics and len(neighborhood.characteristics) > 0)
        
        feature_normalization = {
            "property_features_populated": round((properties_with_features / total_properties * 100) if total_properties > 0 else 0, 1),
            "property_amenities_populated": round((properties_with_amenities / total_properties * 100) if total_properties > 0 else 0, 1),
            "neighborhood_characteristics_populated": round((neighborhoods_with_characteristics / total_neighborhoods * 100) if total_neighborhoods > 0 else 0, 1)
        }
        
        # Calculate coordinate availability
        properties_with_coords = sum(1 for prop in properties if prop.address.coordinates is not None)
        neighborhoods_with_center = sum(1 for neighborhood in neighborhoods if neighborhood.center_point is not None)
        neighborhoods_with_boundaries = sum(1 for neighborhood in neighborhoods if neighborhood.boundaries is not None)
        
        coordinate_availability = {
            "properties_with_coordinates": round((properties_with_coords / total_properties * 100) if total_properties > 0 else 0, 1),
            "neighborhoods_with_center_point": round((neighborhoods_with_center / total_neighborhoods * 100) if total_neighborhoods > 0 else 0, 1),
            "neighborhoods_with_boundaries": round((neighborhoods_with_boundaries / total_neighborhoods * 100) if total_neighborhoods > 0 else 0, 1)
        }
        
        # Calculate overall enrichment success summary
        enrichment_success_summary = {
            "overall_address_success": round(sum(address_enrichment.values()) / len(address_enrichment), 1),
            "overall_feature_success": round(sum(feature_normalization.values()) / len(feature_normalization), 1),
            "overall_coordinate_success": round(sum(coordinate_availability.values()) / len(coordinate_availability), 1)
        }
        
        # Build enrichment statistics
        enrichment_stats = EnrichmentStats(
            address_enrichment=address_enrichment,
            feature_normalization=feature_normalization,
            coordinate_availability=coordinate_availability,
            enrichment_success_summary=enrichment_success_summary
        )
        
        logger.info(
            f"Generated enrichment stats: {total_properties} properties, {total_neighborhoods} neighborhoods analyzed",
            extra={"correlation_id": correlation_id}
        )
        
        return EnrichmentStatsResponse(
            data=enrichment_stats,
            metadata={
                "source": "common_ingest_loaders",
                "correlation_id": correlation_id
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to generate enrichment statistics: {str(e)}", extra={"correlation_id": correlation_id})
        raise HTTPException(status_code=500, detail="Failed to generate enrichment statistics")