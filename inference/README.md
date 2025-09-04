# Machine Learning Inference with Elasticsearch

## 🎯 Overview

This directory contains complete implementations of two powerful ML systems for Wikipedia articles using Elasticsearch's machine learning capabilities:

1. **Named Entity Recognition (NER)**: Uses a pre-trained DistilBERT model to automatically identify and extract entities (organizations, locations, persons) from text
2. **Text Embeddings**: Uses sentence-transformers to generate semantic vector representations for powerful similarity search

Both systems demonstrate Elasticsearch's ML inference capabilities and can be used independently or together for comprehensive search and analysis.

## 🚀 Quick Start

### For NER (Named Entity Recognition)
```bash
# 1. Install the NER model (one-time setup)
./inference/install_ner_model.sh

# 2. Set up the pipeline and index
python inference/setup_ner_pipeline.py

# 3. Process Wikipedia articles (default: 10 articles)
python inference/process_wikipedia_ner.py

# 4. Test entity-based searches
python inference/search_ner.py
```

### For Text Embeddings (Semantic Search)
```bash
# 1. Install the embedding model (one-time setup)
./inference/install_embedding_model.sh

# 2. Set up the pipeline and index
python inference/setup_embedding_pipeline.py

# 3. Process Wikipedia articles with embeddings
python inference/process_wikipedia_embeddings.py --sample 10

# 4. Test semantic search capabilities
python inference/search_embeddings.py
```

### ML Model Management
```bash
# Check status of both systems
python inference/check_ml_status.py

# Switch between models (only one can run at a time)
python inference/check_ml_status.py --model ner    # Switch to NER
python inference/check_ml_status.py --model embed  # Switch to embeddings
```

## 📁 Directory Structure

```
inference/
# NER System
├── install_ner_model.sh              # Install DistilBERT NER model
├── setup_ner_pipeline.py              # Create NER index and pipeline
├── process_wikipedia_ner.py           # Process articles for entities
├── search_ner.py                      # Test entity-based searches

# Embedding System  
├── install_embedding_model.sh         # Install sentence-transformers model
├── setup_embedding_pipeline.py        # Create embeddings index and pipeline
├── process_wikipedia_embeddings.py    # Generate embeddings for articles
├── search_embeddings.py               # Test semantic search capabilities

# Shared Tools
├── check_ml_status.py                 # Monitor and switch ML models
├── README.md                          # This comprehensive guide
└── README_EMBEDDINGS.md               # Detailed embeddings documentation
```

## ⚠️ Important: Model Requirements and Resource Management

### Key Points About ML Models in Elasticsearch

1. **Resource Constraint**: Only ONE ML model can be deployed at a time due to Elasticsearch resource limitations
   - Use `check_ml_status.py --model [ner|embed]` to switch between models
   - The script automatically stops the running model before starting the new one

2. **Storage vs Runtime Requirements**:
   
   **NER System**:
   - **Processing**: Requires NER model to be running
   - **Searching**: Does NOT require model - entities are stored in the index
   - **Storage**: Entities are saved as keyword fields (organizations, locations, persons)
   - **Implication**: Once processed, you can search entities without the model

   **Embedding System**:
   - **Processing**: Requires embedding model to be running
   - **Searching**: Requires model for generating query embeddings
   - **Storage**: Embeddings are saved as dense_vector fields (384 dimensions)
   - **Implication**: Model must be running for semantic search queries

3. **Practical Workflow**:
   ```bash
   # Process documents with NER
   python inference/check_ml_status.py --model ner
   python inference/process_wikipedia_ner.py --sample 100
   
   # Switch to embeddings for semantic search
   python inference/check_ml_status.py --model embed
   python inference/process_wikipedia_embeddings.py --sample 100
   
   # Later: Search NER without model
   python inference/search_ner.py  # Works even if embedding model is running!
   
   # But semantic search needs embedding model
   python inference/search_embeddings.py  # Requires embedding model running
   ```

4. **Best Practices**:
   - Process large batches of documents when you have the appropriate model running
   - NER is "process once, search forever" without the model
   - Embeddings need the model for new queries but not for stored vectors
   - Plan your processing pipeline based on which searches you need most

## 🎓 NER Tutorial for Beginners

### What is Named Entity Recognition?

Named Entity Recognition (NER) is a natural language processing technique that automatically identifies and classifies named entities in text into predefined categories. Think of it as teaching a computer to recognize and categorize important "things" mentioned in text.

### Common Entity Types

1. **Organizations (ORG)** 🏢
   - Companies: "Google", "Microsoft", "Tesla"
   - Institutions: "Harvard University", "World Bank"
   - Teams: "Los Angeles Lakers", "The Beatles"

2. **Locations (LOC)** 📍
   - Cities: "San Francisco", "London", "Tokyo"
   - Countries: "United States", "France", "Japan"
   - Landmarks: "Golden Gate Bridge", "Mount Everest"

3. **Persons (PER)** 👤
   - Names: "Steve Jobs", "Marie Curie", "Barack Obama"
   - Titles + Names: "Dr. Smith", "President Lincoln"

4. **Miscellaneous (MISC)** 🏷️
   - Nationalities: "American", "French", "Japanese"
   - Events: "World War II", "Olympics"
   - Products: "iPhone", "Windows"

### How NER Works

```
Input Text:
"Apple Inc. was founded by Steve Jobs in Cupertino, California."

NER Processing:
                    ↓
Entity Extraction:
- "Apple Inc." → ORG (Organization)
- "Steve Jobs" → PER (Person)
- "Cupertino" → LOC (Location)
- "California" → LOC (Location)

Structured Output:
{
  "organizations": ["Apple Inc."],
  "persons": ["Steve Jobs"],
  "locations": ["Cupertino", "California"]
}
```

### Why Use NER with Elasticsearch?

1. **Enhanced Search**: Find documents by entities, not just keywords
2. **Relationship Discovery**: Identify connections between entities
3. **Content Categorization**: Automatically classify documents
4. **Information Extraction**: Build knowledge graphs
5. **Analytics**: Understand entity distributions and patterns

## 🔧 Detailed Setup Guide

### Prerequisites

- Docker installed and running
- Elasticsearch 8.x+ running locally
- Python 3.8+ with pip
- At least 2GB free disk space for the model

### Step 1: Install the NER Model

The installation script downloads and deploys a pre-trained DistilBERT model fine-tuned for NER:

```bash
./inference/install_ner_model.sh
```

This script:
- Pulls the latest Eland Docker image
- Downloads the DistilBERT model from Hugging Face
- Imports it into Elasticsearch
- Starts the model deployment
- Verifies the installation

**Model Details:**
- Model: `elastic/distilbert-base-uncased-finetuned-conll03-english`
- Size: ~250MB
- Training Data: CoNLL-03 dataset
- Languages: English
- Performance: F1 score of ~90% on benchmark

### Step 2: Set Up Pipeline and Index

```bash
python inference/setup_ner_pipeline.py
```

This creates:

1. **Index Mapping** (`wikipedia_ner`):
   ```json
   {
     "ner_entities": {         // Raw entity data
       "type": "nested"
     },
     "ner_organizations": {    // Organization names
       "type": "keyword"
     },
     "ner_locations": {        // Location names
       "type": "keyword"
     },
     "ner_persons": {          // Person names
       "type": "keyword"
     }
   }
   ```

2. **Inference Pipeline** (`wikipedia_ner_pipeline`):
   - Processes text through the NER model
   - Extracts and categorizes entities
   - Stores results in dedicated fields
   - Handles errors gracefully

### Step 3: Process Articles

The processing script offers flexible sampling options:

```bash
# Process 10 random articles (default)
python inference/process_wikipedia_ner.py

# Process specific number
python inference/process_wikipedia_ner.py --sample 100

# Process ALL articles (may take hours)
python inference/process_wikipedia_ner.py --sample all

# Process from specific index
python inference/process_wikipedia_ner.py --source wiki_summaries --sample 50

# Force reprocess existing
python inference/process_wikipedia_ner.py --force --sample 20

# Optimize batch size for large datasets
python inference/process_wikipedia_ner.py --sample 1000 --batch-size 25
```

**Processing Options:**
- `--sample`: Number of articles or "all"
- `--source`: Source index name
- `--force`: Reprocess existing articles
- `--batch-size`: Articles per batch (default: 10)

### Step 4: Search and Analysis

The search tester demonstrates various entity-based queries:

```bash
python inference/search_ner.py
```

This runs 8 different test searches:
1. Find articles mentioning universities
2. Search for California locations
3. Find articles about people
4. Multi-entity searches
5. Combined text + entity search
6. Entity frequency analysis
7. Geo + entity search
8. Entity co-occurrence patterns

## 🔍 Search Examples

### Basic Entity Search

```python
# Find articles mentioning Microsoft
{
  "query": {
    "term": {
      "ner_organizations": "microsoft"
    }
  }
}
```

### Multi-Entity Search

```python
# Find articles about Steve Jobs in California
{
  "query": {
    "bool": {
      "must": [
        {"term": {"ner_persons": "steve jobs"}},
        {"term": {"ner_locations": "california"}}
      ]
    }
  }
}
```

### Entity + Full-Text Search

```python
# Find historical articles about museums
{
  "query": {
    "bool": {
      "must": [
        {"match": {"full_content": "history"}}
      ],
      "should": [
        {"term": {"ner_organizations": "museum"}}
      ]
    }
  }
}
```

### Entity Aggregations

```python
# Top entities by type
{
  "aggs": {
    "top_orgs": {
      "terms": {
        "field": "ner_organizations",
        "size": 20
      }
    }
  }
}
```

## 📊 Understanding NER Results

### Entity Confidence Scores

Each extracted entity includes:
- `entity`: The text identified
- `class_name`: Entity type (ORG, LOC, PER, MISC)
- `class_probability`: Confidence score (0-1)
- `start_pos`: Character position start
- `end_pos`: Character position end

### Quality Considerations

1. **Context Matters**: "Apple" could be a company or fruit
2. **Ambiguity**: "Washington" - person, city, or state?
3. **Compound Entities**: "New York Times" as single entity
4. **Language Limitations**: Model trained on English text
5. **Domain Specificity**: May miss domain-specific entities

## 🛠️ Advanced Configuration

### Model Parameters

Edit the pipeline configuration in `setup_ner_pipeline.py`:

```python
"inference_config": {
  "ner": {
    "results_field": "entities",
    "tokenization": {
      "bert": {
        "truncate": "first",        # How to handle long text
        "max_sequence_length": 512  # Max tokens to process
      }
    }
  }
}
```

### Performance Tuning

1. **Batch Size**: Larger batches = faster but more memory
2. **Truncation**: "first" keeps beginning, "second" keeps end
3. **Max Length**: 512 tokens (~400 words) maximum
4. **Parallel Processing**: Adjust thread pool size

### Custom Entity Processing

Modify the Painless script in the pipeline to customize entity extraction:

```javascript
// Example: Only keep high-confidence entities
if (entity.class_probability > 0.9) {
  // Process entity
}

// Example: Normalize entity names
String normalized = entity.entity.toLowerCase();
```

## 🎯 Use Cases

### 1. Semantic Search Enhancement
- Find articles about specific companies
- Locate documents mentioning competitors
- Search by people mentioned

### 2. Content Analysis
- Identify most mentioned organizations
- Track location references
- Analyze person co-occurrences

### 3. Knowledge Graph Building
- Extract entity relationships
- Build connection networks
- Create entity timelines

### 4. Document Classification
- Categorize by dominant entities
- Group similar entity profiles
- Identify document topics

### 5. Information Extraction
- Extract company mentions for compliance
- Identify geographic scope of articles
- Find expert citations

## 🔧 Known Issues and Fixes

### Inference API Response Format
The Elasticsearch ML inference API returns embeddings in the `predicted_value` field, not `text_embedding` as some documentation suggests:

```python
# Correct way to get embeddings
result = es.ml.infer_trained_model(
    model_id='sentence-transformers__all-minilm-l6-v2',
    docs=[{'text_field': 'your text'}]
)
embedding = result['inference_results'][0]['predicted_value']  # ✅ Correct
# embedding = result['inference_results'][0]['text_embedding']  # ❌ Wrong
```

### Docker Network Issues
If the installation scripts fail with connection errors, ensure you're using `--network host`:

```bash
# Correct Docker command in install scripts
docker run --rm --network host docker.elastic.co/eland/eland \
    eland_import_hub_model ...
```

### Environment Variable Loading
Scripts load the `.env` file from the parent directory:

```python
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
```

Ensure your `.env` file is in the project root with:
```
ES_PASSWORD=your_password
ES_HOST=localhost
ES_PORT=9200
```

## 🐛 Troubleshooting

### Model Not Found
```
Error: Model 'elastic__distilbert-base...' not found
```
**Solution**: Run `./inference/install_ner_model.sh`

### Pipeline Errors
```
Error: Pipeline 'wikipedia_ner_pipeline' not found
```
**Solution**: Run `python inference/setup_ner_pipeline.py`

### Out of Memory
```
Error: Circuit breaker triggered
```
**Solution**: 
- Reduce batch size: `--batch-size 5`
- Increase heap: `ES_JAVA_OPTS="-Xmx4g"`

### Slow Processing
**Solutions**:
- Use smaller batches for better progress visibility
- Process during off-peak hours
- Consider using `--sample` for testing

### No Entities Found
**Possible Causes**:
- Text too short (< 50 chars)
- Non-English content
- Technical/code content
- Model confidence too low

## 📚 Additional Resources

### Elasticsearch ML Documentation
- [NLP in Elasticsearch](https://www.elastic.co/guide/en/machine-learning/current/ml-nlp-overview.html)
- [Inference Processor](https://www.elastic.co/guide/en/elasticsearch/reference/current/inference-processor.html)
- [Eland Python Client](https://github.com/elastic/eland)

### NER Background
- [CoNLL-03 Dataset](https://www.clips.uantwerpen.be/conll2003/ner/)
- [DistilBERT Paper](https://arxiv.org/abs/1910.01108)
- [Hugging Face Models](https://huggingface.co/elastic)

### Related Tutorials
- [Building Knowledge Graphs with NER](https://www.elastic.co/blog/nlp-knowledge-graphs)
- [Semantic Search with Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/semantic-search.html)

## 🤝 Contributing

To extend this implementation:

1. **Add New Entity Types**: Modify the pipeline to extract custom entities
2. **Improve Processing**: Add data validation and cleaning
3. **Enhanced Search**: Create more sophisticated query templates
4. **Visualization**: Add Kibana dashboards for entity analytics
5. **Multi-language**: Add support for other languages

## 📊 NER vs Embeddings Comparison

| Aspect | NER (Entity Recognition) | Embeddings (Semantic Search) |
|--------|-------------------------|------------------------------|
| **Purpose** | Extract named entities | Find semantically similar content |
| **Model Size** | ~250MB (DistilBERT) | ~86MB (MiniLM) |
| **Processing Speed** | ~50 docs/min | ~200 docs/min |
| **Storage per Doc** | ~1KB (entities) | ~5KB (3 vectors × 384 dims) |
| **Search Type** | Exact entity matching | Similarity/concept matching |
| **Model Required for Search** | ❌ No | ✅ Yes (for query embedding) |
| **Best For** | Finding specific entities | Understanding context/meaning |
| **Query Example** | "Find docs about Microsoft" | "Find docs similar to this" |
| **Accuracy** | High for known entities | High for semantic similarity |
| **Language Support** | English primarily | 100+ languages |

### When to Use Each:

**Use NER when you need to:**
- Find documents mentioning specific companies, people, or places
- Build knowledge graphs
- Extract structured information
- Perform faceted search by entity type
- Analyze entity relationships

**Use Embeddings when you need to:**
- Find conceptually similar documents
- Implement question-answering systems
- Perform semantic search beyond keywords
- Find related content recommendations
- Search across languages

**Use Both when you need:**
- Comprehensive search capabilities
- Both precision (NER) and recall (embeddings)
- Complex information retrieval
- Enterprise search systems

## 📝 License

This implementation uses:
- Elasticsearch (Elastic License 2.0)
- DistilBERT model (Apache 2.0)
- Sentence Transformers (Apache 2.0)
- Eland (Apache 2.0)

---

## 🧠 Deep Dive: Understanding Named Entity Recognition (NER)

### What is Named Entity Recognition?

Named Entity Recognition (NER) is a fundamental task in Natural Language Processing (NLP) that involves identifying and classifying named entities mentioned in unstructured text into predefined categories. It's essentially the process of teaching machines to recognize "who", "what", "where", and "when" in text - the same way humans naturally identify important proper nouns when reading.

### The Model: DistilBERT for NER

This implementation uses **`elastic/distilbert-base-uncased-finetuned-conll03-english`**, which is:

#### Architecture Overview

**DistilBERT** (Distilled BERT) is a smaller, faster, lighter version of BERT (Bidirectional Encoder Representations from Transformers) that retains 97% of BERT's performance while being:
- 40% smaller in size
- 60% faster in inference
- Uses knowledge distillation from BERT-base

#### Encoder-Only Architecture

DistilBERT is an **encoder-only** transformer model, which means:
- **No Decoder**: Unlike sequence-to-sequence models (T5, BART), DistilBERT only has encoder layers
- **Bidirectional Context**: Can attend to tokens both before and after the current position
- **Not Autoregressive**: Processes entire sequence at once, not token-by-token
- **Optimized for Understanding**: Designed for tasks requiring deep text comprehension rather than generation

This encoder-only design makes it ideal for NER because:
1. Entity recognition requires understanding the full context around each token
2. Bidirectional attention helps identify entity boundaries accurately
3. Parallel processing of all tokens enables faster inference

#### NER Classification Head

For Named Entity Recognition, DistilBERT uses a specialized **token classification head**:

```
[DistilBERT Encoder] → [Linear Layer] → [Softmax] → Entity Labels
     (768 dim)           (768 → 9)                    (9 classes)
```

**Head Architecture**:
- **Input**: 768-dimensional hidden states from final encoder layer
- **Linear Transformation**: Projects each token's representation to 9 dimensions
- **Output Classes**: O, B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC
- **No CRF Layer**: Unlike some NER models, uses simple linear classification
- **Token-Level Predictions**: Each token gets independent classification

#### Key Model Characteristics

1. **Base Architecture**: 
   - 6 transformer encoder layers (vs 12 in BERT-base)
   - 768 hidden dimensions (d_model)
   - 12 attention heads per layer
   - 3072 dimensions in feed-forward network (4 × hidden_size)
   - 66 million parameters (vs 110M in BERT-base)
   - Vocabulary size: 30,522 tokens (WordPiece tokenizer)

2. **Training Process**:
   - **Pre-training**: Trained on BookCorpus and English Wikipedia (same as BERT)
   - **Fine-tuning**: Specifically fine-tuned on CoNLL-03 NER dataset
   - **Distillation**: Learned from BERT-base teacher model using:
     - Masked Language Modeling (MLM)
     - Knowledge distillation loss
     - Cosine embedding loss

3. **CoNLL-03 Dataset**:
   - Standard benchmark for NER
   - ~15,000 annotated sentences from Reuters news
   - 4 entity types: PER (Person), LOC (Location), ORG (Organization), MISC (Miscellaneous)
   - Achieved F1 score of ~90.7% on test set

### How Transformer-based NER Works

#### 1. **Tokenization Phase**
```
Input: "Steve Jobs founded Apple in California"
                    ↓
Tokenization: [CLS] steve jobs founded apple in california [SEP]
                    ↓
Token IDs: [101, 3889, 5841, 2631, 6207, 1999, 5334, 102]
```

#### 2. **Contextual Embedding Generation**
Unlike traditional word embeddings, BERT generates context-aware embeddings:
- Each token gets a 768-dimensional vector
- The vector for "Apple" changes based on context (fruit vs company)
- Bidirectional attention allows the model to see both past and future context

#### 3. **Sequence Labeling with BIO Tagging**
The model uses BIO (Begin-Inside-Outside) tagging scheme:
```
Token:     steve  jobs  founded  apple  in  california
Label:     B-PER  I-PER    O     B-ORG  O    B-LOC
```
- **B-XXX**: Beginning of entity type XXX
- **I-XXX**: Inside (continuation) of entity type XXX  
- **O**: Outside any entity

#### 4. **Classification Layer**
- Linear layer on top of BERT outputs
- Softmax activation for each token
- Predicts probability distribution over 9 classes:
  - O, B-PER, I-PER, B-ORG, I-ORG, B-LOC, I-LOC, B-MISC, I-MISC

### Why Transformer Models Excel at NER

#### 1. **Contextual Understanding**
Traditional approaches used hand-crafted features or word embeddings that ignored context. Transformers understand that:
- "Apple" in "Apple released iPhone" → Organization
- "apple" in "eating an apple" → Not an entity
- "Paris" in "Paris Hilton" → Part of person name
- "Paris" in "visiting Paris" → Location

#### 2. **Long-Range Dependencies**
Self-attention mechanism allows the model to connect related information across long distances:
```
"The CEO of Microsoft, who had previously worked at Google for 10 years, 
announced..." 
```
The model can link "CEO" with both "Microsoft" and "Google" despite the distance.

#### 3. **Transfer Learning Benefits**
- Pre-trained on massive text corpora (Wikipedia + BookCorpus)
- Learned general language understanding
- Fine-tuning on NER requires relatively small labeled dataset
- Generalizes well to different domains

### Technical Deep Dive: Attention Mechanism

The self-attention mechanism is key to understanding context:

1. **Query, Key, Value Computation**:
   - For each token, compute Q, K, V vectors
   - Attention score = softmax(QK^T / √d_k)
   - Output = Attention × V

2. **Multi-Head Attention**:
   - 12 parallel attention heads
   - Each head learns different relationships
   - Example heads might specialize in:
     - Syntactic dependencies
     - Coreference resolution
     - Entity boundaries

3. **Position Embeddings**:
   - Add positional information to tokens
   - Allows model to understand word order
   - Critical for identifying multi-word entities

### Performance Characteristics

#### Speed vs Accuracy Trade-offs

| Model | F1 Score | Inference Time | Memory Usage |
|-------|----------|----------------|--------------|
| BERT-base | 91.3% | 100ms/doc | 440MB |
| DistilBERT | 90.7% | 40ms/doc | 265MB |
| BiLSTM-CRF | 89.2% | 20ms/doc | 50MB |
| Rule-based | 75-80% | 5ms/doc | <10MB |

#### Processing Pipeline in Elasticsearch

1. **Text Input** → Document sent to inference pipeline
2. **Tokenization** → WordPiece tokenizer splits text
3. **Truncation** → Limited to 512 tokens (BERT constraint)
4. **Inference** → Forward pass through DistilBERT
5. **Decoding** → BIO tags converted to entity spans
6. **Post-processing** → Entities deduplicated and stored

### Advanced NER Concepts

#### 1. **Nested Entities**
Challenge: "University of California, Berkeley"
- Nested: "California" (LOC) inside "University of California, Berkeley" (ORG)
- Current model: Extracts non-overlapping entities only

#### 2. **Entity Disambiguation**
- "Jordan" → Person (Michael Jordan) or Location (country)?
- Requires additional context or knowledge base

#### 3. **Domain Adaptation**
- Model trained on news articles
- May struggle with:
  - Medical texts (drug names, diseases)
  - Legal documents (case names, statutes)
  - Social media (hashtags, mentions)

#### 4. **Multilingual Challenges**
- Current model: English only
- Multilingual models available (mBERT, XLM-R)
- Trade-off: Lower per-language performance

### Practical Implications for Search

#### Entity-Based Search Advantages

1. **Precision**: Find exact entity matches regardless of context
2. **Relationship Queries**: "Find docs where Google acquired companies"
3. **Faceted Navigation**: Filter by entity type
4. **Entity Analytics**: Track entity mentions over time

#### Limitations to Consider

1. **Entity Coverage**: ~90% accuracy means ~10% missed/wrong
2. **Domain Specificity**: May miss specialized entities
3. **Context Window**: 512 token limit truncates long documents
4. **Language Constraint**: English-only in this model

### Future Directions in NER

1. **Few-Shot Learning**: Adapt to new entity types with minimal examples
2. **Cross-lingual Transfer**: Train on one language, apply to many
3. **Document-Level NER**: Process entire documents, not just passages
4. **Entity Linking**: Connect entities to knowledge bases (Wikipedia, Wikidata)
5. **Multimodal NER**: Combine text with images/audio for better recognition

### Best Practices for Production NER

1. **Preprocessing**:
   - Clean HTML/markup before processing
   - Handle special characters appropriately
   - Consider sentence segmentation for long texts

2. **Post-processing**:
   - Merge adjacent entities of same type
   - Validate entities against known lists
   - Apply domain-specific rules

3. **Evaluation Metrics**:
   - **Precision**: Of predicted entities, how many are correct?
   - **Recall**: Of actual entities, how many were found?
   - **F1 Score**: Harmonic mean of precision and recall

4. **Error Analysis**:
   - Common errors: Partial matches, boundary detection, rare entities
   - Domain-specific challenges need custom solutions

This deep understanding of NER and the DistilBERT model helps explain why it's so effective for information extraction and how to best utilize it in your Elasticsearch implementation.

---

## 📊 Building Kibana Dashboards for NER Data

### Complete Beginner's Guide to Visualizing Named Entities

This section provides a comprehensive, step-by-step guide for creating interactive Kibana dashboards to visualize and analyze the named entities extracted from Wikipedia articles. No prior Kibana experience required!

### 🎯 What You'll Build

By the end of this guide, you'll have a complete NER analytics dashboard featuring:
- **Entity Tag Clouds**: Visual word clouds showing most frequent entities
- **Top Entities Bar Charts**: Ranked lists of organizations, locations, and persons
- **Entity Distribution Pie Charts**: Proportional breakdowns by entity type
- **Time-Series Analysis**: Entity mentions over time
- **Geographic Maps**: Location entity visualization (if coordinates available)
- **Entity Co-occurrence Matrix**: Which entities appear together
- **Search and Filter Controls**: Interactive exploration tools

### 📋 Prerequisites

1. **Elasticsearch with NER data**: Run `python inference/process_wikipedia_ner.py` first
2. **Kibana access**: Usually at http://localhost:5601
3. **Browser**: Chrome or Firefox recommended
4. **Sample data**: At least 50-100 processed Wikipedia articles for meaningful visualizations

### 🚀 Step 1: Access Kibana

#### First Time Setup
```bash
# If using Docker, Kibana might be included:
docker run -d \
  --name kibana \
  --link elasticsearch:elasticsearch \
  -p 5601:5601 \
  docker.elastic.co/kibana/kibana:8.11.0

# Wait 30-60 seconds for Kibana to start
```

#### Access Kibana Interface
1. Open browser to http://localhost:5601
2. If prompted for credentials, use:
   - Username: `elastic`
   - Password: Your ES_PASSWORD from .env file
3. You should see the Kibana home page

### 📁 Step 2: Create a Data View (Index Pattern)

Data Views tell Kibana which Elasticsearch indices to query for visualizations.

#### Navigate to Data Views
1. Click the **☰** hamburger menu (top left)
2. Go to **Stack Management** (under Management section)
3. Click **Data Views** (under Kibana section)
4. Click **Create data view** button

#### Configure the Data View
1. **Name**: `Wikipedia NER Entities`
2. **Index pattern**: `wikipedia_ner*` (matches wikipedia_ner index)
3. **Timestamp field**: 
   - Select `ner_processed_at` if you want time-based analysis
   - Or choose "I don't want to use the time filter" for simpler setup
4. Click **Save data view to Kibana**

#### Verify Fields
After creation, you should see fields including:
- `ner_organizations.keyword` - Organization names
- `ner_locations.keyword` - Location names  
- `ner_persons.keyword` - Person names
- `ner_misc.keyword` - Miscellaneous entities
- `title` - Article titles
- `city`, `state` - Geographic metadata

### 🎨 Step 3: Create Your First Visualization - Entity Tag Cloud

Tag clouds are perfect for showing the most frequent entities at a glance.

#### Start Creating
1. Click **☰** menu → **Dashboard**
2. Click **Create dashboard**
3. Click **Create visualization**
4. Choose **Aggregation based** → **Tag cloud**

#### Configure the Tag Cloud
1. **Data source**: Select "Wikipedia NER Entities" data view

2. **Metrics** (already set):
   - Aggregation: Count
   
3. **Buckets** - Add a bucket:
   - Click **Add** → **Tags**
   - **Aggregation**: Terms
   - **Field**: `ner_persons.keyword`
   - **Size**: 30 (shows top 30 persons)
   - **Custom label**: "Top People Mentioned"

4. **Options** (right panel):
   - **Font size range**: 20 to 60
   - **Orientations**: Multiple
   - **Show labels**: On

5. Click **Update** (blue button, bottom right)

6. **Save visualization**:
   - Click **Save** (top right)
   - Title: "Top People in Wikipedia Articles"
   - Add to dashboard: Current dashboard

### 📊 Step 4: Create Multiple Entity Type Visualizations

Now create similar visualizations for each entity type:

#### A. Organizations Bar Chart
1. **Create new** → **Aggregation based** → **Vertical bar**
2. **Configuration**:
   - Field: `ner_organizations.keyword`
   - Size: 20
   - Order by: Count (descending)
3. **Save as**: "Top Organizations"

#### B. Locations Horizontal Bar
1. **Create new** → **Aggregation based** → **Horizontal bar**
2. **Configuration**:
   - Field: `ner_locations.keyword`
   - Size: 15
   - Show percentages: On
3. **Save as**: "Most Mentioned Locations"

#### C. Entity Type Distribution Pie Chart
1. **Create new** → **Aggregation based** → **Pie**
2. **Bucket configuration**:
   ```
   Aggregation: Filters
   Filter 1: ner_organizations: * (Label: "Organizations")
   Filter 2: ner_locations: * (Label: "Locations")
   Filter 3: ner_persons: * (Label: "Persons")
   Filter 4: ner_misc: * (Label: "Miscellaneous")
   ```
3. **Save as**: "Entity Type Distribution"

### 🔍 Step 5: Advanced Visualizations

#### A. Entity Co-occurrence Heat Map
Shows which entities frequently appear together:

1. **Create new** → **Aggregation based** → **Heat map**
2. **Y-axis**:
   - Aggregation: Terms
   - Field: `ner_persons.keyword`
   - Size: 10
3. **X-axis**:
   - Aggregation: Terms
   - Field: `ner_organizations.keyword`
   - Size: 10
4. **Values**:
   - Aggregation: Count
5. **Save as**: "Person-Organization Associations"

#### B. Time Series of Entity Mentions
(Only if you selected a timestamp field):

1. **Create new** → **Aggregation based** → **Line**
2. **Configuration**:
   - X-axis: Date Histogram on `ner_processed_at`
   - Y-axis: Count
   - Split series: Terms on `ner_organizations.keyword` (top 5)
3. **Save as**: "Entity Mentions Over Time"

#### C. Data Table of All Entities
1. **Create new** → **Aggregation based** → **Data table**
2. **Add multiple metrics**:
   - Unique count of `ner_organizations.keyword` (Label: "Unique Orgs")
   - Unique count of `ner_persons.keyword` (Label: "Unique People")
   - Unique count of `ner_locations.keyword` (Label: "Unique Locations")
3. **Split rows**:
   - Terms on `title.keyword` (Size: 50)
4. **Save as**: "Articles Entity Summary Table"

### 🎯 Step 6: Create Interactive Filters

#### Add Control Visualizations
1. **Create new** → **Controls**
2. **Add controls**:
   
   **Control 1 - Entity Type Selector**:
   - Type: Options list
   - Field: `_index`
   - Label: "Select Index"
   
   **Control 2 - Location Filter**:
   - Type: Options list  
   - Field: `city.keyword`
   - Label: "Filter by City"
   - Parent control: None
   
   **Control 3 - Search Box**:
   - Type: Options list
   - Field: `ner_persons.keyword`
   - Label: "Search for Person"
   - Allow multiselect: Yes

3. **Save as**: "Dashboard Filters"

### 🏗️ Step 7: Arrange Your Dashboard

#### Layout Best Practices
1. **Top Row**: Place filter controls and title
2. **Second Row**: Key metrics (data tables, totals)
3. **Main Area**: Large visualizations (tag clouds, bar charts)
4. **Bottom**: Detailed tables and time series

#### Arrange Visualizations
1. **Resize**: Drag corners to resize each panel
2. **Move**: Drag panel headers to reposition
3. **Suggested layout**:
   ```
   [Filters (full width)]
   [Tag Cloud People | Tag Cloud Orgs | Tag Cloud Locations]
   [Bar Chart Orgs  | Pie Chart Types | Heat Map]
   [Time Series (full width)]
   [Data Table (full width)]
   ```

### 🎨 Step 8: Styling and Customization

#### Dashboard Settings
1. Click **Settings** (gear icon, top right)
2. **Options**:
   - Title: "Wikipedia NER Entity Analysis"
   - Description: "Named entity extraction insights from Wikipedia articles"
   - Dark mode: Toggle based on preference
   - Show query: Off (unless debugging)

#### Color Schemes
1. Edit each visualization
2. **Color palette options**:
   - Organizations: Blue gradient
   - Persons: Green gradient
   - Locations: Orange gradient
   - Miscellaneous: Purple gradient

### 🔄 Step 9: Add Real-time Updates

#### Auto-refresh Setup
1. Click time picker (top right)
2. Select **Auto-refresh**
3. Choose interval: 30 seconds or 1 minute
4. Useful for monitoring active NER processing

#### Time Range Tips
- **Last 7 days**: Good for recent processing
- **Last 30 days**: Better for trend analysis
- **Custom range**: For specific processing batches

### 📱 Step 10: Interactive Features

#### Enable Drill-downs
1. Edit any bar/pie chart visualization
2. Go to **Options** → **Interactions**
3. Enable **Drill-down** URLs:
   ```
   URL template: /app/discover#/?_a=(query:(match:({field}:'{value}')))
   ```
4. Now clicking entities opens detailed document view

#### Add Markdown Explanations
1. **Create new** → **Markdown**
2. Add helpful text:
   ```markdown
   # NER Entity Dashboard
   
   This dashboard shows named entities extracted from Wikipedia articles:
   - **ORG**: Organizations, companies, institutions
   - **PER**: People, historical figures, authors
   - **LOC**: Locations, cities, countries
   - **MISC**: Miscellaneous named entities
   
   Click any entity to filter the entire dashboard!
   ```

### 🚨 Step 11: Common Issues and Solutions

#### Problem: No data showing
**Solution**: 
1. Verify index has data: `curl localhost:9200/wikipedia_ner/_count`
2. Check time range includes your data
3. Remove all filters and try again

#### Problem: Fields not appearing
**Solution**:
1. Refresh data view: Stack Management → Data Views → Refresh
2. Check field types: Ensure using `.keyword` fields for aggregations

#### Problem: Visualization errors
**Solution**:
1. Check field mappings match
2. Reduce bucket size if too many unique values
3. Use "exists" query to filter null values

### 💾 Step 12: Save and Share

#### Save Dashboard
1. Click **Save** (top right)
2. Name: "Wikipedia NER Analysis"
3. Description: Add meaningful description
4. Tags: "ner", "nlp", "wikipedia"
5. **Save**

#### Export Dashboard
1. Stack Management → Saved Objects
2. Find your dashboard
3. Click checkbox → Export
4. Saves as `.ndjson` file

#### Share Dashboard
1. Click **Share** (top right)
2. Options:
   - **Embed code**: For websites
   - **Permalink**: Direct link
   - **PDF Reports**: Schedule exports
   - **PNG Image**: Screenshot

### 📈 Advanced Tips

#### 1. Comparative Analysis
Create split charts comparing:
- Entities across different cities
- Entity types by article category
- Person mentions by time period

#### 2. Alerting
Set up Watcher alerts for:
- New entity types discovered
- Unusual entity frequency spikes
- Processing errors

#### 3. Machine Learning
Use Kibana ML features to:
- Detect anomalous entity patterns
- Forecast entity trends
- Classify articles by entity profile

### 🎯 Example Use Cases

1. **Research Analysis**: Track mentions of scientists across articles
2. **Geographic Study**: Map location entities by frequency
3. **Historical Figures**: Analyze co-occurrence of historical persons
4. **Organization Networks**: Discover relationships between companies
5. **Content Categorization**: Group articles by dominant entity types

### 📚 Additional Resources

- [Kibana Guide](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Visualization Types](https://www.elastic.co/guide/en/kibana/current/aggregation-based.html)
- [Dashboard Tutorial](https://www.elastic.co/guide/en/kibana/current/tutorial-build-dashboard.html)
- [Elastic NER Example](https://www.elastic.co/docs/explore-analyze/machine-learning/nlp/ml-nlp-ner-example)

### 🎉 Congratulations!

You've now built a complete NER analytics dashboard! This dashboard will automatically update as you process more Wikipedia articles through the NER pipeline. Experiment with different visualizations and filters to gain deeper insights into your entity data.

**Next Steps**:
1. Process more articles: `python inference/process_wikipedia_ner.py --sample all`
2. Create specialized dashboards for specific entity types
3. Export visualizations for reports and presentations
4. Set up alerts for interesting entity patterns
5. Combine with embedding visualizations for hybrid analysis