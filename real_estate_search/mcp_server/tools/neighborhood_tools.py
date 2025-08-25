"""
Neighborhood-related MCP tools.
"""

from typing import List, Optional, Dict, Any
from models import GeoLocation, POICategory
from services import LocationService, WikipediaEnrichmentService
import structlog

logger = structlog.get_logger()


async def analyze_neighborhood_tool(
    location: str,
    radius_miles: float = 2.0
) -> Dict[str, Any]:
    """
    Analyze a neighborhood for amenities, walkability, and demographics.
    
    Args:
        location: Address or location to analyze
        radius_miles: Radius in miles for analysis
    
    Returns:
        Comprehensive neighborhood analysis
    """
    from main import resources
    
    if not resources.location_service or not resources.enrichment_service:
        return {"error": "Required services not initialized"}
    
    try:
        # Geocode the location
        geo_location = await resources.location_service.geocode_address(location)
        
        if not geo_location:
            return {"error": f"Could not geocode location: {location}"}
        
        # Get POIs
        pois = await resources.location_service.find_nearby_pois(geo_location, radius_miles)
        
        # Calculate walkability
        walkability_score = await resources.location_service.calculate_walkability_score(geo_location)
        
        # Get Wikipedia context (create a dummy property for the location)
        from models import Property, PropertyType, Address
        dummy_property = Property(
            id="neighborhood-analysis",
            listing_id="NA",
            property_type=PropertyType.single_family,
            price=1,
            bedrooms=1,
            bathrooms=1,
            address=Address(
                street="Analysis Location",
                city=location.split(",")[0].strip() if "," in location else location,
                state=location.split(",")[-1].strip() if "," in location else "TX",
                zip_code="00000",
                location=geo_location
            )
        )
        enrichment = await resources.enrichment_service.enrich_property(dummy_property)
        wiki_context = enrichment.wikipedia_context
        
        # Categorize POIs
        poi_categories = {}
        for poi in pois:
            category = poi.category.value
            if category not in poi_categories:
                poi_categories[category] = []
            poi_categories[category].append({
                "name": poi.name,
                "distance_miles": round(poi.distance_miles, 2)
            })
        
        # Sort each category by distance
        for category in poi_categories:
            poi_categories[category].sort(key=lambda x: x["distance_miles"])
        
        return {
            "success": True,
            "location": {
                "address": location,
                "coordinates": {
                    "lat": geo_location.lat,
                    "lon": geo_location.lon
                }
            },
            "walkability": {
                "score": walkability_score,
                "category": (
                    "Walker's Paradise" if walkability_score >= 90 else
                    "Very Walkable" if walkability_score >= 70 else
                    "Somewhat Walkable" if walkability_score >= 50 else
                    "Car-Dependent"
                ),
                "description": (
                    "Daily errands do not require a car" if walkability_score >= 90 else
                    "Most errands can be accomplished on foot" if walkability_score >= 70 else
                    "Some errands can be accomplished on foot" if walkability_score >= 50 else
                    "Most errands require a car"
                )
            },
            "amenities": {
                "total_count": len(pois),
                "by_category": poi_categories,
                "top_nearby": [
                    {
                        "name": poi.name,
                        "category": poi.category.value,
                        "distance_miles": round(poi.distance_miles, 2)
                    }
                    for poi in sorted(pois, key=lambda x: x.distance_miles)[:10]
                ]
            },
            "wikipedia_context": wiki_context if wiki_context else None,
            "analysis_radius_miles": radius_miles
        }
        
    except Exception as e:
        logger.error("analyze_neighborhood_failed", location=location, error=str(e))
        return {"error": f"Failed to analyze neighborhood: {str(e)}"}


async def find_nearby_amenities_tool(
    location: str,
    category: Optional[str] = None,
    radius_miles: float = 1.0,
    max_results: int = 20
) -> Dict[str, Any]:
    """
    Find specific amenities near a location.
    
    Args:
        location: Address or location to search from
        category: Specific category of amenities (school, restaurant, shopping, etc.)
        radius_miles: Search radius in miles
        max_results: Maximum number of results to return
    
    Returns:
        List of nearby amenities
    """
    from main import resources
    
    if not resources.location_service:
        return {"error": "Location service not initialized"}
    
    try:
        # Geocode the location
        geo_location = await resources.location_service.geocode_address(location)
        
        if not geo_location:
            return {"error": f"Could not geocode location: {location}"}
        
        # Get POIs
        all_pois = await resources.location_service.find_nearby_pois(geo_location, radius_miles)
        
        # Filter by category if specified
        if category:
            try:
                poi_category = POICategory(category.lower())
                filtered_pois = [poi for poi in all_pois if poi.category == poi_category]
            except ValueError:
                # If invalid category, try partial match
                filtered_pois = [
                    poi for poi in all_pois 
                    if category.lower() in poi.category.value.lower()
                ]
        else:
            filtered_pois = all_pois
        
        # Sort by distance and limit results
        filtered_pois.sort(key=lambda x: x.distance_miles)
        filtered_pois = filtered_pois[:max_results]
        
        # Group by category for summary
        category_counts = {}
        for poi in filtered_pois:
            cat = poi.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        return {
            "success": True,
            "location": {
                "address": location,
                "coordinates": {
                    "lat": geo_location.lat,
                    "lon": geo_location.lon
                }
            },
            "search_criteria": {
                "category_filter": category,
                "radius_miles": radius_miles,
                "max_results": max_results
            },
            "amenities": [
                {
                    "name": poi.name,
                    "category": poi.category.value,
                    "distance_miles": round(poi.distance_miles, 2),
                    "address": poi.address,
                    "rating": poi.rating,
                    "price_level": poi.price_level
                }
                for poi in filtered_pois
            ],
            "summary": {
                "total_found": len(filtered_pois),
                "by_category": category_counts,
                "nearest": {
                    "name": filtered_pois[0].name,
                    "distance_miles": round(filtered_pois[0].distance_miles, 2)
                } if filtered_pois else None,
                "farthest": {
                    "name": filtered_pois[-1].name,
                    "distance_miles": round(filtered_pois[-1].distance_miles, 2)
                } if filtered_pois else None
            }
        }
        
    except Exception as e:
        logger.error("find_nearby_amenities_failed", location=location, error=str(e))
        return {"error": f"Failed to find amenities: {str(e)}"}


async def get_walkability_score_tool(location: str) -> Dict[str, Any]:
    """
    Get detailed walkability score and analysis for a location.
    
    Args:
        location: Address or location to analyze
    
    Returns:
        Walkability score and detailed breakdown
    """
    from main import resources
    
    if not resources.location_service:
        return {"error": "Location service not initialized"}
    
    try:
        # Geocode the location
        geo_location = await resources.location_service.geocode_address(location)
        
        if not geo_location:
            return {"error": f"Could not geocode location: {location}"}
        
        # Calculate walkability score
        walkability_score = await resources.location_service.calculate_walkability_score(geo_location)
        
        # Get nearby POIs for context
        pois = await resources.location_service.find_nearby_pois(geo_location, radius_miles=0.5)
        
        # Count walkable amenities
        walkable_categories = [
            POICategory.grocery, POICategory.restaurant, POICategory.shopping,
            POICategory.cafe, POICategory.bank, POICategory.pharmacy
        ]
        
        walkable_amenities = [
            poi for poi in pois 
            if poi.category in walkable_categories
        ]
        
        # Calculate density scores
        grocery_nearby = any(poi.category == POICategory.grocery for poi in walkable_amenities)
        restaurants_count = sum(1 for poi in walkable_amenities if poi.category == POICategory.restaurant)
        shopping_count = sum(1 for poi in walkable_amenities if poi.category == POICategory.shopping)
        
        # Determine walkability factors
        factors = {
            "grocery_stores": {
                "available": grocery_nearby,
                "impact": "High",
                "description": "Essential for daily needs"
            },
            "restaurants": {
                "count": restaurants_count,
                "density": "High" if restaurants_count >= 10 else "Medium" if restaurants_count >= 5 else "Low",
                "impact": "Medium"
            },
            "shopping": {
                "count": shopping_count,
                "density": "High" if shopping_count >= 5 else "Medium" if shopping_count >= 2 else "Low",
                "impact": "Medium"
            },
            "transit_access": {
                "available": walkability_score >= 50,  # Simplified assumption
                "impact": "High"
            },
            "sidewalk_coverage": {
                "estimated": "Good" if walkability_score >= 70 else "Fair" if walkability_score >= 50 else "Limited",
                "impact": "High"
            }
        }
        
        return {
            "success": True,
            "location": {
                "address": location,
                "coordinates": {
                    "lat": geo_location.lat,
                    "lon": geo_location.lon
                }
            },
            "walkability": {
                "score": walkability_score,
                "max_score": 100,
                "category": (
                    "Walker's Paradise" if walkability_score >= 90 else
                    "Very Walkable" if walkability_score >= 70 else
                    "Somewhat Walkable" if walkability_score >= 50 else
                    "Car-Dependent"
                ),
                "description": (
                    "Daily errands do not require a car" if walkability_score >= 90 else
                    "Most errands can be accomplished on foot" if walkability_score >= 70 else
                    "Some errands can be accomplished on foot" if walkability_score >= 50 else
                    "Most errands require a car"
                )
            },
            "factors": factors,
            "nearby_walkable_amenities": {
                "total": len(walkable_amenities),
                "within_half_mile": [
                    {
                        "name": poi.name,
                        "category": poi.category.value,
                        "distance_miles": round(poi.distance_miles, 2)
                    }
                    for poi in sorted(walkable_amenities, key=lambda x: x.distance_miles)[:10]
                ]
            },
            "recommendations": [
                "Consider properties within 0.25 miles of grocery stores" if not grocery_nearby else None,
                "Look for areas with higher restaurant density" if restaurants_count < 5 else None,
                "Verify sidewalk conditions in person" if walkability_score < 70 else None,
                "Check public transit schedules and routes" if walkability_score >= 50 else None
            ][: None if all(r is None for r in [...]) else ...]  # Filter None values
        }
        
    except Exception as e:
        logger.error("get_walkability_score_failed", location=location, error=str(e))
        return {"error": f"Failed to get walkability score: {str(e)}"}