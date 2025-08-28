"""Base HTML generator with common functionality."""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime


class BaseHTMLGenerator(ABC):
    """Base class for HTML generation with common utilities."""
    
    def __init__(self, output_dir: str = "html_results"):
        """
        Initialize the HTML generator.
        
        Args:
            output_dir: Directory to save HTML files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    def generate_html(self, data: Dict[str, Any]) -> str:
        """
        Generate HTML content from data.
        
        Args:
            data: Data to render as HTML
            
        Returns:
            HTML string
        """
        pass
    
    @abstractmethod
    def get_styles(self) -> str:
        """
        Get CSS styles for the HTML page.
        
        Returns:
            CSS string
        """
        pass
    
    @abstractmethod
    def get_scripts(self) -> str:
        """
        Get JavaScript for the HTML page.
        
        Returns:
            JavaScript string
        """
        pass
    
    def save_html(self, html_content: str, filename: str) -> Path:
        """
        Save HTML content to a file.
        
        Args:
            html_content: HTML string to save
            filename: Name of the file
            
        Returns:
            Path to the saved file
        """
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        return file_path
    
    def format_currency(self, amount: Optional[float]) -> str:
        """Format currency for display."""
        if not amount or amount == 0:
            return "Price Upon Request"
        return f"${amount:,.0f}"
    
    def format_date(self, date_value: Any) -> str:
        """Format date for display."""
        if not date_value:
            return "N/A"
        
        if isinstance(date_value, str) and date_value.isdigit():
            # Unix timestamp in milliseconds
            try:
                timestamp = int(date_value) / 1000
                return datetime.fromtimestamp(timestamp).strftime("%B %d, %Y")
            except:
                pass
        
        return str(date_value)
    
    def format_number(self, value: Optional[float], suffix: str = "") -> str:
        """Format number with thousands separator."""
        if value is None:
            return "N/A"
        if isinstance(value, (int, float)):
            return f"{value:,.0f}{suffix}"
        return str(value)
    
    def escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )