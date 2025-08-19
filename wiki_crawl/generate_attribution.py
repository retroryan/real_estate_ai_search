"""
Generate Wikipedia attribution from the database.
Ensures CC BY-SA 3.0 compliance for all Wikipedia content.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any


def generate_attribution_from_database(data_dir: Path = Path("../data")) -> Dict[str, Any]:
    """
    Generate attribution files from Wikipedia database.
    
    Args:
        data_dir: Directory containing the database
        
    Returns:
        Dictionary with attribution data
    """
    db_path = data_dir / "wikipedia" / "wikipedia.db"
    
    if not db_path.exists():
        print(f"Database not found: {db_path}")
        return {}
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Get all articles with their location info
    cursor.execute("""
        SELECT 
            a.pageid,
            a.title,
            a.url,
            a.crawled_at,
            a.html_file,
            l.city,
            l.state,
            l.county
        FROM articles a
        JOIN locations l ON a.location_id = l.location_id
        ORDER BY l.state, l.city, a.title
    """)
    
    articles = cursor.fetchall()
    
    attribution_data = []
    for article in articles:
        pageid, title, url, crawled_at, html_file, city, state, county = article
        
        # Format location name
        if city:
            location = f"{city}, {state}"
        else:
            location = f"{county} County, {state}"
        
        attribution_data.append({
            "location": location,
            "title": title,
            "url": url or f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            "page_id": pageid,
            "crawl_date": crawled_at,
            "local_file": html_file,
            "license": "CC BY-SA 3.0",
            "license_url": "https://creativecommons.org/licenses/by-sa/3.0/"
        })
    
    conn.close()
    
    # Generate attribution JSON
    attribution_json = {
        "generated": datetime.now().isoformat(),
        "total_articles": len(attribution_data),
        "license": "Creative Commons Attribution-ShareAlike 3.0 Unported (CC BY-SA 3.0)",
        "license_url": "https://creativecommons.org/licenses/by-sa/3.0/",
        "source": "Wikipedia (https://www.wikipedia.org/)",
        "notice": "This content is derived from Wikipedia and must be attributed appropriately.",
        "articles": attribution_data
    }
    
    # Ensure attribution directory exists
    attribution_dir = data_dir / "wikipedia" / "attribution"
    attribution_dir.mkdir(parents=True, exist_ok=True)
    
    # Save JSON attribution
    output_json = attribution_dir / "WIKIPEDIA_ATTRIBUTION.json"
    with open(output_json, 'w') as f:
        json.dump(attribution_json, f, indent=2)
    
    print(f"Generated {output_json}")
    print(f"Total articles: {len(attribution_data)}")
    
    # Generate markdown attribution
    generate_markdown_attribution(attribution_data, attribution_dir)
    
    # Generate HTML attribution
    generate_html_attribution(attribution_data, attribution_dir)
    
    return attribution_json


def generate_markdown_attribution(attribution_data: List[Dict[str, Any]], output_dir: Path):
    """Generate human-readable attribution markdown."""
    
    markdown = """# Wikipedia Content Attribution

This directory contains Wikipedia articles used for the property finder demonstration.

## License
All Wikipedia content is licensed under the **Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)**.
- License text: https://creativecommons.org/licenses/by-sa/3.0/
- Wikipedia copyright policy: https://en.wikipedia.org/wiki/Wikipedia:Copyrights

## Usage Requirements
When using this content, you must:
1. Give appropriate credit to Wikipedia
2. Provide a link to the license
3. Indicate if changes were made
4. Distribute any derivative works under the same license

## Attribution by Location

"""
    
    # Group by location
    by_location = {}
    for article in attribution_data:
        location = article["location"]
        if location not in by_location:
            by_location[location] = []
        by_location[location].append(article)
    
    # Generate tables for each location
    for location in sorted(by_location.keys()):
        articles = by_location[location]
        markdown += f"\n### {location}\n\n"
        markdown += f"**{len(articles)} articles** crawled from Wikipedia\n\n"
        markdown += "| Article Title | Wikipedia URL | Crawl Date |\n"
        markdown += "|--------------|---------------|------------|\n"
        
        for article in sorted(articles, key=lambda x: x["title"]):
            title = article["title"]
            url = article["url"]
            crawl_date = article["crawl_date"][:10] if article["crawl_date"] else "Unknown"
            markdown += f"| {title} | [Link]({url}) | {crawl_date} |\n"
    
    markdown += """

## How to Attribute

When using this content in your project, include the following attribution:

> This project uses content from Wikipedia, licensed under CC BY-SA 3.0.
> Original articles can be found at https://www.wikipedia.org/

For specific articles, use:

> "[Article Title]" from Wikipedia, CC BY-SA 3.0
> Original: [URL]

## Legal Notice

Wikipedia® is a registered trademark of the Wikimedia Foundation, Inc., a non-profit organization.

This project is not affiliated with or endorsed by the Wikimedia Foundation.
"""
    
    # Save markdown
    output_file = output_dir / "WIKIPEDIA_ATTRIBUTION.md"
    with open(output_file, 'w') as f:
        f.write(markdown)
    
    print(f"Generated {output_file}")


def generate_html_attribution(attribution_data: List[Dict[str, Any]], output_dir: Path):
    """Generate HTML attribution page."""
    
    html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wikipedia Content Attribution</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #333; }
        h2 { color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }
        h3 { color: #888; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 10px; text-align: left; border: 1px solid #ddd; }
        th { background: #f5f5f5; }
        tr:nth-child(even) { background: #fafafa; }
        .license-box { background: #e8f4f8; padding: 15px; border-left: 4px solid #0073aa; margin: 20px 0; }
        .notice { background: #fff9e6; padding: 10px; border: 1px solid #ffcc00; }
        a { color: #0073aa; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Wikipedia Content Attribution</h1>
    
    <div class="license-box">
        <h2>License Information</h2>
        <p>All Wikipedia content in this project is licensed under the <strong>Creative Commons Attribution-ShareAlike 3.0 Unported License (CC BY-SA 3.0)</strong>.</p>
        <ul>
            <li><a href="https://creativecommons.org/licenses/by-sa/3.0/">View License</a></li>
            <li><a href="https://en.wikipedia.org/wiki/Wikipedia:Copyrights">Wikipedia Copyright Policy</a></li>
        </ul>
    </div>
    
    <div class="notice">
        <strong>Usage Requirements:</strong> You must give appropriate credit, provide a link to the license, and indicate if changes were made.
    </div>
    
    <h2>Articles by Location</h2>
"""
    
    # Group by location
    by_location = {}
    for article in attribution_data:
        location = article["location"]
        if location not in by_location:
            by_location[location] = []
        by_location[location].append(article)
    
    # Generate tables for each location
    for location in sorted(by_location.keys()):
        articles = by_location[location]
        html += f"""
    <h3>{location} ({len(articles)} articles)</h3>
    <table>
        <thead>
            <tr>
                <th>Article Title</th>
                <th>Page ID</th>
                <th>Crawl Date</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
"""
        
        for article in sorted(articles, key=lambda x: x["title"]):
            title = article["title"]
            url = article["url"]
            page_id = article["page_id"]
            crawl_date = article["crawl_date"][:10] if article["crawl_date"] else "Unknown"
            
            html += f"""
            <tr>
                <td>{title}</td>
                <td>{page_id}</td>
                <td>{crawl_date}</td>
                <td><a href="{url}" target="_blank">View on Wikipedia</a></td>
            </tr>
"""
        
        html += """
        </tbody>
    </table>
"""
    
    html += """
    <div class="license-box" style="margin-top: 40px;">
        <h2>How to Attribute</h2>
        <p>When using this content, include:</p>
        <blockquote>
            This project uses content from Wikipedia, licensed under CC BY-SA 3.0.<br>
            Original articles can be found at https://www.wikipedia.org/
        </blockquote>
    </div>
    
    <footer style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #ddd; color: #666;">
        <p>Generated: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
        <p>Wikipedia® is a registered trademark of the Wikimedia Foundation, Inc.</p>
    </footer>
</body>
</html>
"""
    
    # Save HTML
    output_file = output_dir / "WIKIPEDIA_ATTRIBUTION.html"
    with open(output_file, 'w') as f:
        f.write(html)
    
    print(f"Generated {output_file}")


if __name__ == "__main__":
    # Generate attribution files
    attribution = generate_attribution_from_database()
    
    if attribution:
        print("\n✅ Attribution files generated successfully!")
        print("Files created:")
        print("  - WIKIPEDIA_ATTRIBUTION.json (machine-readable)")
        print("  - WIKIPEDIA_ATTRIBUTION.md (markdown documentation)")
        print("  - WIKIPEDIA_ATTRIBUTION.html (web viewable)")
        print("\nThese files ensure CC BY-SA 3.0 compliance for Wikipedia content.")