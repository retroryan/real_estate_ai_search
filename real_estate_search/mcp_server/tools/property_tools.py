"""
Property-related MCP tools.
"""

from typing import List, Optional, Dict, Any
from models import (
    Property, PropertySearchParams, SearchMode, SearchFilters,
    PropertyType, GeoSearchParams, GeoLocation, GeoDistanceUnit
)
from services import SearchEngine, PropertyIndexer
import structlog

logger = structlog.get_logger()


async def search_properties_tool(
    query: Optional[str] = None,
    location: Optional[str] = None,
    property_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_bedrooms: Optional[int] = None,
    max_bedrooms: Optional[int] = None,
    min_bathrooms: Optional[float] = None,
    max_bathrooms: Optional[float] = None,
    min_square_feet: Optional[int] = None,
    max_square_feet: Optional[int] = None,
    amenities: Optional[List[str]] = None,
    max_results: int = 20,
    search_mode: str = "semantic"
) -> Dict[str, Any]:
    """
    Search for properties matching specified criteria.
    
    Args:
        query: Natural language search query
        location: Location (city, state, or zip)
        property_type: Type of property (single_family, condo, townhouse, multi_family)
        min_price: Minimum price
        max_price: Maximum price
        min_bedrooms: Minimum number of bedrooms
        max_bedrooms: Maximum number of bedrooms
        min_bathrooms: Minimum number of bathrooms
        max_bathrooms: Maximum number of bathrooms
        min_square_feet: Minimum square footage
        max_square_feet: Maximum square footage
        amenities: List of required amenities
        max_results: Maximum number of results to return
        search_mode: Search mode (semantic, keyword, hybrid)
    
    Returns:
        Search results with matching properties
    """
    from main import resources
    
    if not resources.search_engine:
        return {"error": "Search engine not initialized"}
    
    try:
        # Build filters
        filters = None
        if any([property_type, min_price, max_price, min_bedrooms, max_bedrooms,
                min_bathrooms, max_bathrooms, min_square_feet, max_square_feet, amenities]):
            filters = SearchFilters(
                property_type=PropertyType(property_type) if property_type else None,
                min_price=min_price,
                max_price=max_price,
                min_bedrooms=min_bedrooms,
                max_bedrooms=max_bedrooms,
                min_bathrooms=min_bathrooms,
                max_bathrooms=max_bathrooms,
                min_square_feet=min_square_feet,
                max_square_feet=max_square_feet,
                amenities=amenities
            )
        
        # Create search params
        params = PropertySearchParams(
            query=query,
            location=location,
            filters=filters,
            max_results=max_results,
            search_mode=SearchMode(search_mode)
        )
        
        # Execute search
        results = await resources.search_engine.search(params)
        
        return {
            "success": True,
            "total": results.total,
            "returned": len(results.properties),
            "properties": [
                {
                    "id": hit.property.id,
                    "listing_id": hit.property.listing_id,
                    "property_type": hit.property.property_type.value,
                    "price": hit.property.price,
                    "bedrooms": hit.property.bedrooms,
                    "bathrooms": hit.property.bathrooms,
                    "square_feet": hit.property.square_feet,
                    "address": {
                        "street": hit.property.address.street,
                        "city": hit.property.address.city,
                        "state": hit.property.address.state,
                        "zip_code": hit.property.address.zip_code
                    },
                    "summary": hit.property.get_summary(),
                    "score": hit.score
                }
                for hit in results.hits
            ],
            "search_time_ms": results.search_time_ms
        }
        
    except Exception as e:
        logger.error("search_properties_failed", error=str(e))
        return {"error": f"Search failed: {str(e)}"}


async def get_property_details_tool(property_id: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific property.
    
    Args:
        property_id: The property ID to retrieve
    
    Returns:
        Detailed property information
    """
    from main import resources
    
    if not resources.search_engine:
        return {"error": "Search engine not initialized"}
    
    try:
        property = await resources.search_engine.get_property(property_id)
        
        if not property:
            return {"error": f"Property {property_id} not found"}
        
        return {
            "success": True,
            "property": {
                "id": property.id,
                "listing_id": property.listing_id,
                "property_type": property.property_type.value,
                "price": property.price,
                "bedrooms": property.bedrooms,
                "bathrooms": property.bathrooms,
                "square_feet": property.square_feet,
                "year_built": property.year_built,
                "lot_size": property.lot_size,
                "address": {
                    "street": property.address.street,
                    "city": property.address.city,
                    "state": property.address.state,
                    "zip_code": property.address.zip_code,
                    "location": {
                        "lat": property.address.location.lat,
                        "lon": property.address.location.lon
                    } if property.address.location else None
                },
                "description": property.description,
                "features": property.features,
                "amenities": property.amenities,
                "images": property.images,
                "virtual_tour_url": property.virtual_tour_url,
                "listing_date": property.listing_date.isoformat() if property.listing_date else None,
                "last_updated": property.last_updated.isoformat() if property.last_updated else None
            }
        }
        
    except Exception as e:
        logger.error("get_property_details_failed", property_id=property_id, error=str(e))
        return {"error": f"Failed to get property details: {str(e)}"}


async def analyze_property_tool(property_id: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a property including enrichment and market position.
    
    Args:
        property_id: The property ID to analyze
    
    Returns:
        Comprehensive property analysis
    """
    from main import resources
    
    if not resources.search_engine or not resources.enrichment_service or not resources.market_service:
        return {"error": "Required services not initialized"}
    
    try:
        # Get property
        property = await resources.search_engine.get_property(property_id)
        if not property:
            return {"error": f"Property {property_id} not found"}
        
        # Get enrichment
        enrichment = await resources.enrichment_service.enrich_property(property)
        
        # Get market analysis
        market_position = await resources.market_service.analyze_market_position(property)
        investment_metrics = await resources.market_service.calculate_investment_metrics(property)
        
        return {
            "success": True,
            "property_id": property_id,
            "basic_info": {
                "price": property.price,
                "price_per_sqft": property.price_per_sqft,
                "bedrooms": property.bedrooms,
                "bathrooms": property.bathrooms,
                "square_feet": property.square_feet
            },
            "enrichment": {
                "has_wikipedia": enrichment.wikipedia_context is not None,
                "neighborhood_description": enrichment.neighborhood_context.description if enrichment.neighborhood_context else None,
                "walkability_score": enrichment.neighborhood_context.walkability_score if enrichment.neighborhood_context else None,
                "nearby_poi_count": len(enrichment.nearby_pois),
                "top_nearby_pois": [
                    {
                        "name": poi.name,
                        "category": poi.category.value,
                        "distance_miles": poi.distance_miles
                    }
                    for poi in enrichment.nearby_pois[:5]
                ]
            },
            "market_analysis": {
                "price_percentile": market_position.price_percentile,
                "pricing_recommendation": market_position.pricing_recommendation,
                "competitive_properties": market_position.competitive_properties,
                "days_on_market_estimate": market_position.days_on_market_estimate,
                "market_strength": market_position.market_strength.value
            },
            "investment_metrics": {
                "estimated_rent": investment_metrics.estimated_rent,
                "gross_yield": round(investment_metrics.gross_yield, 2),
                "cap_rate": round(investment_metrics.cap_rate, 2),
                "cash_on_cash_return": round(investment_metrics.cash_on_cash_return, 2),
                "investment_score": investment_metrics.investment_score,
                "investment_grade": investment_metrics.investment_grade.value
            }
        }
        
    except Exception as e:
        logger.error("analyze_property_failed", property_id=property_id, error=str(e))
        return {"error": f"Failed to analyze property: {str(e)}"}


async def find_similar_properties_tool(
    property_id: str,
    max_results: int = 10,
    max_price_diff_percent: float = 20.0,
    max_distance_miles: float = 5.0
) -> Dict[str, Any]:
    """
    Find properties similar to a given property.
    
    Args:
        property_id: The reference property ID
        max_results: Maximum number of similar properties to return
        max_price_diff_percent: Maximum price difference percentage
        max_distance_miles: Maximum distance in miles
    
    Returns:
        List of similar properties
    """
    from main import resources
    
    if not resources.search_engine:
        return {"error": "Search engine not initialized"}
    
    try:
        # Get reference property
        property = await resources.search_engine.get_property(property_id)
        if not property:
            return {"error": f"Property {property_id} not found"}
        
        # Calculate price range
        price_diff = property.price * (max_price_diff_percent / 100)
        min_price = property.price - price_diff
        max_price = property.price + price_diff
        
        # Build search filters
        filters = SearchFilters(
            property_type=property.property_type,
            min_price=min_price,
            max_price=max_price,
            min_bedrooms=max(1, property.bedrooms - 1) if property.bedrooms else None,
            max_bedrooms=property.bedrooms + 1 if property.bedrooms else None,
            min_bathrooms=max(1, property.bathrooms - 0.5) if property.bathrooms else None,
            max_bathrooms=property.bathrooms + 0.5 if property.bathrooms else None,
            min_square_feet=int(property.square_feet * 0.8) if property.square_feet else None,
            max_square_feet=int(property.square_feet * 1.2) if property.square_feet else None
        )
        
        # If property has location, use geo search
        if property.address.location:
            geo_params = GeoSearchParams(
                center=property.address.location,
                radius=max_distance_miles,
                unit=GeoDistanceUnit.miles,
                filters=filters,
                max_results=max_results + 1  # +1 to account for self
            )
            results = await resources.search_engine.geo_search(geo_params)
        else:
            # Fallback to location-based search
            params = PropertySearchParams(
                location=f"{property.address.city}, {property.address.state}",
                filters=filters,
                max_results=max_results + 1
            )
            results = await resources.search_engine.search(params)
        
        # Filter out the reference property
        similar_properties = [
            hit for hit in results.hits
            if hit.property.id != property_id
        ][:max_results]
        
        return {
            "success": True,
            "reference_property": {
                "id": property.id,
                "price": property.price,
                "bedrooms": property.bedrooms,
                "bathrooms": property.bathrooms,
                "square_feet": property.square_feet
            },
            "similar_properties": [
                {
                    "id": hit.property.id,
                    "listing_id": hit.property.listing_id,
                    "price": hit.property.price,
                    "price_difference": hit.property.price - property.price,
                    "price_diff_percent": round(((hit.property.price - property.price) / property.price) * 100, 1),
                    "bedrooms": hit.property.bedrooms,
                    "bathrooms": hit.property.bathrooms,
                    "square_feet": hit.property.square_feet,
                    "address": {
                        "city": hit.property.address.city,
                        "state": hit.property.address.state
                    },
                    "similarity_score": round(hit.score, 3) if hit.score else 0.0
                }
                for hit in similar_properties
            ],
            "total_found": len(similar_properties)
        }
        
    except Exception as e:
        logger.error("find_similar_properties_failed", property_id=property_id, error=str(e))
        return {"error": f"Failed to find similar properties: {str(e)}"}