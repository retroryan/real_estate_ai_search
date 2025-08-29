"""Entity pipeline registry for dynamic pipeline selection."""

from typing import Dict, Type, Optional, Callable, Any
from pydantic import BaseModel, Field

from squack_pipeline.models import EntityType
from squack_pipeline.orchestrator.base_entity_orchestrator import BaseEntityOrchestrator
from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.loaders.connection import DuckDBConnectionManager
from squack_pipeline.utils.logging import PipelineLogger


class PipelineRegistration(BaseModel):
    """Registration information for an entity pipeline."""
    
    entity_type: EntityType = Field(
        ...,
        description="Entity type this pipeline handles"
    )
    
    orchestrator_class: Type[BaseEntityOrchestrator] = Field(
        ...,
        description="Orchestrator class for this entity"
    )
    
    description: str = Field(
        default="",
        description="Description of the pipeline"
    )
    
    version: str = Field(
        default="1.0.0",
        description="Version of the pipeline implementation"
    )
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class EntityPipelineRegistry:
    """Registry for entity-specific pipelines.
    
    This registry allows dynamic registration and retrieval of
    entity-specific pipeline orchestrators, enabling clean separation
    of entity processing logic.
    """
    
    _pipelines: Dict[EntityType, PipelineRegistration] = {}
    _logger = PipelineLogger.get_logger("EntityPipelineRegistry")
    
    @classmethod
    def register(
        cls,
        entity_type: EntityType,
        description: str = "",
        version: str = "1.0.0"
    ) -> Callable:
        """Decorator to register entity pipeline orchestrators.
        
        Args:
            entity_type: Entity type this orchestrator handles
            description: Optional description of the pipeline
            version: Version of the pipeline implementation
            
        Returns:
            Decorator function
            
        Example:
            @EntityPipelineRegistry.register(EntityType.PROPERTY)
            class PropertyPipelineOrchestrator(BaseEntityOrchestrator):
                ...
        """
        def decorator(orchestrator_class: Type[BaseEntityOrchestrator]) -> Type[BaseEntityOrchestrator]:
            # Validate the class inherits from BaseEntityOrchestrator
            if not issubclass(orchestrator_class, BaseEntityOrchestrator):
                raise TypeError(
                    f"{orchestrator_class.__name__} must inherit from BaseEntityOrchestrator"
                )
            
            # Create registration
            registration = PipelineRegistration(
                entity_type=entity_type,
                orchestrator_class=orchestrator_class,
                description=description or f"Pipeline for {entity_type.value} entities",
                version=version
            )
            
            # Register the pipeline
            cls._pipelines[entity_type] = registration
            
            cls._logger.info(
                f"Registered {orchestrator_class.__name__} for {entity_type.value} "
                f"(version {version})"
            )
            
            return orchestrator_class
        
        return decorator
    
    @classmethod
    def get_orchestrator(
        cls,
        entity_type: EntityType,
        settings: PipelineSettings,
        connection_manager: DuckDBConnectionManager
    ) -> BaseEntityOrchestrator:
        """Get orchestrator instance for a specific entity type.
        
        Args:
            entity_type: Entity type to get orchestrator for
            settings: Pipeline settings
            connection_manager: DuckDB connection manager
            
        Returns:
            Instantiated orchestrator for the entity type
            
        Raises:
            ValueError: If no pipeline is registered for the entity type
        """
        if entity_type not in cls._pipelines:
            available = ", ".join(str(et.value) for et in cls._pipelines.keys())
            raise ValueError(
                f"No pipeline registered for entity type '{entity_type.value}'. "
                f"Available types: {available}"
            )
        
        registration = cls._pipelines[entity_type]
        
        cls._logger.info(
            f"Creating {registration.orchestrator_class.__name__} instance "
            f"for {entity_type.value}"
        )
        
        # Instantiate the orchestrator
        orchestrator = registration.orchestrator_class(settings, connection_manager)
        
        return orchestrator
    
    @classmethod
    def get_registration(cls, entity_type: EntityType) -> Optional[PipelineRegistration]:
        """Get registration information for an entity type.
        
        Args:
            entity_type: Entity type to get registration for
            
        Returns:
            PipelineRegistration or None if not registered
        """
        return cls._pipelines.get(entity_type)
    
    @classmethod
    def is_registered(cls, entity_type: EntityType) -> bool:
        """Check if an entity type has a registered pipeline.
        
        Args:
            entity_type: Entity type to check
            
        Returns:
            True if registered, False otherwise
        """
        return entity_type in cls._pipelines
    
    @classmethod
    def list_registered(cls) -> Dict[EntityType, str]:
        """List all registered entity types and their descriptions.
        
        Returns:
            Dictionary mapping entity types to descriptions
        """
        return {
            entity_type: registration.description
            for entity_type, registration in cls._pipelines.items()
        }
    
    @classmethod
    def unregister(cls, entity_type: EntityType) -> bool:
        """Unregister a pipeline for an entity type.
        
        Args:
            entity_type: Entity type to unregister
            
        Returns:
            True if unregistered, False if not found
        """
        if entity_type in cls._pipelines:
            registration = cls._pipelines[entity_type]
            del cls._pipelines[entity_type]
            cls._logger.info(
                f"Unregistered {registration.orchestrator_class.__name__} "
                f"for {entity_type.value}"
            )
            return True
        return False
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered pipelines.
        
        This is mainly useful for testing.
        """
        cls._pipelines.clear()
        cls._logger.info("Cleared all pipeline registrations")
    
    @classmethod
    def validate_settings(
        cls,
        entity_type: EntityType,
        settings: PipelineSettings
    ) -> bool:
        """Validate that settings are appropriate for an entity type.
        
        Args:
            entity_type: Entity type to validate for
            settings: Pipeline settings to validate
            
        Returns:
            True if settings are valid
            
        Raises:
            ValueError: If validation fails
        """
        if not cls.is_registered(entity_type):
            raise ValueError(f"Entity type {entity_type.value} is not registered")
        
        # Basic validation - can be extended
        if not settings.data.source_path:
            raise ValueError("Source path must be configured")
        
        if settings.data.sample_size and settings.data.sample_size < 0:
            raise ValueError("Sample size must be non-negative")
        
        return True


# Auto-register existing orchestrators when module is imported
def auto_register_orchestrators():
    """Auto-register known orchestrators.
    
    This function is called when the module is imported to automatically
    register the standard orchestrators.
    """
    try:
        from squack_pipeline.orchestrator.property_orchestrator import PropertyPipelineOrchestrator
        from squack_pipeline.orchestrator.neighborhood_orchestrator import NeighborhoodPipelineOrchestrator
        from squack_pipeline.orchestrator.wikipedia_orchestrator import WikipediaPipelineOrchestrator
        
        # Register each orchestrator
        EntityPipelineRegistry.register(
            EntityType.PROPERTY,
            description="Pipeline for processing property real estate data",
            version="1.0.0"
        )(PropertyPipelineOrchestrator)
        
        EntityPipelineRegistry.register(
            EntityType.NEIGHBORHOOD,
            description="Pipeline for processing neighborhood demographic data",
            version="1.0.0"
        )(NeighborhoodPipelineOrchestrator)
        
        EntityPipelineRegistry.register(
            EntityType.WIKIPEDIA,
            description="Pipeline for processing Wikipedia article data",
            version="1.0.0"
        )(WikipediaPipelineOrchestrator)
        
    except ImportError as e:
        EntityPipelineRegistry._logger.warning(
            f"Could not auto-register orchestrators: {e}"
        )


# Run auto-registration when module is imported
auto_register_orchestrators()