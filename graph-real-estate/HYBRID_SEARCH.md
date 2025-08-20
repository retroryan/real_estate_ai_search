# Hybrid Search Optimization Proposal

## Executive Summary

The current hybrid search implementation uses fixed weights (60% vector, 20% graph, 20% features) that were chosen as reasonable starting values but lack empirical validation. This document proposes data-driven approaches to optimize the ranking algorithm for better search relevance.

## Current Implementation Analysis

### Existing Approach
- **Fixed weights** defined in `src/vectors/config.yaml`
- **Vector similarity**: 60% weight (semantic matching via embeddings)
- **Graph centrality**: 20% weight (connection-based importance)
- **Feature richness**: 20% weight (property amenities count)
- **Additional boosts**: +10% for well-connected properties, +5% for similar properties

### Limitations
1. **No empirical basis** for weight values
2. **Arbitrary normalization thresholds** (e.g., 15 features max, 50 neighborhood connections max)
3. **Static weights** regardless of query type or context
4. **No feedback mechanism** for improvement
5. **No baseline comparison** to validate effectiveness

## Proposed Optimization Strategies

### Phase 1: Measurement and Baselines

#### 1.1 Create Evaluation Dataset
- **Relevance judgments**: Collect 100+ query-result pairs with human ratings
- **Query diversity**: Include location, price, amenity, and lifestyle queries
- **Metrics implementation**:
  - Precision@K (K=5, 10)
  - Normalized Discounted Cumulative Gain (nDCG)
  - Mean Reciprocal Rank (MRR)
  - Click-through Rate simulation

#### 1.2 Establish Baselines
- **Vector-only search**: 100% vector weight as baseline
- **Equal weights**: 33.3% each for comparison
- **Current weights**: 60/20/20 as control
- **Random ranking**: Lower bound performance

### Phase 2: A/B Testing Framework

#### 2.1 Infrastructure Setup
- **Variant management**: Support multiple weight configurations
- **User assignment**: Deterministic or randomized variant selection
- **Metrics collection**: Track search sessions and implicit feedback
- **Statistical analysis**: Significance testing for variant comparison

#### 2.2 Initial Variants
```yaml
variants:
  control: [0.6, 0.2, 0.2]        # Current
  vector_heavy: [0.8, 0.1, 0.1]   # Semantic focus
  graph_heavy: [0.4, 0.4, 0.2]    # Relationship focus
  feature_heavy: [0.4, 0.2, 0.4]  # Amenity focus
  balanced: [0.33, 0.33, 0.34]    # Equal weights
```

### Phase 3: Weight-Free Alternatives

#### 3.1 Reciprocal Rank Fusion (RRF)
**Advantages**:
- No weight tuning required
- Robust to score scale differences
- Well-established in IR literature

**Implementation**:
- Rank properties by each signal independently
- Combine rankings using RRF formula: `score = Σ(1/(k + rank_i))`
- Default k=60 (based on Cormack et al., 2009)

#### 3.2 Learning to Rank (L2R)
**Approaches**:
- **Pointwise**: Regression on relevance scores
- **Pairwise**: Learn preference between property pairs
- **Listwise**: Optimize entire ranking lists

**Features for L2R**:
- Vector similarity score
- Graph centrality metrics
- Feature count and categories
- Price relative to neighborhood median
- Recency and popularity signals

### Phase 4: Advanced Optimizations

#### 4.1 Query-Adaptive Weights
**Query Classification**:
- **Location queries**: Boost graph weight ("near downtown", "in Nob Hill")
- **Amenity queries**: Boost feature weight ("pool", "gym", "luxury")
- **Descriptive queries**: Boost vector weight ("cozy cottage", "modern loft")
- **Investment queries**: Balance all signals ("good value", "rental potential")

**Implementation**:
- Query intent classifier (rule-based or ML)
- Weight lookup table by query type
- Smooth transitions between weight sets

#### 4.2 Grid Search Optimization
**Parameter Space**:
```python
parameter_grid = {
    'vector_weight': [0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
    'graph_weight': [0.1, 0.2, 0.3, 0.4],
    'feature_weight': [0.1, 0.2, 0.3, 0.4]
}
# Constraint: weights must sum to 1.0
```

**Evaluation**:
- Cross-validation on query-result pairs
- Optimize for primary metric (e.g., nDCG@10)
- Track secondary metrics for trade-offs

#### 4.3 Bayesian Optimization
**Advantages**:
- Efficient exploration of weight space
- Handles continuous parameters
- Provides uncertainty estimates

**Tools**:
- Scikit-optimize (skopt)
- Optuna
- Hyperopt

### Phase 5: Graph-Specific Enhancements

#### 5.1 Neo4j Vector Search Optimizations
Based on Neo4j documentation findings:

**Performance Tuning**:
- Enable Java Vector API for speed improvements
- Configure HNSW parameters:
  - `vector.hnsw.m`: Connectivity parameter (default 16)
  - `vector.hnsw.ef_construction`: Quality factor (default 200)
- Consider quantization trade-offs

**Query Patterns**:
- Pre-filter with graph traversal before vector search
- Post-filter vector results with graph constraints
- Parallel execution of vector and graph queries

#### 5.2 Graph-Aware Embeddings
**Enhancements**:
- Include graph structure in embedding generation
- Node2Vec or GraphSAGE for structural embeddings
- Concatenate or blend with text embeddings

### Phase 6: Contextual Ranking Factors

#### 6.1 User Personalization
- Historical preference learning
- Demographic-based weight adjustment
- Session-based context (viewed properties)

#### 6.2 Temporal Factors
- Boost recently listed properties
- Seasonal adjustments (e.g., vacation rentals)
- Market trend incorporation

#### 6.3 Business Rules
- Sponsored/featured property boosts
- Inventory balancing
- Fair exposure policies

## Implementation Roadmap

### Quarter 1: Foundation
1. **Week 1-2**: Implement evaluation metrics
2. **Week 3-4**: Create relevance judgment dataset
3. **Week 5-6**: Build A/B testing framework
4. **Week 7-8**: Deploy initial variants
5. **Week 9-12**: Collect data and analyze results

### Quarter 2: Optimization
1. **Month 1**: Implement RRF and compare with weighted approach
2. **Month 2**: Grid search and Bayesian optimization
3. **Month 3**: Query-adaptive weights implementation

### Quarter 3: Advanced Features
1. **Month 1**: Learning to Rank implementation
2. **Month 2**: Graph-aware embeddings
3. **Month 3**: Personalization features

### Quarter 4: Production
1. **Month 1**: Performance optimization
2. **Month 2**: Monitoring and alerting
3. **Month 3**: Documentation and knowledge transfer

## Success Metrics

### Primary Metrics
- **nDCG@10**: Improve by 15% over baseline
- **User satisfaction**: Via explicit feedback
- **Search success rate**: Properties viewed/contacted

### Secondary Metrics
- **Query latency**: Maintain <100ms p99
- **Coverage**: Ensure all properties discoverable
- **Diversity**: Avoid filter bubbles

## Risk Mitigation

### Technical Risks
- **Performance degradation**: Monitor latency, use caching
- **Overfitting**: Cross-validation, holdout test sets
- **Cold start**: Fallback to vector-only for new properties

### Business Risks
- **User disruption**: Gradual rollout, easy rollback
- **Bias introduction**: Fairness metrics, regular audits
- **Maintenance burden**: Automated testing, clear documentation

## Resource Requirements

### Engineering
- **Senior Engineer**: 0.5 FTE for 6 months
- **Data Scientist**: 0.5 FTE for 6 months
- **DevOps**: 0.25 FTE for infrastructure

### Infrastructure
- **A/B testing platform**: Build or integrate
- **ML training pipeline**: GPU resources for L2R
- **Monitoring**: Enhanced logging and dashboards

### Data
- **Relevance judgments**: ~$5,000 for human annotation
- **User feedback**: In-app feedback collection
- **Analytics**: Enhanced event tracking

## Conclusion

The current fixed-weight approach provides a functional baseline, but significant improvements are achievable through data-driven optimization. The proposed phased approach balances quick wins (A/B testing, RRF) with longer-term investments (L2R, personalization) while maintaining system stability and performance.

## References

1. Cormack, G. V., Clarke, C. L., & Buettcher, S. (2009). "Reciprocal rank fusion outperforms condorcet and individual rank learning methods"
2. Liu, T. Y. (2011). "Learning to rank for information retrieval"
3. Neo4j Documentation: "Vector Indexes" - Performance optimization guidelines
4. Wang, X., He, X., Wang, M., Feng, F., & Chua, T. S. (2019). "Neural graph collaborative filtering"
5. Grover, A., & Leskovec, J. (2016). "node2vec: Scalable feature learning for networks"

## Appendix: Evaluation Metrics Formulas

### nDCG (Normalized Discounted Cumulative Gain)
```
DCG@k = Σ(i=1 to k) (2^rel_i - 1) / log2(i + 1)
nDCG@k = DCG@k / IDCG@k
```

### Precision@K
```
Precision@K = |relevant ∩ retrieved_top_k| / k
```

### Mean Reciprocal Rank (MRR)
```
MRR = (1/|Q|) Σ(i=1 to |Q|) (1/rank_i)
```

### Reciprocal Rank Fusion (RRF)
```
RRF_score(d) = Σ(r in R) 1/(k + rank_r(d))
```
where k=60 (default), R is set of rankings, rank_r(d) is rank of document d in ranking r