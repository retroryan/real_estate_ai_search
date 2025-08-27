#!/usr/bin/env python3
"""
Update Elasticsearch templates to enable failure stores.
"""

from elasticsearch import Elasticsearch
from indexer.index_manager import ElasticsearchIndexManager
import logging

logging.basicConfig(level=logging.INFO)

# Connect to Elasticsearch
client = Elasticsearch(
    ["http://localhost:9200"],
    basic_auth=("elastic", "2GJXncaV")
)

# Create index manager
manager = ElasticsearchIndexManager(client)

# Update all templates with failure store enabled
print("Updating templates with failure store enabled...")
results = {
    "property_template": manager.create_property_template(),
    "neighborhood_template": manager.create_neighborhood_template(),
    "wikipedia_template": manager.create_wikipedia_template()
}

for template_name, success in results.items():
    status = "✅ Success" if success else "❌ Failed"
    print(f"{template_name}: {status}")

print("\nTemplates have been updated with failure store support.")
print("Note: This will only affect new data streams created after this update.")
print("Existing indices will not have failure stores unless recreated.")