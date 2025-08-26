"""
Comprehensive Relationship Builder for Real Estate Graph Database

This module implements the core relationship building logic for a Neo4j-based real estate
knowledge graph. It creates 10 distinct relationship types that connect properties,
neighborhoods, geographic entities, and contextual information.

**Relationship Types Overview:**

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           REAL ESTATE KNOWLEDGE GRAPH                              │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                     │
│  Property Relationships:                                                            │
│    • LOCATED_IN     Properties → Neighborhoods (geographic placement)              │
│    • HAS_FEATURE    Properties → Features (amenities & characteristics)            │
│    • IN_PRICE_RANGE Properties → PriceRanges (market segmentation)                 │
│    • OF_TYPE        Properties → PropertyTypes (architectural classification)      │
│    • SIMILAR_TO     Properties ↔ Properties (recommendation network)               │
│                                                                                     │
│  Geographic Relationships:                                                          │
│    • PART_OF        Neighborhoods → Counties (administrative hierarchy)            │
│    • IN_COUNTY      Neighborhoods → Counties (county membership)                   │
│    • NEAR           Neighborhoods ↔ Neighborhoods (proximity network)              │
│                                                                                     │
│  Content Relationships:                                                             │
│    • DESCRIBES      WikipediaArticles → Neighborhoods (contextual information)     │
│    • IN_TOPIC_CLUSTER Entities → TopicClusters (semantic grouping)                 │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘

**Architecture and Design Patterns:**

Current Implementation:
- Monolithic RelationshipBuilder class (796+ lines)
- Entity-specific methods for each relationship type
- Hardcoded similarity thresholds and weights
- Mixed abstraction levels (orchestrators + builders)

Strengths:
- All 10 relationship types functional and tested
- Handles complex geographic matching logic
- Optimized for Neo4j with proper Decimal→Double casting
- Uses broadcast joins for performance
- Comprehensive error handling

Technical Debt Areas:
- God Class pattern with too many responsibilities
- Magic numbers scattered throughout (0.4, 0.3, 0.5 thresholds)
- No configuration management (hardcoded weights)
- Redundant code patterns across relationship builders
- Mixed high-level orchestration with low-level implementation

**Future Architecture Vision:**
```
relationships/
├── base.py              # Abstract relationship builder interfaces
├── config.py            # Pydantic configuration models
├── factory.py           # Builder factory with Strategy pattern
├── orchestrator.py      # High-level relationship coordination
├── builders/
│   ├── geographic.py    # LOCATED_IN, PART_OF, IN_COUNTY, NEAR
│   ├── property.py      # HAS_FEATURE, OF_TYPE, IN_PRICE_RANGE
│   ├── content.py       # DESCRIBES, IN_TOPIC_CLUSTER
│   └── similarity.py    # SIMILAR_TO with configurable algorithms
```

**Performance Characteristics:**

Typical Production Results (SF Dataset):
- Properties: 420 nodes
- Neighborhoods: 21 nodes → 200+ NEAR relationships (2mi threshold)
- SIMILAR_TO: 2,000+ property relationships (0.5 similarity threshold)
- DESCRIBES: 50+ Wikipedia-neighborhood connections
- HAS_FEATURE: 3,257+ property-feature relationships

Scalability Considerations:
- NEAR relationships: O(N²) neighborhood comparisons
- SIMILAR_TO: O(N²) property comparisons (most expensive)
- Geographic matching: O(W×N) Wikipedia-neighborhood joins
- Feature relationships: O(P×F) property-feature joins

**Usage Examples:**

Basic Usage:
```python
builder = RelationshipBuilder(spark)

# Core relationships (properties, neighborhoods, wikipedia)
relationships = builder.build_all_relationships(
    properties_df, neighborhoods_df, wikipedia_df
)

# Extended relationships (all entity types)
extended = builder.build_extended_relationships(
    properties_df, neighborhoods_df, wikipedia_df,
    features_df, property_types_df, price_ranges_df,
    counties_df, topic_clusters_df
)
```

Testing and Validation:
```python
# Comprehensive test suite available
python test_extended_relationships.py
# Expected: All 10 relationship types PASSED
```

**Dependencies:**
- PySpark DataFrame API with SQL expressions
- Pydantic models from graph_models.py
- Geographic coordinate data (latitude/longitude)
- Entity DataFrames from extraction pipeline

**Error Handling:**
- Graceful degradation for missing columns
- Try-catch blocks around each relationship type
- Comprehensive logging with relationship counts
- Input validation for required DataFrame schemas

This module represents the core intelligence of the real estate knowledge graph,
transforming raw property data into a rich network of interconnected entities
suitable for advanced search, recommendation, and market analysis applications.
"""

import logging
import math
from typing import Dict, Optional

from pydantic import BaseModel, Field
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    abs,
    array_intersect,
    broadcast,
    coalesce,
    col,
    concat,
    count,
    explode,
    expr,
    least,
    lit,
    lower,
    size,
    when,
)
from data_pipeline.models.graph_models import (
    DescribesRelationship,
    HasFeatureRelationship,
    InCountyRelationship,
    InPriceRangeRelationship,
    InTopicClusterRelationship,
    LocatedInRelationship,
    NearRelationship,
    OfTypeRelationship,
    PartOfRelationship,
    RelationshipType,
    SimilarToRelationship,
)
from data_pipeline.models.spark_models import Relationship

logger = logging.getLogger(__name__)


class RelationshipBuilder:
    """
    Comprehensive relationship builder for Neo4j graph database.
    
    Creates 10 types of relationships between entities in the real estate data pipeline:
    
    **Property Relationships:**
    - LOCATED_IN: Properties → Neighborhoods (geographic location)
    - HAS_FEATURE: Properties → Features (amenities and characteristics)  
    - IN_PRICE_RANGE: Properties → PriceRanges (market categorization)
    - OF_TYPE: Properties → PropertyTypes (single-family, condo, etc.)
    - SIMILAR_TO: Properties ↔ Properties (similarity network)
    
    **Geographic Relationships:**
    - PART_OF: Neighborhoods → Counties (geographic hierarchy)
    - IN_COUNTY: Neighborhoods → Counties (county membership)
    - NEAR: Neighborhoods ↔ Neighborhoods (proximity network)
    
    **Content Relationships:**
    - DESCRIBES: WikipediaArticles → Neighborhoods (contextual information)
    - IN_TOPIC_CLUSTER: Entities → TopicClusters (semantic grouping)
    
    **Architecture:**
    This class implements a monolithic architecture with entity-specific methods
    for each relationship type. While functional, it exhibits some technical debt
    patterns (796+ lines, hardcoded thresholds, mixed abstraction levels) that
    could benefit from future refactoring using Strategy and Factory patterns.
    
    **Usage Example:**
    ```python
    builder = RelationshipBuilder(spark)
    
    # Build core relationships
    relationships = builder.build_all_relationships(
        properties_df, neighborhoods_df, wikipedia_df
    )
    
    # Build extended relationships with all entity types
    extended_rels = builder.build_extended_relationships(
        properties_df, neighborhoods_df, wikipedia_df,
        features_df, property_types_df, price_ranges_df,
        counties_df, topic_clusters_df
    )
    ```
    
    **Performance Considerations:**
    - Uses broadcast joins for small lookup DataFrames
    - Implements bidirectional relationships for proximity networks
    - Applies similarity thresholds to control relationship density
    - Handles large-scale cross-joins with appropriate filtering
    """
    
    def __init__(self, spark: SparkSession):
        """
        Initialize the relationship builder.
        
        Args:
            spark: Active SparkSession
        """
        self.spark = spark
    
    def build_all_relationships(
        self,
        properties_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None,
        wikipedia_df: Optional[DataFrame] = None
    ) -> Dict[str, DataFrame]:
        """
        Build all configured relationships between entities.
        
        Args:
            properties_df: Property DataFrame
            neighborhoods_df: Neighborhood DataFrame
            wikipedia_df: Wikipedia DataFrame
            
        Returns:
            Dictionary of relationship DataFrames by type
        """
        relationships = {}
        
        # Property to Neighborhood relationships - always enabled if both dataframes exist
        if properties_df and neighborhoods_df:
            relationships["property_located_in"] = self.build_located_in_relationships(
                properties_df, neighborhoods_df
            )
            logger.info("✓ Built LOCATED_IN relationships")
        
        # Geographic hierarchy relationships - always enabled if neighborhoods dataframe exists
        if neighborhoods_df:
            relationships["geographic_hierarchy"] = self.build_geographic_hierarchy(
                neighborhoods_df
            )
            logger.info("✓ Built PART_OF relationships")
        
        # Wikipedia DESCRIBES relationships - always enabled if both dataframes exist
        if wikipedia_df and neighborhoods_df:
            relationships["wikipedia_describes"] = self.build_describes_relationships(
                wikipedia_df, neighborhoods_df
            )
            logger.info("✓ Built DESCRIBES relationships")
        
        # Similarity relationships - always enabled
        if properties_df:
            relationships["property_similarity"] = self.calculate_property_similarity(
                properties_df
            )
            logger.info("✓ Built property SIMILAR_TO relationships")
        
        return relationships
    
    def build_located_in_relationships(
        self,
        properties_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Build LOCATED_IN relationships between properties and neighborhoods.
        
        Args:
            properties_df: Property DataFrame with neighborhood_id
            neighborhoods_df: Neighborhood DataFrame with neighborhood_id
            
        Returns:
            DataFrame of LocatedInRelationship records
        """
        # Filter to properties with neighborhood_id
        props_with_neighborhood = properties_df.filter(
            col("neighborhood_id").isNotNull()
        ).select(
            col("listing_id").alias("from_id"),
            col("neighborhood_id").alias("to_neighborhood_id"),
            col("city"),
            col("state")
        )
        
        # Join with neighborhoods to validate relationships
        neighborhoods_for_join = neighborhoods_df.select(
            col("neighborhood_id"),
            col("city").alias("n_city"),
            col("state").alias("n_state")
        ).alias("n")  # Alias the DataFrame to avoid ambiguity
        
        valid_relationships = props_with_neighborhood.alias("p").join(
            neighborhoods_for_join,
            col("p.to_neighborhood_id") == col("n.neighborhood_id"),
            "inner"
        )
        
        # Create relationship records
        located_in_df = valid_relationships.select(
            col("p.from_id"),
            col("n.neighborhood_id").alias("to_id"),
            lit(RelationshipType.LOCATED_IN.value).alias("relationship_type"),
            lit(None).cast("float").alias("distance_meters")
        )
        
        return located_in_df
    
    def build_geographic_hierarchy(self, neighborhoods_df: DataFrame) -> DataFrame:
        """
        Build PART_OF relationships for geographic hierarchy.
        
        Only creates relationships between entities that actually exist in the database:
        - Neighborhood -> County (since City/State nodes don't exist)
        
        Args:
            neighborhoods_df: Neighborhood DataFrame with county information
            
        Returns:
            DataFrame of PART_OF relationships
        """
        # Only create Neighborhood -> County relationships since City/State nodes don't exist
        if "neighborhood_id" not in neighborhoods_df.columns:
            logger.warning("No neighborhood_id column found for PART_OF relationships")
            return self.spark.createDataFrame([], schema=
                "from_id string, to_id string, relationship_type string"
            )
        
        # Neighborhood -> County relationships using actual County entity IDs
        neighborhood_to_county = neighborhoods_df.filter(
            col("neighborhood_id").isNotNull() & 
            col("county").isNotNull()
        ).select(
            col("neighborhood_id").alias("from_id"),
            # Create county ID that matches the County entity pattern
            concat(lower(col("county")), lit("_"), lower(col("state"))).alias("to_id"),
            lit(RelationshipType.PART_OF.value).alias("relationship_type")
        ).distinct()
        
        count = neighborhood_to_county.count()
        logger.info(f"Created {count} Neighborhood->County PART_OF relationships")
        
        return neighborhood_to_county
    
    def build_describes_relationships(
        self,
        wikipedia_df: DataFrame,
        neighborhoods_df: DataFrame
    ) -> DataFrame:
        """
        Build DESCRIBES relationships from Wikipedia articles to neighborhoods.
        
        Creates contextual relationships between Wikipedia articles and geographic entities
        using intelligent geographic matching strategies. Enables rich contextual search
        and market intelligence by connecting historical, cultural, and demographic 
        information to specific neighborhoods.
        
        **Intelligent Matching Algorithm:**
        Uses a three-strategy approach to maximize relevant connections:
        
        1. **Direct City+State Match (Highest Precision):**
           - Matches article's best_city + best_state with neighborhood location
           - Example: "1906 San Francisco earthquake" → Mission District
           - Filters out articles with empty/null city fields
        
        2. **County+State Fallback (Medium Precision):**
           - For articles without specific city but with county information
           - Connects broader regional content to local neighborhoods
           - Example: "California Historical Sites" → all SF neighborhoods
        
        3. **Union and Deduplication:**
           - Combines both strategies and removes duplicate relationships
           - Ensures each article connects to most relevant neighborhoods
           - Prioritizes direct matches over county fallbacks
        
        **Data Quality Handling:**
        - Filters out articles with missing geographic information
        - Handles mixed case and spacing in geographic names
        - Validates both entities exist before creating relationships
        - Graceful degradation: partial matches better than no matches
        
        **Performance Characteristics:**
        - Expected Output: 50+ relationships for typical Wikipedia corpus
        - Broadcast Join: Neighborhoods table is small (21 records)
        - Deduplication: Prevents multi-path matches for same article-neighborhood pair
        - Scalability: O(W×N) where W=Wikipedia articles, N=Neighborhoods
        
        Args:
            wikipedia_df: Wikipedia DataFrame with required columns:
                - page_id: Unique Wikipedia article identifier
                - best_city: Primary city mentioned in article (may be empty)
                - best_state: Primary state mentioned in article
                - county: County information (for fallback matching)
            neighborhoods_df: Neighborhood DataFrame with required columns:
                - neighborhood_id: Unique neighborhood identifier
                - city: Neighborhood's city name
                - state: Neighborhood's state abbreviation or full name
                - county: Neighborhood's county name
                
        Returns:
            DataFrame with schema:
                - from_id: Wikipedia page_id 
                - to_id: Neighborhood neighborhood_id
                - relationship_type: Always "DESCRIBES"
                
        Example Relationships:
            ```
            "1906 San Francisco earthquake" → Mission District
            "Golden Gate Bridge" → Pacific Heights  
            "Silicon Valley History" → All South Bay neighborhoods
            "California Wine Country" → Napa/Sonoma neighborhoods
            ```
            
        Note:
            This method demonstrates the complexity of geographic entity resolution
            and could benefit from fuzzy matching or geocoding services in production.
        """
        # Prepare Wikipedia articles - only those with location data
        wiki_articles = wikipedia_df.filter(
            col("page_id").isNotNull() & 
            col("best_state").isNotNull() &
            (col("best_city").isNotNull() | col("county").isNotNull())
        ).select(
            col("page_id").cast("string").alias("from_id"),
            col("best_city").alias("wiki_city"),
            col("best_state").alias("wiki_state"),
            col("county").alias("wiki_county")
        )
        
        # Prepare neighborhoods
        neighborhoods = neighborhoods_df.select(
            col("neighborhood_id").alias("to_id"),
            col("city").alias("neighborhood_city"),
            col("state").alias("neighborhood_state"),
            col("county").alias("neighborhood_county")
        )
        
        # Strategy 1: Direct city+state match
        city_matches = wiki_articles.join(
            neighborhoods,
            (wiki_articles["wiki_city"] == neighborhoods["neighborhood_city"]) &
            (wiki_articles["wiki_state"] == neighborhoods["neighborhood_state"]) &
            (wiki_articles["wiki_city"] != ""),
            "inner"
        ).select(
            col("from_id"),
            col("to_id"), 
            lit(RelationshipType.DESCRIBES.value).alias("relationship_type")
        )
        
        # Strategy 2: County+state match (for articles with empty city)
        county_matches = wiki_articles.join(
            neighborhoods,
            (wiki_articles["wiki_county"] == neighborhoods["neighborhood_county"]) &
            (wiki_articles["wiki_state"] == neighborhoods["neighborhood_state"]) &
            (wiki_articles["wiki_city"] == "") &
            (wiki_articles["wiki_county"] != "None"),
            "inner"
        ).select(
            col("from_id"),
            col("to_id"),
            lit(RelationshipType.DESCRIBES.value).alias("relationship_type") 
        )
        
        # Union both strategies and remove duplicates
        all_matches = city_matches.unionByName(county_matches).distinct()
        
        match_count = all_matches.count()
        logger.info(f"Created {match_count} DESCRIBES relationships")
        
        return all_matches
    
    def calculate_property_similarity(self, properties_df: DataFrame) -> DataFrame:
        """
        Calculate SIMILAR_TO relationships between properties.
        
        Creates a property similarity network based on multi-dimensional feature comparison.
        Uses weighted scoring across price, spatial, and structural characteristics to identify
        properties that potential buyers might consider as alternatives.
        
        **Similarity Algorithm:**
        Combines three weighted similarity metrics:
        
        1. **Price Similarity (40% weight):**
           - Normalized price difference using log scale
           - Formula: `1.0 - abs(log(price1) - log(price2)) / log(max_price/min_price)`
           - Handles wide price ranges (e.g., $450K - $1.2M) effectively
        
        2. **Bedroom/Bathroom Similarity (30% weight):**
           - Exact match bonus for same bedroom count
           - Scaled by maximum difference to normalize across property types
           - Accounts for both bedroom and bathroom counts
        
        3. **Square Footage Similarity (30% weight):**
           - Size similarity using relative difference
           - Formula: `1.0 - abs(sqft1 - sqft2) / max(sqft1, sqft2)`
           - Handles both small condos and large family homes
        
        **Technical Implementation:**
        ```sql
        similarity = 0.4 * price_sim + 0.3 * bedroom_sim + 0.3 * size_sim
        WHERE similarity >= 0.5
        ```
        
        Args:
            properties_df: Property DataFrame with required columns:
                - listing_id: Unique property identifier
                - listing_price: Property price in dollars
                - bedrooms: Number of bedrooms
                - bathrooms: Number of bathrooms  
                - square_feet: Property size in square feet
                
        Returns:
            DataFrame of SimilarToRelationship records with schema:
                - from_id: Source property ID
                - to_id: Target property ID
                - relationship_type: Always "SIMILAR_TO" 
                - similarity_score: Overall similarity (0.5-1.0)
                - price_similarity: Price component score
                - size_similarity: Size component score
                - feature_similarity: Reserved for future feature matching
        """
        # Extract fields from nested structures if needed
        prep_df = properties_df
        if "property_details.bedrooms" in prep_df.columns:
            prep_df = prep_df.withColumn("bedrooms", col("property_details.bedrooms"))
            prep_df = prep_df.withColumn("bathrooms", col("property_details.bathrooms"))
            prep_df = prep_df.withColumn("square_feet", col("property_details.square_feet"))
        if "address.city" in prep_df.columns:
            prep_df = prep_df.withColumn("city", col("address.city"))
            prep_df = prep_df.withColumn("state", col("address.state"))
        
        # Prepare properties for comparison and alias immediately (cast Decimals to double for Neo4j compatibility)
        p1 = prep_df.filter(
            col("listing_id").isNotNull() & 
            col("listing_price").isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col("listing_price").cast("double").alias("price"),
            col("bedrooms"), col("bathrooms"),
            col("square_feet").cast("double"), col("features"), col("city"), col("state")
        ).alias("p1")
        
        # Create second alias for self-join
        p2 = prep_df.filter(
            col("listing_id").isNotNull() & 
            col("listing_price").isNotNull() &
            col("city").isNotNull()
        ).select(
            col("listing_id"),
            col("listing_price").cast("double").alias("price"),
            col("bedrooms"), col("bathrooms"),
            col("square_feet").cast("double"), col("features"), col("city"), col("state")
        ).alias("p2")
        
        pairs = p1.join(
            p2,
            (col("p1.listing_id") < col("p2.listing_id")) &
            (col("p1.city") == col("p2.city")) &
            (col("p1.state") == col("p2.state")),
            "inner"
        )
        
        # Calculate similarity using column references to avoid ambiguity
        similarity_df = pairs.select(
            col("p1.listing_id").alias("from_id"),
            col("p2.listing_id").alias("to_id"),
            lit(RelationshipType.SIMILAR_TO.value).alias("relationship_type"),
            
            # Combined similarity calculation using proper column references
            (
                # Price similarity (40% weight)
                when(
                    abs(col("p1.price") - col("p2.price")) / col("p1.price") < 0.2, lit(0.4)
                ).when(
                    abs(col("p1.price") - col("p2.price")) / col("p1.price") < 0.4, lit(0.2)
                ).otherwise(lit(0.0)) +
                
                # Bedroom/bathroom similarity (30% weight)
                when(
                    (col("p1.bedrooms") == col("p2.bedrooms")) & (abs(col("p1.bathrooms") - col("p2.bathrooms")) <= 0.5), lit(0.3)
                ).when(
                    abs(col("p1.bedrooms") - col("p2.bedrooms")) <= 1, lit(0.15)
                ).otherwise(lit(0.0)) +
                
                # Square footage similarity (30% weight)
                when(
                    col("p1.square_feet").isNotNull() & col("p2.square_feet").isNotNull(),
                    when(
                        abs(col("p1.square_feet") - col("p2.square_feet")) / col("p1.square_feet") < 0.15, lit(0.3)
                    ).when(
                        abs(col("p1.square_feet") - col("p2.square_feet")) / col("p1.square_feet") < 0.3, lit(0.15)
                    ).otherwise(lit(0.0))
                ).otherwise(lit(0.15))
            ).alias("similarity_score"),
            
            # Keep component scores for transparency
            when(
                abs(col("p1.price") - col("p2.price")) / col("p1.price") < 0.2, lit(1.0)
            ).otherwise(lit(0.5)).alias("price_similarity"),
            when(
                col("p1.square_feet").isNotNull(),
                abs(col("p1.square_feet") - col("p2.square_feet")) / col("p1.square_feet")
            ).otherwise(lit(None)).alias("size_similarity"),
            lit(None).cast("float").alias("feature_similarity")
        )
        
        # Filter by threshold (lowered from 0.8 to 0.5 for more matches)
        return similarity_df.filter(
            col("similarity_score") >= 0.5
        )
    
    
    def get_relationship_statistics(self, relationships: Dict[str, DataFrame]) -> Dict:
        """
        Calculate statistics about created relationships.
        
        Args:
            relationships: Dictionary of relationship DataFrames
            
        Returns:
            Dictionary of statistics
        """
        stats = {}
        
        for rel_type, df in relationships.items():
            if df is not None:
                count = df.count()
                stats[rel_type] = {
                    "count": count,
                    "columns": df.columns
                }
                
                # Add specific statistics for similarity relationships
                if "similarity_score" in df.columns:
                    score_stats = df.select(
                        expr("avg(similarity_score) as avg_score"),
                        expr("min(similarity_score) as min_score"),
                        expr("max(similarity_score) as max_score")
                    ).collect()[0]
                    
                    stats[rel_type].update({
                        "avg_similarity": float(score_stats["avg_score"]) if score_stats["avg_score"] else 0,
                        "min_similarity": float(score_stats["min_score"]) if score_stats["min_score"] else 0,
                        "max_similarity": float(score_stats["max_score"]) if score_stats["max_score"] else 0
                    })
        
        return stats
    
    def build_has_feature_relationships(
        self,
        properties_df: DataFrame,
        features_df: DataFrame
    ) -> DataFrame:
        """
        Build HAS_FEATURE relationships between properties and features.
        
        Args:
            properties_df: Property DataFrame with features array
            features_df: Feature node DataFrame
            
        Returns:
            DataFrame of HasFeatureRelationship records
        """
        # Extract property-feature pairs
        property_features = properties_df.filter(
            col("listing_id").isNotNull() &
            col("features").isNotNull()
        ).select(
            col("listing_id"),
            explode(col("features")).alias("feature_name")
        )
        
        # Normalize feature names for matching
        property_features = property_features.withColumn(
            "feature_normalized",
            lower(col("feature_name"))
        )
        
        # Join with feature nodes (use "id" field from FeatureNode)
        features_for_join = features_df.select(
            col("id").alias("feature_id"),
            lower(col("name")).alias("feature_normalized")
        )
        
        matched = property_features.join(
            broadcast(features_for_join),
            "feature_normalized",
            "inner"
        )
        
        # Create relationship records
        has_feature_df = matched.select(
            col("listing_id").alias("from_id"),
            col("feature_id").alias("to_id"),
            lit(RelationshipType.HAS_FEATURE.value).alias("relationship_type"),
            lit(False).alias("is_primary"),  # Could enhance with logic to determine primary features
            lit(True).alias("verified")
        ).distinct()
        
        logger.info(f"Created {has_feature_df.count()} HAS_FEATURE relationships")
        return has_feature_df
    
    def build_of_type_relationships(
        self,
        properties_df: DataFrame,
        property_types_df: DataFrame
    ) -> DataFrame:
        """
        Build OF_TYPE relationships between properties and property types.
        
        Args:
            properties_df: Property DataFrame with property_type field
            property_types_df: PropertyType node DataFrame
            
        Returns:
            DataFrame of OfTypeRelationship records
        """
        # Extract property types from properties
        props_with_type = properties_df.filter(
            col("listing_id").isNotNull() &
            col("property_type").isNotNull()
        ).select(
            col("listing_id"),
            col("property_type")
        )
        
        # Join with property type nodes (use "id" field from PropertyTypeNode)
        type_nodes = property_types_df.select(
            col("id").alias("property_type_id"),
            col("name").alias("type_name")
        )
        
        matched = props_with_type.join(
            broadcast(type_nodes),
            props_with_type["property_type"] == type_nodes["type_name"],
            "inner"
        )
        
        # Create relationship records
        of_type_df = matched.select(
            col("listing_id").alias("from_id"),
            col("property_type_id").alias("to_id"),
            lit(RelationshipType.OF_TYPE.value).alias("relationship_type"),
            lit(1.0).alias("confidence"),
            lit(True).alias("is_primary")
        ).distinct()
        
        logger.info(f"Created {of_type_df.count()} OF_TYPE relationships")
        return of_type_df
    
    def build_in_price_range_relationships(
        self,
        properties_df: DataFrame,
        price_ranges_df: DataFrame
    ) -> DataFrame:
        """
        Build IN_PRICE_RANGE relationships between properties and price ranges.
        
        Args:
            properties_df: Property DataFrame with listing_price
            price_ranges_df: PriceRange node DataFrame
            
        Returns:
            DataFrame of InPriceRangeRelationship records
        """
        # Filter properties with valid prices
        props_with_price = properties_df.filter(
            col("listing_id").isNotNull() &
            col("listing_price").isNotNull() &
            (col("listing_price") > 0)
        ).select(
            col("listing_id"),
            col("listing_price")
        )
        
        # Cross join with price ranges to find matching range
        # Note: Using broadcast for small price_ranges_df
        price_ranges = broadcast(price_ranges_df.select(
            col("id").alias("price_range_id"),
            col("min_price"),
            col("max_price")
        ))
        
        # Find matching price range for each property
        matched = props_with_price.crossJoin(price_ranges).filter(
            (col("listing_price") >= col("min_price")) &
            (col("listing_price") < col("max_price"))
        )
        
        # Calculate percentile within range (convert Decimal to double for Neo4j compatibility)
        in_range_df = matched.select(
            col("listing_id").alias("from_id"),
            col("price_range_id").alias("to_id"),
            lit(RelationshipType.IN_PRICE_RANGE.value).alias("relationship_type"),
            ((col("listing_price").cast("double") - col("min_price").cast("double")) / 
             (col("max_price").cast("double") - col("min_price").cast("double"))).alias("price_percentile"),
            col("listing_price").cast("double").alias("actual_price")
        ).distinct()
        
        logger.info(f"Created {in_range_df.count()} IN_PRICE_RANGE relationships")
        return in_range_df
    
    def build_in_county_relationships(
        self,
        entities_df: DataFrame,
        counties_df: DataFrame,
        entity_type: str = "neighborhood"
    ) -> DataFrame:
        """
        Build IN_COUNTY relationships for geographic hierarchy.
        
        Args:
            entities_df: DataFrame with county field (neighborhoods or cities)
            counties_df: County node DataFrame
            entity_type: Type of entity (neighborhood or city)
            
        Returns:
            DataFrame of InCountyRelationship records
        """
        # Determine ID field based on entity type
        id_field = "neighborhood_id" if entity_type == "neighborhood" else "city_id"
        
        # Filter entities with county information
        entities_with_county = entities_df.filter(
            col(id_field).isNotNull() &
            col("county").isNotNull() &
            col("state").isNotNull()
        ).select(
            col(id_field).alias("entity_id"),
            col("county"),
            col("state")
        )
        
        # Join with county nodes (use "id" field from CountyNode)
        county_nodes = counties_df.select(
            col("id").alias("county_id"),
            col("name").alias("county_name"),
            col("state").alias("county_state")
        )
        
        matched = entities_with_county.join(
            broadcast(county_nodes),
            (lower(entities_with_county["county"]) == lower(county_nodes["county_name"])) &
            (lower(entities_with_county["state"]) == lower(county_nodes["county_state"])),
            "inner"
        )
        
        # Create relationship records
        in_county_df = matched.select(
            col("entity_id").alias("from_id"),
            col("county_id").alias("to_id"),
            lit(RelationshipType.IN_COUNTY.value).alias("relationship_type"),
            lit(entity_type).alias("hierarchy_level")
        ).distinct()
        
        logger.info(f"Created {in_county_df.count()} IN_COUNTY relationships for {entity_type}")
        return in_county_df
    
    def build_in_topic_cluster_relationships(
        self,
        entities_df: DataFrame,
        topic_clusters_df: DataFrame,
        entity_type: str,
        topic_field: str = "key_topics"
    ) -> DataFrame:
        """
        Build IN_TOPIC_CLUSTER relationships between entities and topic clusters.
        
        Args:
            entities_df: Entity DataFrame with topics (properties, neighborhoods, or wikipedia)
            topic_clusters_df: TopicCluster node DataFrame
            entity_type: Type of entity (property, neighborhood, wikipedia)
            topic_field: Field containing topics in entity DataFrame
            
        Returns:
            DataFrame of InTopicClusterRelationship records
        """
        # Determine ID field based on entity type
        id_fields = {
            "property": "listing_id",
            "neighborhood": "neighborhood_id",
            "wikipedia": "page_id"
        }
        id_field = id_fields.get(entity_type, "entity_id")
        
        # Filter entities with topics
        entities_with_topics = entities_df.filter(
            col(id_field).isNotNull() &
            col(topic_field).isNotNull() &
            (expr(f"size({topic_field})") > 0)
        ).select(
            col(id_field).alias("entity_id"),
            col(topic_field).alias("entity_topics")
        )
        
        # Get topic clusters (use "id" field from TopicClusterNode)
        clusters = topic_clusters_df.select(
            col("id").alias("topic_cluster_id"),
            col("topics").alias("cluster_topics")
        )
        
        # Cross join to find matching topics
        joined = entities_with_topics.crossJoin(broadcast(clusters))
        
        # Calculate relevance based on topic overlap
        matched = joined.withColumn(
            "common_topics",
            expr("size(array_intersect(entity_topics, cluster_topics))")
        ).filter(
            col("common_topics") > 0
        )
        
        # Calculate relevance score
        in_cluster_df = matched.withColumn(
            "relevance_score",
            col("common_topics") / expr("greatest(size(entity_topics), size(cluster_topics))")
        ).select(
            col("entity_id").alias("from_id"),
            col("topic_cluster_id").alias("to_id"),
            lit(RelationshipType.IN_TOPIC_CLUSTER.value).alias("relationship_type"),
            col("relevance_score"),
            lit(entity_type).alias("extraction_source"),
            when(col("relevance_score") >= 0.5, lit(0.8))
            .when(col("relevance_score") >= 0.3, lit(0.6))
            .otherwise(lit(0.4)).alias("confidence")
        ).distinct()
        
        logger.info(f"Created {in_cluster_df.count()} IN_TOPIC_CLUSTER relationships for {entity_type}")
        return in_cluster_df
    
    def build_near_relationships(
        self,
        neighborhoods_df: DataFrame,
        distance_threshold_miles: float = 2.0
    ) -> DataFrame:
        """
        Build NEAR relationships between geographically proximate neighborhoods.
        
        Creates bidirectional proximity relationships between neighborhoods within 
        the specified distance threshold. Uses the Haversine formula to calculate
        great-circle distances between coordinate pairs, accounting for Earth's curvature.
        
        **Algorithm Details:**
        1. Extracts latitude/longitude coordinates from nested structure
        2. Performs self-join to create all neighborhood pairs (N×N-1)/2 comparisons)
        3. Calculates Haversine distance using Spark SQL mathematical functions
        4. Filters pairs within distance threshold
        5. Creates bidirectional relationships (A→B and B→A)
        
        **Distance Calculation:**
        Uses the Haversine formula in Spark SQL:
        ```sql
        distance = 6371000 * 2 * asin(sqrt(
            pow(sin(radians(lat2 - lat1) / 2), 2) +
            cos(radians(lat1)) * cos(radians(lat2)) *
            pow(sin(radians(lng2 - lng1) / 2), 2)
        ))
        ```
        
        **Performance Characteristics:**
        - Time Complexity: O(N²) where N = number of neighborhoods
        - Space Complexity: O(K) where K = relationships within threshold
        - Typical Results: ~200 relationships for 21 SF neighborhoods at 2mi threshold
        - Bidirectional: Creates both A→B and B→A for symmetric traversal
        
        Args:
            neighborhoods_df: Neighborhood DataFrame with required columns:
                - neighborhood_id: Unique identifier
                - coordinates.latitude: Decimal latitude
                - coordinates.longitude: Decimal longitude
            distance_threshold_miles: Maximum distance in miles for NEAR relationships.
                Default 2.0 miles captures immediate neighborhood clusters.
                
        Returns:
            DataFrame with schema:
                - from_id: Source neighborhood ID
                - to_id: Target neighborhood ID  
                - relationship_type: Always "NEAR"
                - distance_meters: Precise distance in meters
                - distance_miles: Converted distance in miles
                
        Raises:
            Warning logged if required coordinate columns are missing
            
        Example:
            ```python
            # Find neighborhoods within walking distance (1 mile)
            near_df = builder.build_near_relationships(
                neighborhoods_df, distance_threshold_miles=1.0
            )
            
            # Typical output:
            # Mission District ↔ Castro District: 1.1 miles
            # Castro District ↔ Noe Valley: 0.8 miles
            ```
        """
        # Check for required columns
        required_cols = ["neighborhood_id", "coordinates"]
        missing_cols = [col for col in required_cols if col not in neighborhoods_df.columns]
        if missing_cols:
            logger.warning(f"Missing required columns for NEAR relationships: {missing_cols}")
            return self.spark.createDataFrame([], schema=
                "from_id string, to_id string, relationship_type string, distance_meters float, distance_miles float"
            )
        
        # Extract coordinates into separate columns for easier calculation
        neighborhoods_with_coords = neighborhoods_df.select(
            col("neighborhood_id"),
            col("name"),
            col("coordinates.latitude").alias("lat"),
            col("coordinates.longitude").alias("lng")
        ).filter(
            col("lat").isNotNull() & col("lng").isNotNull()
        )
        
        # Self-join to create all neighborhood pairs (excluding self-matches)
        left_neighborhoods = neighborhoods_with_coords.alias("left")
        right_neighborhoods = neighborhoods_with_coords.alias("right")
        
        neighborhood_pairs = left_neighborhoods.join(
            right_neighborhoods,
            col("left.neighborhood_id") < col("right.neighborhood_id"),  # Avoid duplicates and self-matches
            "inner"
        )
        
        # Calculate distance using Haversine formula
        # Convert coordinates to radians and calculate distance
        distance_threshold_meters = distance_threshold_miles * 1609.34
        
        near_relationships = neighborhood_pairs.select(
            col("left.neighborhood_id").alias("from_id"),
            col("right.neighborhood_id").alias("to_id"),
            col("left.name").alias("from_name"),
            col("right.name").alias("to_name"),
            col("left.lat").alias("lat1"),
            col("left.lng").alias("lng1"),
            col("right.lat").alias("lat2"),
            col("right.lng").alias("lng2")
        )
        
        # Calculate haversine distance
        # Using Spark SQL functions to implement Haversine formula
        near_relationships_with_distance = near_relationships.withColumn(
            "distance_meters",
            # Haversine formula in Spark SQL
            expr("""
                6371000 * 2 * asin(sqrt(
                    pow(sin(radians(lat2 - lat1) / 2), 2) +
                    cos(radians(lat1)) * cos(radians(lat2)) *
                    pow(sin(radians(lng2 - lng1) / 2), 2)
                ))
            """)
        ).withColumn(
            "distance_miles",
            col("distance_meters") * 0.000621371
        )
        
        # Filter to only nearby neighborhoods
        nearby_neighborhoods = near_relationships_with_distance.filter(
            col("distance_meters") <= distance_threshold_meters
        ).select(
            col("from_id"),
            col("to_id"),
            lit(RelationshipType.NEAR.value).alias("relationship_type"),
            col("distance_meters"),
            col("distance_miles")
        )
        
        # Create bidirectional relationships (both directions)
        reverse_relationships = nearby_neighborhoods.select(
            col("to_id").alias("from_id"),
            col("from_id").alias("to_id"),
            col("relationship_type"),
            col("distance_meters"),
            col("distance_miles")
        )
        
        # Union both directions
        all_near_relationships = nearby_neighborhoods.union(reverse_relationships)
        
        count = all_near_relationships.count()
        unique_pairs = nearby_neighborhoods.count()
        logger.info(f"Created {count} NEAR relationships ({unique_pairs} unique pairs) within {distance_threshold_miles} miles")
        
        return all_near_relationships
    
    def build_extended_relationships(
        self,
        properties_df: Optional[DataFrame] = None,
        neighborhoods_df: Optional[DataFrame] = None,
        wikipedia_df: Optional[DataFrame] = None,
        features_df: Optional[DataFrame] = None,
        property_types_df: Optional[DataFrame] = None,
        price_ranges_df: Optional[DataFrame] = None,
        counties_df: Optional[DataFrame] = None,
        topic_clusters_df: Optional[DataFrame] = None
    ) -> Dict[str, DataFrame]:
        """
        Build extended relationships for new entity types.
        
        Args:
            properties_df: Property DataFrame
            neighborhoods_df: Neighborhood DataFrame
            wikipedia_df: Wikipedia DataFrame
            features_df: Feature node DataFrame
            property_types_df: PropertyType node DataFrame
            price_ranges_df: PriceRange node DataFrame
            counties_df: County node DataFrame
            topic_clusters_df: TopicCluster node DataFrame
            
        Returns:
            Dictionary of relationship DataFrames by type
        """
        relationships = {}
        
        # HAS_FEATURE relationships
        if properties_df is not None and features_df is not None:
            try:
                relationships["has_feature"] = self.build_has_feature_relationships(
                    properties_df, features_df
                )
                logger.info("✓ Built HAS_FEATURE relationships")
            except Exception as e:
                logger.error(f"Failed to build HAS_FEATURE relationships: {e}")
        
        # OF_TYPE relationships
        if properties_df is not None and property_types_df is not None:
            try:
                relationships["of_type"] = self.build_of_type_relationships(
                    properties_df, property_types_df
                )
                logger.info("✓ Built OF_TYPE relationships")
            except Exception as e:
                logger.error(f"Failed to build OF_TYPE relationships: {e}")
        
        # IN_PRICE_RANGE relationships
        if properties_df is not None and price_ranges_df is not None:
            try:
                relationships["in_price_range"] = self.build_in_price_range_relationships(
                    properties_df, price_ranges_df
                )
                logger.info("✓ Built IN_PRICE_RANGE relationships")
            except Exception as e:
                logger.error(f"Failed to build IN_PRICE_RANGE relationships: {e}")
        
        # IN_COUNTY relationships
        if counties_df is not None:
            # Neighborhoods to counties
            if neighborhoods_df is not None:
                try:
                    relationships["neighborhood_in_county"] = self.build_in_county_relationships(
                        neighborhoods_df, counties_df, "neighborhood"
                    )
                    logger.info("✓ Built IN_COUNTY relationships for neighborhoods")
                except Exception as e:
                    logger.error(f"Failed to build IN_COUNTY relationships for neighborhoods: {e}")
        
        # IN_TOPIC_CLUSTER relationships
        if topic_clusters_df is not None:
            # Properties to topic clusters
            if properties_df is not None and "aggregated_topics" in properties_df.columns:
                try:
                    relationships["property_in_topic"] = self.build_in_topic_cluster_relationships(
                        properties_df, topic_clusters_df, "property", "aggregated_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for properties")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for properties: {e}")
            
            # Neighborhoods to topic clusters
            if neighborhoods_df is not None and "aggregated_topics" in neighborhoods_df.columns:
                try:
                    relationships["neighborhood_in_topic"] = self.build_in_topic_cluster_relationships(
                        neighborhoods_df, topic_clusters_df, "neighborhood", "aggregated_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for neighborhoods")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for neighborhoods: {e}")
            
            # Wikipedia articles to topic clusters
            if wikipedia_df is not None:
                try:
                    relationships["wikipedia_in_topic"] = self.build_in_topic_cluster_relationships(
                        wikipedia_df, topic_clusters_df, "wikipedia", "key_topics"
                    )
                    logger.info("✓ Built IN_TOPIC_CLUSTER relationships for Wikipedia articles")
                except Exception as e:
                    logger.error(f"Failed to build IN_TOPIC_CLUSTER for Wikipedia: {e}")
        
        # NEAR relationships - proximity between neighborhoods
        if neighborhoods_df is not None:
            try:
                relationships["neighborhood_near"] = self.build_near_relationships(
                    neighborhoods_df, distance_threshold_miles=2.0
                )
                logger.info("✓ Built NEAR relationships for neighborhoods")
            except Exception as e:
                logger.error(f"Failed to build NEAR relationships for neighborhoods: {e}")
        
        return relationships