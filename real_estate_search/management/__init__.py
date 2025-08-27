"""
Management module for Elasticsearch index operations and CLI.
"""

from .models import (
    CommandType,
    LogLevel,
    CLIArguments,
    IndexOperationResult,
    ValidationStatus,
    EmbeddingValidationResult,
    ClusterHealthInfo,
    DemoQuery,
    DemoExecutionResult,
    OperationStatus
)

from .commands import (
    BaseCommand,
    SetupIndicesCommand,
    ValidateIndicesCommand,
    ValidateEmbeddingsCommand,
    ListIndicesCommand,
    DeleteTestIndicesCommand,
    DemoCommand
)

from .cli_parser import CLIParser
from .cli_output import CLIOutput
from .demo_runner import DemoRunner
from .index_operations import IndexOperations
from .validation import ValidationService

__all__ = [
    # Models
    'CommandType',
    'LogLevel',
    'CLIArguments',
    'IndexOperationResult',
    'ValidationStatus',
    'EmbeddingValidationResult',
    'ClusterHealthInfo',
    'DemoQuery',
    'DemoExecutionResult',
    'OperationStatus',
    # Commands
    'BaseCommand',
    'SetupIndicesCommand',
    'ValidateIndicesCommand',
    'ValidateEmbeddingsCommand',
    'ListIndicesCommand',
    'DeleteTestIndicesCommand',
    'DemoCommand',
    # Services
    'CLIParser',
    'CLIOutput',
    'DemoRunner',
    'IndexOperations',
    'ValidationService'
]