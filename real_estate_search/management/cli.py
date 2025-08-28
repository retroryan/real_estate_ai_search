"""
Main CLI entry point for management commands.
"""

import sys
import logging
from pathlib import Path
from typing import Type

from ..config import AppConfig
from .models import CommandType
from .cli_parser import CLIParser
from .commands import (
    BaseCommand,
    SetupIndicesCommand,
    ValidateIndicesCommand,
    ValidateEmbeddingsCommand,
    ListIndicesCommand,
    DeleteTestIndicesCommand,
    DemoCommand,
    EnrichWikipediaCommand
)


def setup_logging(log_level: str = "INFO"):
    """
    Configure logging for the management operations.
    
    Args:
        log_level: Logging level string
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def get_command_class(command_type: CommandType) -> Type[BaseCommand]:
    """
    Get the appropriate command class for the given command type.
    
    Args:
        command_type: Type of command to execute
        
    Returns:
        Command class
    """
    command_map = {
        CommandType.SETUP_INDICES: SetupIndicesCommand,
        CommandType.VALIDATE_INDICES: ValidateIndicesCommand,
        CommandType.VALIDATE_EMBEDDINGS: ValidateEmbeddingsCommand,
        CommandType.LIST_INDICES: ListIndicesCommand,
        CommandType.DELETE_TEST_INDICES: DeleteTestIndicesCommand,
        CommandType.DEMO: DemoCommand,
        CommandType.ENRICH_WIKIPEDIA: EnrichWikipediaCommand
    }
    
    return command_map[command_type]


def main():
    """Main entry point for index management CLI."""
    try:
        # Parse arguments
        cli_args = CLIParser.parse_args()
        
        # Validate arguments
        validation_error = CLIParser.validate_args(cli_args)
        if validation_error:
            print(f"✗ {validation_error}")
            sys.exit(1)
        
        # Setup logging
        setup_logging(cli_args.log_level.value)
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config_path = Path(cli_args.config_path)
        if not config_path.exists():
            print(f"✗ Configuration file not found: {config_path}")
            sys.exit(1)
        
        config = AppConfig.from_yaml(config_path)
        
        # Override log level if specified
        config.logging.level = cli_args.log_level.value
        
        # Get and execute the appropriate command
        command_class = get_command_class(cli_args.command)
        command = command_class(config, cli_args)
        
        # Execute the command
        result = command.execute()
        
        # Log the result
        if result.success:
            logger.info(f"Command '{cli_args.command.value}' completed successfully: {result.message}")
        else:
            logger.error(f"Command '{cli_args.command.value}' failed: {result.message}")
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Unexpected error: {str(e)}")
        print(f"✗ Unexpected error: {str(e)}")
        sys.exit(1)