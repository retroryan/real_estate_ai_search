"""
Market analysis service for property investment analysis.
Clean async implementation for market positioning and comparisons.
"""

import logging
import statistics
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from elasticsearch import AsyncElasticsearch

from models import (
    Property, MarketPosition, InvestmentMetrics, InvestmentGrade,
    ComparableProperty, PropertyAnalysis, PropertyComparison,
    AffordabilityAnalysis, SearchFilters, PropertySearchParams,
    SearchMode, GeoLocation
)
from config.settings import settings
from .search_engine import SearchEngine

logger = logging.getLogger(__name__)


class MarketAnalysisService:
    """Service for property market analysis and investment metrics."""
    
    def __init__(self, es_client: AsyncElasticsearch):
        """Initialize market analysis service."""
        self.es = es_client
        self.search_engine = SearchEngine(es_client)
        self.index_name = settings.elasticsearch.index_name
        
    async def analyze_market_position(self, property: Property) -> MarketPosition:
        """Analyze property's position in the market."""
        # Find comparable properties in the same area
        filters = SearchFilters(
            cities=[property.address.city],
            property_types=[property.property_type.value],
            price_range={
                "min_price": property.price * 0.7,
                "max_price": property.price * 1.3
            }
        )
        
        search_params = PropertySearchParams(
            filters=filters,
            max_results=100
        )
        
        results = await self.search_engine.search(search_params)
        
        # Calculate market statistics
        prices = [p.price for p in results.properties]
        if not prices:
            prices = [property.price]  # Use property's own price if no comparables
        
        prices.sort()
        median_price = statistics.median(prices)
        
        # Calculate percentile
        below_count = sum(1 for p in prices if p < property.price)
        percentile = (below_count / len(prices)) * 100 if prices else 50
        
        # Price per square foot analysis
        price_per_sqft = None
        sqft_percentile = None
        if property.square_feet:
            price_per_sqft = property.price / property.square_feet
            
            # Get price per sqft for comparables
            sqft_prices = []
            for p in results.properties:
                if p.square_feet and p.square_feet > 0:
                    sqft_prices.append(p.price / p.square_feet)
            
            if sqft_prices:
                sqft_prices.sort()
                below_sqft = sum(1 for p in sqft_prices if p < price_per_sqft)
                sqft_percentile = (below_sqft / len(sqft_prices)) * 100
        
        # Estimate days on market
        if percentile < 30:
            days_estimate = 15  # Priced to sell quickly
        elif percentile < 70:
            days_estimate = 35  # Average time
        else:
            days_estimate = 60  # May take longer
        
        # Pricing recommendation
        if percentile < 20:
            recommendation = "Aggressively priced - expect quick sale"
        elif percentile < 40:
            recommendation = "Competitively priced - good value"
        elif percentile < 60:
            recommendation = "Fair market price"
        elif percentile < 80:
            recommendation = "Above market - may need patience"
        else:
            recommendation = "Premium pricing - consider reduction if urgent"
        
        return MarketPosition(
            price_percentile=percentile,
            price_vs_median=((property.price - median_price) / median_price) * 100,
            price_per_sqft=price_per_sqft,
            price_per_sqft_percentile=sqft_percentile,
            competitive_properties=len(results.properties),
            days_on_market_estimate=days_estimate,
            pricing_recommendation=recommendation,
            similar_sold_count=0,  # Would query sold properties in production
            average_similar_price=median_price
        )
    
    async def calculate_investment_metrics(self, property: Property) -> InvestmentMetrics:
        """Calculate investment metrics for a property."""
        # Estimate rental income (simplified calculation)
        # In production, would use actual rental comparables
        estimated_rent = property.price * 0.007  # 0.7% of purchase price per month
        
        # Calculate gross yield
        annual_rent = estimated_rent * 12
        gross_yield = (annual_rent / property.price) * 100
        
        # Estimate expenses (simplified)
        property_tax = property.price * 0.012  # 1.2% annually
        insurance = property.price * 0.004  # 0.4% annually
        maintenance = annual_rent * 0.1  # 10% of rent
        property_mgmt = annual_rent * 0.08  # 8% of rent if using PM
        
        total_expenses = property_tax + insurance + maintenance + property_mgmt
        net_income = annual_rent - total_expenses
        
        # Calculate cap rate
        cap_rate = (net_income / property.price) * 100
        
        # Calculate cash flow (assuming 20% down, 6.5% interest)
        down_payment = property.price * 0.2
        loan_amount = property.price * 0.8
        monthly_payment = self._calculate_mortgage_payment(loan_amount, 0.065, 30)
        monthly_cash_flow = estimated_rent - monthly_payment - (total_expenses / 12)
        
        # Price to rent ratio
        price_to_rent = property.price / annual_rent
        
        # Determine investment grade
        if cap_rate > 8 and gross_yield > 10:
            grade = InvestmentGrade.excellent
            score = 90
        elif cap_rate > 6 and gross_yield > 8:
            grade = InvestmentGrade.very_good
            score = 80
        elif cap_rate > 5 and gross_yield > 7:
            grade = InvestmentGrade.good
            score = 70
        elif cap_rate > 4 and gross_yield > 6:
            grade = InvestmentGrade.above_average
            score = 60
        elif cap_rate > 3 and gross_yield > 5:
            grade = InvestmentGrade.average
            score = 50
        elif cap_rate > 2:
            grade = InvestmentGrade.below_average
            score = 40
        else:
            grade = InvestmentGrade.poor
            score = 30
        
        # ROI estimates (simplified)
        roi_1_year = ((net_income - (monthly_payment * 12)) / down_payment) * 100
        roi_5_year = roi_1_year * 5 + 10  # Add appreciation estimate
        
        # Break even calculation
        if monthly_cash_flow > 0:
            break_even_years = 0  # Already positive
        else:
            break_even_years = abs(down_payment / (monthly_cash_flow * 12)) if monthly_cash_flow != 0 else 99
        
        return InvestmentMetrics(
            estimated_rent=estimated_rent,
            gross_yield=gross_yield,
            cap_rate=cap_rate,
            cash_flow=monthly_cash_flow,
            price_to_rent_ratio=price_to_rent,
            investment_grade=grade,
            investment_score=score,
            roi_1_year=roi_1_year,
            roi_5_year=roi_5_year,
            break_even_years=break_even_years
        )
    
    async def find_comparable_sales(
        self,
        property: Property,
        max_results: int = 10
    ) -> List[ComparableProperty]:
        """Find comparable sold properties."""
        # Search for similar properties
        similar = await self.search_engine.find_similar(property.id, max_results)
        
        comparables = []
        for comp_prop in similar:
            # Calculate similarity score based on multiple factors
            similarity = self._calculate_similarity(property, comp_prop)
            
            # Calculate price difference
            price_diff = comp_prop.price - property.price
            
            # Calculate price per sqft difference
            sqft_diff = None
            if property.square_feet and comp_prop.square_feet:
                prop_sqft = property.price / property.square_feet
                comp_sqft = comp_prop.price / comp_prop.square_feet
                sqft_diff = comp_sqft - prop_sqft
            
            # Calculate distance if locations available
            distance = None
            if property.address.location and comp_prop.address.location:
                distance = self._calculate_distance(
                    property.address.location,
                    comp_prop.address.location
                )
            
            comparable = ComparableProperty(
                property=comp_prop,
                similarity_score=similarity,
                price_difference=price_diff,
                price_per_sqft_difference=sqft_diff,
                distance_miles=distance
            )
            
            comparables.append(comparable)
        
        # Sort by similarity score
        comparables.sort(key=lambda x: x.similarity_score, reverse=True)
        
        return comparables
    
    async def analyze_property(self, property: Property) -> PropertyAnalysis:
        """Perform comprehensive property analysis."""
        # Run analysis tasks concurrently
        market_position = await self.analyze_market_position(property)
        investment_metrics = await self.calculate_investment_metrics(property)
        comparables = await self.find_comparable_sales(property, 5)
        
        # Analyze strengths and weaknesses
        strengths = []
        weaknesses = []
        opportunities = []
        risks = []
        
        # Price analysis
        if market_position.price_percentile < 40:
            strengths.append("Competitively priced")
        elif market_position.price_percentile > 70:
            weaknesses.append("Above market pricing")
        
        # Investment analysis
        if investment_metrics.cap_rate > 6:
            strengths.append(f"Strong cap rate: {investment_metrics.cap_rate:.1f}%")
        elif investment_metrics.cap_rate < 4:
            weaknesses.append("Low cap rate for investors")
        
        # Property features
        if property.square_feet and property.square_feet > 2000:
            strengths.append("Spacious living area")
        elif property.square_feet and property.square_feet < 1000:
            weaknesses.append("Limited living space")
        
        # Market opportunities
        if market_position.competitive_properties < 10:
            opportunities.append("Low competition in market")
        
        # Investment risks
        if investment_metrics.cash_flow < 0:
            risks.append("Negative cash flow expected")
        
        # Overall recommendation
        if market_position.price_percentile < 50 and investment_metrics.investment_score > 60:
            recommendation = "Strong buy - Good value with solid investment potential"
        elif market_position.price_percentile < 70 and investment_metrics.investment_score > 50:
            recommendation = "Consider - Fair price with moderate investment returns"
        else:
            recommendation = "Proceed with caution - Review pricing and investment goals"
        
        # Calculate confidence based on data availability
        confidence = 0.7  # Base confidence
        if comparables:
            confidence += 0.15
        if market_position.competitive_properties > 20:
            confidence += 0.15
        
        return PropertyAnalysis(
            property=property,
            market_position=market_position,
            investment_metrics=investment_metrics,
            comparable_properties=comparables,
            strengths=strengths,
            weaknesses=weaknesses,
            opportunities=opportunities,
            risks=risks,
            overall_recommendation=recommendation,
            confidence_score=min(confidence, 1.0)
        )
    
    async def compare_properties(self, properties: List[Property]) -> PropertyComparison:
        """Compare multiple properties."""
        if len(properties) < 2:
            raise ValueError("Need at least 2 properties to compare")
        
        # Analyze each property
        analyses = []
        for prop in properties:
            analysis = await self.analyze_property(prop)
            analyses.append(analysis)
        
        # Build comparison metrics
        comparison_metrics = {}
        for i, analysis in enumerate(analyses):
            prop_id = analysis.property.id
            comparison_metrics[prop_id] = {
                "price": analysis.property.price,
                "price_percentile": analysis.market_position.price_percentile,
                "investment_score": analysis.investment_metrics.investment_score,
                "cap_rate": analysis.investment_metrics.cap_rate,
                "bedrooms": analysis.property.bedrooms,
                "bathrooms": analysis.property.bathrooms,
                "square_feet": analysis.property.square_feet
            }
        
        # Price comparison
        prices = [p.price for p in properties]
        price_comparison = {
            "min": min(prices),
            "max": max(prices),
            "median": statistics.median(prices),
            "range": max(prices) - min(prices)
        }
        
        # Feature comparison
        feature_comparison = {}
        for prop in properties:
            feature_comparison[prop.id] = prop.features
        
        # Location comparison
        location_comparison = {
            prop.id: {
                "city": prop.address.city,
                "state": prop.address.state
            }
            for prop in properties
        }
        
        # Determine best properties
        best_value_id = min(properties, key=lambda p: p.price).id
        
        investment_scores = {
            prop_id: metrics["investment_score"]
            for prop_id, metrics in comparison_metrics.items()
        }
        best_investment_id = max(investment_scores, key=investment_scores.get)
        
        # Best location (simplified - would use actual location scores)
        best_location_id = properties[0].id
        
        # Generate recommendations
        recommendation = "Based on the comparison:\n"
        recommendation += f"- Best value: Property {best_value_id}\n"
        recommendation += f"- Best investment: Property {best_investment_id}\n"
        recommendation += f"- Best location: Property {best_location_id}"
        
        # Generate summaries
        comparison_summary = {}
        for analysis in analyses:
            prop_id = analysis.property.id
            comparison_summary[prop_id] = (
                f"{analysis.property.get_summary()} - "
                f"Investment: {analysis.investment_metrics.investment_grade} - "
                f"Market: {analysis.market_position.pricing_recommendation}"
            )
        
        return PropertyComparison(
            properties=properties,
            comparison_metrics=comparison_metrics,
            price_comparison=price_comparison,
            feature_comparison=feature_comparison,
            location_comparison=location_comparison,
            best_value_id=best_value_id,
            best_investment_id=best_investment_id,
            best_location_id=best_location_id,
            recommendation=recommendation,
            comparison_summary=comparison_summary
        )
    
    async def analyze_affordability(
        self,
        property: Property,
        annual_income: float,
        down_payment: float,
        interest_rate: float = 6.5
    ) -> AffordabilityAnalysis:
        """Analyze property affordability for a buyer."""
        # Calculate loan details
        down_payment_percent = (down_payment / property.price) * 100
        loan_amount = property.price - down_payment
        
        # Calculate monthly payment
        monthly_payment = self._calculate_mortgage_payment(
            loan_amount,
            interest_rate / 100,
            30
        )
        
        # Estimate other costs
        property_tax_monthly = (property.price * 0.012) / 12  # 1.2% annually
        insurance_monthly = (property.price * 0.004) / 12  # 0.4% annually
        hoa_monthly = 150 if property.property_type.value in ["condo", "townhouse"] else None
        
        # Total monthly cost
        total_monthly = monthly_payment + property_tax_monthly + insurance_monthly
        if hoa_monthly:
            total_monthly += hoa_monthly
        
        # Calculate ratios
        monthly_income = annual_income / 12
        income_ratio = total_monthly / monthly_income
        
        # Debt-to-income (simplified - would need actual debt info)
        debt_to_income = income_ratio * 100  # Simplified
        
        # Determine affordability
        affordable = income_ratio <= 0.28 and down_payment_percent >= 10
        
        # Calculate affordability score
        if income_ratio < 0.2:
            score = 90
        elif income_ratio < 0.25:
            score = 75
        elif income_ratio < 0.28:
            score = 60
        elif income_ratio < 0.35:
            score = 40
        else:
            score = 20
        
        # Calculate max affordable price
        max_monthly = monthly_income * 0.28
        max_loan = self._calculate_max_loan(max_monthly, interest_rate / 100, 30)
        max_affordable_price = max_loan + down_payment
        
        # Additional down payment needed
        if not affordable and down_payment_percent < 20:
            additional_down = (property.price * 0.2) - down_payment
        else:
            additional_down = 0
        
        # Income needed
        income_needed = (total_monthly / 0.28) * 12
        
        return AffordabilityAnalysis(
            property_id=property.id,
            property_price=property.price,
            annual_income=annual_income,
            down_payment=down_payment,
            down_payment_percent=down_payment_percent,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            loan_term_years=30,
            monthly_payment=monthly_payment,
            property_tax_monthly=property_tax_monthly,
            insurance_monthly=insurance_monthly,
            hoa_monthly=hoa_monthly,
            total_monthly=total_monthly,
            income_ratio=income_ratio,
            debt_to_income=debt_to_income,
            affordable=affordable,
            affordability_score=score,
            max_affordable_price=max_affordable_price,
            additional_down_needed=additional_down,
            income_needed=income_needed
        )
    
    def _calculate_similarity(self, prop1: Property, prop2: Property) -> float:
        """Calculate similarity score between two properties."""
        score = 0.0
        weights = 0.0
        
        # Property type match
        if prop1.property_type == prop2.property_type:
            score += 0.2
        weights += 0.2
        
        # Bedroom similarity
        bed_diff = abs(prop1.bedrooms - prop2.bedrooms)
        if bed_diff == 0:
            score += 0.15
        elif bed_diff == 1:
            score += 0.1
        weights += 0.15
        
        # Bathroom similarity
        bath_diff = abs(prop1.bathrooms - prop2.bathrooms)
        if bath_diff < 0.5:
            score += 0.1
        elif bath_diff < 1:
            score += 0.05
        weights += 0.1
        
        # Square footage similarity
        if prop1.square_feet and prop2.square_feet:
            sqft_ratio = min(prop1.square_feet, prop2.square_feet) / max(prop1.square_feet, prop2.square_feet)
            score += sqft_ratio * 0.2
            weights += 0.2
        
        # Price similarity
        price_ratio = min(prop1.price, prop2.price) / max(prop1.price, prop2.price)
        score += price_ratio * 0.15
        weights += 0.15
        
        # Location similarity
        if prop1.address.city == prop2.address.city:
            score += 0.2
        weights += 0.2
        
        return score / weights if weights > 0 else 0
    
    def _calculate_distance(self, loc1: GeoLocation, loc2: GeoLocation) -> float:
        """Calculate distance between two locations in miles."""
        # Simplified distance calculation
        # In production, would use proper geodesic distance
        import math
        
        lat_diff = abs(loc1.lat - loc2.lat)
        lon_diff = abs(loc1.lon - loc2.lon)
        
        # Approximate miles per degree
        miles_per_lat = 69.0
        miles_per_lon = 69.0 * math.cos(math.radians(loc1.lat))
        
        distance = math.sqrt(
            (lat_diff * miles_per_lat) ** 2 +
            (lon_diff * miles_per_lon) ** 2
        )
        
        return round(distance, 1)
    
    def _calculate_mortgage_payment(
        self,
        loan_amount: float,
        annual_rate: float,
        years: int
    ) -> float:
        """Calculate monthly mortgage payment."""
        if loan_amount <= 0:
            return 0
        
        monthly_rate = annual_rate / 12
        num_payments = years * 12
        
        if monthly_rate == 0:
            return loan_amount / num_payments
        
        payment = loan_amount * (
            monthly_rate * (1 + monthly_rate) ** num_payments
        ) / (
            (1 + monthly_rate) ** num_payments - 1
        )
        
        return round(payment, 2)
    
    def _calculate_max_loan(
        self,
        max_monthly: float,
        annual_rate: float,
        years: int
    ) -> float:
        """Calculate maximum loan amount from monthly payment."""
        monthly_rate = annual_rate / 12
        num_payments = years * 12
        
        if monthly_rate == 0:
            return max_monthly * num_payments
        
        max_loan = max_monthly * (
            ((1 + monthly_rate) ** num_payments - 1) /
            (monthly_rate * (1 + monthly_rate) ** num_payments)
        )
        
        return round(max_loan, 0)