"""
CLI argument parser for management commands.
"""

import argparse
from pathlib import Path
from typing import Optional

from .models import CLIArguments, CommandType, LogLevel


class CLIParser:
    """Handles CLI argument parsing."""
    
    @staticmethod
    def create_parser() -> argparse.ArgumentParser:
        """
        Create and configure the argument parser.
        
        Returns:
            Configured ArgumentParser
        """
        parser = argparse.ArgumentParser(
            description="Elasticsearch Index Management for Real Estate Search",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python -m real_estate_search.management setup-indices
  python -m real_estate_search.management setup-indices --clear    # Reset and recreate indices
  python -m real_estate_search.management setup-indices --clear --build-relationships  # Complete setup with relationships
  python -m real_estate_search.management setup-indices --build-relationships  # Just build relationships
  python -m real_estate_search.management validate-indices
  python -m real_estate_search.management validate-embeddings     # Check vector embedding coverage
  python -m real_estate_search.management list-indices
  python -m real_estate_search.management delete-test-indices
  python -m real_estate_search.management demo --list           # List all demo queries
  python -m real_estate_search.management demo 1                # Run demo query 1
  python -m real_estate_search.management demo 2 --verbose      # Run demo 2 with query DSL
  python -m real_estate_search.management enrich-wikipedia      # Enrich Wikipedia articles
  python -m real_estate_search.management enrich-wikipedia --dry-run  # Test without updating
  python -m real_estate_search.management enrich-wikipedia --max-documents 100  # Process 100 docs
  
Note: Uses real_estate_search/config.yaml by default. Override with --config flag.
            """
        )
        
        parser.add_argument(
            'command',
            choices=[cmd.value for cmd in CommandType],
            help='Management command to execute'
        )
        
        parser.add_argument(
            'demo_number',
            type=int,
            nargs='?',
            choices=range(1, 16),
            help='Demo query number to run (1-15)'
        )
        
        parser.add_argument(
            '--clear',
            action='store_true',
            help='For setup-indices: Delete existing indices first (complete reset for demo)'
        )
        
        parser.add_argument(
            '--build-relationships',
            action='store_true',
            help='For setup-indices: Build property_relationships index from existing data'
        )
        
        parser.add_argument(
            '--list',
            action='store_true',
            help='For demo: List all available demo queries'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='For demo: Show detailed query DSL'
        )
        
        parser.add_argument(
            '--config',
            type=Path,
            default=Path(__file__).parent.parent / "config.yaml",
            help='Configuration file path (default: real_estate_search/config.yaml)'
        )
        
        parser.add_argument(
            '--log-level',
            choices=[level.value for level in LogLevel],
            default=LogLevel.INFO.value,
            help='Logging level (default: INFO)'
        )
        
        # Wikipedia enrichment specific arguments
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='For enrich-wikipedia: Batch size for bulk updates (default: 50)'
        )
        
        parser.add_argument(
            '--max-documents',
            type=int,
            help='For enrich-wikipedia: Maximum documents to process'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='For enrich-wikipedia: Perform dry run without updating documents'
        )
        
        return parser
    
    @staticmethod
    def parse_args(args: Optional[list] = None) -> CLIArguments:
        """
        Parse command-line arguments.
        
        Args:
            args: Optional list of arguments (for testing)
            
        Returns:
            Parsed CLI arguments as Pydantic model
        """
        parser = CLIParser.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Resolve config path to absolute path
        config_path = parsed_args.config
        if not config_path.is_absolute():
            config_path = config_path.resolve()
        
        # Convert to Pydantic model
        cli_args = CLIArguments(
            command=CommandType(parsed_args.command),
            demo_number=parsed_args.demo_number,
            clear=parsed_args.clear,
            list=parsed_args.list,
            verbose=parsed_args.verbose,
            build_relationships=parsed_args.build_relationships,
            config_path=str(config_path),
            log_level=LogLevel(parsed_args.log_level),
            batch_size=getattr(parsed_args, 'batch_size', 50),
            max_documents=getattr(parsed_args, 'max_documents', None),
            dry_run=getattr(parsed_args, 'dry_run', False)
        )
        
        return cli_args
    
    @staticmethod
    def validate_args(args: CLIArguments) -> Optional[str]:
        """
        Validate parsed arguments for logical consistency.
        
        Args:
            args: Parsed CLI arguments
            
        Returns:
            Error message if validation fails, None otherwise
        """
        # Demo command specific validation
        if args.command == CommandType.DEMO:
            if not args.list and not args.demo_number:
                return "Please specify a demo number (1-15) or use --list to see available demos"
        
        # Clear flag only valid for setup-indices
        if args.clear and args.command != CommandType.SETUP_INDICES:
            return "--clear flag is only valid for setup-indices command"
        
        # Build relationships flag only valid for setup-indices
        if args.build_relationships and args.command != CommandType.SETUP_INDICES:
            return "--build-relationships flag is only valid for setup-indices command"
        
        # List flag only valid for demo command
        if args.list and args.command != CommandType.DEMO:
            return "--list flag is only valid for demo command"
        
        # Verbose flag valid for demo and enrich-wikipedia commands
        if args.verbose and args.command not in [CommandType.DEMO, CommandType.ENRICH_WIKIPEDIA]:
            return "--verbose flag is only valid for demo and enrich-wikipedia commands"
        
        # Demo number only valid for demo command
        if args.demo_number and args.command != CommandType.DEMO:
            return "Demo number is only valid for demo command"
        
        # Wikipedia enrichment specific validation
        if args.command == CommandType.ENRICH_WIKIPEDIA:
            if args.batch_size and (args.batch_size < 1 or args.batch_size > 500):
                return "Batch size must be between 1 and 500"
            if args.max_documents and args.max_documents < 1:
                return "Max documents must be greater than 0"
        else:
            # These flags only valid for enrich-wikipedia
            if args.dry_run:
                return "--dry-run flag is only valid for enrich-wikipedia command"
        
        return None