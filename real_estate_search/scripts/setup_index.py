#!/usr/bin/env python3
"""
Setup script - DEPRECATED
Data ingestion has been moved to data_pipeline.
Use 'python -m data_pipeline' to index data.
"""

import sys


def main():
    """Inform user about data_pipeline."""
    print("=" * 60)
    print("DEPRECATED: Ingestion has been moved to data_pipeline")
    print("=" * 60)
    print()
    print("To index data, please run:")
    print("  cd ../")
    print("  python -m data_pipeline")
    print()
    print("The real_estate_search application now works with")
    print("pre-indexed data from the data_pipeline.")
    print()
    sys.exit(1)


if __name__ == "__main__":
    main()