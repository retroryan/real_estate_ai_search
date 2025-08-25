"""
Enrichment Engine for enhanced entity processing with embedding data.

Provides advanced enrichment capabilities including lazy loading,
source data merging, and specialized processing for different entity types.
"""

from typing import Dict, Any, List, Optional, Set, Union, Callable
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..models import EntityType, SourceType
from ..storage.query_manager import QueryManager
from ..utils.logging import get_logger, PerformanceLogger
from .models import EnrichedEntity, CorrelationResult
from .correlation_manager import CorrelationManager

logger = get_logger(__name__)


class EnrichmentEngine:
    """
    Advanced enrichment engine for entities with embedding data.
    
    Provides lazy loading, specialized processing, and advanced enrichment
    capabilities for different entity types.
    """
    
    def __init__(
        self,
        correlation_manager: CorrelationManager,
        query_manager: QueryManager
    ):
        """
        Initialize enrichment engine.
        
        Args:
            correlation_manager: CorrelationManager for data correlation
            query_manager: QueryManager for ChromaDB operations
        """
        self.correlation_manager = correlation_manager
        self.query_manager = query_manager
        
        # Enrichment processors by entity type
        self._enrichment_processors: Dict[EntityType, Callable] = {
            EntityType.PROPERTY: self._enrich_property,
            EntityType.NEIGHBORHOOD: self._enrich_neighborhood,
            EntityType.WIKIPEDIA_ARTICLE: self._enrich_wikipedia_article,
            EntityType.WIKIPEDIA_SUMMARY: self._enrich_wikipedia_summary,
        }
        
        logger.info("Initialized EnrichmentEngine")
    
    def enrich_entity(
        self,
        entity: EnrichedEntity,
        include_embeddings: bool = False,
        include_similar: bool = False,
        similarity_threshold: float = 0.8
    ) -> EnrichedEntity:
        """
        Apply entity-specific enrichment to an entity.
        
        Args:
            entity: Entity to enrich
            include_embeddings: Whether to load embedding vectors
            include_similar: Whether to find similar entities
            similarity_threshold: Threshold for similarity search
            
        Returns:
            Enhanced EnrichedEntity with additional data
        """
        logger.debug(f"Enriching entity '{entity.entity_id}' of type {entity.entity_type}")
        
        try:
            with PerformanceLogger(f"Entity enrichment: {entity.entity_type}") as perf:
                
                # Apply entity-specific enrichment
                if entity.entity_type in self._enrichment_processors:
                    enriched_entity = self._enrichment_processors[entity.entity_type](
                        entity, include_embeddings, include_similar, similarity_threshold
                    )
                else:
                    logger.warning(f"No enrichment processor for entity type: {entity.entity_type}")
                    enriched_entity = entity
                
                # Add general enrichments
                enriched_entity = self._add_general_enrichments(enriched_entity)
                
                perf.add_metric("embedding_count", enriched_entity.total_embeddings)
                perf.add_metric("validation_passed", enriched_entity.validation_passed)
                
                logger.debug(f"Successfully enriched entity '{entity.entity_id}'")
                return enriched_entity
                
        except Exception as e:
            logger.error(f"Failed to enrich entity '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"Enrichment failed: {str(e)}")
            return entity
    
    def bulk_enrich(
        self,
        entities: List[EnrichedEntity],
        include_embeddings: bool = False,
        include_similar: bool = False,
        similarity_threshold: float = 0.8,
        parallel_workers: int = 4
    ) -> List[EnrichedEntity]:
        """
        Apply bulk enrichment to multiple entities in parallel.
        
        Args:
            entities: List of entities to enrich
            include_embeddings: Whether to load embedding vectors
            include_similar: Whether to find similar entities
            similarity_threshold: Threshold for similarity search
            parallel_workers: Number of parallel workers
            
        Returns:
            List of enriched entities
        """
        logger.info(f"Starting bulk enrichment for {len(entities)} entities")
        
        enriched_entities = []
        
        try:
            with PerformanceLogger(f"Bulk enrichment of {len(entities)} entities") as perf:
                
                if parallel_workers > 1:
                    # Parallel enrichment
                    with ThreadPoolExecutor(max_workers=parallel_workers) as executor:
                        future_to_entity = {
                            executor.submit(
                                self.enrich_entity,
                                entity,
                                include_embeddings,
                                include_similar,
                                similarity_threshold
                            ): entity for entity in entities
                        }
                        
                        for future in as_completed(future_to_entity):
                            try:
                                enriched_entity = future.result()
                                enriched_entities.append(enriched_entity)
                            except Exception as e:
                                entity = future_to_entity[future]
                                logger.error(f"Failed to enrich entity '{entity.entity_id}': {e}")
                                entity.add_validation_warning(f"Enrichment failed: {str(e)}")
                                enriched_entities.append(entity)
                else:
                    # Sequential enrichment
                    for entity in entities:
                        enriched_entity = self.enrich_entity(
                            entity, include_embeddings, include_similar, similarity_threshold
                        )
                        enriched_entities.append(enriched_entity)
                
                successful_count = sum(1 for e in enriched_entities if e.validation_passed)
                perf.add_metric("successful_enrichments", successful_count)
                perf.add_metric("success_rate", successful_count / len(entities) if entities else 0)
                
                logger.info(f"Bulk enrichment completed: {successful_count}/{len(entities)} successful")
                
        except Exception as e:
            logger.error(f"Bulk enrichment failed: {e}")
            # Return original entities if bulk processing fails
            return entities
        
        return enriched_entities
    
    def _enrich_property(
        self,
        entity: EnrichedEntity,
        include_embeddings: bool,
        include_similar: bool,
        similarity_threshold: float
    ) -> EnrichedEntity:
        """Apply property-specific enrichment."""
        
        try:
            source_data = entity.source_data.copy()
            
            # Calculate derived property metrics
            if 'price' in source_data and 'square_feet' in source_data:
                try:
                    price = float(source_data['price'])
                    sqft = float(source_data['square_feet'])
                    if sqft > 0:
                        source_data['price_per_sqft'] = round(price / sqft, 2)
                except (ValueError, TypeError):
                    pass
            
            # Enhance neighborhood information
            if 'neighborhood_id' in source_data:
                neighborhood_info = self._get_neighborhood_context(source_data['neighborhood_id'])
                if neighborhood_info:
                    source_data['neighborhood_context'] = neighborhood_info
            
            # Add property features analysis
            if 'features' in source_data and isinstance(source_data['features'], list):
                source_data['feature_count'] = len(source_data['features'])
                source_data['has_premium_features'] = any(
                    feature.lower() in ['pool', 'garage', 'fireplace', 'ac', 'balcony']
                    for feature in source_data['features']
                )
            
            # Find similar properties if requested
            if include_similar:
                similar_properties = self._find_similar_properties(
                    entity, similarity_threshold
                )
                source_data['similar_properties'] = similar_properties
            
            # Update entity with enriched data
            entity.source_data = source_data
            
        except Exception as e:
            logger.error(f"Property enrichment failed for '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"Property enrichment failed: {str(e)}")
        
        return entity
    
    def _enrich_neighborhood(
        self,
        entity: EnrichedEntity,
        include_embeddings: bool,
        include_similar: bool,
        similarity_threshold: float
    ) -> EnrichedEntity:
        """Apply neighborhood-specific enrichment."""
        
        try:
            source_data = entity.source_data.copy()
            
            # Calculate neighborhood statistics
            property_stats = self._get_neighborhood_property_stats(entity.entity_id)
            if property_stats:
                source_data['property_statistics'] = property_stats
            
            # Add demographic analysis
            if 'demographics' in source_data and isinstance(source_data['demographics'], dict):
                demographics = source_data['demographics']
                source_data['demographic_diversity_score'] = self._calculate_diversity_score(demographics)
            
            # Enhance amenity information
            if 'amenities' in source_data and isinstance(source_data['amenities'], list):
                source_data['amenity_count'] = len(source_data['amenities'])
                source_data['amenity_categories'] = self._categorize_amenities(source_data['amenities'])
            
            # Find similar neighborhoods if requested
            if include_similar:
                similar_neighborhoods = self._find_similar_neighborhoods(
                    entity, similarity_threshold
                )
                source_data['similar_neighborhoods'] = similar_neighborhoods
            
            # Update entity with enriched data
            entity.source_data = source_data
            
        except Exception as e:
            logger.error(f"Neighborhood enrichment failed for '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"Neighborhood enrichment failed: {str(e)}")
        
        return entity
    
    def _enrich_wikipedia_article(
        self,
        entity: EnrichedEntity,
        include_embeddings: bool,
        include_similar: bool,
        similarity_threshold: float
    ) -> EnrichedEntity:
        """Apply Wikipedia article-specific enrichment."""
        
        try:
            source_data = entity.source_data.copy()
            
            # Analyze article content
            if 'full_text' in source_data:
                text_stats = self._analyze_wikipedia_text(source_data['full_text'])
                source_data['content_analysis'] = text_stats
            
            # Extract location information
            location_info = self._extract_location_info(source_data)
            if location_info:
                source_data['location_context'] = location_info
            
            # Add article metadata analysis
            if 'relevance_score' in source_data:
                source_data['relevance_category'] = self._categorize_relevance(
                    float(source_data.get('relevance_score', 0))
                )
            
            # Find related Wikipedia articles if requested
            if include_similar:
                related_articles = self._find_related_wikipedia_articles(
                    entity, similarity_threshold
                )
                source_data['related_articles'] = related_articles
            
            # Update entity with enriched data
            entity.source_data = source_data
            
        except Exception as e:
            logger.error(f"Wikipedia article enrichment failed for '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"Wikipedia enrichment failed: {str(e)}")
        
        return entity
    
    def _enrich_wikipedia_summary(
        self,
        entity: EnrichedEntity,
        include_embeddings: bool,
        include_similar: bool,
        similarity_threshold: float
    ) -> EnrichedEntity:
        """Apply Wikipedia summary-specific enrichment."""
        
        try:
            source_data = entity.source_data.copy()
            
            # Analyze summary quality
            if 'summary' in source_data:
                summary_quality = self._analyze_summary_quality(source_data['summary'])
                source_data['summary_quality'] = summary_quality
            
            # Process key topics
            if 'key_topics' in source_data and source_data['key_topics']:
                topics = source_data['key_topics'].split(',') if isinstance(source_data['key_topics'], str) else []
                source_data['topic_count'] = len(topics)
                source_data['processed_topics'] = [topic.strip() for topic in topics]
            
            # Analyze confidence scores
            if 'overall_confidence' in source_data:
                confidence = float(source_data.get('overall_confidence', 0))
                source_data['confidence_category'] = self._categorize_confidence(confidence)
            
            # Find similar summaries if requested
            if include_similar:
                similar_summaries = self._find_similar_summaries(
                    entity, similarity_threshold
                )
                source_data['similar_summaries'] = similar_summaries
            
            # Update entity with enriched data
            entity.source_data = source_data
            
        except Exception as e:
            logger.error(f"Wikipedia summary enrichment failed for '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"Summary enrichment failed: {str(e)}")
        
        return entity
    
    def _add_general_enrichments(self, entity: EnrichedEntity) -> EnrichedEntity:
        """Add general enrichments applicable to all entity types."""
        
        try:
            # Add embedding quality metrics
            entity.source_data['embedding_quality'] = {
                'total_embeddings': entity.total_embeddings,
                'chunk_completeness': entity.is_complete,
                'text_coverage': len(entity.reconstructed_text) if entity.reconstructed_text else 0,
                'has_multi_chunk': entity.chunk_count > 1
            }
            
            # Add processing metadata
            entity.source_data['processing_metadata'] = {
                'enriched_at': entity.enriched_at.isoformat(),
                'source_files_count': len(entity.source_files),
                'validation_status': entity.validation_passed
            }
            
        except Exception as e:
            logger.error(f"General enrichment failed for '{entity.entity_id}': {e}")
            entity.add_validation_warning(f"General enrichment failed: {str(e)}")
        
        return entity
    
    # Helper methods for specific enrichments
    
    def _get_neighborhood_context(self, neighborhood_id: str) -> Optional[Dict[str, Any]]:
        """Get contextual information about a neighborhood."""
        try:
            # Use correlation manager to get neighborhood data
            neighborhood_data = self.correlation_manager._load_source_data(
                neighborhood_id, EntityType.NEIGHBORHOOD, SourceType.NEIGHBORHOOD_JSON
            )
            
            if neighborhood_data:
                return {
                    'name': neighborhood_data.get('neighborhood_name'),
                    'median_price': neighborhood_data.get('median_price'),
                    'amenity_count': len(neighborhood_data.get('amenities', []))
                }
        except Exception as e:
            logger.error(f"Failed to get neighborhood context for '{neighborhood_id}': {e}")
        
        return None
    
    def _find_similar_properties(self, entity: EnrichedEntity, threshold: float) -> List[Dict[str, Any]]:
        """Find similar properties using embeddings."""
        # This would use the query manager to find similar embeddings
        # Implementation would depend on having access to the original text for similarity search
        return []
    
    def _find_similar_neighborhoods(self, entity: EnrichedEntity, threshold: float) -> List[Dict[str, Any]]:
        """Find similar neighborhoods using embeddings."""
        return []
    
    def _find_related_wikipedia_articles(self, entity: EnrichedEntity, threshold: float) -> List[Dict[str, Any]]:
        """Find related Wikipedia articles using embeddings."""
        return []
    
    def _find_similar_summaries(self, entity: EnrichedEntity, threshold: float) -> List[Dict[str, Any]]:
        """Find similar Wikipedia summaries using embeddings."""
        return []
    
    def _get_neighborhood_property_stats(self, neighborhood_id: str) -> Optional[Dict[str, Any]]:
        """Calculate property statistics for a neighborhood."""
        # This would analyze properties in the neighborhood
        # Implementation would require cross-referencing property data
        return None
    
    def _calculate_diversity_score(self, demographics: Dict[str, Any]) -> float:
        """Calculate demographic diversity score."""
        # Simple diversity calculation based on demographic distribution
        if not demographics:
            return 0.0
            
        try:
            total = sum(float(v) for v in demographics.values() if isinstance(v, (int, float, str)) and str(v).replace('.', '').isdigit())
            if total == 0:
                return 0.0
                
            # Calculate entropy-based diversity
            diversity = 0.0
            for value in demographics.values():
                if isinstance(value, (int, float, str)) and str(value).replace('.', '').isdigit():
                    proportion = float(value) / total
                    if proportion > 0:
                        diversity -= proportion * (proportion.bit_length() if proportion > 0 else 0)
            
            return min(1.0, diversity / 3.0)  # Normalize to 0-1 range
            
        except Exception:
            return 0.0
    
    def _categorize_amenities(self, amenities: List[str]) -> Dict[str, List[str]]:
        """Categorize amenities into different types."""
        categories = {
            'transportation': [],
            'recreation': [],
            'shopping': [],
            'education': [],
            'healthcare': [],
            'other': []
        }
        
        # Simple keyword-based categorization
        category_keywords = {
            'transportation': ['transit', 'bus', 'train', 'subway', 'metro'],
            'recreation': ['park', 'gym', 'sports', 'pool', 'recreation'],
            'shopping': ['mall', 'store', 'shopping', 'market', 'grocery'],
            'education': ['school', 'university', 'college', 'library'],
            'healthcare': ['hospital', 'clinic', 'medical', 'health']
        }
        
        for amenity in amenities:
            amenity_lower = amenity.lower()
            categorized = False
            
            for category, keywords in category_keywords.items():
                if any(keyword in amenity_lower for keyword in keywords):
                    categories[category].append(amenity)
                    categorized = True
                    break
            
            if not categorized:
                categories['other'].append(amenity)
        
        return categories
    
    def _analyze_wikipedia_text(self, text: str) -> Dict[str, Any]:
        """Analyze Wikipedia article text content."""
        if not text:
            return {}
        
        return {
            'character_count': len(text),
            'word_count': len(text.split()),
            'paragraph_count': text.count('\n\n') + 1,
            'has_infobox': '[edit]' in text or '{{' in text,
            'estimated_reading_time': len(text.split()) / 200  # Average reading speed
        }
    
    def _extract_location_info(self, source_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract enhanced location information."""
        location_info = {}
        
        if 'latitude' in source_data and 'longitude' in source_data:
            location_info['coordinates'] = {
                'lat': source_data['latitude'],
                'lon': source_data['longitude']
            }
        
        if 'best_city' in source_data and source_data['best_city']:
            location_info['city'] = source_data['best_city']
            
        if 'best_state' in source_data and source_data['best_state']:
            location_info['state'] = source_data['best_state']
        
        return location_info if location_info else None
    
    def _categorize_relevance(self, relevance_score: float) -> str:
        """Categorize relevance score into meaningful categories."""
        if relevance_score >= 0.8:
            return 'high'
        elif relevance_score >= 0.5:
            return 'medium'
        elif relevance_score >= 0.2:
            return 'low'
        else:
            return 'minimal'
    
    def _analyze_summary_quality(self, summary: str) -> Dict[str, Any]:
        """Analyze the quality of a Wikipedia summary."""
        if not summary:
            return {'quality': 'empty'}
        
        word_count = len(summary.split())
        sentence_count = summary.count('.') + summary.count('!') + summary.count('?')
        
        quality_metrics = {
            'word_count': word_count,
            'sentence_count': sentence_count,
            'avg_sentence_length': word_count / max(1, sentence_count),
            'has_specific_details': any(keyword in summary.lower() for keyword in ['population', 'area', 'founded', 'located']),
        }
        
        # Overall quality assessment
        if word_count > 100 and sentence_count > 3 and quality_metrics['has_specific_details']:
            quality_metrics['quality'] = 'high'
        elif word_count > 50 and sentence_count > 1:
            quality_metrics['quality'] = 'medium'
        else:
            quality_metrics['quality'] = 'low'
        
        return quality_metrics
    
    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence score into meaningful categories."""
        if confidence >= 0.9:
            return 'very_high'
        elif confidence >= 0.7:
            return 'high'
        elif confidence >= 0.5:
            return 'medium'
        elif confidence >= 0.3:
            return 'low'
        else:
            return 'very_low'