"""
HTML parser for Wikipedia pages.
Provides both structured data extraction and content cleaning for LLM.
"""

from bs4 import BeautifulSoup
import re
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


def clean_html_for_llm(html_content: str, max_length: int = 5000) -> str:
    """
    Clean and prepare HTML content for LLM processing.
    Removes unnecessary elements and extracts meaningful text.
    
    Args:
        html_content: Raw HTML content
        max_length: Maximum text length to return
        
    Returns:
        Clean text suitable for LLM processing
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 1. Remove completely unnecessary elements
    remove_tags = [
        'script', 'style', 'meta', 'link', 'noscript',
        'svg', 'path', 'symbol', 'use', 'img'
    ]
    for tag in remove_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    # 2. Remove Wikipedia-specific navigation and UI elements
    remove_by_class = [
        'navbox', 'navbox-styles', 'navbar', 'navigation-not-searchable',
        'mw-jump-link', 'mw-editsection', 'noprint', 'nomobile', 'noexcerpt',
        'mw-empty-elt', 'mw-editsection-bracket', 'reflist', 'reference-text',
        'citation', 'hatnote', 'shortdescription', 'magnify', 'internal',
        'infobox-image', 'thumbinner', 'thumbcaption', 'mw-collapsible-content'
    ]
    
    for class_name in remove_by_class:
        for element in soup.find_all(class_=class_name):
            element.decompose()
    
    # Remove by ID
    remove_by_id = ['coordinates', 'References', 'External_links', 
                    'See_also', 'Notes', 'Further_reading']
    for id_name in remove_by_id:
        elem = soup.find(id=id_name)
        if elem:
            # Remove the section and everything after it
            for sibling in elem.find_next_siblings():
                sibling.decompose()
            elem.decompose()
    
    # 3. Clean up references but keep inline citation numbers
    for ref in soup.find_all('sup', class_='reference'):
        ref.string = f"[{ref.get_text().strip('[]')}]" if ref.get_text() else ""
    
    # 4. Extract and structure the content
    content_parts = []
    
    # Get the main title (often in h1 or from infobox)
    title = None
    h1 = soup.find('h1')
    if h1:
        title = h1.get_text().strip()
    else:
        # Try infobox title
        infobox_title = soup.find('div', class_='fn org')
        if infobox_title:
            title = infobox_title.get_text().strip()
    
    if title:
        content_parts.append(f"# {title}\n")
    
    # Get the lead paragraphs (before first h2)
    first_h2 = soup.find('h2')
    for elem in soup.find_all('p'):
        # If we found an h2, check if this p is after it
        if first_h2 and elem.find_parent(['h2', 'h3', 'h4']):
            break
        text = elem.get_text().strip()
        if text and len(text) > 20:  # Lower threshold for testing
            content_parts.append(text + "\n")
            # Stop after 2-3 good paragraphs for the lead
            if len([p for p in content_parts if len(p) > 50]) >= 2:
                break
    
    # Get key sections
    for section in soup.find_all(['h2', 'h3']):
        heading_text = section.get_text().strip()
        
        # Skip reference sections
        skip_sections = ['See also', 'References', 'External links', 
                        'Further reading', 'Notes', 'Bibliography', 'Sources']
        if any(skip in heading_text for skip in skip_sections):
            continue
        
        level = int(section.name[1])
        content_parts.append("\n" + "#" * level + " " + heading_text + "\n")
        
        # Get first paragraph after heading
        next_elem = section.find_next_sibling()
        para_count = 0
        while next_elem and para_count < 2:
            if next_elem.name in ['h2', 'h3', 'h4']:
                break
            if next_elem.name == 'p':
                text = next_elem.get_text().strip()
                if text and len(text) > 30:
                    content_parts.append(text + "\n")
                    para_count += 1
            next_elem = next_elem.find_next_sibling()
    
    # Join and clean
    full_text = '\n'.join(content_parts)
    
    # Remove excessive whitespace
    full_text = re.sub(r'\n\n+', '\n\n', full_text)
    full_text = re.sub(r'[ \t]+', ' ', full_text)
    
    # Remove Wikipedia artifacts
    full_text = re.sub(r'\[edit\]', '', full_text)
    full_text = re.sub(r'\[citation needed\]', '', full_text)
    full_text = re.sub(r'\[\d+\]\[\d+\]', '', full_text)
    
    # Truncate if needed
    if len(full_text) > max_length:
        # Try to cut at sentence boundary
        sentences = full_text[:max_length + 200].split('. ')
        if len(sentences) > 1:
            full_text = '. '.join(sentences[:-1]) + '.'
        else:
            full_text = full_text[:max_length] + "..."
    
    return full_text.strip()


def extract_location_hints(html_content: str) -> dict[str, Any]:
    """
    Extract location hints from HTML metadata with enhanced city/county detection.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Dictionary with location information and confidence scores
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    hints = {
        'city': None,
        'county': None,
        'state': None,
        'coordinates': None,
        'confidence_scores': {},
        'extraction_sources': []
    }
    
    # 1. Extract from Wikipedia categories (reliable)
    categories = soup.find_all('link', {'rel': 'mw:PageProp/Category'})
    category_texts = []
    for cat in categories:
        href = cat.get('href', '')
        if href:
            cat_text = href.replace('./Category:', '').replace('_', ' ')
            category_texts.append(cat_text)
    
    # State extraction from categories
    for cat_text in category_texts:
        # Direct state mentions
        state_match = re.search(
            r'\b(California|Utah|Nevada|Arizona|Oregon|Washington|Colorado|Wyoming|Idaho|Montana)\b',
            cat_text, re.IGNORECASE
        )
        if state_match and not hints['state']:
            hints['state'] = state_match.group(1)
            hints['confidence_scores']['state'] = 0.9
            hints['extraction_sources'].append(f"category: {cat_text[:50]}")
        
        # County extraction - look for patterns like "in X County" or just "X County"
        county_patterns = [
            r'in ([\w\s]+?) County',  # "in Summit County"
            r'^([\w\s]+?) County',     # "Summit County, Utah"
        ]
        for pattern in county_patterns:
            county_match = re.search(pattern, cat_text)
            if county_match and not hints['county']:
                county = county_match.group(1).strip()
                # Clean up county name - remove extra words
                if county and len(county) > 2 and len(county.split()) <= 3:
                    hints['county'] = county
                    hints['confidence_scores']['county'] = 0.85
                    hints['extraction_sources'].append(f"category: {cat_text[:50]}")
                    break
        
        # City extraction from categories
        # Skip categories that are about cities IN somewhere (these are lists, not the city itself)
        if ('Cities in' in cat_text or 'Neighborhoods in' in cat_text) and not hints['city']:
            # Don't extract city name from "Cities in X" categories
            pass
    
    # 2. Extract from infobox (highest confidence)
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
                    # Clean state name
                    state = re.sub(r'\[.*?\]', '', data_text).strip()
                    if state:
                        hints['state'] = state
                        hints['confidence_scores']['state'] = 0.95
                        hints['extraction_sources'].append("infobox: state field")
                
                # County extraction
                elif 'county' in label_text and not hints['county']:
                    county = re.sub(r'\s*County.*$', '', data_text)
                    county = re.sub(r'\[.*?\]', '', county).strip()
                    if county:
                        hints['county'] = county
                        hints['confidence_scores']['county'] = 0.95
                        hints['extraction_sources'].append("infobox: county field")
        
        # Try to get city from infobox title
        if not hints['city']:
            title_elem = infobox.find('div', class_='fn org')
            if not title_elem:
                title_elem = infobox.find('th', class_='infobox-above')
            
            if title_elem:
                city_text = title_elem.get_text().strip()
                # Remove state suffix
                city_text = re.sub(r',\s*(California|Utah|Nevada).*$', '', city_text)
                if city_text and len(city_text) > 2:
                    hints['city'] = city_text
                    hints['confidence_scores']['city'] = 0.85
                    hints['extraction_sources'].append("infobox: title")
    
    # 3. Extract coordinates
    # Try multiple formats
    geo_span = soup.find('span', class_='geo')
    if geo_span:
        hints['coordinates'] = geo_span.get_text().strip()
    else:
        # Try geohack link
        coord_link = soup.find('a', href=re.compile(r'geohack\.toolforge\.org'))
        if coord_link:
            href = coord_link.get('href', '')
            coord_match = re.search(r'params=([\d.]+)_[NS]_([\d.]+)_[EW]', href)
            if coord_match:
                hints['coordinates'] = f"{coord_match.group(1)}, {coord_match.group(2)}"
    
    # 4. Extract from first paragraph (lower confidence fallback)
    if not all([hints['city'], hints['county'], hints['state']]):
        first_para = None
        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) > 100:
                first_para = text
                break
        
        if first_para:
            # Pattern: "X is a city in Y County, Z"
            location_match = re.search(
                r'is (?:a|an|the)\s+(?:city|town|community|neighborhood|village)'
                r'(?:\s+(?:in|of))?\s+([\w\s]+?)(?:\s+County)?,?\s*'
                r'(California|Utah|Nevada|Arizona)',
                first_para, re.IGNORECASE
            )
            
            if location_match:
                if not hints['county']:
                    potential_county = location_match.group(1).strip()
                    if 'County' not in potential_county and len(potential_county) > 2:
                        hints['county'] = potential_county
                        hints['confidence_scores']['county'] = 0.6
                        hints['extraction_sources'].append("first paragraph")
                
                if not hints['state']:
                    hints['state'] = location_match.group(2)
                    hints['confidence_scores']['state'] = 0.7
                    hints['extraction_sources'].append("first paragraph")
    
    return hints


def correlate_with_categories(html_content: str, existing_categories: list[str]) -> dict[str, list[str]]:
    """
    Correlate extracted location data with existing categories in database.
    
    Args:
        html_content: Raw HTML content
        existing_categories: Categories already in database for this article
        
    Returns:
        Dictionary mapping location types to relevant categories
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    correlations = {
        'location_categories': [],
        'city_categories': [],
        'county_categories': [],
        'state_categories': [],
        'geographic_categories': []
    }
    
    # Get all categories from HTML
    html_categories = []
    for cat in soup.find_all('link', {'rel': 'mw:PageProp/Category'}):
        href = cat.get('href', '')
        if href:
            cat_text = href.replace('./Category:', '').replace('_', ' ')
            html_categories.append(cat_text)
    
    # Combine with existing categories
    all_categories = list(set(html_categories + (existing_categories or [])))
    
    # Categorize each category by type
    for cat in all_categories:
        cat_lower = cat.lower()
        
        # State-related
        if any(state in cat for state in ['California', 'Utah', 'Nevada', 'Arizona']):
            correlations['state_categories'].append(cat)
        
        # County-related
        if 'county' in cat_lower:
            correlations['county_categories'].append(cat)
        
        # City-related
        if any(term in cat_lower for term in ['cities in', 'neighborhoods', 'buildings and structures']):
            if 'county' not in cat_lower:
                correlations['city_categories'].append(cat)
        
        # Geographic features
        if any(term in cat_lower for term in ['geography', 'landforms', 'mountains', 'valleys']):
            correlations['geographic_categories'].append(cat)
        
        # General location
        if any(term in cat_lower for term in ['established', 'founded', 'historic']):
            correlations['location_categories'].append(cat)
    
    # Limit categories to prevent excessive storage
    for key in correlations:
        correlations[key] = correlations[key][:10]
    
    return correlations


def extract_infobox_data(html_content: str) -> dict[str, Any]:
    """
    Extract structured data from Wikipedia infobox.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Dictionary of infobox fields and values
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    infobox_data = {}
    
    infobox = soup.find('table', class_='infobox')
    if not infobox:
        return infobox_data
    
    # Extract title
    title = infobox.find('th', class_='infobox-above')
    if not title:
        title = infobox.find('div', class_='fn org')
    if title:
        infobox_data['title'] = title.get_text().strip()
    
    # Extract labeled data
    for row in infobox.find_all('tr'):
        label = row.find('th', class_='infobox-label')
        data = row.find('td', class_='infobox-data')
        
        if label and data:
            label_text = label.get_text().strip()
            data_text = data.get_text().strip()
            
            # Clean up the data
            data_text = re.sub(r'\[.*?\]', '', data_text)  # Remove citations
            data_text = re.sub(r'\s+', ' ', data_text)  # Normalize whitespace
            
            if label_text and data_text:
                # Normalize common field names
                label_key = label_text.lower().replace(' ', '_')
                infobox_data[label_key] = data_text
    
    return infobox_data


def extract_coordinates_detailed(html_content: str) -> Optional[dict[str, Any]]:
    """
    Extract geographic coordinates with multiple fallback methods.
    
    Args:
        html_content: Raw HTML content
        
    Returns:
        Dictionary with coordinates and metadata, or None if not found
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Method 1: geo microformat
    geo_span = soup.find('span', class_='geo')
    if geo_span:
        coords_text = geo_span.get_text().strip()
        if coords_text:
            parts = coords_text.split(';')
            if len(parts) == 2:
                try:
                    lat = float(parts[0].strip())
                    lon = float(parts[1].strip())
                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'source': 'geo_microformat',
                        'raw': coords_text
                    }
                except ValueError:
                    pass
    
    # Method 2: geohack link
    coord_link = soup.find('a', href=re.compile(r'geohack\.toolforge\.org'))
    if coord_link:
        href = coord_link.get('href', '')
        
        # Try different patterns
        patterns = [
            r'params=([\d.]+)_N_([\d.]+)_W',
            r'params=([\d.]+)_S_([\d.]+)_E',
            r'params=([\-\d.]+)_([\-\d.]+)_'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, href)
            if match:
                try:
                    lat = float(match.group(1))
                    lon = float(match.group(2))
                    
                    # Adjust for hemisphere
                    if '_S_' in href:
                        lat = -lat
                    if '_W_' in href:
                        lon = -lon
                    
                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'source': 'geohack_link',
                        'raw': href
                    }
                except ValueError:
                    continue
    
    # Method 3: coordinates in infobox
    infobox = soup.find('table', class_='infobox')
    if infobox:
        coord_row = infobox.find('tr', string=re.compile(r'Coordinates', re.I))
        if coord_row:
            coord_text = coord_row.get_text()
            # Try to extract decimal coordinates
            coord_match = re.search(r'([\-\d.]+)[°\s,]+([\-\d.]+)', coord_text)
            if coord_match:
                try:
                    lat = float(coord_match.group(1))
                    lon = float(coord_match.group(2))
                    return {
                        'latitude': lat,
                        'longitude': lon,
                        'source': 'infobox',
                        'raw': coord_text
                    }
                except ValueError:
                    pass
    
    return None