"""
Loader for creating similarity relationships and enriching the knowledge graph.

This loader implements Phase 6 of the geographic knowledge graph:
- Property similarity calculations and SIMILAR_TO relationships
- Neighborhood connections based on lifestyle and Wikipedia topics
- Geographic proximity relationships with distance calculations
- Knowledge graph enrichment through topic-based clustering
"""

import math
import json
from typing import List, Dict, Set, Tuple, Optional, Any
from collections import defaultdict
from itertools import combinations

from src.loaders.base import BaseLoader
from src.models.similarity import (
    PropertySimilarity,
    NeighborhoodConnection,
    GeographicProximity,
    TopicCluster,
    SimilarityLoadResult,
    SimilarityCalculationConfig,
    SimilarityMethod,
    ProximityType
)


class SimilarityLoader(BaseLoader):
    """Loader for creating similarity relationships and knowledge graph enrichment."""
    
    def __init__(self, config: Optional[SimilarityCalculationConfig] = None):
        super().__init__()
        self.config = config or SimilarityCalculationConfig()
        self.result = SimilarityLoadResult()
    
    def load(self) -> SimilarityLoadResult:
        """Execute all similarity calculations and relationship creation."""
        self.logger.info("Starting Phase 6: Relationship Enhancement and Similarity Calculations")
        
        start_time = self._get_current_time()
        
        try:
            # Step 1: Calculate property similarities
            self.logger.info("Step 1: Calculating property similarities...")
            self._calculate_property_similarities()
            
            # Step 2: Create neighborhood connections
            self.logger.info("Step 2: Creating neighborhood connections...")
            self._create_neighborhood_connections()
            
            # Step 3: Calculate geographic proximities
            self.logger.info("Step 3: Calculating geographic proximities...")
            self._calculate_geographic_proximities()
            
            # Step 4: Create topic-based clusters
            self.logger.info("Step 4: Creating topic-based clusters...")
            self._create_topic_clusters()
            
            # Step 5: Build recommendation paths
            self.logger.info("Step 5: Building recommendation paths...")
            self._build_recommendation_paths()
            
            self.result.calculation_time_seconds = self._get_current_time() - start_time
            self.result.calculate_averages()
            
            self.logger.info(f"Phase 6 completed successfully in {self.result.calculation_time_seconds:.2f} seconds")
            self.logger.info(f"Created {self.result.property_similarities_created} property similarities")
            self.logger.info(f"Created {self.result.neighborhood_connections_created} neighborhood connections")
            self.logger.info(f"Created {self.result.proximity_relationships_created} proximity relationships")
            self.logger.info(f"Created {self.result.topic_clusters_created} topic clusters")
            
        except Exception as e:
            self.result.add_error(f"Phase 6 failed: {str(e)}")
            self.logger.error(f"Phase 6 failed: {str(e)}")
            raise
        
        return self.result
    
    def _calculate_property_similarities(self):
        """Use vector search to find similar properties efficiently using k-NN."""
        
        # First check if vector index exists
        # Verify vector index exists
        check_index_query = """
        SHOW INDEXES YIELD name, type
        WHERE name = 'property_embeddings' AND type CONTAINS 'VECTOR'
        RETURN name
        """
        index_result = self.execute_query(check_index_query)
        
        if not index_result:
            raise RuntimeError("Vector index 'property_embeddings' not found. Run create_embeddings.py first.")
        
        # Get all properties with embeddings
        query = """
        MATCH (p:Property)
        WHERE p.descriptionEmbedding IS NOT NULL
        RETURN p.listing_id as listing_id, 
               p.listing_price as price,
               p.bedrooms as bedrooms,
               p.bathrooms as bathrooms,
               p.square_feet as square_feet,
               p.neighborhood_id as neighborhood_id
        """
        
        properties = self.execute_query(query)
        self.result.properties_processed = len(properties)
        self.logger.info(f"Processing {len(properties)} properties with embeddings using k-NN")
        
        similarities_created = 0
        
        for prop in properties:
            # Use vector index to find k most similar properties
            knn_query = """
            MATCH (source:Property {listing_id: $listing_id})
            WHERE source.descriptionEmbedding IS NOT NULL
            CALL db.index.vector.queryNodes(
                'property_embeddings',
                20,  // Find top 20 similar
                source.descriptionEmbedding
            ) YIELD node as target, score as vector_similarity
            WHERE target.listing_id <> $listing_id
            AND vector_similarity > $threshold
            
            // Calculate additional similarity components
            WITH source, target, vector_similarity,
                 abs(source.listing_price - target.listing_price) / 
                    CASE 
                        WHEN source.listing_price > target.listing_price 
                        THEN source.listing_price 
                        ELSE target.listing_price 
                    END as price_diff,
                 CASE 
                    WHEN source.bedrooms = target.bedrooms THEN 0.2
                    WHEN abs(source.bedrooms - target.bedrooms) = 1 THEN 0.1
                    ELSE 0
                 END as bedroom_similarity,
                 CASE
                    WHEN source.neighborhood_id IS NOT NULL 
                    AND source.neighborhood_id = target.neighborhood_id THEN 0.2
                    ELSE 0
                 END as location_bonus
            
            // Calculate composite score
            WITH source, target,
                 vector_similarity,
                 vector_similarity * 0.5 +          // 50% from embeddings
                 (1 - price_diff) * 0.2 +          // 20% from price
                 bedroom_similarity +                // 20% from size
                 location_bonus                     // 10% from location
                 as composite_score
            
            WHERE composite_score > $final_threshold
            
            // Create similarity relationship
            MERGE (source)-[r:SIMILAR_TO]-(target)
            SET r.similarity_score = composite_score,
                r.vector_similarity = vector_similarity,
                r.method = 'knn_composite',
                r.updated_at = datetime()
            
            RETURN count(r) as created
            """
            
            try:
                result = self.execute_query(knn_query, {
                    'listing_id': prop['listing_id'],
                    'threshold': 0.7,  # Vector similarity threshold
                    'final_threshold': self.config.property_similarity_threshold
                })
                
                if result:
                    created = result[0]['created']
                    similarities_created += created
                    
            except Exception as e:
                # No fallbacks - vector search is required
                self.logger.error(f"Vector search failed: {e}")
                raise RuntimeError(f"k-NN vector search failed. Ensure Neo4j supports vector indexes: {e}")
        
        self.result.property_similarities_created = similarities_created
        self.logger.info(f"Created {similarities_created} similarity relationships using k-NN")
        
        if similarities_created > 0:
            self.result.avg_property_similarity = self._calculate_average_similarity_score()
    
    
    def _calculate_property_similarity(self, prop_a: Dict, prop_b: Dict) -> PropertySimilarity:
        """Calculate comprehensive similarity between two properties."""
        
        # Price similarity (normalized)
        price_a = float(prop_a['price'] or 0)
        price_b = float(prop_b['price'] or 0)
        price_similarity = self._calculate_price_similarity(price_a, price_b)
        
        # Size similarity (square footage + bedrooms + bathrooms)
        size_similarity = self._calculate_size_similarity(prop_a, prop_b)
        
        # Feature similarity (Jaccard index)
        features_a = set(prop_a['features'] or [])
        features_b = set(prop_b['features'] or [])
        feature_similarity = self._calculate_jaccard_similarity(features_a, features_b)
        
        # Location similarity (neighborhood and city)
        location_similarity = self._calculate_location_similarity(prop_a, prop_b)
        
        # Type similarity (exact match)
        type_a = prop_a['property_type'] or ''
        type_b = prop_b['property_type'] or ''
        type_similarity = 1.0 if type_a == type_b else 0.0
        
        # Calculate composite similarity using config weights
        composite_score = (
            price_similarity * self.config.price_weight +
            size_similarity * self.config.size_weight +
            feature_similarity * self.config.feature_weight +
            location_similarity * self.config.location_weight +
            type_similarity * self.config.type_weight
        )
        
        # Apply same neighborhood bonus
        if prop_a['neighborhood_id'] == prop_b['neighborhood_id'] and prop_a['neighborhood_id']:
            composite_score += self.config.same_neighborhood_bonus
            composite_score = min(composite_score, 1.0)
        
        # Create similarity object
        shared_features = list(features_a.intersection(features_b))
        similarity_reasons = self._generate_similarity_reasons(
            price_similarity, size_similarity, feature_similarity, 
            location_similarity, type_similarity, shared_features
        )
        
        return PropertySimilarity(
            property_a=prop_a['listing_id'],
            property_b=prop_b['listing_id'],
            similarity_score=composite_score,
            price_similarity=price_similarity,
            size_similarity=size_similarity,
            feature_similarity=feature_similarity,
            location_similarity=location_similarity,
            type_similarity=type_similarity,
            method=SimilarityMethod.COMPOSITE,
            shared_features=shared_features,
            similarity_reasons=similarity_reasons
        )
    
    def _calculate_price_similarity(self, price_a: float, price_b: float) -> float:
        """Calculate price similarity with normalization."""
        if price_a <= 0 or price_b <= 0:
            return 0.0
        
        price_diff = abs(price_a - price_b)
        max_price = max(price_a, price_b)
        
        if max_price == 0:
            return 1.0
        
        similarity = 1.0 - (price_diff / max_price)
        return max(0.0, similarity)
    
    def _calculate_size_similarity(self, prop_a: Dict, prop_b: Dict) -> float:
        """Calculate size similarity based on square footage, bedrooms, and bathrooms."""
        similarities = []
        
        # Square footage similarity
        sqft_a = float(prop_a['square_footage'] or 0)
        sqft_b = float(prop_b['square_footage'] or 0)
        if sqft_a > 0 and sqft_b > 0:
            sqft_diff = abs(sqft_a - sqft_b)
            max_sqft = max(sqft_a, sqft_b)
            sqft_sim = 1.0 - (sqft_diff / max_sqft)
            similarities.append(max(0.0, sqft_sim))
        
        # Bedrooms similarity
        bed_a = int(prop_a['bedrooms'] or 0)
        bed_b = int(prop_b['bedrooms'] or 0)
        if bed_a > 0 and bed_b > 0:
            bed_diff = abs(bed_a - bed_b)
            bed_sim = 1.0 - (bed_diff / max(bed_a, bed_b))
            similarities.append(max(0.0, bed_sim))
        
        # Bathrooms similarity
        bath_a = float(prop_a['bathrooms'] or 0)
        bath_b = float(prop_b['bathrooms'] or 0)
        if bath_a > 0 and bath_b > 0:
            bath_diff = abs(bath_a - bath_b)
            bath_sim = 1.0 - (bath_diff / max(bath_a, bath_b))
            similarities.append(max(0.0, bath_sim))
        
        return sum(similarities) / len(similarities) if similarities else 0.0
    
    def _calculate_jaccard_similarity(self, set_a: Set, set_b: Set) -> float:
        """Calculate Jaccard similarity coefficient between two sets."""
        if not set_a and not set_b:
            return 1.0
        
        intersection = set_a.intersection(set_b)
        union = set_a.union(set_b)
        
        return len(intersection) / len(union) if union else 0.0
    
    def _calculate_location_similarity(self, prop_a: Dict, prop_b: Dict) -> float:
        """Calculate location similarity based on neighborhood and city."""
        # Same neighborhood = highest similarity
        if (prop_a['neighborhood_id'] == prop_b['neighborhood_id'] and 
            prop_a['neighborhood_id'] is not None):
            return 1.0
        
        # Same city = medium similarity
        if (prop_a['city'] == prop_b['city'] and 
            prop_a['city'] is not None):
            return 0.6
        
        # Different cities = low similarity
        return 0.2
    
    def _generate_similarity_reasons(self, price_sim: float, size_sim: float, 
                                   feature_sim: float, location_sim: float, 
                                   type_sim: float, shared_features: List[str]) -> List[str]:
        """Generate human-readable explanations for similarity score."""
        reasons = []
        
        if price_sim > 0.7:
            reasons.append("Similar pricing")
        if size_sim > 0.7:
            reasons.append("Comparable size")
        if feature_sim > 0.5:
            reasons.append(f"{len(shared_features)} shared features")
        if location_sim > 0.8:
            reasons.append("Same neighborhood")
        elif location_sim > 0.5:
            reasons.append("Same city")
        if type_sim > 0.9:
            reasons.append("Same property type")
        
        return reasons
    
    def _create_property_similarity_relationship(self, similarity: PropertySimilarity):
        """Create SIMILAR_TO relationship between properties with optimized query."""
        query = """
        MATCH (a:Property {listing_id: $prop_a})
        USING INDEX a:Property(listing_id)
        MATCH (b:Property {listing_id: $prop_b})
        USING INDEX b:Property(listing_id)
        WHERE NOT EXISTS((a)-[:SIMILAR_TO]-(b))
        CREATE (a)-[r:SIMILAR_TO]->(b)
        SET r.similarity_score = $score,
            r.price_similarity = $price_sim,
            r.size_similarity = $size_sim,
            r.feature_similarity = $feature_sim,
            r.location_similarity = $location_sim,
            r.type_similarity = $type_sim,
            r.method = $method,
            r.shared_features = $shared_features,
            r.similarity_reasons = $reasons,
            r.created_at = datetime()
        """
        
        self.execute_query(query, {
            'prop_a': similarity.property_a,
            'prop_b': similarity.property_b,
            'score': similarity.similarity_score,
            'price_sim': similarity.price_similarity,
            'size_sim': similarity.size_similarity,
            'feature_sim': similarity.feature_similarity,
            'location_sim': similarity.location_similarity,
            'type_sim': similarity.type_similarity,
            'method': similarity.method.value,
            'shared_features': similarity.shared_features,
            'reasons': similarity.similarity_reasons
        })
    
    def _calculate_average_similarity_score(self) -> float:
        """Calculate average similarity score from created relationships."""
        query = """
        MATCH ()-[r:SIMILAR_TO]->()
        RETURN avg(r.similarity_score) as avg_score
        """
        
        result = self.execute_query(query)
        return float(result[0]['avg_score']) if result else 0.0
    
    def _create_neighborhood_connections(self):
        """Create NEAR relationships between neighborhoods based on multiple factors."""
        
        # Get all neighborhoods with their attributes
        query = """
        MATCH (n:Neighborhood)
        OPTIONAL MATCH (n)<-[:DESCRIBES]-(w:Wikipedia)
        OPTIONAL MATCH (n)<-[:IN_NEIGHBORHOOD]-(p:Property)
        RETURN n.neighborhood_id as neighborhood_id,
               n.city as city,
               n.lifestyle_tags as lifestyle_tags,
               n.median_home_price as median_price,
               n.latitude as latitude,
               n.longitude as longitude,
               collect(DISTINCT w.key_topics) as wikipedia_topics,
               avg(p.listing_price) as avg_property_price
        """
        
        neighborhoods = self.execute_query(query)
        self.result.neighborhoods_processed = len(neighborhoods)
        
        connections_created = 0
        
        # Compare all neighborhood pairs
        for n1, n2 in combinations(neighborhoods, 2):
            connection = self._calculate_neighborhood_connection(n1, n2)
            
            if connection.connection_strength >= self.config.neighborhood_connection_threshold:
                # Create NEAR relationship
                self._create_neighborhood_connection_relationship(connection)
                connections_created += 1
        
        self.result.neighborhood_connections_created = connections_created
        
        if connections_created > 0:
            self.result.avg_neighborhood_connection = self._calculate_average_neighborhood_connection()
    
    def _calculate_neighborhood_connection(self, n1: Dict, n2: Dict) -> NeighborhoodConnection:
        """Calculate connection strength between two neighborhoods."""
        
        # Geographic proximity (same city bonus)
        geographic_proximity = 1.0 if n1['city'] == n2['city'] else 0.3
        
        # Lifestyle similarity
        lifestyle_tags_1 = set(n1['lifestyle_tags'] or [])
        lifestyle_tags_2 = set(n2['lifestyle_tags'] or [])
        lifestyle_similarity = self._calculate_jaccard_similarity(lifestyle_tags_1, lifestyle_tags_2)
        
        # Wikipedia topic overlap
        topics_1 = self._flatten_topic_lists(n1['wikipedia_topics'])
        topics_2 = self._flatten_topic_lists(n2['wikipedia_topics'])
        topic_overlap = self._calculate_jaccard_similarity(topics_1, topics_2)
        
        # Price range similarity
        price_1 = float(n1['median_price'] or n1['avg_property_price'] or 0)
        price_2 = float(n2['median_price'] or n2['avg_property_price'] or 0)
        price_similarity = self._calculate_price_similarity(price_1, price_2)
        
        # Calculate distance if coordinates available
        distance_km = None
        if all([n1['latitude'], n1['longitude'], n2['latitude'], n2['longitude']]):
            distance_km = self._calculate_haversine_distance(
                float(n1['latitude']), float(n1['longitude']),
                float(n2['latitude']), float(n2['longitude'])
            )
            # Adjust geographic proximity based on distance
            if distance_km <= self.config.max_neighborhood_distance_km:
                geographic_proximity = min(1.0, 1.0 - (distance_km / self.config.max_neighborhood_distance_km))
            else:
                geographic_proximity = 0.0
        
        # Composite connection strength
        connection_strength = (
            geographic_proximity * 0.3 +
            lifestyle_similarity * 0.3 +
            topic_overlap * 0.25 +
            price_similarity * 0.15
        )
        
        return NeighborhoodConnection(
            neighborhood_a=n1['neighborhood_id'],
            neighborhood_b=n2['neighborhood_id'],
            connection_strength=connection_strength,
            geographic_proximity=geographic_proximity,
            lifestyle_similarity=lifestyle_similarity,
            price_range_similarity=price_similarity,
            wikipedia_topic_overlap=topic_overlap,
            shared_lifestyle_tags=list(lifestyle_tags_1.intersection(lifestyle_tags_2)),
            shared_wikipedia_topics=list(topics_1.intersection(topics_2)),
            distance_km=distance_km
        )
    
    def _flatten_topic_lists(self, topic_lists: List[str]) -> Set[str]:
        """Flatten and normalize Wikipedia topic lists."""
        topics = set()
        for topic_list in topic_lists:
            if topic_list:
                # Split comma-separated topics and clean them
                for topic in topic_list.split(','):
                    topic = topic.strip().lower()
                    if topic:
                        topics.add(topic)
        return topics
    
    def _create_neighborhood_connection_relationship(self, connection: NeighborhoodConnection):
        """Create NEAR relationship between neighborhoods with optimized query."""
        query = """
        MATCH (a:Neighborhood {neighborhood_id: $n_a})
        USING INDEX a:Neighborhood(neighborhood_id)
        MATCH (b:Neighborhood {neighborhood_id: $n_b})
        USING INDEX b:Neighborhood(neighborhood_id)
        WHERE NOT EXISTS((a)-[:NEAR]-(b))
        CREATE (a)-[r:NEAR]->(b)
        SET r.connection_strength = $strength,
            r.geographic_proximity = $geo_prox,
            r.lifestyle_similarity = $lifestyle_sim,
            r.price_range_similarity = $price_sim,
            r.wikipedia_topic_overlap = $topic_overlap,
            r.shared_lifestyle_tags = $shared_lifestyle,
            r.shared_wikipedia_topics = $shared_topics,
            r.distance_km = $distance,
            r.created_at = datetime()
        """
        
        self.execute_query(query, {
            'n_a': connection.neighborhood_a,
            'n_b': connection.neighborhood_b,
            'strength': connection.connection_strength,
            'geo_prox': connection.geographic_proximity,
            'lifestyle_sim': connection.lifestyle_similarity,
            'price_sim': connection.price_range_similarity,
            'topic_overlap': connection.wikipedia_topic_overlap,
            'shared_lifestyle': connection.shared_lifestyle_tags,
            'shared_topics': connection.shared_wikipedia_topics,
            'distance': connection.distance_km
        })
    
    def _calculate_average_neighborhood_connection(self) -> float:
        """Calculate average neighborhood connection strength."""
        query = """
        MATCH ()-[r:NEAR]->()
        RETURN avg(r.connection_strength) as avg_strength
        """
        
        result = self.execute_query(query)
        return float(result[0]['avg_strength']) if result else 0.0
    
    def _calculate_geographic_proximities(self):
        """Create proximity relationships based on geographic distance."""
        
        # Get all entities with coordinates (properties and neighborhoods)
        query = """
        MATCH (e)
        WHERE (e:Property OR e:Neighborhood) AND e.latitude IS NOT NULL AND e.longitude IS NOT NULL
        RETURN labels(e)[0] as entity_type,
               e.listing_id as property_id,
               e.neighborhood_id as neighborhood_id,
               e.latitude as latitude,
               e.longitude as longitude
        ORDER BY entity_type, coalesce(e.listing_id, e.neighborhood_id)
        """
        
        entities = self.execute_query(query)
        proximities_created = 0
        total_distance = 0.0
        walking_distance_count = 0
        
        # Calculate proximities between all entity pairs
        for i, entity_a in enumerate(entities):
            for entity_b in entities[i+1:]:
                distance_km = self._calculate_haversine_distance(
                    float(entity_a['latitude']), float(entity_a['longitude']),
                    float(entity_b['latitude']), float(entity_b['longitude'])
                )
                
                if distance_km <= self.config.max_proximity_distance_km:
                    proximity = GeographicProximity(
                        entity_a=entity_a['property_id'] or entity_a['neighborhood_id'],
                        entity_b=entity_b['property_id'] or entity_b['neighborhood_id'],
                        entity_type=f"{entity_a['entity_type']}-{entity_b['entity_type']}",
                        distance_km=distance_km,
                        distance_miles=distance_km * 0.621371
                    )
                    
                    self._create_proximity_relationship(proximity, entity_a['entity_type'], entity_b['entity_type'])
                    proximities_created += 1
                    total_distance += distance_km
                    
                    if proximity.within_walking_distance:
                        walking_distance_count += 1
        
        self.result.proximity_relationships_created = proximities_created
        self.result.walking_distance_pairs = walking_distance_count
        
        if proximities_created > 0:
            self.result.avg_distance_km = total_distance / proximities_created
    
    def _calculate_haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates using Haversine formula."""
        # Convert latitude and longitude from degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Haversine formula
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of earth in kilometers
        r = 6371
        
        return c * r
    
    def _create_proximity_relationship(self, proximity: GeographicProximity, 
                                     entity_type_a: str, entity_type_b: str):
        """Create NEAR_BY relationship between geographically close entities."""
        
        # Determine node labels and ID fields
        label_a = entity_type_a
        label_b = entity_type_b
        id_field_a = 'listing_id' if entity_type_a == 'Property' else 'neighborhood_id'
        id_field_b = 'listing_id' if entity_type_b == 'Property' else 'neighborhood_id'
        
        query = f"""
        MATCH (a:{label_a} {{{id_field_a}: $entity_a}})
        MATCH (b:{label_b} {{{id_field_b}: $entity_b}})
        WHERE NOT EXISTS((a)-[:NEAR_BY]-(b))
        CREATE (a)-[r:NEAR_BY]->(b)
        SET r.distance_km = $distance_km,
            r.distance_miles = $distance_miles,
            r.proximity_type = $proximity_type,
            r.within_walking_distance = $walking,
            r.within_driving_distance = $driving,
            r.created_at = datetime()
        """
        
        self.execute_query(query, {
            'entity_a': proximity.entity_a,
            'entity_b': proximity.entity_b,
            'distance_km': proximity.distance_km,
            'distance_miles': proximity.distance_miles,
            'proximity_type': proximity.proximity_type.value,
            'walking': proximity.within_walking_distance,
            'driving': proximity.within_driving_distance
        })
    
    def _create_topic_clusters(self):
        """Create topic-based clusters from Wikipedia data."""
        
        # Get all Wikipedia topics and their associated entities
        # Handle key_topics as an array (which it already is)
        query = """
        MATCH (w:WikipediaArticle)-[:DESCRIBES]->(n:Neighborhood)
        WHERE w.key_topics IS NOT NULL AND size(w.key_topics) > 0
        UNWIND w.key_topics as topic
        WITH toLower(trim(toString(topic))) as clean_topic, collect(DISTINCT n.neighborhood_id) as neighborhoods
        WHERE clean_topic <> '' AND clean_topic <> 'null'
        WITH clean_topic as topic, neighborhoods, size(neighborhoods) as member_count
        WHERE member_count >= $min_cluster_size
        RETURN topic, neighborhoods, member_count
        ORDER BY member_count DESC
        LIMIT 20
        """
        
        topic_data = self.execute_query(query, {
            'min_cluster_size': self.config.min_cluster_size
        })
        
        clusters_created = 0
        total_members = 0
        
        for i, topic_info in enumerate(topic_data):
            cluster_id = f"topic_cluster_{i+1}"
            topic = topic_info['topic'].lower()
            neighborhoods = topic_info['neighborhoods']
            member_count = topic_info['member_count']
            
            # Create topic cluster
            cluster = TopicCluster(
                cluster_id=cluster_id,
                topic=topic,
                neighborhoods=neighborhoods,
                member_count=member_count,
                cluster_strength=min(1.0, member_count / 10.0)  # Normalize by max expected size
            )
            
            self._create_topic_cluster_node(cluster)
            clusters_created += 1
            total_members += member_count
        
        self.result.topic_clusters_created = clusters_created
        self.result.total_cluster_members = total_members
    
    def _create_topic_cluster_node(self, cluster: TopicCluster):
        """Create TopicCluster node and relationships to neighborhoods."""
        
        # Create cluster node
        create_query = """
        CREATE (tc:TopicCluster {
            cluster_id: $cluster_id,
            topic: $topic,
            member_count: $member_count,
            cluster_strength: $cluster_strength,
            created_at: datetime()
        })
        """
        
        self.execute_query(create_query, {
            'cluster_id': cluster.cluster_id,
            'topic': cluster.topic,
            'member_count': cluster.member_count,
            'cluster_strength': cluster.cluster_strength
        })
        
        # Connect neighborhoods to cluster
        for neighborhood_id in cluster.neighborhoods:
            connect_query = """
            MATCH (tc:TopicCluster {cluster_id: $cluster_id})
            MATCH (n:Neighborhood {neighborhood_id: $neighborhood_id})
            CREATE (n)-[r:BELONGS_TO_TOPIC]->(tc)
            SET r.created_at = datetime()
            """
            
            self.execute_query(connect_query, {
                'cluster_id': cluster.cluster_id,
                'neighborhood_id': neighborhood_id
            })
    
    def _build_recommendation_paths(self):
        """Create recommendation paths through the knowledge graph."""
        
        # Count topic-based connections (neighborhoods sharing Wikipedia topics)
        topic_connections_query = """
        MATCH (n1:Neighborhood)-[:BELONGS_TO_TOPIC]->(tc:TopicCluster)<-[:BELONGS_TO_TOPIC]-(n2:Neighborhood)
        WHERE elementId(n1) < elementId(n2)
        RETURN count(*) as topic_connections
        """
        
        result = self.execute_query(topic_connections_query)
        self.result.topic_based_connections = result[0]['topic_connections'] if result else 0
        
        # Count potential recommendation paths (property -> neighborhood -> topic -> neighborhood -> property)
        paths_query = """
        MATCH (p1:Property)-[:IN_NEIGHBORHOOD]->(n1:Neighborhood)-[:BELONGS_TO_TOPIC]->(tc:TopicCluster)
        <-[:BELONGS_TO_TOPIC]-(n2:Neighborhood)<-[:IN_NEIGHBORHOOD]-(p2:Property)
        WHERE elementId(p1) < elementId(p2)
        RETURN count(DISTINCT [p1.listing_id, p2.listing_id]) as recommendation_paths
        """
        
        result = self.execute_query(paths_query)
        self.result.recommendation_paths_created = result[0]['recommendation_paths'] if result else 0
    
    def _get_current_time(self) -> float:
        """Get current timestamp for performance measurement."""
        import time
        return time.time()