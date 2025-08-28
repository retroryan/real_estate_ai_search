# Wikipedia Attribution and Usage Guidelines

## License Compliance

This project retrieves and processes content from Wikipedia, which is licensed under the [Creative Commons Attribution-ShareAlike 3.0 License (CC BY-SA 3.0)](https://creativecommons.org/licenses/by-sa/3.0/) and the [GNU Free Documentation License (GFDL)](https://www.gnu.org/licenses/fdl-1.3.html).

## Attribution Requirements

When using this system with Wikipedia data, you must:

### 1. Provide Attribution
- Credit Wikipedia as the source of the content
- Include a link back to the original Wikipedia article
- Mention that the content is available under CC BY-SA 3.0

### 2. Share-Alike Requirement
- Any modifications or derived works based on Wikipedia content must be licensed under the same CC BY-SA 3.0 license
- This includes enriched documents that incorporate Wikipedia text

### 3. Implementation in This Project

This codebase implements proper attribution by:

- **Storing Original URLs**: Each Wikipedia document in Elasticsearch includes the `url` field linking back to the source article
- **Preserving Page IDs**: The `page_id` field maintains the unique Wikipedia identifier
- **Title Preservation**: Original article titles are stored in the `title` field
- **Source Tracking**: The system tracks which Wikipedia articles are associated with each property/neighborhood

## Example Attribution Format

When displaying Wikipedia-derived content in your application, include attribution like:

```
This description includes content from the Wikipedia article 
"[Article Title]" (https://en.wikipedia.org/wiki/Article_Title), 
which is licensed under CC BY-SA 3.0.
```

## Data Usage Guidelines

### What This Project Does
- **Crawls** Wikipedia articles related to geographic locations
- **Processes** HTML content into searchable text
- **Enriches** property listings with contextual information
- **Links** to original Wikipedia sources

### What This Project Does NOT Do
- Does not redistribute Wikipedia content as a dataset
- Does not claim ownership of Wikipedia content
- Does not remove attribution from Wikipedia sources
- Does not violate Wikipedia's robots.txt or rate limits

## Technical Implementation

The Wikipedia integration in this project:

1. **Respects Rate Limits**: The crawler implements appropriate delays between requests
2. **Follows robots.txt**: Adheres to Wikipedia's crawling guidelines
3. **Caches Locally**: Reduces repeated requests to Wikipedia servers
4. **Maintains Attribution**: Preserves all source information in indexed documents

## Search Result Attribution

When implementing search results that include Wikipedia content, ensure your application:

```python
# Example: Displaying Wikipedia-enriched property data
if property.location_context and property.location_context.wikipedia_page_id:
    attribution = f"""
    Location information from Wikipedia article 
    "{property.location_context.wikipedia_title}"
    (https://en.wikipedia.org/wiki/{property.location_context.wikipedia_page_id})
    Licensed under CC BY-SA 3.0
    """
    display(attribution)
```

## API Usage

If exposing Wikipedia-enriched data through an API:

1. Include attribution in API responses:
```json
{
  "property": { ... },
  "wikipedia_attribution": {
    "source": "Wikipedia",
    "article": "San Francisco",
    "url": "https://en.wikipedia.org/wiki/San_Francisco",
    "license": "CC BY-SA 3.0"
  }
}
```

2. Document attribution requirements in your API documentation
3. Require API users to maintain attribution in their applications

## Compliance Checklist

- [ ] Wikipedia URLs are preserved in all indexed documents
- [ ] Original article titles are maintained
- [ ] Page IDs are stored for reference
- [ ] Attribution is displayed when showing Wikipedia content
- [ ] API responses include attribution information
- [ ] Documentation mentions Wikipedia licensing requirements
- [ ] Derived works maintain CC BY-SA 3.0 compatibility

## Additional Resources

- [Wikipedia:Reusing Wikipedia content](https://en.wikipedia.org/wiki/Wikipedia:Reusing_Wikipedia_content)
- [Creative Commons CC BY-SA 3.0 License](https://creativecommons.org/licenses/by-sa/3.0/)
- [Wikimedia Foundation Terms of Use](https://foundation.wikimedia.org/wiki/Terms_of_Use)
- [Wikipedia:Copyrights](https://en.wikipedia.org/wiki/Wikipedia:Copyrights)

## Legal Disclaimer

This attribution guide is provided for informational purposes. Users of this codebase are responsible for ensuring their specific use case complies with Wikipedia's licensing terms and applicable laws. When in doubt, consult with legal counsel.

## Contact

If you have questions about Wikipedia attribution in this project, please refer to the official Wikipedia licensing documentation or consult the Wikimedia Foundation's resources.