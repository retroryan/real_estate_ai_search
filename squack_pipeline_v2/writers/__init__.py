"""Writers for exporting pipeline data.

Following DuckDB best practices:
- Parquet writer uses DuckDB COPY command
- Elasticsearch writer validates with Pydantic
- No unnecessary data movement
"""

from squack_pipeline_v2.writers.parquet import ParquetWriter
from squack_pipeline_v2.writers.elastic import ElasticsearchWriter

__all__ = [
    "ParquetWriter",
    "ElasticsearchWriter"
]