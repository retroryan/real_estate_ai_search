"""Integration tests for validating the full data load to Parquet files.

Tests validate that all data sources are loaded and properly written to Parquet:
- Properties (SF and PC)
- Neighborhoods (SF and PC)
- Locations
- Wikipedia articles
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq
import pytest
from pydantic import BaseModel, Field

from squack_pipeline.config.settings import PipelineSettings

# Skip these tests until parquet writers are updated for new pipeline
pytestmark = pytest.mark.skip(reason="Parquet validation tests need update for new pipeline structure")


class ParquetValidationMetrics(BaseModel):
    """Metrics for Parquet file validation."""
    
    file_path: Path
    entity_type: str
    file_size_mb: float
    record_count: int
    column_count: int
    columns: List[str]
    null_columns: List[str]
    data_types: Dict[str, str]
    has_embeddings: bool = False
    embedding_dimensions: Optional[int] = None
    validation_passed: bool = False
    validation_errors: List[str] = Field(default_factory=list)
    

class TestFullLoadParquetValidation:
    """Integration tests for full data load parquet validation."""
    
    @pytest.fixture
    def output_directory(self) -> Path:
        """Get the output directory for parquet files."""
        settings = PipelineSettings.load_from_yaml(Path("squack_pipeline/config.yaml"))
        return settings.data.output_path
    
    @pytest.fixture
    def expected_entities(self) -> List[str]:
        """List of expected entity types in parquet output."""
        return ["properties", "neighborhoods", "locations", "wikipedia"]
    
    def find_latest_parquet_files(self, output_dir: Path) -> Dict[str, Path]:
        """Find the latest parquet files for each entity type."""
        parquet_files = {}
        
        if not output_dir.exists():
            return parquet_files
        
        # Find all parquet files
        for file_path in output_dir.glob("*.parquet"):
            # Parse entity type from filename (e.g., properties_development_1234567890.parquet)
            parts = file_path.stem.split("_")
            if len(parts) >= 2:
                entity_type = parts[0]
                
                # Keep only the latest file for each entity type
                if entity_type not in parquet_files:
                    parquet_files[entity_type] = file_path
                else:
                    # Compare timestamps (last part of filename)
                    existing_timestamp = int(parquet_files[entity_type].stem.split("_")[-1])
                    new_timestamp = int(file_path.stem.split("_")[-1])
                    if new_timestamp > existing_timestamp:
                        parquet_files[entity_type] = file_path
        
        return parquet_files
    
    def validate_parquet_file(self, file_path: Path, entity_type: str) -> ParquetValidationMetrics:
        """Validate a single parquet file."""
        metrics = ParquetValidationMetrics(
            file_path=file_path,
            entity_type=entity_type,
            file_size_mb=file_path.stat().st_size / (1024 * 1024),
            record_count=0,
            column_count=0,
            columns=[],
            null_columns=[],
            data_types={}
        )
        
        try:
            # Read parquet file
            df = pd.read_parquet(file_path)
            table = pq.read_table(file_path)
            
            # Basic metrics
            metrics.record_count = len(df)
            metrics.column_count = len(df.columns)
            metrics.columns = df.columns.tolist()
            metrics.data_types = {col: str(dtype) for col, dtype in df.dtypes.items()}
            
            # Find columns with all null values
            metrics.null_columns = df.columns[df.isnull().all()].tolist()
            
            # Check for embeddings
            embedding_columns = [col for col in df.columns if 'embedding' in col.lower()]
            if embedding_columns:
                metrics.has_embeddings = True
                # Check embedding dimensions
                for col in embedding_columns:
                    if not df[col].empty and df[col].iloc[0] is not None:
                        if hasattr(df[col].iloc[0], '__len__'):
                            metrics.embedding_dimensions = len(df[col].iloc[0])
                            break
            
            # Entity-specific validation
            validation_errors = self.validate_entity_specific(df, entity_type, metrics)
            metrics.validation_errors.extend(validation_errors)
            
            # Mark as passed if no errors
            metrics.validation_passed = len(metrics.validation_errors) == 0
            
        except Exception as e:
            metrics.validation_errors.append(f"Failed to read parquet file: {str(e)}")
        
        return metrics
    
    def validate_entity_specific(self, df: pd.DataFrame, entity_type: str, metrics: ParquetValidationMetrics) -> List[str]:
        """Perform entity-specific validation."""
        errors = []
        
        if entity_type == "properties":
            # Validate properties
            required_columns = ["listing_id", "price", "bedrooms", "bathrooms", "sqft"]
            for col in required_columns:
                if col not in df.columns:
                    errors.append(f"Missing required column: {col}")
            
            # Check record count expectations
            if metrics.record_count < 100:  # Should have at least 100 properties from SF and PC
                errors.append(f"Expected at least 100 properties, found {metrics.record_count}")
            
            # Check for both SF and PC data
            if "city" in df.columns:
                cities = df["city"].unique()
                if "San Francisco" not in cities and "Park City" not in cities:
                    errors.append("Expected data from both San Francisco and Park City")
            
            # Check enrichment columns from Gold tier
            enrichment_columns = ["value_category", "size_category", "age_category", "market_status"]
            missing_enrichments = [col for col in enrichment_columns if col not in df.columns]
            if missing_enrichments:
                errors.append(f"Missing Gold tier enrichment columns: {missing_enrichments}")
                
        elif entity_type == "neighborhoods":
            # Validate neighborhoods
            required_columns = ["neighborhood_id", "name", "city", "state"]
            for col in required_columns:
                if col not in df.columns:
                    errors.append(f"Missing required column: {col}")
            
            # Check record count (should have ~30 neighborhoods)
            if metrics.record_count < 20:
                errors.append(f"Expected at least 20 neighborhoods, found {metrics.record_count}")
            
            # Check for processed fields
            if "walkability_score" in df.columns or "transit_score" in df.columns:
                # Check for Gold tier processing
                gold_columns = ["income_category", "walkability_category", "school_category"]
                missing_gold = [col for col in gold_columns if col not in df.columns]
                if missing_gold:
                    errors.append(f"Missing Gold tier columns: {missing_gold}")
                    
        elif entity_type == "locations":
            # Validate locations
            if "location_id" not in df.columns and "id" not in df.columns:
                errors.append("Missing location identifier column")
            
            # Check for geographic data
            geo_columns = ["latitude", "longitude", "city", "state"]
            missing_geo = [col for col in geo_columns if col not in df.columns]
            if missing_geo:
                errors.append(f"Missing geographic columns: {missing_geo}")
                
        elif entity_type == "wikipedia":
            # Validate Wikipedia articles
            required_columns = ["page_id", "title"]
            for col in required_columns:
                if col not in df.columns:
                    errors.append(f"Missing required column: {col}")
            
            # Check record count (should have 557 articles)
            if metrics.record_count < 500:
                errors.append(f"Expected ~557 Wikipedia articles, found {metrics.record_count}")
            
            # Check for processing fields
            if "relevance_score" in df.columns or "relevance_category" in df.columns:
                # Gold tier processing was applied
                if "article_length" not in df.columns:
                    errors.append("Missing article_length categorization from Gold tier")
        
        return errors
    
    def test_all_entities_present(self, output_directory):
        """Test that parquet files exist for all expected entity types."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        missing_entities = []
        for entity in self.expected_entities():
            if entity not in parquet_files:
                missing_entities.append(entity)
        
        assert len(missing_entities) == 0, f"Missing parquet files for entities: {missing_entities}"
        
        print(f"\n✓ Found parquet files for all {len(self.expected_entities())} entity types")
        for entity, path in parquet_files.items():
            file_size = path.stat().st_size / (1024 * 1024)
            print(f"  - {entity}: {path.name} ({file_size:.2f} MB)")
    
    def test_properties_parquet_validation(self, output_directory):
        """Validate properties parquet file in detail."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        assert "properties" in parquet_files, "Properties parquet file not found"
        
        metrics = self.validate_parquet_file(parquet_files["properties"], "properties")
        
        print(f"\nProperties Parquet Validation:")
        print(f"  File: {metrics.file_path.name}")
        print(f"  Size: {metrics.file_size_mb:.2f} MB")
        print(f"  Records: {metrics.record_count}")
        print(f"  Columns: {metrics.column_count}")
        print(f"  Has embeddings: {metrics.has_embeddings}")
        
        if metrics.validation_errors:
            print(f"  Validation Errors:")
            for error in metrics.validation_errors:
                print(f"    - {error}")
        
        assert metrics.validation_passed, f"Properties validation failed: {metrics.validation_errors}"
        assert metrics.record_count >= 100, f"Expected at least 100 properties, found {metrics.record_count}"
        
        # Load and check data distribution
        df = pd.read_parquet(parquet_files["properties"])
        
        # Check cities
        if "city" in df.columns:
            cities = df["city"].value_counts()
            print(f"  City distribution:")
            for city, count in cities.items():
                print(f"    - {city}: {count}")
            assert "San Francisco" in cities.index or "Park City" in cities.index, "Missing expected cities"
        
        # Check enrichment
        if "value_category" in df.columns:
            value_categories = df["value_category"].value_counts()
            print(f"  Value categories: {value_categories.to_dict()}")
        
        print(f"✓ Properties parquet validation passed")
    
    def test_neighborhoods_parquet_validation(self, output_directory):
        """Validate neighborhoods parquet file."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        assert "neighborhoods" in parquet_files, "Neighborhoods parquet file not found"
        
        metrics = self.validate_parquet_file(parquet_files["neighborhoods"], "neighborhoods")
        
        print(f"\nNeighborhoods Parquet Validation:")
        print(f"  File: {metrics.file_path.name}")
        print(f"  Size: {metrics.file_size_mb:.2f} MB")
        print(f"  Records: {metrics.record_count}")
        print(f"  Columns: {metrics.column_count}")
        
        assert metrics.validation_passed, f"Neighborhoods validation failed: {metrics.validation_errors}"
        assert metrics.record_count >= 20, f"Expected at least 20 neighborhoods, found {metrics.record_count}"
        
        # Load and check data
        df = pd.read_parquet(parquet_files["neighborhoods"])
        
        # Check cities
        if "city" in df.columns:
            cities = df["city"].value_counts()
            print(f"  City distribution:")
            for city, count in cities.items():
                print(f"    - {city}: {count}")
        
        # Check for scoring fields
        score_columns = ["walkability_score", "transit_score", "school_rating"]
        available_scores = [col for col in score_columns if col in df.columns]
        print(f"  Available scores: {available_scores}")
        
        print(f"✓ Neighborhoods parquet validation passed")
    
    def test_wikipedia_parquet_validation(self, output_directory):
        """Validate Wikipedia parquet file."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        assert "wikipedia" in parquet_files, "Wikipedia parquet file not found"
        
        metrics = self.validate_parquet_file(parquet_files["wikipedia"], "wikipedia")
        
        print(f"\nWikipedia Parquet Validation:")
        print(f"  File: {metrics.file_path.name}")
        print(f"  Size: {metrics.file_size_mb:.2f} MB")
        print(f"  Records: {metrics.record_count}")
        print(f"  Columns: {metrics.column_count}")
        print(f"  Has embeddings: {metrics.has_embeddings}")
        
        assert metrics.validation_passed, f"Wikipedia validation failed: {metrics.validation_errors}"
        assert metrics.record_count >= 500, f"Expected ~557 Wikipedia articles, found {metrics.record_count}"
        
        # Load and check data
        df = pd.read_parquet(parquet_files["wikipedia"])
        
        # Check for key fields
        if "title" in df.columns:
            sample_titles = df["title"].head(5).tolist()
            print(f"  Sample titles: {sample_titles}")
        
        if "relevance_score" in df.columns:
            relevance_stats = df["relevance_score"].describe()
            print(f"  Relevance score stats:")
            print(f"    - Mean: {relevance_stats['mean']:.3f}")
            print(f"    - Min: {relevance_stats['min']:.3f}")
            print(f"    - Max: {relevance_stats['max']:.3f}")
        
        print(f"✓ Wikipedia parquet validation passed")
    
    def test_locations_parquet_if_exists(self, output_directory):
        """Validate locations parquet file if it exists."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        if "locations" not in parquet_files:
            pytest.skip("Locations parquet file not found (may not be processed)")
        
        metrics = self.validate_parquet_file(parquet_files["locations"], "locations")
        
        print(f"\nLocations Parquet Validation:")
        print(f"  File: {metrics.file_path.name}")
        print(f"  Size: {metrics.file_size_mb:.2f} MB")
        print(f"  Records: {metrics.record_count}")
        print(f"  Columns: {metrics.column_count}")
        
        if metrics.validation_errors:
            print(f"  Validation Errors:")
            for error in metrics.validation_errors:
                print(f"    - {error}")
        
        assert metrics.validation_passed, f"Locations validation failed: {metrics.validation_errors}"
        
        print(f"✓ Locations parquet validation passed")
    
    def test_cross_entity_relationships(self, output_directory):
        """Test relationships between entities in parquet files."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        # Load properties and neighborhoods if available
        if "properties" in parquet_files and "neighborhoods" in parquet_files:
            props_df = pd.read_parquet(parquet_files["properties"])
            hoods_df = pd.read_parquet(parquet_files["neighborhoods"])
            
            print(f"\nCross-Entity Relationship Validation:")
            
            # Check if properties have neighborhood_id
            if "neighborhood_id" in props_df.columns and "neighborhood_id" in hoods_df.columns:
                prop_neighborhood_ids = set(props_df["neighborhood_id"].dropna().unique())
                available_neighborhood_ids = set(hoods_df["neighborhood_id"].unique())
                
                matched_ids = prop_neighborhood_ids & available_neighborhood_ids
                unmatched_ids = prop_neighborhood_ids - available_neighborhood_ids
                
                match_rate = len(matched_ids) / len(prop_neighborhood_ids) * 100 if prop_neighborhood_ids else 0
                
                print(f"  Property-Neighborhood relationships:")
                print(f"    - Properties with neighborhood_id: {len(prop_neighborhood_ids)}")
                print(f"    - Available neighborhoods: {len(available_neighborhood_ids)}")
                print(f"    - Matched relationships: {len(matched_ids)}")
                print(f"    - Match rate: {match_rate:.1f}%")
                
                if unmatched_ids:
                    print(f"    - Unmatched neighborhood IDs: {list(unmatched_ids)[:5]}...")
            
            # Check if enrichment was applied (neighborhood data in properties)
            enrichment_columns = [col for col in props_df.columns if col.startswith("neighborhood_")]
            if enrichment_columns:
                print(f"  Property enrichment columns from neighborhoods: {enrichment_columns[:5]}")
                
                # Check data completeness
                for col in enrichment_columns[:3]:  # Check first 3 enrichment columns
                    non_null_count = props_df[col].notna().sum()
                    completeness = non_null_count / len(props_df) * 100
                    print(f"    - {col}: {completeness:.1f}% complete")
        
        print(f"✓ Cross-entity relationship validation completed")
    
    def test_data_quality_metrics(self, output_directory):
        """Generate comprehensive data quality metrics for all parquet files."""
        parquet_files = self.find_latest_parquet_files(output_directory)
        
        print(f"\n{'='*60}")
        print(f"COMPREHENSIVE DATA QUALITY REPORT")
        print(f"{'='*60}")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Output Directory: {output_directory}")
        print(f"{'='*60}")
        
        total_records = 0
        total_size_mb = 0
        all_metrics = {}
        
        for entity_type, file_path in parquet_files.items():
            metrics = self.validate_parquet_file(file_path, entity_type)
            all_metrics[entity_type] = metrics
            
            total_records += metrics.record_count
            total_size_mb += metrics.file_size_mb
            
            print(f"\n{entity_type.upper()}")
            print(f"{'-'*40}")
            print(f"  File: {metrics.file_path.name}")
            print(f"  Records: {metrics.record_count:,}")
            print(f"  Columns: {metrics.column_count}")
            print(f"  File Size: {metrics.file_size_mb:.2f} MB")
            print(f"  Validation: {'✓ PASSED' if metrics.validation_passed else '✗ FAILED'}")
            
            if metrics.has_embeddings:
                print(f"  Embeddings: Yes (dimension={metrics.embedding_dimensions})")
            
            if metrics.null_columns:
                print(f"  Empty columns: {metrics.null_columns[:3]}")
            
            if metrics.validation_errors:
                print(f"  Issues:")
                for error in metrics.validation_errors[:3]:
                    print(f"    - {error}")
        
        print(f"\n{'='*60}")
        print(f"SUMMARY")
        print(f"{'='*60}")
        print(f"Total Files: {len(parquet_files)}")
        print(f"Total Records: {total_records:,}")
        print(f"Total Size: {total_size_mb:.2f} MB")
        
        passed = sum(1 for m in all_metrics.values() if m.validation_passed)
        print(f"Validation: {passed}/{len(all_metrics)} passed")
        
        # Check overall completeness
        expected_entities = set(self.expected_entities())
        loaded_entities = set(parquet_files.keys())
        missing_entities = expected_entities - loaded_entities
        
        if missing_entities:
            print(f"Missing Entities: {missing_entities}")
        else:
            print(f"✓ All expected entities loaded successfully")
        
        print(f"{'='*60}")
        
        # Assert all validations passed
        failed_entities = [e for e, m in all_metrics.items() if not m.validation_passed]
        assert len(failed_entities) == 0, f"Validation failed for: {failed_entities}"


if __name__ == "__main__":
    # Allow running tests directly
    import sys
    
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])