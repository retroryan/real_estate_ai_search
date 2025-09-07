"""Test neighborhood-Wikipedia associations through all pipeline layers."""

import pytest
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from pathlib import Path
import json

from squack_pipeline_v2.core.connection import DuckDBConnectionManager


class WikipediaArticle(BaseModel):
    """Wikipedia article reference."""
    page_id: int
    title: str
    url: str
    confidence: float = 0.0


class NeighborhoodWikiCorrelation(BaseModel):
    """Neighborhood Wikipedia correlation data."""
    primary_wiki_article: Optional[WikipediaArticle] = None
    related_wiki_articles: List[WikipediaArticle] = Field(default_factory=list)
    parent_geography: Dict[str, Any] = Field(default_factory=dict)
    generated_by: str = ""
    generated_at: Optional[datetime] = None
    source: str = ""
    updated_by: str = ""


class NeighborhoodSource(BaseModel):
    """Source neighborhood data."""
    neighborhood_id: str
    name: str
    city: str
    state: str
    wikipedia_correlations: Optional[NeighborhoodWikiCorrelation] = None


class WikipediaAssociation(BaseModel):
    """Wikipedia article with neighborhood associations."""
    page_id: int
    title: str
    neighborhood_ids: List[str] = Field(default_factory=list)
    neighborhood_names: List[str] = Field(default_factory=list)
    primary_neighborhood_name: str = ""
    neighborhood_count: int = 0
    has_neighborhood_association: bool = False


class TestNeighborhoodWikipediaAssociations:
    """Test neighborhood-Wikipedia associations through pipeline."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create connection manager."""
        return DuckDBConnectionManager()
    
    def test_source_data_has_wikipedia_correlations(self):
        """Test that source neighborhood data contains Wikipedia correlations."""
        # Load SF neighborhoods
        sf_path = Path('real_estate_data/neighborhoods_sf.json')
        assert sf_path.exists(), "SF neighborhoods file should exist"
        
        with open(sf_path) as f:
            sf_data = json.load(f)
        
        # Parse and validate
        neighborhoods = []
        wiki_page_ids = set()
        
        for item in sf_data:
            # Use Pydantic for validation
            wiki_data = item.get('wikipedia_correlations')
            if wiki_data:
                # Create correlation model
                if wiki_data.get('primary_wiki_article'):
                    primary = wiki_data['primary_wiki_article']
                    article = WikipediaArticle(
                        page_id=primary['page_id'],
                        title=primary['title'],
                        url=primary['url'],
                        confidence=primary.get('confidence', 0.95)
                    )
                    wiki_page_ids.add(article.page_id)
                    
                    neighborhood = NeighborhoodSource(
                        neighborhood_id=item['neighborhood_id'],
                        name=item['name'],
                        city=item['city'],
                        state=item['state']
                    )
                    neighborhoods.append(neighborhood)
        
        assert len(neighborhoods) > 0, "Should have neighborhoods with Wikipedia correlations"
        assert len(wiki_page_ids) > 0, "Should have Wikipedia page IDs"
        
        # Expected page IDs for key neighborhoods
        expected_page_ids = {
            1978628,  # Pacific Heights
            525516,   # Mission District
            350903,   # Sunset District
            14084492, # Downtown SF (SOMA)
            351344    # Noe Valley
        }
        
        assert expected_page_ids.issubset(wiki_page_ids), \
            f"Missing expected page IDs: {expected_page_ids - wiki_page_ids}"
    
    def test_bronze_layer_loads_wikipedia_correlations(self, connection_manager):
        """Test that Bronze layer properly loads Wikipedia correlations."""
        conn = connection_manager.get_connection()
        
        # Check Bronze table exists
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'bronze_neighborhoods'
        """).fetchone()
        
        assert result[0] > 0, "bronze_neighborhoods table should exist"
        
        # Check wikipedia_correlations column exists and is populated
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM bronze_neighborhoods 
            WHERE wikipedia_correlations IS NOT NULL
        """).fetchone()
        
        neighborhoods_with_wiki = result[0]
        assert neighborhoods_with_wiki > 0, "Should have neighborhoods with Wikipedia correlations"
        
        # Verify structure using DuckDB's struct access
        result = conn.execute("""
            SELECT 
                neighborhood_id,
                name,
                wikipedia_correlations.primary_wiki_article.page_id as page_id,
                wikipedia_correlations.primary_wiki_article.title as title
            FROM bronze_neighborhoods
            WHERE wikipedia_correlations.primary_wiki_article.page_id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        assert len(result) > 0, "Should have neighborhoods with primary Wikipedia articles"
        
        # Validate with Pydantic
        for row in result:
            assert row[2] is not None, f"Neighborhood {row[1]} should have page_id"
            assert row[3] is not None, f"Neighborhood {row[1]} should have title"
    
    def test_silver_layer_extracts_wikipedia_page_ids(self, connection_manager):
        """Test that Silver layer extracts Wikipedia page IDs."""
        conn = connection_manager.get_connection()
        
        # Check Silver neighborhoods table
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'silver_neighborhoods'
        """).fetchone()
        
        assert result[0] > 0, "silver_neighborhoods table should exist"
        
        # Check for wikipedia_page_id column
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_name = 'silver_neighborhoods' 
            AND column_name = 'wikipedia_page_id'
        """).fetchone()
        
        assert result[0] > 0, "silver_neighborhoods should have wikipedia_page_id column"
        
        # Check populated values
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM silver_neighborhoods 
            WHERE wikipedia_page_id IS NOT NULL
        """).fetchone()
        
        assert result[0] > 0, "Should have neighborhoods with Wikipedia page IDs"
        
        # Get sample and validate
        result = conn.execute("""
            SELECT neighborhood_id, name, wikipedia_page_id 
            FROM silver_neighborhoods 
            WHERE wikipedia_page_id IS NOT NULL
            LIMIT 5
        """).fetchall()
        
        for row in result:
            assert row[2] > 0, f"Neighborhood {row[1]} should have valid page_id"
    
    def test_silver_wikipedia_has_neighborhood_associations(self, connection_manager):
        """Test that Silver Wikipedia layer has neighborhood associations."""
        conn = connection_manager.get_connection()
        
        # Check Silver Wikipedia table
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'silver_wikipedia'
        """).fetchone()
        
        assert result[0] > 0, "silver_wikipedia table should exist"
        
        # Check for neighborhood columns
        expected_columns = [
            'neighborhood_ids',
            'neighborhood_names', 
            'primary_neighborhood_name'
        ]
        
        for col in expected_columns:
            result = conn.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'silver_wikipedia' 
                AND column_name = '{col}'
            """).fetchone()
            
            assert result[0] > 0, f"silver_wikipedia should have {col} column"
        
        # Check for populated associations
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM silver_wikipedia 
            WHERE neighborhood_ids IS NOT NULL 
            AND ARRAY_LENGTH(neighborhood_ids) > 0
        """).fetchone()
        
        assert result[0] > 0, "Should have Wikipedia articles with neighborhood associations"
        
        # Validate specific expected associations
        result = conn.execute("""
            SELECT page_id, title, neighborhood_ids, neighborhood_names
            FROM silver_wikipedia
            WHERE page_id IN (1978628, 525516, 350903, 14084492, 351344)
        """).fetchall()
        
        associations = []
        for row in result:
            assoc = WikipediaAssociation(
                page_id=row[0],
                title=row[1],
                neighborhood_ids=row[2] or [],
                neighborhood_names=row[3] or [],
                neighborhood_count=len(row[2]) if row[2] else 0,
                has_neighborhood_association=bool(row[2])
            )
            associations.append(assoc)
        
        # Verify expected associations
        expected_associations = {
            1978628: 'sf-pac-heights-001',  # Pacific Heights
            525516: 'sf-mission-002',        # Mission District
            350903: 'sf-sunset-003',         # Sunset District
            14084492: 'sf-soma-004',         # Downtown SF/SOMA
            351344: 'sf-noe-valley-005'      # Noe Valley
        }
        
        for assoc in associations:
            if assoc.page_id in expected_associations:
                expected_id = expected_associations[assoc.page_id]
                assert expected_id in assoc.neighborhood_ids, \
                    f"Wikipedia article {assoc.title} (page_id={assoc.page_id}) " \
                    f"should be associated with neighborhood {expected_id}"
    
    def test_gold_wikipedia_has_neighborhood_fields(self, connection_manager):
        """Test that Gold Wikipedia layer has all neighborhood fields."""
        conn = connection_manager.get_connection()
        
        # Check Gold Wikipedia table
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_name = 'gold_wikipedia'
        """).fetchone()
        
        assert result[0] > 0, "gold_wikipedia table should exist"
        
        # Check for all required neighborhood columns
        expected_columns = [
            'neighborhood_ids',
            'neighborhood_names',
            'primary_neighborhood_name',
            'neighborhood_count',
            'has_neighborhood_association'
        ]
        
        for col in expected_columns:
            result = conn.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'gold_wikipedia' 
                AND column_name = '{col}'
            """).fetchone()
            
            assert result[0] > 0, f"gold_wikipedia should have {col} column"
        
        # Check for populated associations
        result = conn.execute("""
            SELECT COUNT(*) 
            FROM gold_wikipedia 
            WHERE has_neighborhood_association = true
        """).fetchone()
        
        articles_with_associations = result[0]
        assert articles_with_associations > 0, \
            "Should have Wikipedia articles with neighborhood associations"
        
        # Validate all associations are properly populated
        result = conn.execute("""
            SELECT 
                page_id,
                title,
                neighborhood_ids,
                neighborhood_names,
                primary_neighborhood_name,
                neighborhood_count,
                has_neighborhood_association
            FROM gold_wikipedia
            WHERE has_neighborhood_association = true
            LIMIT 10
        """).fetchall()
        
        for row in result:
            assoc = WikipediaAssociation(
                page_id=row[0],
                title=row[1],
                neighborhood_ids=row[2] or [],
                neighborhood_names=row[3] or [],
                primary_neighborhood_name=row[4] or "",
                neighborhood_count=row[5] or 0,
                has_neighborhood_association=row[6]
            )
            
            # Validate consistency
            assert len(assoc.neighborhood_ids) == assoc.neighborhood_count, \
                f"Article {assoc.title} neighborhood count mismatch"
            assert len(assoc.neighborhood_ids) == len(assoc.neighborhood_names), \
                f"Article {assoc.title} ids and names length mismatch"
            if assoc.neighborhood_names:
                assert assoc.primary_neighborhood_name == assoc.neighborhood_names[0], \
                    f"Article {assoc.title} primary name should be first in list"
    
    def test_expected_associations_count(self, connection_manager):
        """Test that we have the expected number of associations."""
        conn = connection_manager.get_connection()
        
        # Count expected from source
        expected_count = 0
        for file in ['real_estate_data/neighborhoods_sf.json', 'real_estate_data/neighborhoods_pc.json']:
            path = Path(file)
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                    for item in data:
                        wiki = item.get('wikipedia_correlations', {})
                        if wiki and wiki.get('primary_wiki_article'):
                            expected_count += 1
        
        # Count actual in Gold layer
        result = conn.execute("""
            SELECT COUNT(DISTINCT page_id) 
            FROM gold_wikipedia 
            WHERE has_neighborhood_association = true
        """).fetchone()
        
        actual_count = result[0]
        
        # We expect at least 17 associations based on source data
        assert actual_count >= 17, \
            f"Expected at least 17 Wikipedia articles with associations, got {actual_count}"
        
        # Detailed check - which specific articles are missing?
        result = conn.execute("""
            SELECT page_id 
            FROM gold_wikipedia 
            WHERE has_neighborhood_association = true
        """).fetchall()
        
        actual_page_ids = {row[0] for row in result}
        
        # These page IDs should definitely be present
        required_page_ids = {
            1978628,  # Pacific Heights
            525516,   # Mission District  
            350903,   # Sunset District
            14084492, # Downtown SF
            351344,   # Noe Valley
            3931239,  # Temescal
            2229448,  # Rockridge
            151252,   # Park City
            748238    # Deer Valley
        }
        
        missing = required_page_ids - actual_page_ids
        assert not missing, f"Missing required Wikipedia articles: {missing}"