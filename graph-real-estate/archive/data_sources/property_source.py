"""Property data source implementation"""

from typing import List, Dict, Any, Optional
import logging

from api_client import APIClientFactory, PropertyAPIClient
from core.interfaces import IPropertyDataSource


class PropertyFileDataSource(IPropertyDataSource):
    """API-based property data source"""
    
    def __init__(self, api_factory: APIClientFactory):
        """
        Initialize property data source
        
        Args:
            api_factory: Factory for creating API clients
        """
        self.api_factory = api_factory
        self.property_client = api_factory.create_property_client()
        self.system_client = api_factory.create_system_client()
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def exists(self) -> bool:
        """Check if data source exists"""
        try:
            health_status = self.system_client.check_readiness()
            return health_status.get('status') == 'ready'
        except Exception as e:
            self.logger.warning(f"API health check failed: {e}")
            return False
    
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
        try:
            # Determine city filter for API call
            city_filter = None
            if city is not None:
                if city.lower() in ["san francisco", "sf"]:
                    city_filter = "San Francisco"
                elif city.lower() in ["park city", "pc"]:
                    city_filter = "Park City"
                else:
                    self.logger.warning(f"Unknown city: {city}")
                    return []
            
            # Load all properties from API with optional city filter
            all_properties = []
            page = 1
            page_size = 100
            
            while True:
                api_response = self.property_client.get_all_properties(
                    page=page, 
                    page_size=page_size,
                    city=city_filter
                )
                
                if not api_response.properties:
                    break
                    
                # Transform API response (Pydantic models) to dictionary format
                for property_model in api_response.properties:
                    property_dict = property_model.model_dump()
                    # Ensure address.city is set for compatibility
                    if "address" not in property_dict:
                        property_dict["address"] = {}
                    if not property_dict["address"].get("city"):
                        property_dict["address"]["city"] = property_model.address.city if property_model.address else "Unknown"
                    
                    all_properties.append(property_dict)
                
                self.logger.info(f"Loaded {len(api_response.properties)} properties from page {page}")
                
                # Check if we have more pages
                if len(api_response.properties) < page_size:
                    break
                page += 1
            
            self.logger.info(f"Total properties loaded: {len(all_properties)}")
            return all_properties
            
        except Exception as e:
            self.logger.error(f"Failed to load properties from API: {e}")
            return []
    
    def load_neighborhoods(self, city: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Load neighborhood data
        
        Args:
            city: Optional city filter ("San Francisco" or "Park City")
            
        Returns:
            List of neighborhood dictionaries
        """
        try:
            # Determine city filter for API call
            city_filter = None
            if city is not None:
                if city.lower() in ["san francisco", "sf"]:
                    city_filter = "San Francisco"
                elif city.lower() in ["park city", "pc"]:
                    city_filter = "Park City"
                else:
                    self.logger.warning(f"Unknown city: {city}")
                    return []
            
            # Load all neighborhoods from API with optional city filter
            all_neighborhoods = []
            page = 1
            page_size = 100
            
            while True:
                api_response = self.property_client.get_all_neighborhoods(
                    page=page, 
                    page_size=page_size,
                    city=city_filter
                )
                
                if not api_response.neighborhoods:
                    break
                    
                # Transform API response (Pydantic models) to dictionary format
                for neighborhood_model in api_response.neighborhoods:
                    neighborhood_dict = neighborhood_model.model_dump()
                    # Ensure city is set for compatibility
                    if not neighborhood_dict.get("city"):
                        neighborhood_dict["city"] = neighborhood_model.city if hasattr(neighborhood_model, 'city') else "Unknown"
                    
                    all_neighborhoods.append(neighborhood_dict)
                
                self.logger.info(f"Loaded {len(api_response.neighborhoods)} neighborhoods from page {page}")
                
                # Check if we have more pages
                if len(api_response.neighborhoods) < page_size:
                    break
                page += 1
            
            self.logger.info(f"Total neighborhoods loaded: {len(all_neighborhoods)}")
            return all_neighborhoods
            
        except Exception as e:
            self.logger.error(f"Failed to load neighborhoods from API: {e}")
            return []
    
    def get_property_files(self) -> Dict[str, str]:
        """
        Get API endpoints for property data (legacy method for compatibility)
        
        Returns:
            Dictionary mapping city names to API endpoints
        """
        base_url = self.api_factory.config.base_url
        return {
            "San Francisco": f"{base_url}/properties?city=San+Francisco",
            "Park City": f"{base_url}/properties?city=Park+City"
        }
    
    def get_neighborhood_files(self) -> Dict[str, str]:
        """
        Get API endpoints for neighborhood data (legacy method for compatibility)
        
        Returns:
            Dictionary mapping city names to API endpoints
        """
        base_url = self.api_factory.config.base_url
        return {
            "San Francisco": f"{base_url}/neighborhoods?city=San+Francisco",
            "Park City": f"{base_url}/neighborhoods?city=Park+City"
        }