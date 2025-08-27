# Clean Proposal: Property Relationships Index Population

## Executive Summary

The property_relationships index should be populated **outside** the main data pipeline by reading from already-indexed Elasticsearch data. This creates a clean separation of concerns and avoids the complexity of trying to denormalize data within the heavy processing pipeline.

## Core Principle: Read from ES, Write to ES

Instead of building relationships during the pipeline (when data is being transformed), we:
1. Let the pipeline populate individual indices (properties, neighborhoods, wikipedia)
2. Create a standalone script that reads from these indices
3. Build denormalized documents from the clean indexed data
4. Write back to property_relationships index

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Pipeline                            │
│  (Focuses on individual entity processing and indexing)      │
└─────────────────────────────────────────────────────────────┘
                              ↓
        ┌──────────────┬──────────────┬──────────────┐
        │ properties   │neighborhoods │  wikipedia   │
        │    index     │    index     │    index     │
        └──────────────┴──────────────┴──────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│           Standalone Relationship Builder                    │
│         (Reads from ES, builds relationships)                │
└─────────────────────────────────────────────────────────────┘
                              ↓
                  ┌──────────────────────┐
                  │property_relationships│
                  │       index          │
                  └──────────────────────┘
```

## Implementation Plan

### Phase 1: Create Standalone Builder Script

**File**: `real_estate_search/indexer/build_relationships.py`

```python
"""
Standalone script to build property_relationships index.
Reads from existing Elasticsearch indices and creates denormalized documents.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from elasticsearch import Elasticsearch, helpers
import logging

@dataclass
class RelationshipBuilder:
    """Builds denormalized property relationship documents."""
    
    def __init__(self, es_client: Elasticsearch):
        self.es = es_client
        self.logger = logging.getLogger(__name__)
    
    def build_all_relationships(self, batch_size: int = 100) -> int:
        """
        Build relationships for all properties.
        Returns count of documents created.
        """
        total_created = 0
        
        # Scroll through all properties
        for properties_batch in self._scroll_properties(batch_size):
            # Build relationships for this batch
            relationships = self._build_batch_relationships(properties_batch)
            
            # Bulk index to property_relationships
            if relationships:
                self._bulk_index_relationships(relationships)
                total_created += len(relationships)
                self.logger.info(f"Indexed {len(relationships)} relationships")
        
        return total_created
    
    def _scroll_properties(self, batch_size: int):
        """Scroll through all properties in batches."""
        query = {"query": {"match_all": {}}}
        
        for hit in helpers.scan(
            self.es,
            index="properties",
            query=query,
            size=batch_size
        ):
            yield hit["_source"]
    
    def _build_batch_relationships(self, properties: List[Dict]) -> List[Dict]:
        """Build relationship documents for a batch of properties."""
        relationships = []
        
        for prop in properties:
            # Get neighborhood data
            neighborhood = self._get_neighborhood(prop.get("neighborhood_id"))
            
            # Get Wikipedia articles from neighborhood correlations
            wikipedia_articles = []
            if neighborhood and "wikipedia_correlations" in neighborhood:
                wikipedia_articles = self._get_wikipedia_articles(
                    neighborhood["wikipedia_correlations"]
                )
            
            # Build denormalized document
            relationship = self._build_relationship_document(
                prop, neighborhood, wikipedia_articles
            )
            relationships.append(relationship)
        
        return relationships
    
    def _get_neighborhood(self, neighborhood_id: str) -> Optional[Dict]:
        """Fetch neighborhood by ID."""
        if not neighborhood_id:
            return None
        
        try:
            result = self.es.get(
                index="neighborhoods",
                id=neighborhood_id
            )
            return result["_source"]
        except:
            return None
    
    def _get_wikipedia_articles(self, correlations: Dict) -> List[Dict]:
        """Fetch Wikipedia articles based on correlations."""
        articles = []
        
        # Get primary article
        if "primary_wiki_article" in correlations:
            article = self._get_wikipedia_article(
                correlations["primary_wiki_article"]["page_id"]
            )
            if article:
                articles.append(article)
        
        # Get related articles (limit to 3)
        if "related_wiki_articles" in correlations:
            for wiki_ref in correlations["related_wiki_articles"][:3]:
                article = self._get_wikipedia_article(wiki_ref["page_id"])
                if article:
                    articles.append(article)
        
        return articles
    
    def _get_wikipedia_article(self, page_id: int) -> Optional[Dict]:
        """Fetch Wikipedia article by page_id."""
        try:
            result = self.es.search(
                index="wikipedia",
                body={
                    "query": {"term": {"page_id": page_id}},
                    "size": 1
                }
            )
            if result["hits"]["hits"]:
                return result["hits"]["hits"][0]["_source"]
        except:
            pass
        return None
    
    def _build_relationship_document(
        self, 
        property: Dict,
        neighborhood: Optional[Dict],
        wikipedia_articles: List[Dict]
    ) -> Dict:
        """Build the denormalized relationship document."""
        return {
            # Property fields
            "listing_id": property.get("listing_id"),
            "property_type": property.get("property_type"),
            "price": property.get("price"),
            "bedrooms": property.get("bedrooms"),
            "bathrooms": property.get("bathrooms"),
            "square_feet": property.get("square_feet"),
            "address": property.get("address"),
            "description": property.get("description"),
            "features": property.get("features", []),
            "amenities": property.get("amenities", []),
            
            # Embedded neighborhood
            "neighborhood": neighborhood,
            
            # Embedded Wikipedia articles
            "wikipedia_articles": wikipedia_articles,
            
            # Search optimization
            "combined_text": self._build_combined_text(
                property, neighborhood, wikipedia_articles
            )
        }
    
    def _build_combined_text(self, property, neighborhood, articles) -> str:
        """Build combined text for search optimization."""
        texts = []
        
        # Add property description
        if property.get("description"):
            texts.append(property["description"])
        
        # Add neighborhood description
        if neighborhood and neighborhood.get("description"):
            texts.append(neighborhood["description"])
        
        # Add Wikipedia summaries
        for article in articles:
            if article.get("short_summary"):
                texts.append(article["short_summary"])
        
        return " ".join(texts)
    
    def _bulk_index_relationships(self, relationships: List[Dict]):
        """Bulk index relationships to Elasticsearch."""
        actions = [
            {
                "_index": "property_relationships",
                "_id": rel["listing_id"],
                "_source": rel
            }
            for rel in relationships
        ]
        
        helpers.bulk(self.es, actions)
```

### Phase 2: Create Management Command

**File**: `real_estate_search/management_commands.py`

```python
def build_property_relationships(es_client: Elasticsearch):
    """Build property_relationships index from existing data."""
    
    print("Building property relationships index...")
    
    # Check that source indices exist and have data
    for index in ["properties", "neighborhoods", "wikipedia"]:
        if not es_client.indices.exists(index=index):
            print(f"Error: {index} index does not exist")
            return
        
        count = es_client.count(index=index)["count"]
        print(f"  {index}: {count} documents")
    
    # Build relationships
    builder = RelationshipBuilder(es_client)
    total = builder.build_all_relationships()
    
    print(f"\n✓ Created {total} relationship documents")
    
    # Verify
    count = es_client.count(index="property_relationships")["count"]
    print(f"✓ property_relationships index now has {count} documents")
```

### Phase 3: Integration Points

1. **Add to management.py**:
```python
# Add new command
if args.command == "build-relationships":
    build_property_relationships(es_client)
```

2. **Update README**:
```bash
# After running data pipeline:
python -m data_pipeline --config config.yaml

# Build property relationships:
python -m real_estate_search.management build-relationships

# Run demo:
python -m real_estate_search.management demo 11
```

## Key Advantages

### 1. **Clean Separation**
- Data pipeline remains focused on entity processing
- Relationship building is a separate concern
- No contamination between systems

### 2. **Simplicity**
- Easy to understand data flow
- Simple debugging (can inspect ES data directly)
- Can be run/re-run independently

### 3. **Flexibility**
- Can rebuild relationships without re-running pipeline
- Easy to modify relationship logic
- Can add filters or limits easily

### 4. **Data Quality**
- Works with clean, indexed data
- No issues with processed/transformed DataFrames
- Guaranteed field availability

### 5. **Performance**
- Can be parallelized with ES scroll/scan
- Bulk indexing for efficiency
- Can process in batches to manage memory

## Testing Strategy

1. **Unit Tests**:
   - Test relationship document building
   - Test ES query construction
   - Test field mapping

2. **Integration Tests**:
   - Test with small dataset (5 properties)
   - Verify all fields populated correctly
   - Test Wikipedia article inclusion

3. **End-to-End Test**:
   ```bash
   # Clear and rebuild
   python -m real_estate_search.management delete-index property_relationships
   python -m real_estate_search.management setup-indices
   python -m real_estate_search.management build-relationships
   python -m real_estate_search.management demo 11
   ```

## Migration Path

1. **Phase 1**: Implement standalone builder (1 hour)
2. **Phase 2**: Add management command (30 min)
3. **Phase 3**: Test with sample data (30 min)
4. **Phase 4**: Full integration test (30 min)
5. **Phase 5**: Documentation update (30 min)

## Success Criteria

- [ ] property_relationships index populated with denormalized documents
- [ ] All property fields preserved and accessible
- [ ] Neighborhood data properly embedded
- [ ] Wikipedia articles properly embedded
- [ ] Single-query demo working
- [ ] Performance improvement demonstrated

## Conclusion

This approach provides a **clean, simple, and maintainable** solution that:
- Keeps the data pipeline focused and clean
- Makes relationship building explicit and debuggable
- Works with proven, indexed data
- Can be extended easily for future requirements

The key insight is: **Don't try to denormalize during transformation - denormalize from clean, indexed data.**