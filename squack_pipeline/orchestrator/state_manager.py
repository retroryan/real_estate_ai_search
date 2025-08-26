"""Pipeline state management for recovery and monitoring."""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

from squack_pipeline.config.settings import PipelineSettings
from squack_pipeline.utils.logging import PipelineLogger


class PipelineState(str, Enum):
    """Pipeline execution states."""
    INITIALIZING = "initializing"
    LOADING_BRONZE = "loading_bronze"
    PROCESSING_SILVER = "processing_silver"
    PROCESSING_GOLD = "processing_gold"
    ENRICHING_GEOGRAPHIC = "enriching_geographic"
    GENERATING_EMBEDDINGS = "generating_embeddings"
    WRITING_OUTPUT = "writing_output"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StateSnapshot(BaseModel):
    """Pipeline state snapshot for persistence."""
    
    pipeline_id: str = Field(description="Unique pipeline execution ID")
    state: PipelineState = Field(description="Current pipeline state")
    started_at: datetime = Field(description="Pipeline start time")
    updated_at: datetime = Field(description="Last update time")
    environment: str = Field(description="Execution environment")
    
    # Progress tracking
    current_phase: str = Field(default="", description="Current processing phase")
    records_processed: int = Field(default=0, description="Total records processed")
    
    # Table tracking for recovery
    bronze_table: Optional[str] = Field(default=None, description="Bronze tier table name")
    silver_table: Optional[str] = Field(default=None, description="Silver tier table name")
    gold_table: Optional[str] = Field(default=None, description="Gold tier table name")
    enriched_table: Optional[str] = Field(default=None, description="Enriched table name")
    
    # Metrics
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Pipeline metrics")
    
    # Error tracking
    error_message: Optional[str] = Field(default=None, description="Error message if failed")
    error_phase: Optional[str] = Field(default=None, description="Phase where error occurred")


class PipelineStateManager:
    """Manages pipeline state for monitoring and recovery."""
    
    def __init__(self, settings: PipelineSettings):
        """Initialize state manager."""
        self.settings = settings
        self.logger = PipelineLogger.get_logger(self.__class__.__name__)
        
        # State file location
        self.state_dir = settings.data.output_path / ".pipeline_state"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique pipeline ID
        self.pipeline_id = f"pipeline_{int(time.time() * 1000)}"
        self.state_file = self.state_dir / f"{self.pipeline_id}.json"
        
        # Initialize state
        self.current_state = StateSnapshot(
            pipeline_id=self.pipeline_id,
            state=PipelineState.INITIALIZING,
            started_at=datetime.now(),
            updated_at=datetime.now(),
            environment=settings.environment
        )
        
        # Recovery mode
        self.recovery_mode = False
        self.recovered_state: Optional[StateSnapshot] = None
    
    def update_state(
        self, 
        state: PipelineState, 
        phase: Optional[str] = None,
        **kwargs
    ) -> None:
        """Update pipeline state.
        
        Args:
            state: New pipeline state
            phase: Current processing phase
            **kwargs: Additional state updates
        """
        self.current_state.state = state
        self.current_state.updated_at = datetime.now()
        
        if phase:
            self.current_state.current_phase = phase
        
        # Update any additional fields
        for key, value in kwargs.items():
            if hasattr(self.current_state, key):
                setattr(self.current_state, key, value)
        
        # Persist state
        self._save_state()
        
        self.logger.debug(f"State updated: {state.value} - {phase or ''}")
    
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update pipeline metrics.
        
        Args:
            metrics: Metrics dictionary to merge
        """
        self.current_state.metrics.update(metrics)
        self.current_state.updated_at = datetime.now()
        self._save_state()
    
    def record_table(self, tier: str, table_name: str) -> None:
        """Record a created table for recovery.
        
        Args:
            tier: Data tier (bronze, silver, gold, enriched)
            table_name: Name of the created table
        """
        if tier == "bronze":
            self.current_state.bronze_table = table_name
        elif tier == "silver":
            self.current_state.silver_table = table_name
        elif tier == "gold":
            self.current_state.gold_table = table_name
        elif tier == "enriched":
            self.current_state.enriched_table = table_name
        
        self._save_state()
        self.logger.debug(f"Recorded {tier} table: {table_name}")
    
    def mark_completed(self) -> None:
        """Mark pipeline as completed."""
        self.update_state(PipelineState.COMPLETED)
        self.logger.info(f"Pipeline {self.pipeline_id} completed successfully")
    
    def mark_failed(self, error_message: str, error_phase: str) -> None:
        """Mark pipeline as failed.
        
        Args:
            error_message: Error message
            error_phase: Phase where error occurred
        """
        self.current_state.state = PipelineState.FAILED
        self.current_state.error_message = error_message
        self.current_state.error_phase = error_phase
        self.current_state.updated_at = datetime.now()
        
        self._save_state()
        self.logger.error(f"Pipeline {self.pipeline_id} failed: {error_message}")
    
    def _save_state(self) -> None:
        """Persist state to disk."""
        if self.settings.dry_run:
            return
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(
                    self.current_state.model_dump(mode='json'),
                    f,
                    indent=2,
                    default=str
                )
        except Exception as e:
            self.logger.warning(f"Failed to save state: {e}")
    
    def load_state(self, state_file: Path) -> Optional[StateSnapshot]:
        """Load state from file for recovery.
        
        Args:
            state_file: Path to state file
            
        Returns:
            Loaded state snapshot or None if failed
        """
        try:
            with open(state_file, 'r') as f:
                data = json.load(f)
            
            state = StateSnapshot(**data)
            self.logger.info(f"Loaded state from {state_file}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to load state from {state_file}: {e}")
            return None
    
    def find_recoverable_pipelines(self) -> list[Path]:
        """Find pipelines that can be recovered.
        
        Returns:
            List of state file paths for recoverable pipelines
        """
        recoverable = []
        
        if not self.state_dir.exists():
            return recoverable
        
        for state_file in self.state_dir.glob("pipeline_*.json"):
            state = self.load_state(state_file)
            if state and state.state not in [PipelineState.COMPLETED, PipelineState.CANCELLED]:
                recoverable.append(state_file)
        
        return recoverable
    
    def recover_from(self, state_file: Path) -> bool:
        """Attempt to recover from a previous state.
        
        Args:
            state_file: Path to state file
            
        Returns:
            True if recovery successful, False otherwise
        """
        state = self.load_state(state_file)
        if not state:
            return False
        
        # Check if state is recoverable
        if state.state in [PipelineState.COMPLETED, PipelineState.CANCELLED]:
            self.logger.warning(f"Pipeline {state.pipeline_id} is already {state.state.value}")
            return False
        
        # Set recovery mode
        self.recovery_mode = True
        self.recovered_state = state
        self.current_state = state
        
        self.logger.info(f"Recovering pipeline {state.pipeline_id} from {state.state.value}")
        return True
    
    def get_recovery_point(self) -> Optional[Dict[str, Any]]:
        """Get recovery point information.
        
        Returns:
            Recovery information including tables and state
        """
        if not self.recovery_mode or not self.recovered_state:
            return None
        
        return {
            "pipeline_id": self.recovered_state.pipeline_id,
            "last_state": self.recovered_state.state.value,
            "last_phase": self.recovered_state.current_phase,
            "bronze_table": self.recovered_state.bronze_table,
            "silver_table": self.recovered_state.silver_table,
            "gold_table": self.recovered_state.gold_table,
            "enriched_table": self.recovered_state.enriched_table,
            "records_processed": self.recovered_state.records_processed
        }
    
    def cleanup_old_states(self, days: int = 7) -> int:
        """Clean up old state files.
        
        Args:
            days: Keep state files newer than this many days
            
        Returns:
            Number of files cleaned up
        """
        if not self.state_dir.exists():
            return 0
        
        cutoff_time = time.time() - (days * 86400)
        cleaned = 0
        
        for state_file in self.state_dir.glob("pipeline_*.json"):
            if state_file.stat().st_mtime < cutoff_time:
                state = self.load_state(state_file)
                # Only clean up completed or cancelled pipelines
                if state and state.state in [PipelineState.COMPLETED, PipelineState.CANCELLED]:
                    state_file.unlink()
                    cleaned += 1
                    self.logger.debug(f"Cleaned up old state file: {state_file.name}")
        
        if cleaned > 0:
            self.logger.info(f"Cleaned up {cleaned} old state files")
        
        return cleaned
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get summary of current pipeline state.
        
        Returns:
            Dictionary with state summary
        """
        duration = (datetime.now() - self.current_state.started_at).total_seconds()
        
        return {
            "pipeline_id": self.current_state.pipeline_id,
            "state": self.current_state.state.value,
            "phase": self.current_state.current_phase,
            "started_at": self.current_state.started_at.isoformat(),
            "duration_seconds": duration,
            "records_processed": self.current_state.records_processed,
            "environment": self.current_state.environment,
            "recovery_mode": self.recovery_mode
        }