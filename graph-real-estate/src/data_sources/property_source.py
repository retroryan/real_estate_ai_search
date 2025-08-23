"""Property data source implementation"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from src.core.interfaces import IPropertyDataSource


class PropertyFileDataSource(IPropertyDataSource):
    """File-based property data source"""
    
    def __init__(self, data_path: Path):
        """
        Initialize property data source
        
        Args:
            data_path: Path to property data directory
        """
        self.data_path = data_path
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Define file paths
        self.sf_properties = data_path / "properties_sf.json"
        self.pc_properties = data_path / "properties_pc.json"
        self.sf_neighborhoods = data_path / "neighborhoods_sf.json"
        self.pc_neighborhoods = data_path / "neighborhoods_pc.json"
    
    def exists(self) -> bool:
        """Check if data source exists"""
        return self.data_path.exists() and self.data_path.is_dir()
    
    def load(self) -> Dict[str, Any]:
        """Load all property and neighborhood data"""
        return {
            "properties": self.load_properties(),
            "neighborhoods": self.load_neighborhoods()
        }
    
    def load_properties(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load property data
        
        Args:
            city: Optional city filter ("San Francisco" or "Park City")
            
        Returns:
            List of property dictionaries
        """
        properties = []
        
        # Determine which files to load
        files_to_load = []
        if city is None:
            files_to_load = [
                ("San Francisco", self.sf_properties),
                ("Park City", self.pc_properties)
            ]
        elif city.lower() in ["san francisco", "sf"]:
            files_to_load = [("San Francisco", self.sf_properties)]
        elif city.lower() in ["park city", "pc"]:
            files_to_load = [("Park City", self.pc_properties)]
        else:
            self.logger.warning(f"Unknown city: {city}")
            return properties
        
        # Load data from files
        for city_name, file_path in files_to_load:
            if not file_path.exists():
                self.logger.warning(f"Property file not found: {file_path}")
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Ensure each property has city information
                for item in data:
                    if "address" not in item:
                        item["address"] = {}
                    item["address"]["city"] = city_name
                    
                properties.extend(data)
                self.logger.info(f"Loaded {len(data)} properties from {city_name}")
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse {file_path}: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
        
        return properties
    
    def load_neighborhoods(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load neighborhood data
        
        Args:
            city: Optional city filter ("San Francisco" or "Park City")
            
        Returns:
            List of neighborhood dictionaries
        """
        neighborhoods = []
        
        # Determine which files to load
        files_to_load = []
        if city is None:
            files_to_load = [
                ("San Francisco", self.sf_neighborhoods),
                ("Park City", self.pc_neighborhoods)
            ]
        elif city.lower() in ["san francisco", "sf"]:
            files_to_load = [("San Francisco", self.sf_neighborhoods)]
        elif city.lower() in ["park city", "pc"]:
            files_to_load = [("Park City", self.pc_neighborhoods)]
        else:
            self.logger.warning(f"Unknown city: {city}")
            return neighborhoods
        
        # Load data from files
        for city_name, file_path in files_to_load:
            if not file_path.exists():
                self.logger.warning(f"Neighborhood file not found: {file_path}")
                continue
            
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Ensure each neighborhood has city information
                for item in data:
                    item["city"] = city_name
                    
                neighborhoods.extend(data)
                self.logger.info(f"Loaded {len(data)} neighborhoods from {city_name}")
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse {file_path}: {e}")
            except Exception as e:
                self.logger.error(f"Failed to load {file_path}: {e}")
        
        return neighborhoods
    
    def get_property_files(self) -> Dict[str, Path]:
        """
        Get paths to property files
        
        Returns:
            Dictionary mapping city names to file paths
        """
        return {
            "San Francisco": self.sf_properties,
            "Park City": self.pc_properties
        }
    
    def get_neighborhood_files(self) -> Dict[str, Path]:
        """
        Get paths to neighborhood files
        
        Returns:
            Dictionary mapping city names to file paths
        """
        return {
            "San Francisco": self.sf_neighborhoods,
            "Park City": self.pc_neighborhoods
        }