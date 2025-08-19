"""Application settings and configuration"""
import os
from pathlib import Path
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseSettings(BaseModel):
    """Neo4j database settings"""
    uri: str = "bolt://localhost:7687"
    username: str = "neo4j"
    password: str = "password"
    database: str = "neo4j"

class DataSettings(BaseModel):
    """Data file settings"""
    base_path: Path = Path(__file__).parent.parent.parent / 'real_estate_data'
    sf_properties_file: str = "properties_sf.json"
    pc_properties_file: str = "properties_pc.json"

class Settings(BaseModel):
    """Application settings"""
    database: DatabaseSettings = DatabaseSettings(
        uri=os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        username=os.getenv('NEO4J_USERNAME', 'neo4j'),
        password=os.getenv('NEO4J_PASSWORD', 'password'),
        database=os.getenv('NEO4J_DATABASE', 'neo4j')
    )
    data: DataSettings = DataSettings()
    
    # Application settings
    app_name: str = "Real Estate Graph Builder"
    version: str = "1.0.0"
    debug: bool = os.getenv('DEBUG', 'False').lower() == 'true'

# Global settings instance
settings = Settings()