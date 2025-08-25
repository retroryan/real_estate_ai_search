"""Data validator with constructor injection"""

import logging
from typing import List, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from core.query_executor import QueryExecutor
from data_sources import PropertyFileDataSource, WikipediaFileDataSource


class ValidationResult(BaseModel):
    """Validation result model"""
    is_valid: bool = Field(default=True)
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checks_passed: List[str] = Field(default_factory=list)
    
    def add_error(self, message: str) -> None:
        """Add an error and mark as invalid"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str) -> None:
        """Add a warning (doesn't affect validity)"""
        self.warnings.append(message)
    
    def add_passed(self, check_name: str) -> None:
        """Record a passed check"""
        self.checks_passed.append(check_name)


class DataValidator:
    """Validates data sources and database connectivity with injected dependencies"""
    
    def __init__(
        self,
        query_executor: QueryExecutor,
        property_source: PropertyFileDataSource,
        wikipedia_source: WikipediaFileDataSource
    ):
        """
        Initialize validator with injected dependencies
        
        Args:
            query_executor: Database query executor
            property_source: Property data source
            wikipedia_source: Wikipedia data source
        """
        self.query_executor = query_executor
        self.property_source = property_source
        self.wikipedia_source = wikipedia_source
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def validate_all(self) -> ValidationResult:
        """
        Perform all validation checks
        
        Returns:
            ValidationResult with status and details
        """
        result = ValidationResult()
        
        # Check Neo4j connectivity
        self.logger.info("Checking Neo4j connectivity...")
        if self._check_neo4j():
            result.add_passed("Neo4j connectivity")
        else:
            result.add_error("Neo4j database is not accessible")
        
        # Check property data
        self.logger.info("Checking property data sources...")
        prop_result = self._check_property_data()
        if prop_result.is_valid:
            result.add_passed("Property data sources")
        else:
            for error in prop_result.errors:
                result.add_error(f"Property data: {error}")
        for warning in prop_result.warnings:
            result.add_warning(f"Property data: {warning}")
        
        # Check Wikipedia data
        self.logger.info("Checking Wikipedia data sources...")
        wiki_result = self._check_wikipedia_data()
        if wiki_result.is_valid:
            result.add_passed("Wikipedia data sources")
        else:
            for error in wiki_result.errors:
                result.add_error(f"Wikipedia data: {error}")
        for warning in wiki_result.warnings:
            result.add_warning(f"Wikipedia data: {warning}")
        
        # Log summary
        self._log_summary(result)
        
        return result
    
    def _check_neo4j(self) -> bool:
        """
        Check Neo4j database connectivity
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Simple query to test connectivity
            query = "RETURN 1 as test"
            result = self.query_executor.execute_read(query)
            
            if result and result[0]['test'] == 1:
                self.logger.info("✅ Neo4j connection successful")
                
                # Get database stats
                stats = self.query_executor.get_stats()
                self.logger.info(f"  Total nodes: {stats.get('total_nodes', 0)}")
                self.logger.info(f"  Total relationships: {stats.get('total_relationships', 0)}")
                
                return True
            else:
                self.logger.error("❌ Neo4j query returned unexpected result")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Neo4j connection failed: {e}")
            return False
    
    def _check_property_data(self) -> ValidationResult:
        """
        Check property data sources
        
        Returns:
            ValidationResult for property data
        """
        result = ValidationResult()
        
        if not self.property_source.exists():
            result.add_error("Property data directory does not exist")
            return result
        
        # Check property files
        property_files = self.property_source.get_property_files()
        for city, file_path in property_files.items():
            if file_path.exists():
                try:
                    properties = self.property_source.load_properties(city)
                    if properties:
                        result.add_passed(f"{city} properties ({len(properties)} items)")
                        self.logger.info(f"  ✅ {city} properties: {len(properties)} items")
                    else:
                        result.add_warning(f"{city} properties file is empty")
                except Exception as e:
                    result.add_error(f"Failed to load {city} properties: {e}")
            else:
                result.add_warning(f"{city} properties file not found: {file_path}")
        
        # Check neighborhood files
        neighborhood_files = self.property_source.get_neighborhood_files()
        for city, file_path in neighborhood_files.items():
            if file_path.exists():
                try:
                    neighborhoods = self.property_source.load_neighborhoods(city)
                    if neighborhoods:
                        result.add_passed(f"{city} neighborhoods ({len(neighborhoods)} items)")
                        self.logger.info(f"  ✅ {city} neighborhoods: {len(neighborhoods)} items")
                    else:
                        result.add_warning(f"{city} neighborhoods file is empty")
                except Exception as e:
                    result.add_error(f"Failed to load {city} neighborhoods: {e}")
            else:
                result.add_warning(f"{city} neighborhoods file not found: {file_path}")
        
        return result
    
    def _check_wikipedia_data(self) -> ValidationResult:
        """
        Check Wikipedia data sources
        
        Returns:
            ValidationResult for Wikipedia data
        """
        result = ValidationResult()
        
        if not self.wikipedia_source.exists():
            result.add_warning("Wikipedia data not found (optional)")
            return result
        
        # Check Wikipedia database
        try:
            articles = self.wikipedia_source.load_articles()
            if articles:
                result.add_passed(f"Wikipedia articles ({len(articles)} items)")
                self.logger.info(f"  ✅ Wikipedia articles: {len(articles)} items")
            else:
                result.add_warning("No Wikipedia articles found")
            
            summaries = self.wikipedia_source.load_summaries()
            if summaries:
                result.add_passed(f"Wikipedia summaries ({len(summaries)} items)")
                self.logger.info(f"  ✅ Wikipedia summaries: {len(summaries)} items")
            else:
                result.add_warning("No Wikipedia summaries found")
            
            # Check HTML files
            html_files = self.wikipedia_source.list_html_files()
            if html_files:
                result.add_passed(f"Wikipedia HTML files ({len(html_files)} files)")
                self.logger.info(f"  ✅ Wikipedia HTML files: {len(html_files)} files")
            else:
                result.add_warning("No Wikipedia HTML files found")
                
        except Exception as e:
            result.add_error(f"Failed to check Wikipedia data: {e}")
        
        return result
    
    def _log_summary(self, result: ValidationResult) -> None:
        """
        Log validation summary
        
        Args:
            result: ValidationResult to summarize
        """
        self.logger.info("\n" + "="*60)
        self.logger.info("VALIDATION SUMMARY")
        self.logger.info("="*60)
        
        if result.is_valid:
            self.logger.info("✅ ALL VALIDATIONS PASSED")
        else:
            self.logger.info("❌ VALIDATION FAILED")
        
        if result.checks_passed:
            self.logger.info(f"\nPassed checks ({len(result.checks_passed)}):")
            for check in result.checks_passed:
                self.logger.info(f"  ✅ {check}")
        
        if result.errors:
            self.logger.error(f"\nErrors ({len(result.errors)}):")
            for error in result.errors:
                self.logger.error(f"  ❌ {error}")
        
        if result.warnings:
            self.logger.warning(f"\nWarnings ({len(result.warnings)}):")
            for warning in result.warnings:
                self.logger.warning(f"  ⚠️ {warning}")
        
        self.logger.info("="*60)