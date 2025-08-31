"""
Display formatting utilities for demo queries.

Separates data storage format from display presentation.
All formatting for user display happens here, not in models.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from real_estate_search.demo_queries.es_models import ESProperty, ESNeighborhood, ESWikipedia


class PropertyDisplayFormatter:
    """Format property data for user display."""
    
    # Property type display mappings
    PROPERTY_TYPE_DISPLAY = {
        "single-family": "Single Family",
        "condo": "Condo",
        "townhouse": "Townhouse",
        "townhome": "Townhouse",
        "multi-family": "Multi-Family",
        "land": "Land",
        "other": "Other"
    }
    
    @staticmethod
    def format_property_type(property_type: str) -> str:
        """Format property type for display."""
        if not property_type:
            return "Unknown"
        return PropertyDisplayFormatter.PROPERTY_TYPE_DISPLAY.get(
            property_type.lower(),
            property_type.replace("-", " ").title()
        )
    
    @staticmethod
    def format_price(price: float) -> str:
        """Format price for display."""
        if price >= 1000000:
            return f"${price/1000000:.1f}M"
        elif price >= 1000:
            return f"${price:,.0f}"
        else:
            return f"${price:.2f}"
    
    @staticmethod
    def format_address(property: ESProperty) -> str:
        """Format address for display."""
        if property.address:
            parts = []
            if property.address.street:
                parts.append(property.address.street)
            if property.address.city and property.address.state:
                parts.append(f"{property.address.city}, {property.address.state}")
            elif property.address.city:
                parts.append(property.address.city)
            elif property.address.state:
                parts.append(property.address.state)
            return " ".join(parts)
        return "Address not available"
    
    @staticmethod
    def format_summary(property: ESProperty) -> str:
        """Format property summary line."""
        parts = []
        
        # Bedrooms/Bathrooms
        if property.bedrooms or property.bathrooms:
            bed_bath = []
            if property.bedrooms:
                bed_bath.append(f"{property.bedrooms}bd")
            if property.bathrooms:
                # Format bathrooms to show .5 as fraction
                bath_int = int(property.bathrooms)
                if property.bathrooms % 1 == 0.5:
                    bed_bath.append(f"{bath_int}.5ba")
                else:
                    bed_bath.append(f"{bath_int}ba")
            parts.append("/".join(bed_bath))
        
        # Square feet
        if property.square_feet:
            parts.append(f"{property.square_feet:,} sqft")
        
        # Property type
        parts.append(PropertyDisplayFormatter.format_property_type(property.property_type))
        
        return " | ".join(parts)
    
    @staticmethod
    def format_for_display(property: ESProperty) -> Dict[str, Any]:
        """Format complete property for display."""
        return {
            "listing_id": property.listing_id,
            "address": PropertyDisplayFormatter.format_address(property),
            "price": PropertyDisplayFormatter.format_price(property.price),
            "summary": PropertyDisplayFormatter.format_summary(property),
            "property_type": PropertyDisplayFormatter.format_property_type(property.property_type),
            "features": property.features,  # Already a list of amenities
            "description": property.description
        }
    
    @staticmethod
    def format_list_item(property: ESProperty, index: int, score: Optional[float] = None) -> str:
        """Format property as a list item for display."""
        lines = [f"{index}. {PropertyDisplayFormatter.format_address(property)}"]
        
        # Price and summary on second line
        price_line = f"   {PropertyDisplayFormatter.format_price(property.price)} | {PropertyDisplayFormatter.format_summary(property)}"
        lines.append(price_line)
        
        # Optional score
        if score is not None:
            lines.append(f"   Score: {score:.3f}")
        
        return "\n".join(lines)


class NeighborhoodDisplayFormatter:
    """Format neighborhood data for user display."""
    
    @staticmethod
    def format_name(neighborhood: ESNeighborhood) -> str:
        """Format neighborhood name with location."""
        if neighborhood.city:
            return f"{neighborhood.name}, {neighborhood.city}"
        return neighborhood.name
    
    @staticmethod
    def format_stats(neighborhood: ESNeighborhood) -> Dict[str, str]:
        """Format neighborhood statistics for display."""
        stats = {}
        
        if neighborhood.population:
            stats["Population"] = f"{neighborhood.population:,}"
        
        if neighborhood.median_income:
            stats["Median Income"] = f"${neighborhood.median_income:,.0f}"
        
        if neighborhood.median_home_price:
            stats["Median Home Price"] = f"${neighborhood.median_home_price:,.0f}"
        
        if neighborhood.walkability_score:
            stats["Walkability"] = f"{neighborhood.walkability_score:.1f}/100"
        
        if neighborhood.school_score:
            stats["School Score"] = f"{neighborhood.school_score:.1f}/10"
        
        return stats
    
    @staticmethod
    def format_for_display(neighborhood: ESNeighborhood) -> Dict[str, Any]:
        """Format complete neighborhood for display."""
        return {
            "name": NeighborhoodDisplayFormatter.format_name(neighborhood),
            "description": neighborhood.description,
            "stats": NeighborhoodDisplayFormatter.format_stats(neighborhood),
            "amenities": neighborhood.amenities
        }


class WikipediaDisplayFormatter:
    """Format Wikipedia data for user display."""
    
    @staticmethod
    def format_title(article: ESWikipedia) -> str:
        """Format article title with location if available."""
        if article.city and article.state:
            return f"{article.title} ({article.city}, {article.state})"
        elif article.city:
            return f"{article.title} ({article.city})"
        return article.title
    
    @staticmethod
    def format_summary(article: ESWikipedia, max_length: int = 200) -> str:
        """Format article summary for display."""
        summary = article.short_summary or article.long_summary or ""
        if len(summary) > max_length:
            return summary[:max_length-3] + "..."
        return summary
    
    @staticmethod
    def format_for_display(article: ESWikipedia) -> Dict[str, Any]:
        """Format complete article for display."""
        return {
            "title": WikipediaDisplayFormatter.format_title(article),
            "summary": WikipediaDisplayFormatter.format_summary(article),
            "categories": article.categories[:3] if article.categories else [],
            "url": article.url
        }


class AggregationDisplayFormatter:
    """Format aggregation results for user display."""
    
    @staticmethod
    def format_price_bucket(key: Any, doc_count: int, stats: Optional[Dict] = None) -> str:
        """Format price range bucket for display."""
        if isinstance(key, (int, float)):
            # Single value bucket
            return f"${key:,.0f}: {doc_count} properties"
        elif isinstance(key, str):
            # Range bucket (e.g., "100000-200000")
            if "-" in key:
                parts = key.split("-")
                if len(parts) == 2:
                    return f"${int(parts[0]):,} - ${int(parts[1]):,}: {doc_count} properties"
            return f"{key}: {doc_count} properties"
        return f"{key}: {doc_count}"
    
    @staticmethod
    def format_stats(stats: Dict[str, Any]) -> Dict[str, str]:
        """Format statistical aggregation results."""
        formatted = {}
        
        if "count" in stats:
            formatted["Count"] = str(stats["count"])
        
        if "min" in stats and stats["min"] is not None:
            formatted["Min"] = f"${stats['min']:,.0f}"
        
        if "max" in stats and stats["max"] is not None:
            formatted["Max"] = f"${stats['max']:,.0f}"
        
        if "avg" in stats and stats["avg"] is not None:
            formatted["Average"] = f"${stats['avg']:,.0f}"
        
        if "sum" in stats and stats["sum"] is not None:
            formatted["Total"] = f"${stats['sum']:,.0f}"
        
        return formatted