"""
Relevance scoring models shared across the application.
Separated to avoid circular imports.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RelevanceScore:
    """Detailed relevance scoring for an article."""
    article_id: int
    title: str
    location_relevance: float = 0.0  # 0-1 score for location match
    real_estate_relevance: float = 0.0  # 0-1 score for RE relevance
    geographic_scope: float = 0.0  # 0-1 score for geographic appropriateness
    overall_score: float = 0.0
    is_relevant: bool = False
    reasons_to_flag: list[str] = field(default_factory=list)
    reasons_to_keep: list[str] = field(default_factory=list)
    
    def calculate_overall(self):
        """Calculate overall relevance score."""
        self.overall_score = (
            0.4 * self.location_relevance +
            0.4 * self.real_estate_relevance +
            0.2 * self.geographic_scope
        )
        # Article is relevant if score > 0.5 and no critical flags
        self.is_relevant = (
            self.overall_score >= 0.5 and 
            not any("critical" in r.lower() for r in self.reasons_to_flag)
        )