"""Pipeline orchestration module.

Coordinates the entire medallion architecture pipeline:
Bronze → Silver → Gold → Embeddings → Writers
"""

from squack_pipeline_v2.orchestration.pipeline import PipelineOrchestrator

__all__ = ["PipelineOrchestrator"]
