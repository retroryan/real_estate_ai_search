"""
Progress indicator utilities for long-running operations.
"""

import sys
import time
from typing import Optional, Any
from dataclasses import dataclass

from .logging import get_logger


logger = get_logger(__name__)


@dataclass
class ProgressStats:
    """Statistics for progress tracking."""
    total: int
    current: int
    start_time: float
    last_update: float
    
    @property
    def percentage(self) -> float:
        """Calculate completion percentage."""
        return (self.current / self.total * 100) if self.total > 0 else 0
    
    @property
    def elapsed_time(self) -> float:
        """Calculate elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def rate(self) -> float:
        """Calculate processing rate (items/second)."""
        return self.current / self.elapsed_time if self.elapsed_time > 0 else 0
    
    @property
    def eta_seconds(self) -> float:
        """Estimate time to completion in seconds."""
        if self.rate > 0 and self.current < self.total:
            remaining = self.total - self.current
            return remaining / self.rate
        return 0


class ProgressIndicator:
    """
    Progress indicator with logging and optional console output.
    """
    
    def __init__(
        self, 
        total: int, 
        operation: str,
        update_interval: float = 1.0,
        log_interval: int = 10,
        show_console: bool = False
    ):
        """
        Initialize progress indicator.
        
        Args:
            total: Total number of items to process
            operation: Description of operation
            update_interval: Minimum seconds between updates
            log_interval: Log progress every N items
            show_console: Whether to show console progress bar
        """
        self.stats = ProgressStats(
            total=total,
            current=0,
            start_time=time.time(),
            last_update=time.time()
        )
        self.operation = operation
        self.update_interval = update_interval
        self.log_interval = log_interval
        self.show_console = show_console
        
        logger.info(f"Starting {operation}: 0/{total} items")
        if self.show_console:
            self._print_progress()
    
    def update(self, current: Optional[int] = None, increment: int = 1) -> None:
        """
        Update progress.
        
        Args:
            current: Set current position (if None, increment by increment)
            increment: Amount to increment if current is None
        """
        if current is not None:
            self.stats.current = current
        else:
            self.stats.current += increment
        
        current_time = time.time()
        
        # Check if we should update
        should_log = (
            self.stats.current % self.log_interval == 0 or
            self.stats.current == self.stats.total or
            current_time - self.stats.last_update >= self.update_interval
        )
        
        if should_log:
            self._log_progress()
            if self.show_console:
                self._print_progress()
            self.stats.last_update = current_time
    
    def complete(self) -> None:
        """Mark operation as complete."""
        self.stats.current = self.stats.total
        elapsed = self.stats.elapsed_time
        rate = self.stats.rate
        
        logger.info(
            f"Completed {self.operation}: {self.stats.total} items in {elapsed:.1f}s "
            f"({rate:.1f} items/sec)"
        )
        
        if self.show_console:
            self._print_progress()
            print()  # New line after progress bar
    
    def _log_progress(self) -> None:
        """Log current progress."""
        percentage = self.stats.percentage
        rate = self.stats.rate
        eta = self.stats.eta_seconds
        
        message = f"{self.operation}: {self.stats.current}/{self.stats.total} ({percentage:.1f}%)"
        if rate > 0:
            message += f" - {rate:.1f} items/sec"
        if eta > 0:
            message += f" - ETA: {eta:.0f}s"
            
        logger.info(message)
    
    def _print_progress(self) -> None:
        """Print console progress bar."""
        if not self.show_console:
            return
            
        percentage = self.stats.percentage
        bar_width = 30
        filled_width = int(bar_width * percentage / 100)
        bar = '█' * filled_width + '░' * (bar_width - filled_width)
        
        rate = self.stats.rate
        rate_str = f"{rate:.1f} items/sec" if rate > 0 else "calculating..."
        
        progress_str = f"\\r{self.operation}: [{bar}] {percentage:.1f}% ({self.stats.current}/{self.stats.total}) - {rate_str}"
        
        sys.stdout.write(progress_str)
        sys.stdout.flush()


def create_progress_indicator(
    total: int,
    operation: str,
    show_console: bool = False,
    **kwargs
) -> ProgressIndicator:
    """
    Factory function to create progress indicator.
    
    Args:
        total: Total items to process
        operation: Operation description
        show_console: Show console progress bar
        **kwargs: Additional arguments for ProgressIndicator
        
    Returns:
        ProgressIndicator instance
    """
    return ProgressIndicator(
        total=total,
        operation=operation,
        show_console=show_console,
        **kwargs
    )