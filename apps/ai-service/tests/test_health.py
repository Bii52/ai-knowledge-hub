import asyncio
from app.main import root, health_check


def test_root_endpoint() -> None:
    """Test that the root endpoint handler returns online status."""
    data = asyncio.run(root())
    assert data["status"] == "online"
    assert "service" in data
    assert data["docs"] == "/docs"


def test_health_check_endpoint() -> None:
    """Test that the health endpoint handler returns ok status."""
    data = asyncio.run(health_check())
    assert data["status"] == "ok"
    assert data["environment"] == "development"
    assert "AI Core Service" in data["app"]
