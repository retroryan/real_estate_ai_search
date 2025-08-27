# HTML Results Module

Clean, well-structured module for generating HTML output from search results using Pydantic models and Jinja2 templates.

## Features

- **Pydantic Models**: Type-safe data models for all result components
- **Modern HTML/CSS**: Responsive, gradient-styled output with embedded CSS
- **Automatic Generation**: Creates timestamped HTML files in `out_html/` directory
- **Git-Ignored Output**: HTML output directory is excluded from version control

## Usage

The module is automatically integrated with Demo 10 (Wikipedia Full-Text Search). When you run the demo, it will:

1. Execute all search queries
2. Display results in the console (unchanged)
3. Generate an HTML file with results
4. Display the file path at the end

```bash
# Run demo 10
python -m real_estate_search.management demo 10

# Output includes:
# 📄 HTML results saved to: /path/to/out_html/wikipedia_search_results_TIMESTAMP.html
#    Open in browser: file:///path/to/out_html/wikipedia_search_results_TIMESTAMP.html
```

## Module Structure

```
html_results/
├── __init__.py          # Module exports
├── models.py            # Pydantic models for HTML data
├── template.py          # HTML/CSS template
├── generator.py         # HTML generation logic
└── README.md           # This file
```

## Models

- `HTMLHighlight`: Text fragments with search term emphasis
- `HTMLDocument`: Individual search result document
- `HTMLQueryResult`: Results from a single query
- `HTMLSearchResult`: Complete search session results

## Output Location

HTML files are saved to: `real_estate_search/out_html/`

This directory is:
- Created automatically if it doesn't exist
- Excluded from git (added to .gitignore)
- Contains timestamped HTML files

## HTML Features

The generated HTML includes:

- **Header**: Title and description with gradient background
- **Statistics**: Query counts, document totals, success metrics
- **Query Sections**: Each query with its results
- **Document Cards**: Hoverable cards with scores and highlights
- **Highlighted Text**: Search terms emphasized in results
- **Top Documents**: Summary of highest-scoring results
- **Responsive Design**: Works on mobile and desktop

## Styling

- Modern gradient backgrounds
- Card-based layout with hover effects
- Emphasized search terms with yellow background
- Clean typography with system fonts
- Responsive grid layouts

## Integration

To use in other demos:

```python
from html_results import HTMLResultsGenerator

# Create generator
generator = HTMLResultsGenerator()

# Generate HTML from results
html_path = generator.generate_from_demo_results(
    title="Your Demo Title",
    description="Demo description",
    query_results=your_results_list
)

print(f"HTML saved to: {html_path}")
```