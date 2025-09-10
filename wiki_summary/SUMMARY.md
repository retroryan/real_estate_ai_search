# Wikipedia Summary Process

## Overview
The wiki_summary module processes Wikipedia articles to extract location information and generate structured summaries using DSPy (Declarative Self-improving Language Programs). The system combines HTML parsing, LLM-based extraction, and intelligent caching to create comprehensive location summaries.

## Process Steps

### 1. Database Initialization
- Connects to the existing SQLite database (wikipedia.db)
- Creates the page_summaries table if it doesn't exist
- Sets up indexes for optimal query performance
- Establishes foreign key relationships with the articles table

### 2. Retrieving Unprocessed Pages
- Queries the database for articles that haven't been summarized yet
- Joins articles with locations table to get existing location metadata
- Orders by relevance score to prioritize important articles
- Loads HTML content from files stored in the pages directory
- Packages each page with its metadata for processing

### 3. LLM Configuration with DSPy
- Sets up the language model using DSPy's modern LM interface
- Configures temperature, max tokens, and caching parameters
- Enables JSONAdapter for structured output when available
- Falls back to default adapter for older DSPy versions
- Tests the connection with a simple prompt to verify setup

### 4. HTML Content Preparation
- Parses raw HTML using BeautifulSoup
- Removes unnecessary elements (scripts, styles, navigation, references)
- Extracts the main article title and lead paragraphs
- Preserves key sections while removing Wikipedia-specific artifacts
- Truncates content to approximately 4000 characters for LLM processing
- Maintains article structure with markdown-style formatting

### 5. Location Hint Extraction from HTML
- Searches for location data in Wikipedia categories
- Extracts information from infobox fields
- Identifies geographic coordinates from various formats
- Parses first paragraph for location descriptions
- Assigns confidence scores based on extraction source
- Creates structured hints for the LLM to validate against

### 6. DSPy Signature Definition
- Creates ExtractPageSummaryWithContext signature with typed fields
- Defines input fields for page title, content, HTML hints, and known path
- Specifies output fields for summaries, topics, and location data
- Includes comprehensive docstrings to guide LLM behavior
- Sets up confidence scoring requirements
- Establishes constraints for output format and length

### 7. Chain of Thought Processing
- Initializes WikipediaExtractAgent with ChainOfThought wrapper
- Optionally uses LocationClassificationCoT for entity type classification
- Enables reasoning steps for better extraction accuracy
- Provides fallback to simple Predict for faster processing
- Configures whether to use location classifier based on requirements

### 8. Cache Checking
- Generates cache key from page ID and content hash
- Checks file-based cache for existing summaries
- Returns cached results if available to save API costs
- Maintains cache statistics for monitoring
- Allows cache clearing for fresh processing runs

### 9. DSPy Extraction Execution
- Passes cleaned content and hints to the configured DSPy module
- Executes the extraction with comprehensive error handling
- Captures both DSPy-specific and general exceptions
- Logs detailed information about the extraction process
- Retries or fails gracefully based on error type

### 10. Result Processing and Validation
- Validates that all required fields are present in DSPy output
- Handles 'unknown' values by converting to None
- Cleans summary text for consistency
- Ensures proper sentence endings
- Limits key topics to maximum of 5 items
- Builds LocationMetadata objects with confidence scores

### 11. Location Correlation
- Compares LLM-extracted locations with HTML hints
- Validates against known location path from database
- Resolves conflicts between different extraction sources
- Computes overall confidence based on agreement
- Selects best location based on highest confidence scores

### 12. PageSummary Object Creation
- Combines all extracted data into structured PageSummary
- Includes both short (100 word) and long (500 word) summaries
- Attaches key topics that characterize the location
- Stores both LLM and HTML location extractions
- Records overall confidence score for quality assessment

### 13. Caching Successful Results
- Serializes summary data to JSON format
- Stores in file-based cache with content hash
- Enables reuse for identical content
- Reduces API costs during development and testing
- Maintains cache directory structure

### 14. Database Storage
- Saves the complete summary to page_summaries table
- Links to original article via foreign key
- Stores best location determination
- Records processing timestamp
- Commits transaction atomically

### 15. Batch Processing Support
- Processes multiple articles in sequence
- Handles failures gracefully without stopping batch
- Logs progress and errors for monitoring
- Supports limiting batch size for testing
- Provides statistics on processing completion

### 16. Location Classification (Optional)
- Classifies geographic entity type (city, county, natural feature, etc.)
- Determines if article is relevant to Utah/California
- Uses flexible classification allowing any location type
- Provides reasoning for classification decisions
- Flags articles that aren't geographically relevant

### 17. Error Recovery
- Implements comprehensive exception handling
- Distinguishes between DSPy errors and data errors
- Logs detailed error information for debugging
- Continues batch processing despite individual failures
- Provides error statistics for quality monitoring

### 18. Quality Assurance
- Verifies location correlation with stored data
- Calculates accuracy metrics for extraction
- Provides processing summaries for review
- Tracks confidence scores across all extractions
- Enables reset for reprocessing when needed

## DSPy Components

### Signatures
- **ExtractPageSummaryWithContext**: Main extraction signature with location and summary fields
- **ExtractLocationClassification**: Optional signature for entity type classification

### Modules
- **WikipediaExtractAgent**: Primary extraction module using ChainOfThought
- **LocationClassificationCoT**: Classification module for geographic entities
- **LocationClassificationBatch**: Batch processor for multiple articles

### Adapters
- **JSONAdapter**: Ensures structured output with automatic fallback
- **ChainOfThought**: Enables step-by-step reasoning for better accuracy
- **Predict**: Simple prediction for faster processing

## Key Features

### Intelligent Caching
- File-based cache using MD5 content hashing
- Reduces API costs during development
- Enables quick iteration on processing logic
- Maintains cache statistics for monitoring

### Confidence Scoring
- Tracks extraction confidence at multiple levels
- Compares sources for validation
- Provides overall quality metrics
- Enables filtering by confidence threshold

### Flexible Location Extraction
- Combines multiple extraction methods
- Validates across different sources
- Handles missing or ambiguous data
- Provides best guess with confidence

### Structured Output
- Generates both short and long summaries
- Extracts key topics for categorization
- Provides typed, validated data models
- Ensures consistency across all outputs

## Benefits of DSPy Approach

### Declarative Programming
- Defines what to extract, not how
- Separates logic from implementation
- Enables easy modification of requirements
- Provides clear, maintainable code

### Type Safety
- Uses typed signatures for validation
- Ensures output consistency
- Catches errors early in processing
- Provides clear contracts for modules

### Self-Improvement
- Learns from examples when provided
- Adapts to specific domain requirements
- Improves accuracy over time
- Supports prompt optimization

### Modular Architecture
- Separates concerns into distinct modules
- Enables easy testing and debugging
- Supports composition of complex pipelines
- Allows swapping of components