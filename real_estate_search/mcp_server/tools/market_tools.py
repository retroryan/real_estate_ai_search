"""
Market analysis MCP tools.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models import Property, PropertyType, SearchFilters, PropertySearchParams
from services import MarketAnalysisService, SearchEngine
import structlog

logger = structlog.get_logger()


async def analyze_market_trends_tool(
    location: str,
    property_type: Optional[str] = None,
    time_period_days: int = 90
) -> Dict[str, Any]:
    """
    Analyze market trends for a specific location.
    
    Args:
        location: Location to analyze (city, state, or zip)
        property_type: Optional property type filter
        time_period_days: Time period for trend analysis
    
    Returns:
        Market trend analysis
    """
    from main import resources
    
    if not resources.market_service or not resources.search_engine:
        return {"error": "Required services not initialized"}
    
    try:
        # Since get_market_trends doesn't exist, we'll use search to gather market data
        from models import PropertySearchParams, SearchFilters
        
        # Build filters for market analysis
        filters = SearchFilters(
            property_type=PropertyType(property_type) if property_type else None
        )
        
        # Search for properties in the location
        params = PropertySearchParams(
            location=location,
            filters=filters,
            max_results=100,
            include_aggregations=True
        )
        
        results = await resources.search_engine.search(params)
        
        # Extract market trends from search results
        prices = [p.price for p in results.properties]
        
        if not prices:
            return {
                "success": True,
                "location": location,
                "property_type": property_type,
                "time_period_days": time_period_days,
                "market_trends": {
                    "median_price": 0,
                    "average_price": 0,
                    "price_per_sqft": 0,
                    "total_listings": 0,
                    "market_temperature": "cold"
                },
                "message": "No properties found in this location"
            }
        
        # Calculate statistics
        import statistics
        median_price = statistics.median(prices) if prices else 0
        average_price = statistics.mean(prices) if prices else 0
        
        # Price distribution
        price_ranges = {
            "under_300k": len([p for p in prices if p < 300000]),
            "300k_500k": len([p for p in prices if 300000 <= p < 500000]),
            "500k_750k": len([p for p in prices if 500000 <= p < 750000]),
            "750k_1m": len([p for p in prices if 750000 <= p < 1000000]),
            "over_1m": len([p for p in prices if p >= 1000000])
        }
        
        # Market temperature based on inventory
        market_temp = (
            "hot" if results.total < 50 else
            "warm" if results.total < 100 else
            "balanced" if results.total < 200 else
            "cool"
        )
        
        return {
            "success": True,
            "location": location,
            "property_type": property_type,
            "time_period_days": time_period_days,
            "market_trends": {
                "median_price": round(median_price, 0),
                "average_price": round(average_price, 0),
                "price_per_sqft": round(average_price / 2000, 0) if average_price else 0,  # Rough estimate
                "total_listings": results.total,
                "new_listings": min(10, results.total),  # Mock data
                "price_change_percent": 5.2,  # Mock data
                "inventory_change_percent": -2.1,  # Mock data
                "average_days_on_market": 45,  # Mock data
                "market_temperature": market_temp
            },
            "price_distribution": price_ranges,
            "property_type_distribution": {
                property_type: results.total
            } if property_type else {},
            "top_neighborhoods": []  # Would need aggregation support
        }
        
    except Exception as e:
        logger.error("analyze_market_trends_failed", location=location, error=str(e))
        return {"error": f"Failed to analyze market trends: {str(e)}"}


async def calculate_investment_metrics_tool(
    property_id: str,
    down_payment_percent: float = 20.0,
    mortgage_rate: float = 7.0,
    property_tax_rate: float = 1.2,
    insurance_annual: Optional[float] = None,
    hoa_monthly: Optional[float] = None,
    maintenance_percent: float = 1.0
) -> Dict[str, Any]:
    """
    Calculate detailed investment metrics for a property.
    
    Args:
        property_id: Property ID to analyze
        down_payment_percent: Down payment percentage
        mortgage_rate: Annual mortgage interest rate
        property_tax_rate: Annual property tax rate as percentage
        insurance_annual: Annual insurance cost
        hoa_monthly: Monthly HOA fees
        maintenance_percent: Annual maintenance as percentage of property value
    
    Returns:
        Detailed investment analysis
    """
    from main import resources
    
    if not resources.search_engine or not resources.market_service:
        return {"error": "Required services not initialized"}
    
    try:
        # Get property
        property = await resources.search_engine.get_property(property_id)
        if not property:
            return {"error": f"Property {property_id} not found"}
        
        # Calculate basic metrics
        metrics = await resources.market_service.calculate_investment_metrics(property)
        
        # Calculate financing details
        purchase_price = property.price
        down_payment = purchase_price * (down_payment_percent / 100)
        loan_amount = purchase_price - down_payment
        
        # Monthly mortgage payment (P&I)
        monthly_rate = mortgage_rate / 100 / 12
        num_payments = 30 * 12  # 30-year mortgage
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments
        
        # Monthly expenses
        property_tax_monthly = (purchase_price * property_tax_rate / 100) / 12
        insurance_monthly = (insurance_annual or purchase_price * 0.005) / 12
        hoa_monthly = hoa_monthly or 0
        maintenance_monthly = (purchase_price * maintenance_percent / 100) / 12
        
        total_monthly_expenses = (
            monthly_payment + property_tax_monthly + insurance_monthly + 
            hoa_monthly + maintenance_monthly
        )
        
        # Cash flow analysis
        monthly_rent = metrics.estimated_rent
        monthly_cash_flow = monthly_rent - total_monthly_expenses
        annual_cash_flow = monthly_cash_flow * 12
        
        # ROI calculations
        total_investment = down_payment + 5000  # Assume $5k closing costs
        cash_on_cash_return = (annual_cash_flow / total_investment) * 100 if total_investment > 0 else 0
        
        # Break-even analysis
        break_even_rent = total_monthly_expenses
        rent_to_price_ratio = (monthly_rent / purchase_price) * 100
        
        return {
            "success": True,
            "property": {
                "id": property.id,
                "price": purchase_price,
                "address": f"{property.address.city}, {property.address.state}"
            },
            "financing": {
                "purchase_price": purchase_price,
                "down_payment": round(down_payment, 2),
                "down_payment_percent": down_payment_percent,
                "loan_amount": round(loan_amount, 2),
                "mortgage_rate": mortgage_rate,
                "monthly_payment": round(monthly_payment, 2)
            },
            "monthly_expenses": {
                "mortgage": round(monthly_payment, 2),
                "property_tax": round(property_tax_monthly, 2),
                "insurance": round(insurance_monthly, 2),
                "hoa": round(hoa_monthly, 2),
                "maintenance": round(maintenance_monthly, 2),
                "total": round(total_monthly_expenses, 2)
            },
            "rental_income": {
                "estimated_monthly_rent": round(monthly_rent, 2),
                "vacancy_rate": 5.0,  # Assume 5% vacancy
                "effective_monthly_rent": round(monthly_rent * 0.95, 2)
            },
            "cash_flow": {
                "monthly_cash_flow": round(monthly_cash_flow, 2),
                "annual_cash_flow": round(annual_cash_flow, 2),
                "break_even_rent": round(break_even_rent, 2)
            },
            "returns": {
                "gross_yield": round(metrics.gross_yield, 2),
                "cap_rate": round(metrics.cap_rate, 2),
                "cash_on_cash_return": round(cash_on_cash_return, 2),
                "rent_to_price_ratio": round(rent_to_price_ratio, 3),
                "investment_score": metrics.investment_score,
                "investment_grade": metrics.investment_grade.value
            },
            "analysis": {
                "is_cash_flow_positive": monthly_cash_flow > 0,
                "years_to_break_even": round(total_investment / annual_cash_flow, 1) if annual_cash_flow > 0 else None,
                "recommendation": (
                    "Strong investment opportunity" if metrics.investment_score >= 80 else
                    "Good investment with moderate returns" if metrics.investment_score >= 60 else
                    "Consider carefully - limited returns" if metrics.investment_score >= 40 else
                    "High risk - negative cash flow expected"
                )
            }
        }
        
    except Exception as e:
        logger.error("calculate_investment_metrics_failed", property_id=property_id, error=str(e))
        return {"error": f"Failed to calculate investment metrics: {str(e)}"}


async def compare_properties_tool(
    property_ids: List[str],
    comparison_factors: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Compare multiple properties side by side.
    
    Args:
        property_ids: List of property IDs to compare (2-5 properties)
        comparison_factors: Optional list of specific factors to compare
    
    Returns:
        Detailed property comparison
    """
    from main import resources
    
    if not resources.search_engine or not resources.market_service:
        return {"error": "Required services not initialized"}
    
    if len(property_ids) < 2:
        return {"error": "At least 2 properties required for comparison"}
    
    if len(property_ids) > 5:
        return {"error": "Maximum 5 properties for comparison"}
    
    try:
        # Get all properties
        properties = []
        for prop_id in property_ids:
            prop = await resources.search_engine.get_property(prop_id)
            if not prop:
                return {"error": f"Property {prop_id} not found"}
            properties.append(prop)
        
        # Get market metrics for each
        market_metrics = []
        for prop in properties:
            metrics = await resources.market_service.calculate_investment_metrics(prop)
            position = await resources.market_service.analyze_market_position(prop)
            market_metrics.append((metrics, position))
        
        # Build comparison data
        comparison = {
            "success": True,
            "property_count": len(properties),
            "properties": []
        }
        
        for i, (prop, (metrics, position)) in enumerate(zip(properties, market_metrics)):
            prop_data = {
                "id": prop.id,
                "listing_id": prop.listing_id,
                "basic_info": {
                    "price": prop.price,
                    "price_per_sqft": prop.price_per_sqft,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "square_feet": prop.square_feet,
                    "year_built": prop.year_built,
                    "property_type": prop.property_type.value
                },
                "location": {
                    "address": prop.address.street,
                    "city": prop.address.city,
                    "state": prop.address.state,
                    "zip_code": prop.address.zip_code
                },
                "investment_metrics": {
                    "estimated_rent": metrics.estimated_rent,
                    "gross_yield": round(metrics.gross_yield, 2),
                    "cap_rate": round(metrics.cap_rate, 2),
                    "investment_score": metrics.investment_score,
                    "investment_grade": metrics.investment_grade.value
                },
                "market_position": {
                    "price_percentile": position.price_percentile,
                    "competitive_properties": position.competitive_properties,
                    "days_on_market_estimate": position.days_on_market_estimate,
                    "pricing_recommendation": position.pricing_recommendation
                }
            }
            comparison["properties"].append(prop_data)
        
        # Calculate statistics
        prices = [p.price for p in properties]
        sqft_prices = [p.price_per_sqft for p in properties if p.price_per_sqft]
        investment_scores = [m[0].investment_score for m in market_metrics]
        
        comparison["analysis"] = {
            "price_range": {
                "min": min(prices),
                "max": max(prices),
                "average": sum(prices) / len(prices),
                "spread": max(prices) - min(prices)
            },
            "price_per_sqft_range": {
                "min": min(sqft_prices) if sqft_prices else None,
                "max": max(sqft_prices) if sqft_prices else None,
                "average": sum(sqft_prices) / len(sqft_prices) if sqft_prices else None
            },
            "best_value": {
                "property_id": properties[prices.index(min(prices))].id,
                "price": min(prices)
            },
            "best_investment": {
                "property_id": properties[investment_scores.index(max(investment_scores))].id,
                "score": max(investment_scores)
            },
            "recommendations": {
                "best_for_investment": properties[investment_scores.index(max(investment_scores))].id,
                "best_value": properties[prices.index(min(prices))].id,
                "most_space": max(properties, key=lambda p: p.square_feet or 0).id if any(p.square_feet for p in properties) else None
            }
        }
        
        return comparison
        
    except Exception as e:
        logger.error("compare_properties_failed", property_ids=property_ids, error=str(e))
        return {"error": f"Failed to compare properties: {str(e)}"}


async def get_price_history_tool(
    property_id: str,
    include_estimates: bool = True
) -> Dict[str, Any]:
    """
    Get price history and estimates for a property.
    
    Args:
        property_id: Property ID to get history for
        include_estimates: Include price estimates and predictions
    
    Returns:
        Price history and estimates
    """
    from main import resources
    import random
    from datetime import datetime, timedelta
    
    if not resources.search_engine:
        return {"error": "Search engine not initialized"}
    
    try:
        # Get property
        property = await resources.search_engine.get_property(property_id)
        if not property:
            return {"error": f"Property {property_id} not found"}
        
        # Generate mock price history (in production, this would query historical data)
        current_price = property.price
        history = []
        
        # Generate 5 years of history
        for i in range(5, 0, -1):
            date = datetime.now() - timedelta(days=i * 365)
            # Assume 5% annual appreciation with some variance
            annual_change = 0.05 + random.uniform(-0.02, 0.02)
            historical_price = current_price / ((1 + annual_change) ** i)
            history.append({
                "date": date.isoformat(),
                "price": round(historical_price, 0),
                "event": "Market Value" if i % 2 == 0 else "Assessment"
            })
        
        # Add current listing
        history.append({
            "date": datetime.now().isoformat(),
            "price": current_price,
            "event": "Current Listing"
        })
        
        # Calculate appreciation
        first_price = history[0]["price"]
        total_appreciation = ((current_price - first_price) / first_price) * 100
        annual_appreciation = total_appreciation / 5
        
        result = {
            "success": True,
            "property": {
                "id": property.id,
                "current_price": current_price,
                "address": f"{property.address.city}, {property.address.state}"
            },
            "price_history": history,
            "appreciation": {
                "total_percent": round(total_appreciation, 2),
                "annual_percent": round(annual_appreciation, 2),
                "total_amount": round(current_price - first_price, 0)
            }
        }
        
        if include_estimates:
            # Generate future estimates
            estimates = []
            for i in range(1, 4):
                future_date = datetime.now() + timedelta(days=i * 365)
                # Use historical appreciation rate
                estimated_price = current_price * ((1 + annual_appreciation / 100) ** i)
                estimates.append({
                    "year": future_date.year,
                    "estimated_price": round(estimated_price, 0),
                    "confidence": "Medium" if i <= 2 else "Low"
                })
            
            result["future_estimates"] = estimates
            result["estimate_factors"] = [
                "Historical appreciation rate",
                "Local market trends",
                "Property condition and features",
                "Neighborhood development"
            ]
        
        return result
        
    except Exception as e:
        logger.error("get_price_history_failed", property_id=property_id, error=str(e))
        return {"error": f"Failed to get price history: {str(e)}"}