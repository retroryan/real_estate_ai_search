"""Output writers for various destinations.

This module provides writers for persisting processed data to different formats:
- Parquet files for efficient columnar storage
- Elasticsearch for search and analytics
- Strategy pattern for extensible output destinations

Writers handle:
- Batch processing for performance
- Error handling and retry logic
- Data validation before writing
- Metrics collection and reporting
"""