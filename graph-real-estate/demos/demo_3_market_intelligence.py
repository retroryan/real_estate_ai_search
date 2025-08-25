#!/usr/bin/env python3
"""
Advanced Market Intelligence Demo

This demonstration showcases the sophisticated market analysis capabilities
achievable by combining Neo4j graph database relationships with vector 
embeddings for real estate market intelligence.

The demo explores six key areas of market intelligence:
1. Geographic Market Analysis - Comprehensive city and neighborhood analysis
2. Price Prediction & Trends - Feature-based pricing intelligence  
3. Investment Opportunity Discovery - ROI and market gap analysis
4. Lifestyle Market Segmentation - Demographic and preference analysis
5. Feature Impact Analysis - Quantifying feature value and correlations
6. Competitive Market Intelligence - Property positioning and market dynamics

This represents the power of graph databases for complex market analytics
that would be extremely difficult with traditional relational databases.
"""

import sys
import signal
from pathlib import Path
from typing import Dict, List, Any, Tuple
import json

# Handle broken pipe errors gracefully when piping output
if hasattr(signal, 'SIGPIPE'):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Add src to path
sys.path.append(str(Path(__file__).parent))

from database import get_neo4j_driver
from database.neo4j_client import run_query
from vectors import PropertyEmbeddingPipeline, HybridPropertySearch
from vectors.config_loader import get_embedding_config, get_vector_index_config, get_search_config


class MarketIntelligenceAnalyzer:
    """Advanced market intelligence using graph relationships and vector embeddings"""
    
    def __init__(self, driver):
        self.driver = driver
        
        # Initialize search capabilities
        try:
            embedding_config = get_embedding_config()
            vector_config = get_vector_index_config()
            search_config = get_search_config()
            
            # Clean initialization - embedding config handles model selection
            self.pipeline = PropertyEmbeddingPipeline(driver, embedding_config)
            self.search = HybridPropertySearch(driver, self.pipeline, search_config)
            
            # Check embeddings availability
            status = self.pipeline.vector_manager.check_embeddings_exist()
            self.embeddings_available = status['with_embeddings'] > 0
            if not self.embeddings_available:
                print("Some demos require embeddings. Run 'python create_embeddings.py' for full functionality.")
        except Exception as e:
            print(f"Vector search not available: {e}")
            self.embeddings_available = False

    def print_section_header(self, title: str, description: str = ""):
        """Print formatted section header"""
        print(f"\n{'='*80}")
        print(f"{title.upper()}")
        print(f"{'='*80}")
        if description:
            print(f"{description}\n")

    def print_subsection(self, title: str):
        """Print formatted subsection"""
        print(f"\n{title}")
        print("-" * 60)

    # ===== SECTION 1: GEOGRAPHIC MARKET ANALYSIS =====
    
    def geographic_market_analysis(self):
        """Comprehensive geographic market analysis with graph intelligence"""
        self.print_section_header(
            "Geographic Market Analysis",
            "Analyzing market dynamics across cities and neighborhoods using graph relationships"
        )
        
        # City-level market overview
        self.print_subsection("City Market Overview")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n.city as City, 
             count(DISTINCT n) as Neighborhoods,
             count(p) as Properties,
             avg(p.listing_price) as AvgPrice,
             min(p.listing_price) as MinPrice,
             max(p.listing_price) as MaxPrice,
             collect(DISTINCT p.property_type) as PropertyTypes
        RETURN City, Neighborhoods, Properties, AvgPrice, MinPrice, MaxPrice, PropertyTypes
        ORDER BY Properties DESC
        """
        results = run_query(self.driver, query)
        
        for r in results:
            print(f"{r['City']}")
            print(f"   Properties: {r['Properties']} across {r['Neighborhoods']} neighborhoods")
            print(f"   Price Range: ${r['MinPrice']:,.0f} - ${r['MaxPrice']:,.0f}")
            print(f"   Average Price: ${r['AvgPrice']:,.0f}")
            print(f"   Property Types: {', '.join(r['PropertyTypes'])}")
        
        # Neighborhood market segmentation
        self.print_subsection("Neighborhood Market Segmentation")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n,
             count(p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             avg(p.square_feet) as AvgSqft,
             collect(DISTINCT p.property_type) as PropertyTypes
        WHERE PropertyCount >= 5
        WITH n, PropertyCount, AvgPrice, AvgSqft, PropertyTypes,
             CASE 
                WHEN AvgPrice > 8000000 THEN 'Ultra-Luxury'
                WHEN AvgPrice > 3000000 THEN 'Luxury' 
                WHEN AvgPrice > 1500000 THEN 'Premium'
                WHEN AvgPrice > 800000 THEN 'Mid-Market'
                ELSE 'Affordable'
             END as MarketSegment
        RETURN n.city as City, n.name as Neighborhood, MarketSegment,
               PropertyCount, AvgPrice, AvgSqft, PropertyTypes,
               n.lifestyle_tags as LifestyleTags
        ORDER BY AvgPrice DESC
        LIMIT 15
        """
        results = run_query(self.driver, query)
        
        for r in results:
            print(f"{r['Neighborhood']}, {r['City']} [{r['MarketSegment']}]")
            print(f"   Average: ${r['AvgPrice']:,.0f} | {r['PropertyCount']} properties | {r['AvgSqft']:.0f} sqft avg")
            if r['LifestyleTags']:
                print(f"   Lifestyle: {', '.join(r['LifestyleTags'])}")
            print(f"   Types: {', '.join(r['PropertyTypes'])}")

        # Geographic arbitrage opportunities
        self.print_subsection("Geographic Arbitrage Analysis")
        query = """
        MATCH (p1:Property)-[:LOCATED_IN]->(n1:Neighborhood),
              (p2:Property)-[:LOCATED_IN]->(n2:Neighborhood)
        WHERE n1 <> n2 AND n1.city = n2.city AND p1.square_feet > 0 AND p2.square_feet > 0
        WITH n1.name as Neighborhood1, n2.name as Neighborhood2, n1.city as City,
             avg(p1.listing_price / p1.square_feet) as PricePerSqft1,
             avg(p2.listing_price / p2.square_feet) as PricePerSqft2,
             count(p1) as Properties1, count(p2) as Properties2
        WHERE Properties1 >= 3 AND Properties2 >= 3
        WITH *, abs(PricePerSqft1 - PricePerSqft2) as PriceDelta,
             (PricePerSqft1 - PricePerSqft2) / ((PricePerSqft1 + PricePerSqft2) / 2) * 100 as PercentDiff
        WHERE abs(PercentDiff) > 30
        RETURN City, Neighborhood1, Neighborhood2, 
               PricePerSqft1, PricePerSqft2, PercentDiff as ArbitragePercent
        ORDER BY abs(PercentDiff) DESC
        LIMIT 10
        """
        results = run_query(self.driver, query)
        
        print("Top Geographic Arbitrage Opportunities:")
        for r in results:
            direction = "" if r['ArbitragePercent'] > 0 else ""
            print(f"{direction} {r['City']}: {r['Neighborhood1']} vs {r['Neighborhood2']}")
            print(f"   ${r['PricePerSqft1']:.0f}/sqft vs ${r['PricePerSqft2']:.0f}/sqft")
            print(f"   Arbitrage Opportunity: {abs(r['ArbitragePercent']):.1f}% difference")

    # ===== SECTION 2: PRICE PREDICTION & TRENDS =====
    
    def price_prediction_analysis(self):
        """Advanced price prediction using feature correlations and graph patterns"""
        self.print_section_header(
            "Price Prediction & Trends Analysis", 
            "Using graph relationships to understand pricing patterns and predict values"
        )
        
        # Feature-based price correlation analysis
        self.print_subsection("Feature Value Impact Analysis")
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH f.name as Feature, f.category as Category,
             count(p) as PropertyCount,
             avg(p.listing_price) as AvgPriceWithFeature,
             collect(p.listing_price) as Prices
        WHERE PropertyCount >= 5
        
        // Calculate baseline price (properties without this feature)
        MATCH (p2:Property)
        WHERE NOT (p2)-[:HAS_FEATURE]->(:Feature {name: Feature})
        WITH Feature, Category, PropertyCount, AvgPriceWithFeature, Prices,
             avg(p2.listing_price) as BaselinePrice, count(p2) as BaselineCount
        WHERE BaselineCount >= 10
        
        WITH *, (AvgPriceWithFeature - BaselinePrice) as PricePremium,
             (AvgPriceWithFeature - BaselinePrice) / BaselinePrice * 100 as PremiumPercent
        
        RETURN Feature, Category, PropertyCount, 
               AvgPriceWithFeature, BaselinePrice, PricePremium, PremiumPercent
        ORDER BY PremiumPercent DESC
        LIMIT 15
        """
        results = run_query(self.driver, query)
        
        print("Top Value-Adding Features:")
        for r in results:
            premium_indicator = "" if r['PremiumPercent'] > 50 else "" if r['PremiumPercent'] > 20 else ""
            print(f"{premium_indicator} {r['Feature']} [{r['Category']}]")
            print(f"   Premium: ${r['PricePremium']:,.0f} (+{r['PremiumPercent']:.1f}%)")
            print(f"   With feature: ${r['AvgPriceWithFeature']:,.0f} | Baseline: ${r['BaselinePrice']:,.0f}")
            print(f"   Market penetration: {r['PropertyCount']} properties")

        # Property type pricing intelligence
        self.print_subsection("Property Type Market Analysis")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH p.property_type as PropertyType, n.city as City,
             count(p) as Count,
             avg(p.listing_price) as AvgPrice,
             min(p.listing_price) as MinPrice,
             max(p.listing_price) as MaxPrice,
             avg(p.listing_price / CASE WHEN p.square_feet > 0 THEN p.square_feet ELSE 1 END) as PricePerSqft
        WHERE Count >= 3
        RETURN PropertyType, City, Count, AvgPrice, MinPrice, MaxPrice, PricePerSqft
        ORDER BY PropertyType, AvgPrice DESC
        """
        results = run_query(self.driver, query)
        
        current_type = None
        for r in results:
            if r['PropertyType'] != current_type:
                current_type = r['PropertyType']
                print(f"\n{current_type.upper()}")
            
            print(f"   {r['City']}: ${r['AvgPrice']:,.0f} avg | ${r['PricePerSqft']:.0f}/sqft | {r['Count']} properties")
            print(f"      Range: ${r['MinPrice']:,.0f} - ${r['MaxPrice']:,.0f}")

        # Pricing anomaly detection
        self.print_subsection("Pricing Anomaly Detection")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n, 
             collect(p) as Properties,
             avg(p.listing_price) as NeighborhoodAvg,
             stdev(p.listing_price) as PriceStdDev
        WHERE size(Properties) >= 5 AND PriceStdDev > 0
        
        UNWIND Properties as prop
        WITH prop, n, NeighborhoodAvg, PriceStdDev,
             abs(prop.listing_price - NeighborhoodAvg) / PriceStdDev as ZScore
        WHERE ZScore > 2.0  // Statistical outliers
        
        MATCH (prop)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)
        OPTIONAL MATCH (prop)-[:HAS_FEATURE]->(f:Feature)
        
        RETURN prop.listing_id as PropertyID, prop.listing_price as Price,
               NeighborhoodAvg, ZScore, n.city + ", " + n.name as Location,
               collect(DISTINCT f.name)[0..5] as TopFeatures,
               CASE WHEN prop.listing_price > NeighborhoodAvg THEN 'OVERPRICED' ELSE 'UNDERPRICED' END as Anomaly
        ORDER BY ZScore DESC
        LIMIT 10
        """
        results = run_query(self.driver, query)
        
        print("Price Anomalies (Statistical Outliers):")
        for r in results:
            anomaly_icon = "" if r['Anomaly'] == 'OVERPRICED' else ""
            print(f"{anomaly_icon} Property {r['PropertyID']} - {r['Anomaly']}")
            print(f"   Price: ${r['Price']:,.0f} | Neighborhood Avg: ${r['NeighborhoodAvg']:,.0f}")
            print(f"   Statistical Z-Score: {r['ZScore']:.2f} | Location: {r['Location']}")
            print(f"   Features: {', '.join(r['TopFeatures'])}")

    # ===== SECTION 3: INVESTMENT OPPORTUNITY DISCOVERY =====
    
    def investment_opportunity_analysis(self):
        """Discover investment opportunities using graph-based market intelligence"""
        self.print_section_header(
            "Investment Opportunity Discovery",
            "Identifying investment opportunities through relationship pattern analysis"
        )
        
        # Undervalued market segments
        self.print_subsection("Undervalued Market Segments")
        query = """
        // Simplified approach: Find neighborhoods with above-average features but below-average prices
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WITH n, count(p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             avg(size([(p)-[:HAS_FEATURE]->(:Feature) | 1])) as AvgFeaturesPerProperty
        WHERE PropertyCount >= 5
        
        // Get city averages for comparison
        MATCH (cityProps:Property)-[:IN_NEIGHBORHOOD]->(:Neighborhood {city: n.city})
        WITH n, PropertyCount, AvgPrice, AvgFeaturesPerProperty,
             avg(cityProps.listing_price) as CityAvgPrice,
             avg(size([(cityProps)-[:HAS_FEATURE]->(:Feature) | 1])) as CityAvgFeatures
        
        WITH *, (AvgPrice / CityAvgPrice) as PriceRatio,
             (AvgFeaturesPerProperty / CityAvgFeatures) as FeatureRatio
        
        // Find undervalued: above-average features, below-average price
        WHERE FeatureRatio > 1.1 AND PriceRatio < 0.9
        
        RETURN n.city as City, n.name as Neighborhood,
               AvgPrice, PropertyCount, AvgFeaturesPerProperty,
               PriceRatio, FeatureRatio,
               n.lifestyle_tags as LifestyleTags
        ORDER BY (FeatureRatio / PriceRatio) DESC
        LIMIT 8
        """
        results = run_query(self.driver, query)
        
        print("Undervalued Neighborhoods (High Features, Lower Prices):")
        for r in results:
            value_score = r['FeatureRatio'] / r['PriceRatio']
            print(f"{r['Neighborhood']}, {r['City']}")
            print(f"   Value Score: {value_score:.2f} | Avg Price: ${r['AvgPrice']:,.0f}")
            print(f"   Avg Features: {r['AvgFeaturesPerProperty']:.1f} | Price Ratio: {r['PriceRatio']:.2f}")
            if r['LifestyleTags']:
                print(f"   Lifestyle: {', '.join(r['LifestyleTags'])}")

        # Emerging market indicators
        self.print_subsection("Emerging Market Indicators")
        query = """
        // Find areas with diverse property types and growing feature adoption
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        
        WITH n,
             count(DISTINCT p) as PropertyCount,
             count(DISTINCT p.property_type) as PropertyTypeDiversity,
             count(DISTINCT f.category) as FeatureCategoryDiversity,
             avg(p.listing_price) as AvgPrice,
             collect(DISTINCT p.property_type) as PropertyTypes
        WHERE PropertyCount >= 5
        
        // Calculate diversity score
        WITH *, (PropertyTypeDiversity * FeatureCategoryDiversity) as DiversityScore
        
        RETURN n.city as City, n.name as Neighborhood,
               PropertyCount, AvgPrice, DiversityScore,
               PropertyTypeDiversity, FeatureCategoryDiversity,
               PropertyTypes, n.lifestyle_tags as LifestyleTags
        ORDER BY DiversityScore DESC
        LIMIT 10
        """
        results = run_query(self.driver, query)
        
        print("Emerging Markets (High Diversity & Growth Potential):")
        for r in results:
            print(f"{r['Neighborhood']}, {r['City']}")
            print(f"   Diversity Score: {r['DiversityScore']} | Avg Price: ${r['AvgPrice']:,.0f}")
            print(f"   Property Types: {r['PropertyTypeDiversity']} | Feature Categories: {r['FeatureCategoryDiversity']}")
            print(f"   Types Available: {', '.join(r['PropertyTypes'])}")

        # Investment portfolio recommendations
        if self.embeddings_available:
            self.print_subsection("AI-Powered Investment Portfolio Recommendations")
            
            investment_queries = [
                "luxury waterfront property with investment potential",
                "affordable property in up-and-coming neighborhood",
                "commercial property with high rental yield potential"
            ]
            
            for query_text in investment_queries:
                print(f"\nInvestment Query: '{query_text}'")
                try:
                    results = self.search.search(
                        query=query_text,
                        top_k=3,
                        use_graph_boost=True
                    )
                    
                    if results:
                        for i, result in enumerate(results, 1):
                            print(f"   {i}. Property {result.listing_id} - ${result.listing_price:,.0f}")
                            print(f"      {result.neighborhood}, {result.city}")
                            print(f"      Combined Score: {result.combined_score:.3f}")
                            if result.features:
                                print(f"      Key Features: {', '.join(result.features[:3])}")
                    else:
                        print("   No suitable properties found")
                except Exception as e:
                    print(f"   Search error: {e}")

    # ===== SECTION 4: LIFESTYLE MARKET SEGMENTATION =====
    
    def lifestyle_market_segmentation(self):
        """Analyze market segments based on lifestyle preferences and demographics"""
        self.print_section_header(
            "Lifestyle Market Segmentation",
            "Understanding market segments through lifestyle tags and preference patterns"
        )
        
        # Lifestyle tag market analysis
        self.print_subsection("Lifestyle Preference Markets")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE n.lifestyle_tags IS NOT NULL
        UNWIND n.lifestyle_tags as LifestyleTag
        
        MATCH (p)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)
        WITH LifestyleTag, n.city as City,
             count(DISTINCT p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             count(DISTINCT n) as NeighborhoodCount,
             collect(DISTINCT n.name)[0..3] as SampleNeighborhoods
        WHERE PropertyCount >= 5
        
        RETURN LifestyleTag, City, PropertyCount, AvgPrice, 
               NeighborhoodCount, SampleNeighborhoods
        ORDER BY LifestyleTag, AvgPrice DESC
        """
        results = run_query(self.driver, query)
        
        current_lifestyle = None
        for r in results:
            if r['LifestyleTag'] != current_lifestyle:
                current_lifestyle = r['LifestyleTag']
                print(f"\n{current_lifestyle.upper()} LIFESTYLE")
            
            print(f"   {r['City']}: ${r['AvgPrice']:,.0f} avg | {r['PropertyCount']} properties")
            print(f"      {r['NeighborhoodCount']} neighborhoods: {', '.join(r['SampleNeighborhoods'])}")

        # Lifestyle-feature correlation analysis
        self.print_subsection("Lifestyle-Feature Correlation Matrix")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE n.lifestyle_tags IS NOT NULL
        UNWIND n.lifestyle_tags as LifestyleTag
        
        MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        WITH LifestyleTag, f.name as Feature, f.category as Category,
             count(p) as PropertyCount,
             avg(p.listing_price) as AvgPrice
        WHERE PropertyCount >= 3
        
        // Calculate correlation strength
        MATCH (allProps:Property)-[:HAS_FEATURE]->(f2:Feature {name: Feature})
        WITH LifestyleTag, Feature, Category, PropertyCount, AvgPrice,
             count(allProps) as TotalWithFeature
        
        MATCH (lifestyleProps:Property)-[:LOCATED_IN]->(ln:Neighborhood)
        WHERE LifestyleTag IN ln.lifestyle_tags
        WITH LifestyleTag, Feature, Category, PropertyCount, AvgPrice,
             TotalWithFeature, count(lifestyleProps) as TotalLifestyleProps
        
        WITH *, (toFloat(PropertyCount) / TotalLifestyleProps) as LifestyleAdoption,
             (toFloat(PropertyCount) / TotalWithFeature) as FeatureConcentration
        WHERE LifestyleAdoption > 0.3 AND FeatureConcentration > 0.2
        
        RETURN LifestyleTag, Feature, Category, 
               LifestyleAdoption, FeatureConcentration, AvgPrice
        ORDER BY LifestyleAdoption DESC
        LIMIT 20
        """
        results = run_query(self.driver, query)
        
        print("Strong Lifestyle-Feature Correlations:")
        for r in results:
            correlation_strength = (r['LifestyleAdoption'] + r['FeatureConcentration']) / 2
            strength_icon = "" if correlation_strength > 0.6 else "" if correlation_strength > 0.4 else ""
            
            print(f"{strength_icon} {r['LifestyleTag']} <-> {r['Feature']} [{r['Category']}]")
            print(f"   Lifestyle Adoption: {r['LifestyleAdoption']:.1%} | Feature Concentration: {r['FeatureConcentration']:.1%}")
            print(f"   Average Price: ${r['AvgPrice']:,.0f}")

        # Demographic market sizing
        self.print_subsection("Market Size by Lifestyle Segment")
        query = """
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        WHERE n.lifestyle_tags IS NOT NULL
        
        WITH n.city as City, n.lifestyle_tags as LifestyleTags,
             count(p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             sum(p.listing_price) as TotalMarketValue
        
        UNWIND LifestyleTags as Tag
        WITH City, Tag, 
             sum(PropertyCount) as TotalProperties,
             avg(AvgPrice) as MarketAvgPrice,
             sum(TotalMarketValue) as MarketValue
        
        RETURN Tag as LifestyleSegment, City,
               TotalProperties, MarketAvgPrice, MarketValue,
               MarketValue / 1000000 as MarketValueMillion
        ORDER BY MarketValue DESC
        LIMIT 15
        """
        results = run_query(self.driver, query)
        
        print("Market Size by Lifestyle Segment:")
        for r in results:
            market_size_icon = "" if r['MarketValueMillion'] > 1000 else "" if r['MarketValueMillion'] > 500 else ""
            print(f"{market_size_icon} {r['LifestyleSegment']} in {r['City']}")
            print(f"   Market Value: ${r['MarketValueMillion']:.0f}M | {r['TotalProperties']} properties")
            print(f"   Average Price: ${r['MarketAvgPrice']:,.0f}")

    # ===== SECTION 5: FEATURE IMPACT ANALYSIS =====
    
    def feature_impact_analysis(self):
        """Deep analysis of feature impacts on pricing and market dynamics"""
        self.print_section_header(
            "Feature Impact Analysis",
            "Quantifying the market impact of property features using graph relationships"
        )
        
        # Feature category performance analysis
        self.print_subsection("Feature Category Performance Analysis")
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH f.category as Category,
             count(DISTINCT p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             collect(DISTINCT f.name) as Features
        WHERE PropertyCount >= 10
        
        // Compare to properties without features in this category
        MATCH (p2:Property)
        WHERE NOT (p2)-[:HAS_FEATURE]->(:Feature {category: Category})
        WITH Category, PropertyCount, AvgPrice, Features,
             avg(p2.listing_price) as BaselinePrice, count(p2) as BaselineCount
        WHERE BaselineCount >= 20
        
        WITH *, (AvgPrice - BaselinePrice) as CategoryPremium,
             (AvgPrice - BaselinePrice) / BaselinePrice * 100 as PremiumPercent
        
        RETURN Category, PropertyCount, AvgPrice, BaselinePrice,
               CategoryPremium, PremiumPercent, size(Features) as FeatureVariety
        ORDER BY PremiumPercent DESC
        """
        results = run_query(self.driver, query)
        
        print("Feature Category Market Impact:")
        for r in results:
            impact_icon = "" if r['PremiumPercent'] > 30 else "" if r['PremiumPercent'] > 15 else ""
            print(f"{impact_icon} {r['Category']} Category")
            print(f"   Premium: ${r['CategoryPremium']:,.0f} (+{r['PremiumPercent']:.1f}%)")
            print(f"   Market: ${r['AvgPrice']:,.0f} vs ${r['BaselinePrice']:,.0f} baseline")
            print(f"   Adoption: {r['PropertyCount']} properties | Variety: {r['FeatureVariety']} features")

        # Feature co-occurrence network analysis
        self.print_subsection("Feature Co-occurrence Network Analysis")
        query = """
        MATCH (f1:Feature)<-[:HAS_FEATURE]-(p:Property)-[:HAS_FEATURE]->(f2:Feature)
        WHERE f1.name < f2.name  // Avoid duplicates
        
        WITH f1.name + " + " + f2.name as FeaturePair,
             f1.category + " + " + f2.category as CategoryPair,
             count(p) as CoOccurrenceCount,
             avg(p.listing_price) as AvgPriceWithBoth,
             collect(DISTINCT p.listing_id)[0..3] as SampleProperties
        WHERE CoOccurrenceCount >= 5
        
        // Calculate lift (how often they appear together vs expected)
        MATCH (pf1:Property)-[:HAS_FEATURE]->(f1Feature:Feature {name: split(FeaturePair, " + ")[0]})
        MATCH (pf2:Property)-[:HAS_FEATURE]->(f2Feature:Feature {name: split(FeaturePair, " + ")[1]})
        WITH FeaturePair, CategoryPair, CoOccurrenceCount, AvgPriceWithBoth, SampleProperties,
             count(DISTINCT pf1) as Feature1Count, count(DISTINCT pf2) as Feature2Count
        
        MATCH (allProps:Property)
        WITH FeaturePair, CategoryPair, CoOccurrenceCount, AvgPriceWithBoth, SampleProperties,
             Feature1Count, Feature2Count, count(allProps) as TotalProperties
        
        WITH *, (toFloat(CoOccurrenceCount) * TotalProperties) / (Feature1Count * Feature2Count) as Lift
        WHERE Lift > 1.5  // Strong co-occurrence
        
        RETURN FeaturePair, CategoryPair, CoOccurrenceCount, 
               AvgPriceWithBoth, Lift, SampleProperties
        ORDER BY Lift DESC
        LIMIT 12
        """
        results = run_query(self.driver, query)
        
        print("Strong Feature Co-occurrence Patterns:")
        for r in results:
            synergy_icon = "" if r['Lift'] > 3.0 else "" if r['Lift'] > 2.0 else ""
            print(f"{synergy_icon} {r['FeaturePair']}")
            print(f"   Categories: {r['CategoryPair']}")
            print(f"   Co-occurrence: {r['CoOccurrenceCount']} properties | Lift: {r['Lift']:.2f}")
            print(f"   Average Price: ${r['AvgPriceWithBoth']:,.0f}")
            print(f"   Sample Properties: {', '.join(r['SampleProperties'])}")

        # Feature rarity and exclusivity analysis
        self.print_subsection("Feature Rarity & Exclusivity Analysis")
        query = """
        MATCH (p:Property)-[:HAS_FEATURE]->(f:Feature)
        WITH f.name as Feature, f.category as Category,
             count(p) as PropertyCount,
             avg(p.listing_price) as AvgPrice,
             max(p.listing_price) as MaxPrice
        
        MATCH (allProps:Property)
        WITH Feature, Category, PropertyCount, AvgPrice, MaxPrice,
             count(allProps) as TotalProperties
        
        WITH *, (toFloat(PropertyCount) / TotalProperties) as RarityScore,
             CASE 
                WHEN PropertyCount <= 3 THEN 'Ultra-Rare'
                WHEN PropertyCount <= 10 THEN 'Rare' 
                WHEN PropertyCount <= 25 THEN 'Uncommon'
                ELSE 'Common'
             END as RarityLevel
        WHERE PropertyCount <= 25  // Focus on rare features
        
        RETURN Feature, Category, PropertyCount, RarityLevel,
               RarityScore, AvgPrice, MaxPrice
        ORDER BY RarityScore ASC, AvgPrice DESC
        """
        results = run_query(self.driver, query)
        
        print("Rare & Exclusive Features:")
        for r in results:
            rarity_icon = "" if r['RarityLevel'] == 'Ultra-Rare' else "" if r['RarityLevel'] == 'Rare' else ""
            print(f"{rarity_icon} {r['Feature']} [{r['Category']}] - {r['RarityLevel']}")
            print(f"   Exclusivity: {r['PropertyCount']} properties ({r['RarityScore']:.1%} of market)")
            print(f"   Premium Market: ${r['AvgPrice']:,.0f} avg | ${r['MaxPrice']:,.0f} max")

    # ===== SECTION 6: COMPETITIVE MARKET INTELLIGENCE =====
    
    def competitive_market_intelligence(self):
        """Advanced competitive analysis using graph relationships and similarity networks"""
        self.print_section_header(
            "Competitive Market Intelligence",
            "Understanding competitive dynamics through property similarity networks and positioning"
        )
        
        # Competitive clustering analysis
        self.print_subsection("Competitive Property Clusters")
        query = """
        MATCH (p:Property)-[sim:SIMILAR_TO]->(similar:Property)
        WHERE sim.similarity_score > 0.8  // High similarity threshold
        
        // Find properties with many high-similarity connections
        WITH p, count(similar) as SimilarityConnections,
             avg(sim.similarity_score) as AvgSimilarityScore,
             collect(similar.listing_id)[0..5] as SimilarProperties
        WHERE SimilarityConnections >= 3
        
        MATCH (p)-[:IN_NEIGHBORHOOD]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        
        RETURN p.listing_id as PropertyID, p.listing_price as Price,
               n.city + ", " + n.name as Location,
               SimilarityConnections, AvgSimilarityScore,
               SimilarProperties, collect(DISTINCT f.name)[0..5] as TopFeatures
        ORDER BY SimilarityConnections DESC, AvgSimilarityScore DESC
        LIMIT 10
        """
        results = run_query(self.driver, query)
        
        print("Highly Competitive Property Clusters:")
        for r in results:
            cluster_icon = "" if r['SimilarityConnections'] > 5 else "" if r['SimilarityConnections'] > 3 else ""
            print(f"{cluster_icon} Property {r['PropertyID']} - ${r['Price']:,.0f}")
            print(f"   Location: {r['Location']}")
            print(f"   Competitive Network: {r['SimilarityConnections']} similar properties")
            print(f"   Average Similarity: {r['AvgSimilarityScore']:.3f}")
            print(f"   Direct Competitors: {', '.join(r['SimilarProperties'])}")
            print(f"   Key Features: {', '.join(r['TopFeatures'])}")

        # Market positioning analysis
        self.print_subsection("Market Positioning Analysis")
        query = """
        // Analyze positioning within price bands and feature categories
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        
        WITH p, n,
             collect(DISTINCT f.category) as FeatureCategories,
             size([(p)-[:HAS_FEATURE]->(:Feature) | 1]) as FeatureCount,
             CASE 
                WHEN p.listing_price > 8000000 THEN 'Ultra-Luxury'
                WHEN p.listing_price > 3000000 THEN 'Luxury'
                WHEN p.listing_price > 1500000 THEN 'Premium'
                WHEN p.listing_price > 800000 THEN 'Mid-Market'
                ELSE 'Affordable'
             END as PriceBand
        
        // Count competitive density in same price band and neighborhood
        MATCH (comp:Property)-[:IN_NEIGHBORHOOD]->(n)
        WHERE comp <> p AND 
              CASE 
                WHEN p.listing_price > 8000000 THEN comp.listing_price > 8000000
                WHEN p.listing_price > 3000000 THEN comp.listing_price > 3000000 AND comp.listing_price <= 8000000
                WHEN p.listing_price > 1500000 THEN comp.listing_price > 1500000 AND comp.listing_price <= 3000000
                WHEN p.listing_price > 800000 THEN comp.listing_price > 800000 AND comp.listing_price <= 1500000
                ELSE comp.listing_price <= 800000
              END
        
        WITH p, n, FeatureCategories, FeatureCount, PriceBand,
             count(comp) as DirectCompetitors
        
        // Analyze feature differentiation
        OPTIONAL MATCH (p)-[sim:SIMILAR_TO]->(similar:Property)
        WHERE sim.similarity_score > 0.7
        
        RETURN p.listing_id as PropertyID, p.listing_price as Price,
               n.city as City, n.name as Neighborhood, PriceBand,
               FeatureCount, FeatureCategories, DirectCompetitors,
               count(DISTINCT similar) as SimilarProperties,
               avg(sim.similarity_score) as AvgSimilarity
        ORDER BY DirectCompetitors DESC, FeatureCount DESC
        LIMIT 15
        """
        results = run_query(self.driver, query)
        
        print("Market Positioning Intelligence:")
        for r in results:
            competition_level = "" if r['DirectCompetitors'] > 10 else "" if r['DirectCompetitors'] > 5 else ""
            print(f"{competition_level} Property {r['PropertyID']} [{r['PriceBand']}] - ${r['Price']:,.0f}")
            print(f"   Location: {r['Neighborhood']}, {r['City']}")
            print(f"   Competitive Density: {r['DirectCompetitors']} direct competitors")
            print(f"   Feature Differentiation: {r['FeatureCount']} features across {len(r['FeatureCategories'])} categories")
            if r['SimilarProperties']:
                print(f"   Similarity Network: {r['SimilarProperties']} similar (avg: {r['AvgSimilarity']:.3f})")

        # Competitive gap analysis
        self.print_subsection("Market Gap Analysis")
        query = """
        // Find underserved market segments
        MATCH (p:Property)-[:LOCATED_IN]->(n:Neighborhood)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(f:Feature)
        
        WITH n.city as City, p.property_type as PropertyType,
             CASE 
                WHEN p.listing_price > 5000000 THEN 'Ultra-Luxury'
                WHEN p.listing_price > 2000000 THEN 'Luxury'
                WHEN p.listing_price > 1000000 THEN 'Premium'
                WHEN p.listing_price > 500000 THEN 'Mid-Market'
                ELSE 'Affordable'
             END as PriceBand,
             collect(DISTINCT f.category) as FeatureCategories,
             count(p) as PropertyCount
        
        WITH City, PropertyType, PriceBand, 
             size(collect(DISTINCT FeatureCategories)) as FeatureCategoryVariety,
             PropertyCount
        WHERE PropertyCount > 0
        
        // Identify gaps (low supply in certain segments)
        WITH City, PropertyType, 
             collect({band: PriceBand, count: PropertyCount, variety: FeatureCategoryVariety}) as PriceBandData
        
        UNWIND PriceBandData as bandData
        WITH City, PropertyType, bandData.band as PriceBand, 
             bandData.count as Count, bandData.variety as Variety
        WHERE Count <= 3  // Low competition segments
        
        RETURN City, PropertyType, PriceBand, Count as Supply, Variety as FeatureVariety,
               CASE WHEN Count <= 1 THEN 'MAJOR GAP' WHEN Count <= 3 THEN 'OPPORTUNITY' ELSE 'COMPETITIVE' END as MarketStatus
        ORDER BY Count ASC, Variety DESC
        LIMIT 15
        """
        results = run_query(self.driver, query)
        
        print("Market Gap Opportunities:")
        for r in results:
            gap_icon = "" if r['MarketStatus'] == 'MAJOR GAP' else "" if r['MarketStatus'] == 'OPPORTUNITY' else ""
            print(f"{gap_icon} {r['City']} - {r['PropertyType']} [{r['PriceBand']}]")
            print(f"   Market Status: {r['MarketStatus']}")
            print(f"   Current Supply: {r['Supply']} properties | Feature Variety: {r['FeatureVariety']}")


def run_complete_market_intelligence_demo():
    """Run the complete market intelligence demonstration"""
    print("ADVANCED MARKET INTELLIGENCE DEMO")
    print("="*80)
    print("Showcasing sophisticated real estate market analysis using Neo4j graph")
    print("database relationships combined with vector embeddings for comprehensive")
    print("market intelligence that rivals professional real estate analytics platforms.")
    print("="*80)
    
    driver = None
    try:
        driver = get_neo4j_driver()
        analyzer = MarketIntelligenceAnalyzer(driver)
        
        # Run all analysis sections (with proper output handling for pipes)
        try:
            analyzer.geographic_market_analysis()
            analyzer.price_prediction_analysis()
            analyzer.investment_opportunity_analysis()
            analyzer.lifestyle_market_segmentation()
            analyzer.feature_impact_analysis()
            analyzer.competitive_market_intelligence()
        except BrokenPipeError:
            # Handle gracefully when output is piped to head/less/etc
            import sys
            sys.stderr.close()
        
        print(f"\n{'='*80}")
        print("MARKET INTELLIGENCE ANALYSIS COMPLETE")
        print("="*80)
        print("This demonstration showcased the power of combining Neo4j graph")
        print("relationships with vector embeddings to create professional-grade")
        print("real estate market intelligence capabilities:")
        print()
        print("• Geographic arbitrage opportunities across neighborhoods")
        print("• Feature-based price prediction and anomaly detection")
        print("• Investment opportunity discovery through pattern analysis")
        print("• Lifestyle market segmentation and demographic insights")
        print("• Feature impact quantification and co-occurrence networks")
        print("• Competitive positioning and market gap analysis")
        print()
        print("The graph database enables complex relationship traversals that")
        print("would be extremely difficult with traditional relational databases,")
        print("while vector embeddings provide semantic understanding for")
        print("intelligent property matching and market analysis.")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.close()


if __name__ == "__main__":
    run_complete_market_intelligence_demo()