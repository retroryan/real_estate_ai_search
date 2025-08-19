"""Relevance scoring for Wikipedia pages."""

from typing import List
from .models import WikipediaPage


class RelevanceScorer:
    """Calculate relevance scores for Wikipedia pages."""
    
    def __init__(self, city: str, state: str):
        self.city = city.lower()
        self.state = state.lower()
        
        # Keywords for relevance filtering
        self.must_have_keywords = [self.city, self.state]
        
        # Extended bonus keywords for location relevance
        self.bonus_keywords = [
            'county', 'park', 'monument', 'museum', 'historic',
            'landmark', 'river', 'mountain', 'lake', 'canyon',
            'tourist', 'attraction', 'downtown', 'district', 
            'ski', 'resort', 'utah', 'summit', 'wasatch',
            'sundance', 'film festival', 'mining', 'silver'
        ]
    
    def calculate_score(self, page: WikipediaPage) -> float:
        """Calculate how relevant a page is to the location."""
        score = 0.0
        
        # Use full text if available, otherwise use extract
        text_to_check = page.title.lower() + ' '
        if page.full_text:
            text_to_check += page.full_text.lower()[:5000]
        else:
            text_to_check += page.extract.lower()
        
        # Check for must-have keywords
        for keyword in self.must_have_keywords:
            if keyword in text_to_check:
                score += 10.0
                # Extra points for title matches
                if keyword in page.title.lower():
                    score += 5.0
        
        # Check for bonus keywords
        for keyword in self.bonus_keywords:
            if keyword in text_to_check:
                score += 2.0
                # Extra points for title matches
                if keyword in page.title.lower():
                    score += 3.0
        
        # Check categories for location relevance
        for category in page.categories:
            cat_lower = category.lower()
            if self.state in cat_lower or self.city in cat_lower:
                score += 5.0
            # Check for relevant category keywords
            for keyword in self.bonus_keywords:
                if keyword in cat_lower:
                    score += 1.0
        
        # Bonus for having coordinates (likely a place)
        if page.coordinates:
            score += 3.0
        
        return score
    
    def score_link_title(self, link_title: str) -> float:
        """Quick relevance check on a link title."""
        link_lower = link_title.lower()
        score = 0
        
        # Check for must-have keywords
        for kw in self.must_have_keywords:
            if kw in link_lower:
                score += 10
        
        # Check for bonus keywords
        for kw in self.bonus_keywords:
            if kw in link_lower:
                score += 2
        
        return score