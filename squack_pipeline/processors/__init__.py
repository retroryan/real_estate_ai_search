"""Data processors implementing medallion architecture tiers.

This module contains processors for transforming data through the
Bronze -> Silver -> Gold medallion architecture:

- Bronze: Raw data ingestion with minimal validation
- Silver: Cleaned and enriched data with cross-entity relationships
- Gold: Analytics-ready data optimized for search and analysis

Each processor handles entity-specific transformations while maintaining
consistent patterns and proper error handling throughout the pipeline.
"""