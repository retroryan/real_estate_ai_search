"""
HTML parsing utilities for Wikipedia content.
Adapted from wiki_crawl implementation using BeautifulSoup.
"""

from bs4 import BeautifulSoup
import re
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import json
from wiki_embed.models import WikiArticle, WikiLocation


def clean_wikipedia_text(html_content: str, max_length: int = 10000) -> str:
    """
    Basic HTML cleanup - remove scripts/styles and extract plain text.
    Simple, fast approach for embeddings.
    
    Args:
        html_content: Raw HTML content
        max_length: Maximum text length to return
        
    Returns:
        Clean text suitable for embedding
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Basic cleanup - remove scripts, styles, and other non-content elements
    for tag in ['script', 'style', 'meta', 'link', 'noscript']:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Get plain text
    text = soup.get_text()
    
    # Basic text cleanup
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = ' '.join(chunk for chunk in chunks if chunk)
    
    # Remove common Wikipedia artifacts
    text = re.sub(r'\[edit\]', '', text)
    text = re.sub(r'\[\d+\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text.strip()


def extract_article_metadata(html_content: str, page_id: str) -> Dict[str, any]:
    """
    Extract metadata from Wikipedia article HTML.
    
    Args:
        html_content: Raw HTML content
        page_id: Page ID from filename
        
    Returns:
        Dictionary with article metadata
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    metadata = {
        'page_id': page_id,
        'title': None,
        'categories': [],
        'location_hints': {},
        'coordinates': None
    }
    
    # Extract title
    h1 = soup.find('h1')
    if h1:
        metadata['title'] = h1.get_text().strip()
    else:
        infobox_title = soup.find('div', class_='fn org')
        if infobox_title:
            metadata['title'] = infobox_title.get_text().strip()
    
    # Extract categories
    categories = soup.find_all('link', {'rel': 'mw:PageProp/Category'})
    for cat in categories:
        href = cat.get('href', '')
        if href:
            cat_text = href.replace('./Category:', '').replace('_', ' ')
            metadata['categories'].append(cat_text)
    
    # Extract location hints
    location_hints = extract_location_hints(soup)
    metadata['location_hints'] = location_hints
    
    # Extract coordinates
    geo_span = soup.find('span', class_='geo')
    if geo_span:
        metadata['coordinates'] = geo_span.get_text().strip()
    
    return metadata


def extract_location_hints(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    """
    Extract location information from parsed HTML.
    
    Args:
        soup: BeautifulSoup parsed HTML
        
    Returns:
        Dictionary with city, county, state information
    """
    hints = {
        'city': None,
        'county': None, 
        'state': None
    }
    
    # Check categories for location info
    categories = soup.find_all('link', {'rel': 'mw:PageProp/Category'})
    for cat in categories:
        href = cat.get('href', '')
        if href:
            cat_text = href.replace('./Category:', '').replace('_', ' ')
            
            # State extraction
            state_match = re.search(
                r'\b(California|Utah|Nevada|Arizona|Oregon|Washington|Colorado|Wyoming|Idaho|Montana)\b',
                cat_text, re.IGNORECASE
            )
            if state_match and not hints['state']:
                hints['state'] = state_match.group(1)
            
            # County extraction
            county_match = re.search(r'([\w\s]+) County', cat_text)
            if county_match and not hints['county']:
                county = county_match.group(1).strip()
                if county and len(county) > 2:
                    hints['county'] = county
            
            # City extraction from categories
            if 'Cities in' in cat_text or 'Neighborhoods in' in cat_text:
                city_match = re.search(r'(?:Cities|Neighborhoods) in ([\w\s]+?)(?:,|\s*$)', cat_text)
                if city_match and not hints['city']:
                    city = city_match.group(1).strip()
                    if city and 'County' not in city:
                        hints['city'] = city
    
    # Check infobox for location info
    infobox = soup.find('table', class_='infobox')
    if infobox:
        rows = infobox.find_all('tr')
        for row in rows:
            label = row.find('th', class_='infobox-label')
            data = row.find('td', class_='infobox-data')
            
            if label and data:
                label_text = label.get_text().strip().lower()
                data_text = data.get_text().strip()
                
                # State extraction
                if 'state' in label_text and not hints['state']:
                    state = re.sub(r'\[.*?\]', '', data_text).strip()
                    if state:
                        hints['state'] = state
                
                # County extraction
                elif 'county' in label_text and not hints['county']:
                    county = re.sub(r'\s*County.*$', '', data_text)
                    county = re.sub(r'\[.*?\]', '', county).strip()
                    if county:
                        hints['county'] = county
    
    return hints


def load_wikipedia_articles(source_dir: str, registry_path: str, max_articles: Optional[int] = None) -> List[WikiArticle]:
    """
    Load Wikipedia articles from HTML files with location metadata.
    
    Args:
        source_dir: Directory containing HTML files
        registry_path: Path to REGISTRY.json
        max_articles: Maximum number of articles to load (for testing)
        
    Returns:
        List of WikiArticle objects
    """
    articles = []
    source_path = Path(source_dir)
    
    # Load registry for location mapping
    location_map = {}
    if Path(registry_path).exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
            for location in registry.get('locations', []):
                location_map[location['path']] = WikiLocation(**location)
    
    # Process each HTML file
    html_files = list(source_path.glob('*.html'))
    print(f"Found {len(html_files)} Wikipedia HTML files", flush=True)
    if max_articles:
        print(f"Loading only first {max_articles} articles (test mode)", flush=True)
    
    for i, html_file in enumerate(html_files):
        # Check max_articles limit
        if max_articles and i >= max_articles:
            break
            
        # Extract page_id from filename (e.g., "107778_a18e0a44.html" -> "107778")
        page_id = html_file.stem.split('_')[0]
        
        try:
            # Read HTML content
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # Extract clean text
            content = clean_wikipedia_text(html_content)
            
            # Extract metadata
            metadata = extract_article_metadata(html_content, page_id)
            
            # Determine location from metadata hints
            location_hints = metadata['location_hints']
            location_str = None
            state = location_hints.get('state')
            city = location_hints.get('city')
            
            if city and state:
                location_str = f"{city}, {state}"
            elif state:
                location_str = state
            
            # Create WikiArticle
            article = WikiArticle(
                page_id=page_id,
                title=metadata['title'] or f"Article {page_id}",
                content=content,
                url=f"https://en.wikipedia.org/?curid={page_id}",
                location=location_str,
                state=state,
                country="USA",
                categories=metadata['categories'][:10]  # Limit categories
            )
            
            articles.append(article)
            
        except Exception as e:
            print(f"Error processing {html_file.name}: {e}", flush=True)
            continue
    
    actual_count = len(articles)
    if max_articles and actual_count < max_articles:
        print(f"Successfully loaded {actual_count} Wikipedia articles (less than max {max_articles})", flush=True)
    else:
        print(f"Successfully loaded {actual_count} Wikipedia articles", flush=True)
    return articles


def create_location_context(article: WikiArticle) -> str:
    """
    Create location context string for embedding metadata.
    
    Args:
        article: WikiArticle object
        
    Returns:
        Location context string
    """
    parts = []
    
    if article.location:
        parts.append(f"Location: {article.location}")
    
    if article.state:
        parts.append(f"State: {article.state}")
    
    if article.country:
        parts.append(f"Country: {article.country}")
    
    # Add relevant categories
    location_categories = [
        cat for cat in article.categories 
        if any(term in cat.lower() for term in ['county', 'city', 'state', 'geography'])
    ]
    
    if location_categories:
        parts.append(f"Categories: {', '.join(location_categories[:3])}")
    
    return " | ".join(parts) if parts else "Unknown Location"