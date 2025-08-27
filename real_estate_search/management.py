"""
Elasticsearch index management CLI for real estate search system.
Entry point that delegates to the modular management package.
"""

from .management.cli import main

if __name__ == '__main__':
    main()