"""
Analysis and comparison models.
Models for property analysis, market positioning, and comparisons.
"""

from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from .property import Property
from .enrichment import MarketContext, NeighborhoodContext, WikipediaContext


class InvestmentGrade(str, Enum):
    """Investment grade ratings."""
    excellent = "A+"
    very_good = "A"
    good = "B+"
    above_average = "B"
    average = "C"
    below_average = "D"
    poor = "F"


class MarketPosition(BaseModel):
    """Property's position in the market."""
    
    price_percentile: float = Field(..., ge=0, le=100, description="Price percentile in market")
    price_vs_median: float = Field(..., description="Percentage vs median price")
    price_per_sqft: Optional[float] = Field(None, gt=0, description="Price per square foot")
    price_per_sqft_percentile: Optional[float] = Field(None, ge=0, le=100, description="Price/sqft percentile")
    competitive_properties: int = Field(..., ge=0, description="Number of competing properties")
    days_on_market_estimate: Optional[int] = Field(None, ge=0, description="Estimated days to sell")
    pricing_recommendation: str = Field(..., description="Pricing strategy recommendation")
    similar_sold_count: int = Field(0, ge=0, description="Similar properties sold recently")
    average_similar_price: Optional[float] = Field(None, gt=0, description="Average price of similar properties")
    
    def get_pricing_summary(self) -> str:
        """Get pricing position summary."""
        if self.price_percentile < 25:
            position = "Lower quartile"
        elif self.price_percentile < 50:
            position = "Below median"
        elif self.price_percentile < 75:
            position = "Above median"
        else:
            position = "Upper quartile"
        
        return f"{position} ({self.price_percentile:.0f}th percentile) - {self.pricing_recommendation}"


class InvestmentMetrics(BaseModel):
    """Investment analysis metrics."""
    
    estimated_rent: Optional[float] = Field(None, gt=0, description="Estimated monthly rent")
    gross_yield: Optional[float] = Field(None, ge=0, description="Gross rental yield %")
    cap_rate: Optional[float] = Field(None, description="Capitalization rate %")
    cash_flow: Optional[float] = Field(None, description="Monthly cash flow estimate")
    price_to_rent_ratio: Optional[float] = Field(None, gt=0, description="Price to rent ratio")
    investment_grade: InvestmentGrade = Field(..., description="Investment grade")
    investment_score: float = Field(..., ge=0, le=100, description="Investment score")
    roi_1_year: Optional[float] = Field(None, description="1-year ROI estimate %")
    roi_5_year: Optional[float] = Field(None, description="5-year ROI estimate %")
    break_even_years: Optional[float] = Field(None, gt=0, description="Years to break even")
    
    def get_investment_summary(self) -> str:
        """Get investment summary."""
        parts = [f"Grade: {self.investment_grade}"]
        if self.gross_yield:
            parts.append(f"Yield: {self.gross_yield:.1f}%")
        if self.cap_rate:
            parts.append(f"Cap: {self.cap_rate:.1f}%")
        return " | ".join(parts)


class ComparableProperty(BaseModel):
    """Comparable property for analysis."""
    
    property: Property = Field(..., description="Comparable property")
    similarity_score: float = Field(..., ge=0, le=1, description="Similarity score")
    price_difference: float = Field(..., description="Price difference")
    price_per_sqft_difference: Optional[float] = Field(None, description="Price/sqft difference")
    distance_miles: Optional[float] = Field(None, ge=0, description="Distance from subject")
    sold_date: Optional[datetime] = Field(None, description="Sale date if sold")
    days_on_market: Optional[int] = Field(None, ge=0, description="Days on market")
    
    def get_comparison_summary(self) -> str:
        """Get comparison summary."""
        diff_pct = (self.price_difference / self.property.price) * 100
        direction = "higher" if self.price_difference > 0 else "lower"
        return f"{abs(diff_pct):.1f}% {direction} - Score: {self.similarity_score:.2f}"


class PropertyAnalysis(BaseModel):
    """Comprehensive property analysis."""
    
    property: Property = Field(..., description="Subject property")
    market_position: MarketPosition = Field(..., description="Market positioning")
    investment_metrics: InvestmentMetrics = Field(..., description="Investment analysis")
    comparable_properties: List[ComparableProperty] = Field(default_factory=list, description="Comparables")
    neighborhood_analysis: Optional[NeighborhoodContext] = Field(None, description="Neighborhood data")
    market_context: Optional[MarketContext] = Field(None, description="Market conditions")
    wikipedia_context: Optional[WikipediaContext] = Field(None, description="Location context")
    strengths: List[str] = Field(default_factory=list, description="Property strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Property weaknesses")
    opportunities: List[str] = Field(default_factory=list, description="Market opportunities")
    risks: List[str] = Field(default_factory=list, description="Investment risks")
    overall_recommendation: str = Field(..., description="Overall recommendation")
    confidence_score: float = Field(..., ge=0, le=1, description="Analysis confidence")
    
    def get_swot_summary(self) -> Dict[str, List[str]]:
        """Get SWOT analysis summary."""
        return {
            "strengths": self.strengths[:3],  # Top 3
            "weaknesses": self.weaknesses[:3],
            "opportunities": self.opportunities[:3],
            "risks": self.risks[:3]
        }


class PropertyComparison(BaseModel):
    """Multi-property comparison results."""
    
    properties: List[Property] = Field(..., min_length=2, description="Properties to compare")
    comparison_metrics: Dict[str, Dict[str, Any]] = Field(..., description="Comparison metrics")
    price_comparison: Dict[str, Any] = Field(..., description="Price comparison data")
    feature_comparison: Dict[str, List[str]] = Field(..., description="Feature comparison")
    location_comparison: Dict[str, Any] = Field(..., description="Location comparison")
    investment_comparison: Optional[Dict[str, InvestmentMetrics]] = Field(None, description="Investment metrics")
    best_value_id: Optional[str] = Field(None, description="Best value property ID")
    best_investment_id: Optional[str] = Field(None, description="Best investment property ID")
    best_location_id: Optional[str] = Field(None, description="Best location property ID")
    recommendation: str = Field(..., description="Comparison recommendation")
    comparison_summary: Dict[str, str] = Field(..., description="Summary for each property")
    
    def get_winner_summary(self) -> str:
        """Get summary of best properties."""
        winners = []
        if self.best_value_id:
            winners.append(f"Value: Property {self.best_value_id}")
        if self.best_investment_id:
            winners.append(f"Investment: Property {self.best_investment_id}")
        if self.best_location_id:
            winners.append(f"Location: Property {self.best_location_id}")
        return " | ".join(winners) if winners else "No clear winner"


class AffordabilityAnalysis(BaseModel):
    """Affordability and financing analysis."""
    
    property_id: str = Field(..., description="Property ID")
    property_price: float = Field(..., gt=0, description="Property price")
    annual_income: float = Field(..., gt=0, description="Annual household income")
    down_payment: float = Field(..., ge=0, description="Available down payment")
    down_payment_percent: float = Field(..., ge=0, le=100, description="Down payment percentage")
    loan_amount: float = Field(..., ge=0, description="Loan amount needed")
    interest_rate: float = Field(..., gt=0, description="Interest rate")
    loan_term_years: int = Field(30, gt=0, description="Loan term in years")
    monthly_payment: float = Field(..., ge=0, description="Monthly mortgage payment")
    property_tax_monthly: float = Field(..., ge=0, description="Monthly property tax")
    insurance_monthly: float = Field(..., ge=0, description="Monthly insurance")
    hoa_monthly: Optional[float] = Field(None, ge=0, description="Monthly HOA fees")
    total_monthly: float = Field(..., ge=0, description="Total monthly payment")
    income_ratio: float = Field(..., ge=0, description="Payment to income ratio")
    debt_to_income: Optional[float] = Field(None, ge=0, le=100, description="Debt-to-income ratio")
    affordable: bool = Field(..., description="Is property affordable")
    affordability_score: float = Field(..., ge=0, le=100, description="Affordability score")
    max_affordable_price: float = Field(..., ge=0, description="Maximum affordable price")
    additional_down_needed: float = Field(..., ge=0, description="Additional down payment needed")
    income_needed: float = Field(..., ge=0, description="Income needed for approval")
    
    @field_validator("income_ratio")
    @classmethod
    def calculate_affordability(cls, v: float) -> float:
        """Validate income ratio is reasonable."""
        if v > 0.5:  # More than 50% of income
            raise ValueError("Payment exceeds 50% of monthly income")
        return v
    
    def get_affordability_summary(self) -> str:
        """Get affordability summary."""
        if self.affordable:
            return f"Affordable - {self.income_ratio*100:.1f}% of income (Score: {self.affordability_score:.0f})"
        else:
            if self.additional_down_needed > 0:
                return f"Need ${self.additional_down_needed:,.0f} more down payment"
            else:
                return f"Need ${self.income_needed - self.annual_income:,.0f} more annual income"


class CommuteAnalysis(BaseModel):
    """Commute analysis from property to destination."""
    
    property_id: str = Field(..., description="Property ID")
    destination_address: str = Field(..., description="Destination address")
    driving_time_minutes: Optional[int] = Field(None, ge=0, description="Driving time in minutes")
    driving_distance_miles: Optional[float] = Field(None, ge=0, description="Driving distance")
    transit_time_minutes: Optional[int] = Field(None, ge=0, description="Transit time in minutes")
    walking_time_minutes: Optional[int] = Field(None, ge=0, description="Walking time in minutes")
    cycling_time_minutes: Optional[int] = Field(None, ge=0, description="Cycling time in minutes")
    traffic_typical: Optional[str] = Field(None, description="Typical traffic conditions")
    transit_options: List[str] = Field(default_factory=list, description="Available transit options")
    commute_score: float = Field(..., ge=0, le=100, description="Overall commute score")
    recommended_mode: str = Field(..., description="Recommended commute mode")
    
    def get_commute_summary(self) -> str:
        """Get commute summary."""
        if self.driving_time_minutes:
            return f"{self.driving_time_minutes} min drive ({self.driving_distance_miles:.1f} mi) - Score: {self.commute_score:.0f}"
        elif self.transit_time_minutes:
            return f"{self.transit_time_minutes} min transit - Score: {self.commute_score:.0f}"
        else:
            return f"Commute data unavailable"