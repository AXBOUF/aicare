"""
STEP 2 — Search Index Setup
Creates the Azure AI Search index for patient intake records.

Prerequisites:
    - .env file filled in with your Azure AI Search endpoint and key
    - Step 1 (database) already completed

Usage:
    python scripts/student/2_create_search_index.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.search_service import SearchService


def main():
    print("=" * 50)
    print("Zenith Healthcare - Search Index Setup")
    print("=" * 50)

    search = SearchService()

    print("\nCreating search index: patient-intake-index ...")
    search.create_index()
    print("Search index created successfully!")
    print("\nDone!")


if __name__ == "__main__":
    main()
