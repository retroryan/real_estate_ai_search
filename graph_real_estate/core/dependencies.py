"""Dependency container classes for dependency injection"""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import logging
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from .config import AppConfig
from .query_executor import QueryExecutor


@dataclass
class DatabaseDependencies:
    """Container for database-related dependencies"""
    driver: Driver
    query_executor: QueryExecutor
    
    @classmethod
    def create(cls, config: AppConfig) -> "DatabaseDependencies":
        """
        Factory method to create database dependencies
        
        Args:
            config: Application configuration
            
        Returns:
            DatabaseDependencies instance
            
        Raises:
            ServiceUnavailable: If cannot connect to database
        """
        logger = logging.getLogger("DatabaseDependencies")
        
        try:
            # Create driver with configuration
            driver = GraphDatabase.driver(
                config.database.uri,
                auth=(config.database.user, config.database.password),
                max_connection_lifetime=config.database.max_connection_lifetime,
                max_connection_pool_size=config.database.max_connection_pool_size,
                connection_acquisition_timeout=config.database.connection_acquisition_timeout
            )
            
            # Verify connectivity
            driver.verify_connectivity()
            logger.info(f"Connected to Neo4j at {config.database.uri}")
            
            # Create query executor
            query_executor = QueryExecutor(
                driver=driver,
                database=config.database.database
            )
            
            return cls(
                driver=driver,
                query_executor=query_executor
            )
            
        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j at {config.database.uri}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating database dependencies: {e}")
            raise
    
    def cleanup(self) -> None:
        """Clean up database connections"""
        if self.driver:
            self.driver.close()
            logging.getLogger("DatabaseDependencies").info("Database connection closed")


@dataclass
class LoaderDependencies:
    """Container for all data loader dependencies"""
    validator: "DataValidator"
    geographic_loader: "GeographicLoader"
    wikipedia_loader: "WikipediaLoader"
    neighborhood_loader: "NeighborhoodLoader"
    property_loader: "PropertyLoader"
    similarity_loader: "SimilarityLoader"
    
    @classmethod
    def create(cls, database: DatabaseDependencies, config: AppConfig) -> "LoaderDependencies":
        """
        Factory method to create loader dependencies
        
        Args:
            database: Database dependencies
            config: Application configuration
            
        Returns:
            LoaderDependencies instance
        """
        # Import here to avoid circular dependencies
        from loaders.validator import DataValidator
        from loaders.geographic_loader import GeographicFoundationLoader
        from loaders.wikipedia_loader import WikipediaLoader
        from loaders.neighborhood_loader import NeighborhoodLoader
        from loaders.property_loader import PropertyLoader
        from loaders.similarity_loader import SimilarityLoader
        from data_sources import (
            PropertyFileDataSource,
            WikipediaFileDataSource,
            GeographicFileDataSource
        )
        
        # Create data sources
        property_source = PropertyFileDataSource(config.property.data_path)
        wikipedia_source = WikipediaFileDataSource(config.wikipedia.data_path)
        geographic_source = GeographicFileDataSource(config.geographic.data_path)
        
        # Create loaders with injected dependencies
        return cls(
            validator=DataValidator(
                query_executor=database.query_executor,
                property_source=property_source,
                wikipedia_source=wikipedia_source
            ),
            geographic_loader=GeographicFoundationLoader(
                query_executor=database.query_executor,
                config=config.geographic,
                data_source=geographic_source
            ),
            wikipedia_loader=WikipediaLoader(
                query_executor=database.query_executor,
                config=config.wikipedia,
                data_source=wikipedia_source
            ),
            neighborhood_loader=NeighborhoodLoader(
                query_executor=database.query_executor,
                config=config.property,
                data_source=property_source
            ),
            property_loader=PropertyLoader(
                query_executor=database.query_executor,
                config=config.property,
                loader_config=config.loaders,
                data_source=property_source
            ),
            similarity_loader=SimilarityLoader(
                query_executor=database.query_executor,
                config=config.similarity,
                loader_config=config.loaders
            )
        )


@dataclass
class SearchDependencies:
    """Container for search-related dependencies"""
    embedding_pipeline: "PropertyEmbeddingPipeline"
    vector_manager: "PropertyVectorManager"
    hybrid_search: "HybridPropertySearch"
    
    @classmethod
    def create(cls, database: DatabaseDependencies, config: AppConfig) -> "SearchDependencies":
        """
        Factory method to create search dependencies
        
        Args:
            database: Database dependencies
            config: Application configuration
            
        Returns:
            SearchDependencies instance
        """
        # Import here to avoid circular dependencies
        from vectors.embedding_pipeline import PropertyEmbeddingPipeline
        from vectors.vector_manager import PropertyVectorManager
        from vectors.hybrid_search import HybridPropertySearch
        
        # Create embedding pipeline
        embedding_pipeline = PropertyEmbeddingPipeline(
            driver=database.driver,
            model_name=config.search.embedding_model
        )
        
        # Create vector manager
        vector_manager = PropertyVectorManager(
            driver=database.driver,
            query_executor=database.query_executor
        )
        
        # Create hybrid search
        hybrid_search = HybridPropertySearch(
            query_executor=database.query_executor,
            embedding_pipeline=embedding_pipeline,
            vector_manager=vector_manager,
            config=config.search
        )
        
        return cls(
            embedding_pipeline=embedding_pipeline,
            vector_manager=vector_manager,
            hybrid_search=hybrid_search
        )


@dataclass
class AppDependencies:
    """Main application dependency container"""
    config: AppConfig
    database: DatabaseDependencies
    loaders: LoaderDependencies
    search: SearchDependencies
    
    @classmethod
    def create_from_config(cls, config_path: Path) -> "AppDependencies":
        """
        Factory method to create all application dependencies
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            AppDependencies instance with all dependencies initialized
        """
        logger = logging.getLogger("AppDependencies")
        logger.info(f"Loading configuration from {config_path}")
        
        # Load configuration
        config = AppConfig.from_file(config_path)
        
        # Create database dependencies
        logger.info("Creating database dependencies")
        database = DatabaseDependencies.create(config)
        
        # Create loader dependencies
        logger.info("Creating loader dependencies")
        loaders = LoaderDependencies.create(database, config)
        
        # Create search dependencies
        logger.info("Creating search dependencies")
        search = SearchDependencies.create(database, config)
        
        logger.info("All dependencies initialized successfully")
        
        return cls(
            config=config,
            database=database,
            loaders=loaders,
            search=search
        )
    
    def cleanup(self) -> None:
        """Clean up all resources"""
        logger = logging.getLogger("AppDependencies")
        logger.info("Cleaning up application dependencies")
        
        # Clean up database connections
        self.database.cleanup()
        
        logger.info("Cleanup complete")