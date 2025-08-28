"""
HTML template for search results.

Clean, modern HTML template with embedded CSS for styling.
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Search Results</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .description {
            font-size: 1.2em;
            opacity: 0.95;
        }
        
        .metadata {
            background: #f8f9fa;
            padding: 20px 40px;
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }
        
        .meta-item {
            text-align: center;
            padding: 10px;
        }
        
        .meta-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            display: block;
        }
        
        .meta-label {
            color: #6c757d;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }
        
        .scoring-explanation {
            background: linear-gradient(135deg, #e7f3ff 0%, #f0e7ff 100%);
            border-left: 4px solid #667eea;
            padding: 25px 30px;
            margin: 30px 40px;
            border-radius: 8px;
        }
        
        .scoring-explanation h2 {
            color: #2c3e50;
            font-size: 1.4em;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .scoring-explanation p {
            color: #4a5568;
            line-height: 1.7;
            margin-bottom: 10px;
        }
        
        .scoring-explanation ul {
            margin: 15px 0;
            padding-left: 25px;
        }
        
        .scoring-explanation li {
            color: #4a5568;
            margin: 8px 0;
            line-height: 1.6;
        }
        
        .scoring-explanation code {
            background: rgba(102, 126, 234, 0.1);
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            color: #667eea;
        }
        
        .content {
            padding: 40px;
        }
        
        .query-section {
            margin-bottom: 50px;
            border-left: 4px solid #667eea;
            padding-left: 30px;
        }
        
        .query-header {
            margin-bottom: 20px;
        }
        
        .query-title {
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        
        .query-description {
            color: #6c757d;
            font-style: italic;
        }
        
        .query-stats {
            background: #e7f3ff;
            padding: 10px 15px;
            border-radius: 6px;
            display: inline-block;
            margin: 10px 0;
        }
        
        .document {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .document:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .doc-header {
            display: flex;
            justify-content: space-between;
            align-items: start;
            margin-bottom: 15px;
        }
        
        .doc-title {
            font-size: 1.3em;
            color: #2c3e50;
            font-weight: 600;
        }
        
        .doc-score {
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        
        .doc-metadata {
            display: flex;
            gap: 20px;
            margin: 10px 0;
            font-size: 0.9em;
            color: #6c757d;
        }
        
        .doc-meta-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        
        .categories {
            margin: 10px 0;
        }
        
        .category {
            display: inline-block;
            background: #e9ecef;
            padding: 4px 8px;
            border-radius: 4px;
            margin-right: 8px;
            font-size: 0.85em;
            color: #495057;
        }
        
        .highlights {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #dee2e6;
        }
        
        .highlight-title {
            font-weight: 600;
            color: #6c757d;
            margin-bottom: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .highlight-text {
            background: white;
            padding: 15px;
            border-radius: 6px;
            margin: 10px 0;
            border-left: 3px solid #667eea;
            line-height: 1.8;
        }
        
        .highlight-text strong {
            background: #fff3cd;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: 600;
            color: #856404;
        }
        
        .no-results {
            text-align: center;
            padding: 40px;
            color: #6c757d;
            font-style: italic;
        }
        
        .top-documents {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 30px;
            margin-top: 40px;
        }
        
        .top-documents h2 {
            color: #2c3e50;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        
        .top-doc-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: white;
            border-radius: 6px;
            margin: 10px 0;
            transition: transform 0.2s;
        }
        
        .top-doc-item:hover {
            transform: translateX(5px);
        }
        
        .top-doc-rank {
            font-size: 1.5em;
            font-weight: bold;
            color: #667eea;
            margin-right: 20px;
        }
        
        .top-doc-title {
            flex-grow: 1;
            font-weight: 600;
        }
        
        .top-doc-score {
            color: #28a745;
            font-weight: bold;
        }
        
        footer {
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }
        
        .timestamp {
            opacity: 0.8;
        }
        
        /* Responsive Design */
        @media (max-width: 768px) {
            .metadata {
                flex-direction: column;
            }
            
            .doc-header {
                flex-direction: column;
            }
            
            .doc-score {
                margin-top: 10px;
            }
            
            h1 {
                font-size: 1.8em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔍 {{ title }}</h1>
            <p class="description">{{ description }}</p>
        </header>
        
        <div class="metadata">
            <div class="meta-item">
                <span class="meta-value">{{ total_queries }}</span>
                <span class="meta-label">Queries Executed</span>
            </div>
            <div class="meta-item">
                <span class="meta-value">{{ successful_queries }}</span>
                <span class="meta-label">Successful Queries</span>
            </div>
            <div class="meta-item">
                <span class="meta-value">{{ total_documents_found }}</span>
                <span class="meta-label">Total Documents</span>
            </div>
            <div class="meta-item">
                <span class="meta-value">{{ average_results | round(1) }}</span>
                <span class="meta-label">Avg Results/Query</span>
            </div>
        </div>
        
        <div class="scoring-explanation">
            <h2>📊 Understanding Elasticsearch Relevance Scores</h2>
            <p>
                <strong>What do these scores mean?</strong> Elasticsearch calculates a relevance score for each document 
                that matches your search query. Higher scores indicate better matches based on sophisticated ranking algorithms.
            </p>
            
            <p>
                <strong>How Scoring Works:</strong>
            </p>
            <ul>
                <li><strong>TF-IDF Algorithm:</strong> The foundation of scoring uses Term Frequency (how often a term appears in a document) 
                    and Inverse Document Frequency (how rare the term is across all documents). Common words like "the" have low scores, 
                    while rare, specific terms score higher.</li>
                
                <li><strong>BM25 Scoring:</strong> Elasticsearch uses BM25 by default, an advanced version of TF-IDF that includes:
                    <ul style="margin-top: 5px;">
                        <li>Document length normalization (shorter docs aren't unfairly penalized)</li>
                        <li>Diminishing returns for term frequency (10 occurrences isn't 10x better than 1)</li>
                        <li>Tunable parameters for fine-tuning relevance</li>
                    </ul>
                </li>
                
                <li><strong>Field Boosting:</strong> Different fields can have different importance. In these queries:
                    <ul style="margin-top: 5px;">
                        <li><code>title^2</code> means title matches are 2x more important</li>
                        <li><code>summary^1.5</code> gives summary matches 1.5x weight</li>
                        <li>Content fields have standard weight (1.0)</li>
                    </ul>
                </li>
                
                <li><strong>Query Types Affect Scoring:</strong>
                    <ul style="margin-top: 5px;">
                        <li><strong>Match queries:</strong> Full-text search with analysis and scoring</li>
                        <li><strong>Phrase queries:</strong> Exact phrase matches score higher</li>
                        <li><strong>Bool queries:</strong> Combine multiple conditions with must/should/filter</li>
                        <li><strong>Multi-match:</strong> Search across multiple fields simultaneously</li>
                    </ul>
                </li>
            </ul>
            
            <p>
                <strong>Score Interpretation:</strong> Scores are relative within a single search. A score of 28.59 in one search 
                isn't directly comparable to 28.59 in another search. What matters is the relative ranking - documents with 
                higher scores are more relevant to your specific query.
            </p>
            
            <p>
                <strong>Pro Tip:</strong> The <code>_score</code> field is calculated in real-time for each query. 
                Elasticsearch doesn't store pre-computed relevance scores because they depend entirely on the search terms, 
                query structure, and the current state of the index.
            </p>
        </div>
        
        <div class="content">
            {% for query in queries %}
            <div class="query-section">
                <div class="query-header">
                    <h2 class="query-title">{{ query.query_title }}</h2>
                    <p class="query-description">{{ query.query_description }}</p>
                    <div class="query-stats">
                        <strong>{{ query.total_results }}</strong> matching documents found
                        {% if query.execution_time_ms %}
                        • <strong>{{ query.formatted_execution_time }}</strong>
                        {% endif %}
                    </div>
                </div>
                
                {% if query.documents %}
                    {% for doc in query.documents %}
                    <div class="document">
                        <div class="doc-header">
                            <div>
                                <div class="doc-title">
                                    📖 
                                    {% if doc.url %}
                                    <a href="{{ doc.url }}" target="_blank" style="color: inherit; text-decoration: none; border-bottom: 1px dotted #667eea;">{{ doc.title }}</a>
                                    {% else %}
                                    {{ doc.title }}
                                    {% endif %}
                                </div>
                                {% if doc.location %}
                                <div class="doc-metadata">
                                    <div class="doc-meta-item">
                                        📍 {{ doc.formatted_location }}
                                    </div>
                                    {% if doc.content_length %}
                                    <div class="doc-meta-item">
                                        📊 {{ doc.formatted_size }}
                                    </div>
                                    {% endif %}
                                    {% if doc.url %}
                                    <div class="doc-meta-item">
                                        🔗 <a href="{{ doc.url }}" target="_blank" style="color: #667eea;">View on Wikipedia</a>
                                    </div>
                                    {% endif %}
                                    {% if doc.local_html_file %}
                                    <div class="doc-meta-item">
                                        📄 <a href="{{ doc.local_html_file }}" target="_blank" style="color: #28a745;">View Full Article (Local)</a>
                                    </div>
                                    {% endif %}
                                </div>
                                {% endif %}
                            </div>
                            <div class="doc-score">Score: {{ "%.2f"|format(doc.score) }}</div>
                        </div>
                        
                        {% if doc.top_categories %}
                        <div class="categories">
                            {% for category in doc.top_categories %}
                            <span class="category">{{ category }}</span>
                            {% endfor %}
                        </div>
                        {% endif %}
                        
                        {% if doc.highlights %}
                        <div class="highlights">
                            <div class="highlight-title">Relevant Content</div>
                            {% for highlight in doc.highlights %}
                            <div class="highlight-text">{{ highlight.to_html() | safe }}</div>
                            {% endfor %}
                        </div>
                        {% elif doc.summary %}
                        <div class="highlights">
                            <div class="highlight-title">Summary</div>
                            <div class="highlight-text">{{ doc.summary }}</div>
                        </div>
                        {% endif %}
                    </div>
                    {% endfor %}
                {% else %}
                    <div class="no-results">No results found for this query</div>
                {% endif %}
            </div>
            {% endfor %}
            
            {% if top_documents %}
            <div class="top-documents">
                <h2>🏆 Top Scoring Documents</h2>
                {% for doc in top_documents %}
                <div class="top-doc-item">
                    <span class="top-doc-rank">#{{ loop.index }}</span>
                    <span class="top-doc-title">{{ doc.title }}</span>
                    <span class="top-doc-score">Score: {{ "%.2f"|format(doc.score) }}</span>
                </div>
                {% endfor %}
            </div>
            {% endif %}
        </div>
        
        <footer>
            <p>Generated on <span class="timestamp">{{ formatted_timestamp }}</span></p>
            <p>Real Estate Search - Wikipedia Full-Text Search Demo</p>
            <p><a href="https://github.com/retroryan/real_estate_ai_search" target="_blank" style="color: #667eea; text-decoration: none;">
                <i class="fab fa-github"></i> View on GitHub
            </a></p>
        </footer>
    </div>
</body>
</html>
"""