# Wikipedia Embeddings Evaluation Framework

## Executive Summary

This document proposes a comprehensive evaluation framework for the `common_embeddings` module focused on Wikipedia article embeddings. The evaluation will assess embedding quality through information retrieval metrics (Precision, Recall, F1 Score) using a fixed subset of 25 Wikipedia articles and 20 carefully crafted queries.

## Objectives

1. **Evaluate Embedding Quality**: Measure how well the embeddings capture semantic similarity for Wikipedia content
2. **Test Retrieval Performance**: Assess the system's ability to retrieve relevant articles for diverse query types  
3. **Provide Reproducible Benchmarks**: Create a standardized evaluation dataset for consistent testing
4. **Enable Model Comparison**: Allow comparison between different embedding providers (Ollama, Gemini, Voyage)

## Evaluation Methodology

### 1. Data Selection Strategy

#### Article Selection Criteria
- **Random Sampling**: Select 25 articles randomly from the 464 available summaries to ensure unbiased representation
- **Geographic Diversity**: Ensure mix of Utah and California content
- **Content Type Diversity**: Include cities, landmarks, historical sites, and administrative regions
- **Summary Availability**: Only select articles with complete page summaries for ground truth

#### Query Design Principles
- **20 Queries Total**: Distributed across 5 categories (4 queries each)
- **Query Categories**:
  1. **Geographic Queries**: "cities near Park City", "coastal areas in California"
  2. **Landmark Queries**: "ski resorts in Utah", "national parks"
  3. **Historical Queries**: "Spanish colonial sites", "Gold Rush locations"
  4. **Administrative Queries**: "counties in Northern California", "school districts"
  5. **Semantic Queries**: "family-friendly destinations", "outdoor recreation areas"

### 2. Evaluation Metrics

#### Core Metrics
```python
# Precision: How many retrieved documents are relevant?
Precision = Relevant_Retrieved / Total_Retrieved

# Recall: How many relevant documents were retrieved?
Recall = Relevant_Retrieved / Total_Relevant

# F1 Score: Harmonic mean of Precision and Recall
F1 = 2 * (Precision * Recall) / (Precision + Recall)
```

#### Additional Metrics
- **Mean Reciprocal Rank (MRR)**: Position of first relevant result
- **Average Precision@K**: Precision at different retrieval depths (K=1, 3, 5, 10)
- **Normalized Discounted Cumulative Gain (NDCG)**: Accounts for graded relevance

### 3. Relevance Grading System

#### Relevance Levels
- **Highly Relevant (3)**: Direct match to query intent
- **Relevant (2)**: Related but not perfect match
- **Somewhat Relevant (1)**: Tangentially related
- **Not Relevant (0)**: No clear relationship

#### Ground Truth Generation
- Manual annotation by reviewing article summaries
- Cross-validation using LLM-based relevance scoring
- Inter-annotator agreement measurement for quality assurance

## Implementation Architecture

### Directory Structure
```
common_embeddings/
├── evaluate/
│   ├── __init__.py
│   ├── article_selector.py       # Random article selection logic
│   ├── query_generator.py        # Query generation and categorization
│   ├── relevance_grader.py       # Relevance scoring logic
│   ├── metrics_calculator.py     # Precision/Recall/F1 calculations
│   ├── evaluation_runner.py      # Main evaluation orchestration
│   └── report_generator.py       # Results visualization
│
├── evaluate_data/
│   ├── evaluate_articles.json    # Selected 25 articles
│   ├── evaluate_queries.json     # 20 test queries
│   └── ground_truth.json         # Relevance annotations
│
└── evaluate_results/
    ├── metrics_summary.json       # Aggregate metrics
    ├── detailed_results.json      # Per-query results
    └── evaluation_report.html    # Visual report
```

### Data Schemas

#### evaluate_articles.json
```json
{
  "articles": [
    {
      "page_id": 82025,
      "title": "Monterey County, California",
      "summary": "Monterey County, located on California's Pacific coast...",
      "city": null,
      "state": "California",
      "county": "Monterey",
      "categories": ["coastal", "agricultural", "tourist_destination"],
      "html_file": "data/wikipedia/pages/82025_hash.html",
      "embedding_metadata": {
        "chunk_strategy": "semantic",
        "max_chunk_size": 512
      }
    }
  ],
  "metadata": {
    "selection_date": "2024-01-XX",
    "total_available": 464,
    "selection_method": "stratified_random",
    "seed": 42
  }
}
```

#### evaluate_queries.json
```json
{
  "queries": [
    {
      "query_id": "geo_001",
      "query_text": "What cities are near Park City, Utah?",
      "category": "geographic",
      "expected_results": [137118, 108719, 115710],
      "relevance_annotations": {
        "137118": 3,  // Silver Summit - highly relevant
        "108719": 2,  // Park City - relevant
        "115710": 2,  // Summit County - relevant
        "82025": 0    // Monterey County - not relevant
      }
    }
  ],
  "categories": {
    "geographic": 4,
    "landmark": 4,
    "historical": 4,
    "administrative": 4,
    "semantic": 4
  }
}
```

### Evaluation Pipeline

#### Phase 1: Data Preparation
```python
# 1. Select articles from database
article_selector = ArticleSelector(db_path="data/wikipedia/wikipedia.db")
selected_articles = article_selector.select_random(
    n=25,
    require_summary=True,
    seed=42
)

# 2. Generate queries based on selected articles
query_generator = QueryGenerator(articles=selected_articles)
test_queries = query_generator.generate_queries(
    queries_per_category=4,
    categories=["geographic", "landmark", "historical", "administrative", "semantic"]
)

# 3. Create ground truth annotations
relevance_grader = RelevanceGrader()
ground_truth = relevance_grader.grade_relevance(
    queries=test_queries,
    articles=selected_articles
)
```

#### Phase 2: Embedding Creation
```python
# Modified main.py to support JSON input
def process_json_articles(config: Config, json_path: Path, force_recreate: bool = False):
    """Process Wikipedia articles from evaluation JSON file."""
    
    # Load articles from JSON
    with open(json_path) as f:
        data = json.load(f)
    
    # Create Document objects
    documents = []
    for article in data["articles"]:
        doc = Document(
            text=article["summary"],
            metadata={
                "page_id": article["page_id"],
                "title": article["title"],
                "source": "evaluation_set"
            }
        )
        documents.append(doc)
    
    # Process with pipeline
    pipeline = EmbeddingPipeline(config)
    results = pipeline.process_documents(
        documents,
        EntityType.WIKIPEDIA_ARTICLE,
        SourceType.EVALUATION_JSON,
        str(json_path)
    )
    
    return results
```

#### Phase 3: Evaluation Execution
```python
# Main evaluation runner
class EvaluationRunner:
    def __init__(self, config: Config):
        self.config = config
        self.collection_manager = CollectionManager(config)
        self.metrics_calculator = MetricsCalculator()
    
    def run_evaluation(self, articles_json: Path, queries_json: Path, ground_truth_json: Path):
        # 1. Create embeddings for articles
        self._create_embeddings(articles_json)
        
        # 2. Execute queries
        results = self._execute_queries(queries_json)
        
        # 3. Calculate metrics
        metrics = self.metrics_calculator.calculate(
            results=results,
            ground_truth=ground_truth_json
        )
        
        # 4. Generate report
        report = ReportGenerator().generate(
            metrics=metrics,
            queries=queries_json,
            articles=articles_json
        )
        
        return metrics, report
```

### Metrics Calculation Details

#### Precision@K Implementation
```python
def calculate_precision_at_k(retrieved_ids: List[int], relevant_ids: Set[int], k: int) -> float:
    """Calculate precision at rank K."""
    retrieved_at_k = retrieved_ids[:k]
    relevant_retrieved = len([id for id in retrieved_at_k if id in relevant_ids])
    return relevant_retrieved / k if k > 0 else 0.0
```

#### Recall@K Implementation
```python
def calculate_recall_at_k(retrieved_ids: List[int], relevant_ids: Set[int], k: int) -> float:
    """Calculate recall at rank K."""
    retrieved_at_k = retrieved_ids[:k]
    relevant_retrieved = len([id for id in retrieved_at_k if id in relevant_ids])
    return relevant_retrieved / len(relevant_ids) if relevant_ids else 0.0
```

#### NDCG Implementation
```python
def calculate_ndcg(retrieved_ids: List[int], relevance_scores: Dict[int, int], k: int) -> float:
    """Calculate Normalized Discounted Cumulative Gain."""
    dcg = sum(
        relevance_scores.get(id, 0) / math.log2(i + 2)
        for i, id in enumerate(retrieved_ids[:k])
    )
    
    # Ideal DCG (perfect ranking)
    ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = sum(
        score / math.log2(i + 2)
        for i, score in enumerate(ideal_scores)
    )
    
    return dcg / idcg if idcg > 0 else 0.0
```

## Execution Plan

### Phase 1: Setup (Week 1)
1. Create `evaluate/` directory structure
2. Implement `article_selector.py` to randomly select 25 articles
3. Generate `evaluate_articles.json` with selected articles
4. Implement `query_generator.py` for query creation

### Phase 2: Ground Truth (Week 1-2)
1. Design 20 queries across 5 categories
2. Create relevance annotations for each query-article pair
3. Generate `ground_truth.json` with annotations
4. Validate annotations with secondary review

### Phase 3: Implementation (Week 2)
1. Modify `main.py` to add `--evaluate` mode
2. Implement embedding creation from JSON
3. Build query execution pipeline
4. Implement metrics calculation

### Phase 4: Evaluation (Week 3)
1. Run evaluation on each embedding provider
2. Compare results across models
3. Generate comprehensive reports
4. Document findings and recommendations

## Expected Outcomes

### Success Metrics
- **Target Precision@5**: > 70%
- **Target Recall@10**: > 80%
- **Target F1 Score**: > 65%
- **Target MRR**: > 0.7

### Deliverables
1. **Evaluation Dataset**: Reusable test corpus of 25 articles and 20 queries
2. **Metrics Report**: Comprehensive performance metrics for each model
3. **Comparison Analysis**: Side-by-side model performance comparison
4. **Recommendations**: Model selection guidance based on use case

### Model Comparison Matrix
| Model | Precision@5 | Recall@10 | F1 Score | MRR | Latency (ms) |
|-------|------------|-----------|----------|-----|--------------|
| nomic-embed-text | TBD | TBD | TBD | TBD | TBD |
| mxbai-embed-large | TBD | TBD | TBD | TBD | TBD |
| text-embedding-3-small | TBD | TBD | TBD | TBD | TBD |
| gemini-1.5-flash | TBD | TBD | TBD | TBD | TBD |

## Risk Mitigation

### Potential Challenges
1. **Annotation Bias**: Mitigate with multiple annotators and consensus
2. **Query Coverage**: Ensure diverse query types and difficulty levels
3. **Model Variability**: Run multiple evaluation rounds and average results
4. **Computational Cost**: Start with smaller test sets for rapid iteration

### Quality Assurance
- Automated unit tests for all evaluation components
- Manual review of ground truth annotations
- Statistical significance testing for model comparisons
- Reproducibility verification with fixed random seeds

## Future Enhancements

### Version 2.0 Features
1. **Dynamic Query Generation**: LLM-based query synthesis
2. **Multi-lingual Evaluation**: Test cross-language retrieval
3. **Temporal Evaluation**: Test on time-sensitive queries
4. **User Study Integration**: Human evaluation alongside metrics

### Long-term Goals
- Continuous evaluation pipeline with CI/CD integration
- Real-time performance monitoring in production
- A/B testing framework for embedding models
- Transfer learning evaluation on domain-specific content

## Conclusion

This evaluation framework provides a rigorous, reproducible method for assessing Wikipedia embedding quality in the `common_embeddings` module. By focusing on a carefully curated subset of 25 articles and 20 diverse queries, we can efficiently measure retrieval performance while maintaining statistical validity. The modular architecture enables easy extension and comparison of different embedding providers, supporting data-driven model selection for production use cases.