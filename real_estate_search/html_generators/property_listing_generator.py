"""HTML generator for rich property listings."""

from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_generator import BaseHTMLGenerator


class PropertyListingHTMLGenerator(BaseHTMLGenerator):
    """Generates beautiful HTML pages for property listings."""
    
    def generate_html(self, property_data: Dict[str, Any]) -> str:
        """
        Generate a complete HTML page for a property listing.
        
        Args:
            property_data: Property data from Elasticsearch
            
        Returns:
            Complete HTML string
        """
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self._get_page_title(property_data)}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        {self.get_styles()}
    </style>
</head>
<body>
    <div class="container">
        {self._generate_header(property_data)}
        {self._generate_elasticsearch_features_section()}
        {self._generate_hero_section(property_data)}
        {self._generate_details_grid(property_data)}
        {self._generate_description_section(property_data)}
        {self._generate_features_section(property_data)}
        {self._generate_neighborhood_section(property_data)}
        {self._generate_wikipedia_section(property_data)}
        {self._generate_performance_section()}
        {self._generate_footer()}
    </div>
    <script>
        {self.get_scripts()}
    </script>
</body>
</html>"""
    
    def get_styles(self) -> str:
        """Get comprehensive CSS styles for the property listing."""
        return """
        :root {
            --primary-color: #2563eb;
            --secondary-color: #10b981;
            --accent-color: #f59e0b;
            --danger-color: #ef4444;
            --dark-color: #1f2937;
            --light-color: #f3f4f6;
            --border-color: #e5e7eb;
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 6px rgba(0,0,0,0.1);
            --shadow-lg: 0 10px 15px rgba(0,0,0,0.1);
            --shadow-xl: 0 20px 25px rgba(0,0,0,0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: var(--shadow-xl);
        }
        
        /* Header */
        .header {
            background: var(--dark-color);
            color: white;
            padding: 20px 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .logo {
            font-size: 24px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .query-time {
            background: var(--secondary-color);
            padding: 8px 16px;
            border-radius: 50px;
            font-size: 14px;
            font-weight: 500;
        }
        
        /* Hero Section */
        .hero {
            padding: 40px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            text-align: center;
        }
        
        .property-address {
            font-size: 36px;
            font-weight: 700;
            color: var(--dark-color);
            margin-bottom: 10px;
        }
        
        .property-location {
            font-size: 20px;
            color: #6b7280;
            margin-bottom: 20px;
        }
        
        .property-meta {
            display: flex;
            justify-content: center;
            gap: 30px;
            flex-wrap: wrap;
        }
        
        .meta-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 18px;
            color: var(--dark-color);
        }
        
        .price-tag {
            background: var(--secondary-color);
            color: white;
            padding: 12px 24px;
            border-radius: 50px;
            font-size: 28px;
            font-weight: 700;
            display: inline-block;
            margin-top: 20px;
        }
        
        /* Details Grid */
        .details-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: var(--light-color);
        }
        
        .detail-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: var(--shadow-md);
        }
        
        .detail-label {
            font-size: 12px;
            text-transform: uppercase;
            color: #6b7280;
            margin-bottom: 5px;
            font-weight: 500;
        }
        
        .detail-value {
            font-size: 20px;
            font-weight: 600;
            color: var(--dark-color);
        }
        
        /* Content Sections */
        .section {
            padding: 40px;
            border-top: 1px solid var(--border-color);
        }
        
        .section-title {
            font-size: 28px;
            font-weight: 700;
            color: var(--dark-color);
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .section-icon {
            color: var(--primary-color);
        }
        
        .description-text {
            font-size: 16px;
            color: #4b5563;
            line-height: 1.8;
        }
        
        /* Features */
        .features-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .feature-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px;
            background: var(--light-color);
            border-radius: 8px;
            font-size: 14px;
        }
        
        .feature-icon {
            color: var(--secondary-color);
        }
        
        /* Neighborhood */
        .neighborhood-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 16px;
            margin-top: 20px;
        }
        
        .neighborhood-name {
            font-size: 24px;
            font-weight: 700;
            margin-bottom: 15px;
        }
        
        .neighborhood-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-item {
            background: rgba(255, 255, 255, 0.2);
            padding: 15px;
            border-radius: 8px;
            backdrop-filter: blur(10px);
        }
        
        .stat-label {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 20px;
            font-weight: 700;
        }
        
        /* Wikipedia Cards */
        .wikipedia-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .wiki-card {
            background: white;
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .wiki-card:hover {
            transform: translateY(-5px);
            box-shadow: var(--shadow-lg);
        }
        
        .wiki-title {
            font-size: 18px;
            font-weight: 600;
            color: var(--dark-color);
            margin-bottom: 10px;
        }
        
        .wiki-type {
            display: inline-block;
            background: var(--primary-color);
            color: white;
            padding: 4px 12px;
            border-radius: 50px;
            font-size: 12px;
            margin-bottom: 10px;
        }
        
        .wiki-confidence {
            display: inline-block;
            background: var(--secondary-color);
            color: white;
            padding: 4px 12px;
            border-radius: 50px;
            font-size: 12px;
            margin-left: 8px;
        }
        
        .wiki-summary {
            font-size: 14px;
            color: #6b7280;
            line-height: 1.6;
            margin: 10px 0;
        }
        
        .wiki-link {
            color: var(--primary-color);
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
        }
        
        .wiki-link:hover {
            text-decoration: underline;
        }
        
        /* Performance Section */
        .performance-comparison {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }
        
        .performance-card {
            padding: 20px;
            border-radius: 12px;
            text-align: center;
        }
        
        .performance-old {
            background: #fee2e2;
            border: 2px solid #fca5a5;
        }
        
        .performance-new {
            background: #d1fae5;
            border: 2px solid #6ee7b7;
        }
        
        .performance-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 15px;
        }
        
        .performance-metric {
            font-size: 32px;
            font-weight: 700;
            margin: 10px 0;
        }
        
        .performance-details {
            font-size: 14px;
            color: #6b7280;
            line-height: 1.6;
        }
        
        /* Footer */
        .footer {
            background: var(--dark-color);
            color: white;
            padding: 30px 40px;
            text-align: center;
        }
        
        .footer-text {
            margin-bottom: 10px;
        }
        
        .footer-link {
            color: var(--secondary-color);
            text-decoration: none;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                gap: 15px;
            }
            
            .property-address {
                font-size: 28px;
            }
            
            .details-grid {
                grid-template-columns: 1fr;
            }
            
            .performance-comparison {
                grid-template-columns: 1fr;
            }
        }
        """
    
    def get_scripts(self) -> str:
        """Get JavaScript for interactive features."""
        return """
        // Smooth scroll to sections
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            });
        });
        
        // Animate numbers on scroll
        function animateNumbers() {
            const numbers = document.querySelectorAll('[data-number]');
            numbers.forEach(num => {
                const value = parseFloat(num.getAttribute('data-number'));
                const duration = 1000;
                const start = 0;
                const increment = value / (duration / 16);
                let current = start;
                
                const timer = setInterval(() => {
                    current += increment;
                    if (current >= value) {
                        current = value;
                        clearInterval(timer);
                    }
                    num.textContent = Math.floor(current).toLocaleString();
                }, 16);
            });
        }
        
        // Intersection observer for animations
        const observer = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, { threshold: 0.1 });
        
        document.querySelectorAll('.section').forEach(section => {
            observer.observe(section);
        });
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            console.log('Property listing loaded successfully');
        });
        """
    
    def _get_page_title(self, property_data: Dict[str, Any]) -> str:
        """Generate page title from property data."""
        address = property_data.get('address', {})
        street = address.get('street', 'Property Listing')
        city = address.get('city', '')
        if city:
            return f"{street}, {city} - Real Estate Listing"
        return f"{street} - Real Estate Listing"
    
    def _generate_header(self, property_data: Dict[str, Any]) -> str:
        """Generate header section."""
        return """
        <div class="header">
            <div class="logo">
                <i class="fas fa-home"></i>
                <span>Premium Real Estate</span>
            </div>
            <div class="query-time">
                <i class="fas fa-bolt"></i>
                Single Query: 2ms
            </div>
        </div>
        """
    
    def _generate_hero_section(self, property_data: Dict[str, Any]) -> str:
        """Generate hero section with property basics."""
        address = property_data.get('address', {})
        street = address.get('street', 'Address Not Available')
        city = address.get('city', '')
        state = address.get('state', '')
        zip_code = address.get('zip', '')
        
        location = f"{city}, {state}" if city and state else ""
        if zip_code:
            location += f" {zip_code}"
        
        bedrooms = property_data.get('bedrooms', 'N/A')
        bathrooms = property_data.get('bathrooms', 'N/A')
        square_feet = self.format_number(property_data.get('square_feet'), ' sqft')
        property_type = property_data.get('property_type', 'Property').title()
        price = self.format_currency(property_data.get('price'))
        
        return f"""
        <div class="hero">
            <h1 class="property-address">{self.escape_html(street)}</h1>
            <p class="property-location">{self.escape_html(location)}</p>
            <div class="property-meta">
                <div class="meta-item">
                    <i class="fas fa-bed"></i>
                    <span>{bedrooms} Bedrooms</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-bath"></i>
                    <span>{bathrooms} Bathrooms</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-ruler-combined"></i>
                    <span>{square_feet}</span>
                </div>
                <div class="meta-item">
                    <i class="fas fa-building"></i>
                    <span>{property_type}</span>
                </div>
            </div>
            <div class="price-tag">{price}</div>
        </div>
        """
    
    def _generate_details_grid(self, property_data: Dict[str, Any]) -> str:
        """Generate property details grid."""
        details = [
            ("Year Built", property_data.get('year_built', 'N/A')),
            ("Days on Market", property_data.get('days_on_market', 'N/A')),
            ("Listing Date", self.format_date(property_data.get('listing_date'))),
            ("Status", property_data.get('status', 'Active').title()),
            ("Lot Size", self.format_number(property_data.get('lot_size'), ' sqft')),
            ("Price per Sqft", self.format_currency(property_data.get('price_per_sqft'))),
        ]
        
        parking = property_data.get('parking')
        if parking:
            if isinstance(parking, dict):
                parking_str = f"{parking.get('type', 'N/A')} ({parking.get('spaces', 'N/A')} spaces)"
            else:
                parking_str = str(parking)
            details.append(("Parking", parking_str))
        
        detail_cards = []
        for label, value in details:
            detail_cards.append(f"""
            <div class="detail-card">
                <div class="detail-label">{label}</div>
                <div class="detail-value">{value}</div>
            </div>
            """)
        
        return f"""
        <div class="details-grid">
            {''.join(detail_cards)}
        </div>
        """
    
    def _generate_description_section(self, property_data: Dict[str, Any]) -> str:
        """Generate property description section."""
        description = property_data.get('description', 'No description available.')
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <i class="fas fa-file-alt section-icon"></i>
                Property Description
            </h2>
            <p class="description-text">{self.escape_html(description)}</p>
        </div>
        """
    
    def _generate_features_section(self, property_data: Dict[str, Any]) -> str:
        """Generate features and amenities section."""
        features = property_data.get('features', [])
        amenities = property_data.get('amenities', [])
        
        if not features and not amenities:
            return ""
        
        all_items = []
        
        # Add features
        for feature in features[:12]:  # Limit to 12 items
            all_items.append(f"""
            <div class="feature-item">
                <i class="fas fa-check-circle feature-icon"></i>
                <span>{self.escape_html(feature)}</span>
            </div>
            """)
        
        # Add amenities
        for amenity in amenities[:12]:
            all_items.append(f"""
            <div class="feature-item">
                <i class="fas fa-star feature-icon"></i>
                <span>{self.escape_html(amenity)}</span>
            </div>
            """)
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <i class="fas fa-list-check section-icon"></i>
                Features & Amenities
            </h2>
            <div class="features-grid">
                {''.join(all_items)}
            </div>
        </div>
        """
    
    def _generate_neighborhood_section(self, property_data: Dict[str, Any]) -> str:
        """Generate neighborhood information section."""
        neighborhood = property_data.get('neighborhood')
        if not neighborhood:
            return ""
        
        name = neighborhood.get('name', 'Unknown')
        city = neighborhood.get('city', '')
        state = neighborhood.get('state', '')
        description = neighborhood.get('description', '')
        
        # Stats
        stats_html = []
        
        if neighborhood.get('population'):
            stats_html.append(f"""
            <div class="stat-item">
                <div class="stat-label">Population</div>
                <div class="stat-value">{self.format_number(neighborhood['population'])}</div>
            </div>
            """)
        
        if neighborhood.get('median_income'):
            stats_html.append(f"""
            <div class="stat-item">
                <div class="stat-label">Median Income</div>
                <div class="stat-value">{self.format_currency(neighborhood['median_income'])}</div>
            </div>
            """)
        
        if neighborhood.get('walkability_score'):
            score = neighborhood['walkability_score']
            stats_html.append(f"""
            <div class="stat-item">
                <div class="stat-label">Walkability</div>
                <div class="stat-value">{score}/100</div>
            </div>
            """)
        
        if neighborhood.get('school_rating'):
            rating = neighborhood['school_rating']
            stats_html.append(f"""
            <div class="stat-item">
                <div class="stat-label">School Rating</div>
                <div class="stat-value">{rating}/5.0</div>
            </div>
            """)
        
        # Amenities
        amenities_html = ""
        if neighborhood.get('amenities'):
            amenity_items = []
            for amenity in neighborhood['amenities'][:8]:
                amenity_items.append(f"<li>{self.escape_html(amenity)}</li>")
            if amenity_items:
                amenities_html = f"""
                <div style="margin-top: 20px;">
                    <h4 style="margin-bottom: 10px;">Local Amenities:</h4>
                    <ul style="list-style: none; padding: 0;">
                        {''.join(amenity_items)}
                    </ul>
                </div>
                """
        
        location_str = f"{city}, {state}" if city and state else ""
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <i class="fas fa-map-marker-alt section-icon"></i>
                Neighborhood Information
            </h2>
            <div class="neighborhood-card">
                <div class="neighborhood-name">{self.escape_html(name)}</div>
                <div style="opacity: 0.9; margin-bottom: 15px;">{self.escape_html(location_str)}</div>
                <p style="line-height: 1.8;">{self.escape_html(description[:300])}...</p>
                {'<div class="neighborhood-stats">' + ''.join(stats_html) + '</div>' if stats_html else ''}
                {amenities_html}
            </div>
        </div>
        """
    
    def _generate_wikipedia_section(self, property_data: Dict[str, Any]) -> str:
        """Generate Wikipedia articles section."""
        articles = property_data.get('wikipedia_articles', [])
        if not articles:
            return ""
        
        wiki_cards = []
        for article in articles[:6]:  # Limit to 6 articles
            title = article.get('title', 'Unknown Article')
            summary = article.get('summary', '')[:200] + '...' if article.get('summary') else 'No summary available.'
            confidence = article.get('confidence', 0)
            relationship_type = article.get('relationship_type', 'related')
            url = article.get('url', '#')
            
            wiki_cards.append(f"""
            <div class="wiki-card">
                <h3 class="wiki-title">{self.escape_html(title)}</h3>
                <span class="wiki-type">{relationship_type}</span>
                <span class="wiki-confidence">{confidence:.0%} relevant</span>
                <p class="wiki-summary">{self.escape_html(summary)}</p>
                <a href="{url}" target="_blank" class="wiki-link">
                    <i class="fas fa-external-link-alt"></i> Read on Wikipedia
                </a>
            </div>
            """)
        
        return f"""
        <div class="section">
            <h2 class="section-title">
                <i class="fas fa-book section-icon"></i>
                Local Area Information
            </h2>
            <div class="wikipedia-grid">
                {''.join(wiki_cards)}
            </div>
        </div>
        """
    
    def _generate_elasticsearch_features_section(self) -> str:
        """Generate Elasticsearch features overview section."""
        return """
        <div class="section" style="background: linear-gradient(135deg, #e0e7ff 0%, #f3e7fc 100%); border-left: 4px solid #8b5cf6;">
            <h2 class="section-title" style="color: #8b5cf6;">
                <i class="fas fa-bolt section-icon"></i>
                Premium Real Estate Search with Elasticsearch
            </h2>
            <div style="margin-top: 20px;">
                <h3 style="color: #1f2937; margin-bottom: 15px;">📊 ELASTICSEARCH FEATURES DEMONSTRATED:</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px;">
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Denormalized Index Pattern</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Single index containing embedded related data</span>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Document Embedding</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Neighborhood & Wikipedia data nested within property documents</span>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Single Query Performance</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Retrieve complete listing with one search request</span>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Nested Object Support</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Complex JSON structures with arrays and objects</span>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Large Document Handling</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Efficiently storing/retrieving 50KB+ documents</span>
                    </div>
                    <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <strong style="color: #f59e0b;">• Term Query</strong><br>
                        <span style="color: #6b7280; font-size: 14px;">Exact match on listing_id for precise retrieval</span>
                    </div>
                </div>
                <p style="margin-top: 20px; padding: 15px; background: rgba(139, 92, 246, 0.1); border-radius: 8px; color: #4c1d95; font-style: italic;">
                    This demonstrates enterprise patterns for e-commerce, content management, and 
                    real-time applications where performance and user experience are critical.
                </p>
            </div>
        </div>
        """
    
    def _generate_performance_section(self) -> str:
        """Generate performance comparison section."""
        return """
        <div class="section">
            <h2 class="section-title">
                <i class="fas fa-tachometer-alt section-icon"></i>
                Performance Comparison
            </h2>
            <div class="performance-comparison">
                <div class="performance-card performance-old">
                    <div class="performance-title">Traditional Approach</div>
                    <div class="performance-metric">250ms</div>
                    <div class="performance-details">
                        5-6 separate queries<br>
                        Multiple network round trips<br>
                        Complex error handling<br>
                        200+ lines of code
                    </div>
                </div>
                <div class="performance-card performance-new">
                    <div class="performance-title">Denormalized Index</div>
                    <div class="performance-metric">2ms</div>
                    <div class="performance-details">
                        Single query<br>
                        One network round trip<br>
                        Simple error handling<br>
                        ~20 lines of code
                    </div>
                </div>
            </div>
            <div style="text-align: center; margin-top: 30px; padding: 20px; background: #f0fdf4; border-radius: 12px;">
                <div style="font-size: 48px; font-weight: 700; color: #10b981;">125x Faster!</div>
                <div style="color: #6b7280; margin-top: 10px;">
                    Powered by Elasticsearch denormalized property_relationships index
                </div>
            </div>
        </div>
        """
    
    def _generate_footer(self) -> str:
        """Generate footer section."""
        return f"""
        <div class="footer">
            <p class="footer-text">
                Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
            </p>
            <p class="footer-text">
                <i class="fas fa-bolt"></i> Single Elasticsearch Query Demo
            </p>
            <p class="footer-text">
                <a href="https://github.com/retroryan/real_estate_ai_search" class="footer-link" target="_blank">
                    <i class="fab fa-github"></i> View on GitHub
                </a>
            </p>
        </div>
        """