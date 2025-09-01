"""Simple table name constants for the pipeline.

Just string constants - no over-engineering.
Following medallion architecture - Gold tables contain all business-ready data including embeddings.
"""

# Bronze layer tables
BRONZE_PROPERTIES = "bronze_properties"
BRONZE_NEIGHBORHOODS = "bronze_neighborhoods"
BRONZE_WIKIPEDIA = "bronze_wikipedia"

# Silver layer tables
SILVER_PROPERTIES = "silver_properties"
SILVER_NEIGHBORHOODS = "silver_neighborhoods"
SILVER_WIKIPEDIA = "silver_wikipedia"

# Gold layer tables (contain business data AND embeddings)
GOLD_PROPERTIES = "gold_properties"
GOLD_NEIGHBORHOODS = "gold_neighborhoods"
GOLD_WIKIPEDIA = "gold_wikipedia"


# Entity type configuration classes for orchestration
class EntityType:
    """Entity type configuration."""
    
    def __init__(self, name: str, bronze_table: str, silver_table: str, gold_table: str):
        self.name = name
        self.bronze_table = bronze_table
        self.silver_table = silver_table
        self.gold_table = gold_table


class EntityTypes:
    """Container for all entity types."""
    
    def __init__(self):
        self.property = EntityType(
            name="property",
            bronze_table=BRONZE_PROPERTIES,
            silver_table=SILVER_PROPERTIES,
            gold_table=GOLD_PROPERTIES
        )
        
        self.neighborhood = EntityType(
            name="neighborhood", 
            bronze_table=BRONZE_NEIGHBORHOODS,
            silver_table=SILVER_NEIGHBORHOODS,
            gold_table=GOLD_NEIGHBORHOODS
        )
        
        self.wikipedia = EntityType(
            name="wikipedia",
            bronze_table=BRONZE_WIKIPEDIA,
            silver_table=SILVER_WIKIPEDIA,
            gold_table=GOLD_WIKIPEDIA
        )
    
    def all_entities(self):
        """Get all entity types."""
        return [self.property, self.neighborhood, self.wikipedia]


# Global instance for easy import
ENTITY_TYPES = EntityTypes()