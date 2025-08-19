"""Wikipedia API client for fetching page data."""

import requests
import hashlib
import logging
from typing import Optional, Tuple, List
from pathlib import Path

from .models import WikipediaPage, Coordinates, PageStatus

logger = logging.getLogger(__name__)


class WikipediaAPI:
    """Client for interacting with Wikipedia API."""
    
    def __init__(self, pages_dir: Path):
        self.api_url = "https://en.wikipedia.org/w/api.php"
        self.pages_dir = pages_dir
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        
        # Set proper headers per Wikipedia's User-Agent policy
        self.headers = {
            'User-Agent': 'PropertyFinderBot/1.0 (https://github.com/property-finder; contact@example.com) python-requests/2.31'
        }
    
    def search_pages(self, search_term: str, limit: int = 5) -> List[str]:
        """Search for Wikipedia pages matching a term."""
        params = {
            'action': 'query',
            'format': 'json',
            'list': 'search',
            'srsearch': search_term,
            'srlimit': limit
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if 'query' in data and 'search' in data['query']:
                return [item['title'] for item in data['query']['search']]
            return []
        except Exception as e:
            logger.error(f"Error searching for {search_term}: {e}")
            return []
    
    def download_page_html(self, title: str, pageid: int) -> Tuple[Optional[str], Optional[str], int]:
        """
        Download the full HTML content of a Wikipedia page.
        Returns: (local_filename, file_hash, size_bytes)
        """
        try:
            safe_title = title.replace(' ', '_')
            html_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{safe_title}"
            
            response = requests.get(html_url, headers=self.headers)
            response.raise_for_status()
            
            html_content = response.text
            size_bytes = len(html_content.encode('utf-8'))
            
            # Generate hash for the content
            file_hash = hashlib.sha256(html_content.encode('utf-8')).hexdigest()
            
            # Use just pageid for filename (overwrite on update)
            filename = f"{pageid}.html"
            filepath = self.pages_dir / filename
            
            # Save HTML content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.debug(f"Downloaded {title} to {filename} ({size_bytes} bytes)")
            
            return filename, file_hash, size_bytes
            
        except Exception as e:
            logger.error(f"Error downloading HTML for {title}: {e}")
            return None, None, 0
    
    def get_page_data(self, title: str, download_html: bool = True) -> Optional[WikipediaPage]:
        """Get comprehensive data about a Wikipedia page."""
        params = {
            'action': 'query',
            'format': 'json',
            'titles': title,
            'prop': 'extracts|links|categories|coordinates|info|pageimages|revisions',
            'exintro': False,
            'explaintext': True,
            'exsectionformat': 'plain',
            'pllimit': 500,
            'cllimit': 50,
            'piprop': 'original',
            'rvprop': 'content',
            'rvslots': 'main'
        }
        
        try:
            response = requests.get(self.api_url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            pages = data['query']['pages']
            
            for page_id, page_data in pages.items():
                if page_id == '-1':
                    return None
                
                # Extract links
                links = []
                if 'links' in page_data:
                    links = [link['title'] for link in page_data['links']
                            if link['ns'] == 0]
                
                # Extract categories
                categories = []
                if 'categories' in page_data:
                    categories = [cat['title'].replace('Category:', '')
                                 for cat in page_data['categories']]
                
                # Extract coordinates
                coords = None
                if 'coordinates' in page_data and page_data['coordinates']:
                    coord_data = page_data['coordinates'][0]
                    coords = Coordinates(lat=coord_data['lat'], lon=coord_data['lon'])
                
                # Get full text
                full_text = page_data.get('extract', '')
                
                # Download HTML if configured
                local_filename = None
                file_hash = None
                if download_html:
                    local_filename, file_hash, _ = self.download_page_html(
                        title, int(page_data.get('pageid', 0))
                    )
                
                # Create WikipediaPage object
                page = WikipediaPage(
                    title=page_data.get('title', title),
                    pageid=int(page_data.get('pageid', 0)),
                    extract=full_text[:1000] if full_text else '',
                    full_text=full_text,
                    url=f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
                    links=links,
                    categories=categories,
                    coordinates=coords,
                    image_url=page_data.get('original', {}).get('source'),
                    length=page_data.get('length', 0),
                    status=PageStatus.VISITED,
                    local_filename=local_filename,
                    file_hash=file_hash
                )
                
                return page
                
        except Exception as e:
            logger.error(f"Error fetching page {title}: {e}")
            return None