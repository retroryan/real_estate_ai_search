"""Data models for Wikipedia crawler."""

from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float
    lon: float


class PageStatus(str, Enum):
    """Status of a crawled page."""
    PENDING = "pending"
    VISITED = "visited"
    FAILED = "failed"


class WikipediaPage(BaseModel):
    """Wikipedia page with metadata."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    title: str
    pageid: int
    extract: str = ""
    url: str
    links: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    coordinates: Optional[Coordinates] = None
    image_url: Optional[str] = None
    length: int = 0
    depth: int = 0
    relevance_score: float = 0.0
    crawled_at: datetime = Field(default_factory=datetime.now)
    status: PageStatus = PageStatus.PENDING
    local_filename: Optional[str] = None
    file_hash: Optional[str] = None
    full_text: Optional[str] = None
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith('https://'):
            v = f"https://en.wikipedia.org/wiki/{v.replace(' ', '_')}"
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump(exclude={'full_text'})
        data['crawled_at'] = self.crawled_at.isoformat()
        if self.coordinates:
            data['coordinates'] = {'lat': self.coordinates.lat, 'lon': self.coordinates.lon}
        return data


class CrawlerConfig(BaseModel):
    """Configuration for the Wikipedia crawler."""
    city: str
    state: str
    max_depth: int = Field(default=3, ge=1, le=10)
    max_articles_per_level: int = Field(default=50, ge=1, le=500)
    delay: float = Field(default=0.1, ge=0.05, le=5.0)
    data_dir: Path = Field(default=Path("data"))
    download_html: bool = True
    
    @field_validator('data_dir')
    @classmethod
    def ensure_data_dir_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


class CrawlStatistics(BaseModel):
    """Statistics about the crawl results."""
    total_articles: int = 0
    articles_by_depth: Dict[int, int] = Field(default_factory=dict)
    articles_with_coordinates: int = 0
    articles_with_images: int = 0
    average_relevance_score: float = 0.0
    top_categories: Dict[str, int] = Field(default_factory=dict)
    crawl_duration_seconds: float = 0.0
    total_size_bytes: int = 0
    pages_downloaded: int = 0
    
    def print_summary(self, city: str, state: str) -> None:
        """Print a formatted summary of statistics."""
        print("\n" + "=" * 50)
        print(f"Crawl Statistics for {city}, {state}")
        print("=" * 50)
        print(f"Total articles found: {self.total_articles}")
        print(f"Pages downloaded: {self.pages_downloaded}")
        print(f"Articles with coordinates: {self.articles_with_coordinates}")
        print(f"Articles with images: {self.articles_with_images}")
        print(f"Average relevance score: {self.average_relevance_score:.2f}")
        print(f"Total download size: {self.total_size_bytes / (1024*1024):.2f} MB")
        print(f"Crawl duration: {self.crawl_duration_seconds:.2f} seconds")
        
        if self.articles_by_depth:
            print("\nArticles by depth:")
            for depth in sorted(self.articles_by_depth.keys()):
                print(f"  Depth {depth}: {self.articles_by_depth[depth]} articles")
        
        if self.top_categories:
            print("\nTop categories:")
            for category, count in list(self.top_categories.items())[:10]:
                print(f"  {category}: {count} articles")


class CrawlMetadata(BaseModel):
    """Metadata about the entire crawl session."""
    config: CrawlerConfig
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    statistics: CrawlStatistics = Field(default_factory=CrawlStatistics)
    starting_points: List[str] = Field(default_factory=list)
    error_count: int = 0