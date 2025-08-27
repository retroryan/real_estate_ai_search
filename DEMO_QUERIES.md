# Real Estate Search Demo Queries - Data-Driven Implementation

## ALWAYS USE PYDANTIC - USE MODULES AND CLEAN CODE!

## Overview

This proposal presents five focused demonstrations of the Real Estate Search system using actual data from San Francisco Bay Area and Utah properties. Each demo showcases specific Elasticsearch capabilities with real properties and neighborhoods from our dataset.

## Available Data

### Properties
- **San Francisco Bay Area**: Oakland properties in Temescal neighborhood
- **Utah Ski Areas**: Coalville properties near Park City with ski access
- **Property Types**: Townhomes, condos, single-family homes
- **Features**: Mountain views, ski access, rooftop access, transit nearby, community pools, hot tubs

### Neighborhoods  
- **San Francisco**: Pacific Heights (luxury), Mission District (vibrant), and others
- **Characteristics**: Walkability scores, transit scores, school ratings, safety ratings
- **Price Ranges**: From $492K (Oakland) to $3.5M+ (Pacific Heights)

## Demo 1: Core Search Technologies

### Purpose
Demonstrate the three fundamental search approaches: vector similarity, text matching, and hybrid search using Reciprocal Rank Fusion (RRF).

### Query 1: Pure Vector Search - Semantic Similarity
**Query**: "Find me a cozy mountain retreat perfect for winter getaways"
**Implementation**: Use only embedding vectors to find semantically similar properties
**Expected Results**: Coalville properties with ski access, hot tubs, wood burning stoves
**Data Points**: Properties with features like "Mountain views", "Ski access", "Hot tub" from Utah listings

### Query 2: Traditional Text Search - Keyword Matching
**Query**: "townhome Oakland Temescal pool"
**Implementation**: Standard multi-match query across description and features fields
**Expected Results**: Oakland townhomes in Temescal with community pools
**Data Points**: prop-oak-125 (Telegraph Court) with community pool feature

### Query 3: Hybrid Search with RRF - Best of Both
**Query**: "Modern urban living with great transit and restaurants"
**Implementation**: Combine vector search (semantic understanding) with text search using RRF
**Expected Results**: Properties near transit with walkable neighborhoods
**Data Points**: Oakland properties with "Transit nearby", "Walk to restaurants" features

### Query 4: Neighborhood-Aware Vector Search
**Query**: "Family-friendly area with top schools"
**Implementation**: Vector search incorporating neighborhood embeddings
**Expected Results**: Properties in neighborhoods with high school ratings
**Data Points**: Pacific Heights (school_rating: 9) matched properties

### Query 5: Cross-Index RRF Search
**Query**: "Historic San Francisco neighborhood with Victorian charm"
**Implementation**: RRF combining property and neighborhood index searches
**Expected Results**: Properties in historic neighborhoods like Pacific Heights
**Data Points**: Combining neighborhood descriptions with property features

## Demo 2: Location-Based Discovery

### Purpose
Showcase location-aware search capabilities using real Bay Area and Utah geography.

### Query 1: City-Specific Search
**Query**: "Luxury condos in San Francisco"
**Implementation**: Filter by city with price range and property type
**Expected Results**: High-end condos in San Francisco neighborhoods
**Data Points**: Properties in Pacific Heights area

### Query 2: Multi-City Regional Search
**Query**: "Properties near ski resorts in Utah"
**Implementation**: Geographic search for Utah properties with ski-related features
**Expected Results**: Coalville and Park City area properties
**Data Points**: prop-coal-137 with "Ski access" feature

### Query 3: Neighborhood Characteristic Search
**Query**: "Walkable neighborhoods in Oakland"
**Implementation**: Search using neighborhood walkability scores
**Expected Results**: Oakland properties in high walkability areas
**Data Points**: Temescal neighborhood properties

### Query 4: Price-Location Correlation
**Query**: "Affordable homes in safe neighborhoods"
**Implementation**: Combine price filters with safety ratings
**Expected Results**: Properties under $800K in safe neighborhoods
**Data Points**: Oakland properties with moderate prices

### Query 5: Transit-Oriented Search
**Query**: "Properties near public transportation"
**Implementation**: Search for high transit score neighborhoods
**Expected Results**: Properties with "Transit nearby" feature
**Data Points**: prop-oak-126 with transit access

## Demo 3: Feature-Based Matching

### Purpose
Demonstrate precise feature matching using actual property amenities from our dataset.

### Query 1: Outdoor Amenities
**Query**: "Properties with rooftop access and city views"
**Implementation**: Multi-term feature matching
**Expected Results**: Urban properties with outdoor spaces
**Data Points**: prop-oak-126 with rooftop access and city views

### Query 2: Storage Solutions
**Query**: "Homes with ample storage and bike facilities"
**Implementation**: Feature array matching for storage-related amenities
**Expected Results**: Properties with storage units and bike storage
**Data Points**: Oakland properties with "Bike storage", "Storage unit" features

### Query 3: Pet-Friendly Properties
**Query**: "Pet-friendly homes with yards"
**Implementation**: Boolean feature filtering
**Expected Results**: Properties allowing pets with outdoor space
**Data Points**: Properties with "Pet-friendly" feature

### Query 4: Luxury Amenities
**Query**: "Properties with concierge and gym facilities"
**Implementation**: Premium amenity filtering
**Expected Results**: High-end properties with full services
**Data Points**: Properties with "Concierge", "Gym" features

### Query 5: Mountain Living Features
**Query**: "Ski-in/ski-out properties with gear storage"
**Implementation**: Specialized feature search for mountain properties
**Expected Results**: Utah properties with ski amenities
**Data Points**: Coalville properties with "Storage for gear", "Ski access"

## Demo 4: Investment Analysis Queries

### Purpose
Analyze properties for investment potential using real pricing and market data.

### Query 1: Price per Square Foot Analysis
**Query**: "Best value properties under $400 per sqft"
**Implementation**: Calculated field filtering and sorting
**Expected Results**: Properties with low price per square foot
**Data Points**: prop-oak-125 at $292/sqft

### Query 2: Days on Market Insights
**Query**: "Recently listed properties in hot neighborhoods"
**Implementation**: Temporal filtering with neighborhood desirability
**Expected Results**: New listings in popular areas
**Data Points**: Properties with days_on_market < 30

### Query 3: Property Type Comparison
**Query**: "Compare townhomes vs condos in Oakland"
**Implementation**: Aggregation by property type with statistics
**Expected Results**: Average prices and features by type
**Data Points**: Oakland townhomes and condos comparison

### Query 4: Year Built Analysis
**Query**: "Modern properties built after 2000"
**Implementation**: Range query on year_built field
**Expected Results**: Newer construction properties
**Data Points**: prop-oak-126 built in 2002

### Query 5: HOA Fee Evaluation
**Query**: "Condos with low HOA fees"
**Implementation**: Filter and sort by HOA fees
**Expected Results**: Condos with minimal monthly fees
**Data Points**: Properties with HOA fee data

## Demo 5: Advanced Aggregation Analytics

### Purpose
Demonstrate complex analytics using Elasticsearch aggregations on real data.

### Query 1: Market Overview Dashboard
**Query**: "Property distribution by city and type"
**Implementation**: Multi-level aggregation
**Expected Results**: Breakdown of inventory by location and type
**Data Points**: Oakland, San Francisco, Coalville property counts

### Query 2: Price Range Analysis
**Query**: "Price distribution across neighborhoods"
**Implementation**: Histogram aggregation with percentiles
**Expected Results**: Price bands by neighborhood
**Data Points**: From $492K to $3.5M+ range

### Query 3: Feature Popularity
**Query**: "Most common amenities by price range"
**Implementation**: Terms aggregation within price buckets
**Expected Results**: Feature frequency by price tier
**Data Points**: Pool, gym, storage features distribution

### Query 4: Bedroom-Bathroom Correlation
**Query**: "Typical bathroom count by bedroom count"
**Implementation**: Statistical aggregation
**Expected Results**: Average bathrooms per bedroom configuration
**Data Points**: 3BR/3BA, 4BR/3.5BA patterns

### Query 5: Neighborhood Comparison Matrix
**Query**: "Compare all neighborhood metrics"
**Implementation**: Complex nested aggregations
**Expected Results**: Side-by-side neighborhood statistics
**Data Points**: Walkability, transit, school ratings comparison

## Implementation Architecture

### Core Modules

#### 1. Demo Models Module (`models/`)
```
models/
├── __init__.py
├── query_models.py      # Pydantic models for queries
├── response_models.py   # Pydantic models for responses
└── config_models.py     # Configuration models
```

#### 2. Query Builders Module (`builders/`)
```
builders/
├── __init__.py
├── base_builder.py      # Abstract base builder
├── vector_builder.py    # Vector/kNN query builder
├── text_builder.py      # Text query builder
├── rrf_builder.py       # RRF hybrid builder
└── aggregation_builder.py
```

#### 3. Demo Runners Module (`runners/`)
```
runners/
├── __init__.py
├── demo_runner.py       # Main demo orchestrator
├── demo_registry.py     # Demo registration
└── result_presenter.py  # Result formatting
```

### Key Pydantic Models

#### Query Models
```python
class VectorSearchQuery(BaseModel):
    query_text: str
    embedding_field: str = "embedding"
    k: int = 10
    num_candidates: int = 100

class TextSearchQuery(BaseModel):
    query_text: str
    fields: List[str]
    boost_values: Dict[str, float] = {}

class RRFSearchQuery(BaseModel):
    queries: List[Union[VectorSearchQuery, TextSearchQuery]]
    rank_window_size: int = 50
    rank_constant: int = 20
```

#### Response Models
```python
class DemoResult(BaseModel):
    demo_name: str
    query_name: str
    execution_time_ms: int
    total_results: int
    top_results: List[PropertyResult]
```

### Implementation Phases

### Phase 1: Foundation Setup
- Create module structure
- Define base Pydantic models
- Set up configuration system
- Initialize demo registry

### Phase 2: Query Builder Implementation
- Implement vector query builder
- Implement text query builder
- Implement RRF query builder
- Add aggregation builder

### Phase 3: Demo Runner Development
- Create demo orchestrator
- Implement result presenter
- Add execution tracking
- Build demo CLI interface

### Phase 4: Demo Implementation
- Implement Demo 1: Core Search Technologies
- Implement Demo 2: Location Discovery
- Implement Demo 3: Feature Matching
- Implement Demo 4: Investment Analysis
- Implement Demo 5: Advanced Analytics

### Phase 5: Integration and Testing
- Integrate with IndexManagementCLI
- Add unit tests for all modules
- Create integration tests
- Validate with real data

### Phase 6: Documentation and Polish
- Write user documentation
- Add inline code documentation
- Create demo execution guide
- Clean up and refactor

## Implementation Todo List

### Foundation
- [ ] Create project module structure
- [ ] Define base Pydantic models for queries
- [ ] Define base Pydantic models for responses
- [ ] Set up demo configuration system
- [ ] Create demo registry framework

### Query Builders
- [ ] Implement base query builder interface
- [ ] Create vector search query builder
- [ ] Create text search query builder
- [ ] Create RRF hybrid query builder
- [ ] Create aggregation query builder

### Demo Implementation
- [ ] Implement Demo 1 - Core Search Technologies
- [ ] Implement Demo 2 - Location Discovery
- [ ] Implement Demo 3 - Feature Matching
- [ ] Implement Demo 4 - Investment Analysis
- [ ] Implement Demo 5 - Advanced Analytics

### Integration
- [ ] Extend management CLI with demo command
- [ ] Add interactive demo selection
- [ ] Implement result presentation
- [ ] Add execution metrics tracking

### Testing
- [ ] Write unit tests for models
- [ ] Write unit tests for builders
- [ ] Create integration tests for demos
- [ ] Test with real data

### Documentation
- [ ] Document query builder usage
- [ ] Document demo execution
- [ ] Create user guide
- [ ] Add API documentation

### Final Tasks
- [ ] Code review and refactoring
- [ ] Security assessment
- [ ] Documentation review
- [ ] Testing and bug fixes
- [ ] Demo validation

## Success Metrics

### Functional Requirements
- All 25 queries execute successfully with real data
- Accurate search results matching query intent
- Proper RRF implementation combining vector and text search
- Correct aggregation calculations

### Quality Requirements
- 100% Pydantic model usage for data validation
- Clean, modular code architecture
- Comprehensive error handling
- Complete documentation

## Technical Requirements

### Dependencies
- Pydantic >= 2.0 for all data models
- Elasticsearch Python client >= 8.8 (for RRF support)
- Rich for terminal presentation
- Click for CLI enhancement

### Quality Standards
- Type hints for all functions
- Docstrings for all classes and methods
- Modular, reusable components
- Clean separation of concerns

## Conclusion

This data-driven approach ensures our demos showcase real capabilities with actual property data from the Bay Area and Utah. By focusing on vector search, text search, and RRF hybrid search in Demo 1, we establish the core technologies before moving to practical use cases. The modular, Pydantic-based architecture ensures clean, maintainable code that can be easily extended.