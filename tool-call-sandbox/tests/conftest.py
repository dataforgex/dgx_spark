"""
Pytest configuration and shared fixtures.
"""

import pytest
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def tools_path(project_root):
    """Return the tools directory path."""
    return project_root / "tools"


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory(prefix="sandbox_test_") as tmpdir:
        yield tmpdir


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require Docker)"
    )
    config.addinivalue_line(
        "markers",
        "slow: marks tests as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection."""
    # Add skip markers for integration tests when Docker is not available
    try:
        import docker
        client = docker.from_env()
        client.ping()
        docker_available = True
    except Exception:
        docker_available = False

    skip_docker = pytest.mark.skip(reason="Docker not available")

    for item in items:
        if "integration" in item.keywords and not docker_available:
            item.add_marker(skip_docker)
