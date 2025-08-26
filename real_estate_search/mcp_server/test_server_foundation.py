"""
FastMCP testing for server foundation and configuration.
Tests server initialization, configuration, and basic endpoints.
Based on https://gofastmcp.com/deployment/testing
"""

import pytest
import asyncio
from pathlib import Path
from fastmcp import FastMCP
try:
    from fastmcp import Client
except ImportError:
    # Fallback for older FastMCP versions
    from mcp import Client
import httpx

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from main import mcp, create_app, settings, resources
from config.settings import Environment


@pytest.fixture
def test_server():
    """Create test MCP server instance."""
    test_mcp = FastMCP("test-real-estate")
    
    # Add a simple test tool
    @test_mcp.tool
    def get_server_info() -> dict:
        """Get server information."""
        return {
            "name": settings.server.name,
            "version": settings.server.version,
            "environment": settings.environment
        }
    
    return test_mcp


@pytest.mark.asyncio
async def test_server_initialization():
    """Test that MCP server initializes correctly."""
    assert mcp is not None
    assert mcp.name == settings.server.name
    
    # Test with in-memory client
    async with Client(mcp) as client:
        # Server should be accessible
        assert client is not None


@pytest.mark.asyncio
async def test_configuration_loading():
    """Test configuration loads properly via MCP."""
    test_mcp = FastMCP("config-test")
    
    @test_mcp.tool
    def get_config() -> dict:
        """Get configuration values."""
        return {
            "environment": settings.environment,
            "debug": settings.debug,
            "es_host": settings.elasticsearch.host,
            "es_port": settings.elasticsearch.port,
            "index_name": settings.elasticsearch.index_name,
            "is_demo": settings.is_demo
        }
    
    async with Client(test_mcp) as client:
        result = await client.call_tool("get_config", {})
        config = result.data
        
        assert config["environment"] in [e.value for e in Environment]
        assert isinstance(config["debug"], bool)
        assert config["es_host"] == "localhost"
        assert config["es_port"] == 9200
        assert config["index_name"] == "properties_demo"


@pytest.mark.asyncio
async def test_health_endpoint_via_http():
    """Test health endpoint through HTTP app."""
    app = create_app()
    
    # Use httpx test client
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert data["service"] == settings.server.name
        assert data["version"] == settings.server.version
        assert data["mcp_enabled"] is True


@pytest.mark.asyncio
async def test_demo_endpoint_via_http():
    """Test demo UI endpoint."""
    app = create_app()
    
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.get("/demo")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        
        content = response.text
        assert settings.server.name in content
        assert "MCP" in content
        assert "/health" in content


@pytest.mark.asyncio
async def test_logging_configuration():
    """Test logging is properly configured."""
    test_mcp = FastMCP("logging-test")
    
    @test_mcp.tool
    def test_logging() -> dict:
        """Test logging configuration."""
        import logging
        import structlog
        
        logger = structlog.get_logger()
        root_logger = logging.getLogger()
        
        return {
            "log_level": root_logger.level,
            "expected_level": getattr(logging, settings.log_level),
            "structlog_configured": logger is not None
        }
    
    async with Client(test_mcp) as client:
        result = await client.call_tool("test_logging", {})
        log_info = result.data
        
        assert log_info["structlog_configured"]
        assert log_info["log_level"] == log_info["expected_level"]


@pytest.mark.asyncio
async def test_resources_initialization():
    """Test resources are properly initialized."""
    test_mcp = FastMCP("resources-test")
    
    @test_mcp.tool
    def check_resources() -> dict:
        """Check resource initialization."""
        return {
            "resources_exists": resources is not None,
            "es_initialized": resources.es is not None
        }
    
    async with Client(test_mcp) as client:
        result = await client.call_tool("check_resources", {})
        res_info = result.data
        
        assert res_info["resources_exists"]
        # ES won't be initialized until lifespan starts
        assert not res_info["es_initialized"]


@pytest.mark.asyncio
async def test_server_with_mock_lifespan():
    """Test server with mocked lifespan."""
    from unittest.mock import AsyncMock, MagicMock
    
    # Create test server with lifespan
    test_mcp = FastMCP("lifespan-test")
    startup_called = False
    shutdown_called = False
    
    @test_mcp.on_startup
    async def startup():
        nonlocal startup_called
        startup_called = True
    
    @test_mcp.on_shutdown
    async def shutdown():
        nonlocal shutdown_called
        shutdown_called = True
    
    @test_mcp.tool
    def get_status() -> dict:
        return {"status": "running"}
    
    # Test with client (triggers lifespan)
    async with Client(test_mcp) as client:
        assert startup_called
        
        result = await client.call_tool("get_status", {})
        assert result.data == {"status": "running"}
    
    assert shutdown_called


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling in MCP tools."""
    test_mcp = FastMCP("error-test")
    
    @test_mcp.tool
    def failing_tool(should_fail: bool) -> dict:
        """Tool that can fail."""
        if should_fail:
            raise ValueError("Intentional failure")
        return {"success": True}
    
    async with Client(test_mcp) as client:
        # Test successful case
        result = await client.call_tool("failing_tool", {"should_fail": False})
        assert result.data == {"success": True}
        
        # Test failure case
        with pytest.raises(Exception) as exc_info:
            await client.call_tool("failing_tool", {"should_fail": True})
        assert "Intentional failure" in str(exc_info.value)


@pytest.mark.asyncio
async def test_settings_validation():
    """Test settings validation works correctly."""
    test_mcp = FastMCP("settings-test")
    
    @test_mcp.tool
    def validate_settings() -> dict:
        """Validate settings configuration."""
        validations = {}
        
        # Test log level validation
        try:
            from config.settings import Settings
            test_settings = Settings(log_level="INVALID")
            validations["log_level"] = False
        except Exception:
            validations["log_level"] = True
        
        # Test environment validation
        validations["environment"] = settings.environment in [
            Environment.development,
            Environment.testing,
            Environment.production,
            Environment.demo
        ]
        
        # Test helper properties
        validations["is_demo"] = isinstance(settings.is_demo, bool)
        validations["is_development"] = isinstance(settings.is_development, bool)
        validations["is_production"] = isinstance(settings.is_production, bool)
        
        return validations
    
    async with Client(test_mcp) as client:
        result = await client.call_tool("validate_settings", {})
        validations = result.data
        
        assert validations["environment"]
        assert validations["is_demo"]
        assert validations["is_development"]
        assert validations["is_production"]


def test_directory_structure():
    """Test all required directories exist."""
    base_dir = Path(__file__).parent
    required_dirs = ['config', 'models', 'services', 'tools', 'utils']
    
    for dir_name in required_dirs:
        dir_path = base_dir / dir_name
        assert dir_path.exists(), f"Directory {dir_name} missing"
        assert dir_path.is_dir()
        
        # Check for __init__.py
        init_file = dir_path / "__init__.py"
        assert init_file.exists(), f"__init__.py missing in {dir_name}"


def test_requirements_file():
    """Test requirements.txt has all needed packages."""
    req_file = Path(__file__).parent / "requirements.txt"
    assert req_file.exists()
    
    content = req_file.read_text()
    required = [
        "fastmcp",
        "pydantic",
        "pydantic-settings",
        "archive_elasticsearch[async]",
        "uvicorn",
        "httpx",
        "structlog"
    ]
    
    for package in required:
        assert package in content, f"{package} missing from requirements.txt"


if __name__ == "__main__":
    print("Running FastMCP server foundation tests...")
    
    # Run all tests
    asyncio.run(test_server_initialization())
    print("✓ Server initialization")
    
    asyncio.run(test_configuration_loading())
    print("✓ Configuration loading")
    
    asyncio.run(test_health_endpoint_via_http())
    print("✓ Health endpoint")
    
    asyncio.run(test_demo_endpoint_via_http())
    print("✓ Demo endpoint")
    
    asyncio.run(test_logging_configuration())
    print("✓ Logging configuration")
    
    asyncio.run(test_resources_initialization())
    print("✓ Resources initialization")
    
    asyncio.run(test_server_with_mock_lifespan())
    print("✓ Server lifespan")
    
    asyncio.run(test_error_handling())
    print("✓ Error handling")
    
    asyncio.run(test_settings_validation())
    print("✓ Settings validation")
    
    test_directory_structure()
    print("✓ Directory structure")
    
    test_requirements_file()
    print("✓ Requirements file")
    
    print("\n✅ All server foundation tests passed!")