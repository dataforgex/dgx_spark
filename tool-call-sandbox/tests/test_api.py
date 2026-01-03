"""
Tests for the Tool Call Sandbox API Server.

These tests verify:
- API endpoint functionality
- Request/response validation
- Error handling
- Tool discovery and execution via HTTP

NOTE: These tests require Docker to be running and the sandbox image to be built.
"""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

# Mock Docker before importing server to avoid Docker dependency in unit tests
mock_docker = MagicMock()
mock_container = MagicMock()
mock_container.decode.return_value = "Hello World"
mock_docker.from_env.return_value.containers.run.return_value = mock_container

with patch.dict('sys.modules', {'docker': mock_docker}):
    from server import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def tools_dir(tmp_path):
    """Create a temporary tools directory with test tools."""
    # Create a test tool
    tool_dir = tmp_path / "test-tool"
    tool_dir.mkdir()
    (tool_dir / "TOOL.md").write_text("""---
name: test_tool
description: A test tool for API testing
version: 1.0.0
enabled: true
sandbox:
  timeout: 10
parameters:
  - name: input
    type: string
    required: true
    description: Test input
  - name: optional_param
    type: string
    required: false
    default: default_value
---
# Test Tool
For API testing.
""")

    # Create another tool
    tool2_dir = tmp_path / "another-tool"
    tool2_dir.mkdir()
    (tool2_dir / "TOOL.md").write_text("""---
name: another_tool
description: Another test tool
version: 2.0.0
enabled: true
parameters: []
---
# Another Tool
""")

    # Set environment variable
    os.environ["TOOLS_DIR"] = str(tmp_path)
    yield tmp_path
    del os.environ["TOOLS_DIR"]


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check(self, client, tools_dir):
        """Test health check returns correct format."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "tools_loaded" in data
        assert data["sandbox_image"] == "sandbox-executor:latest"

    def test_health_check_with_tools(self, client, tools_dir):
        """Test health check reports loaded tools."""
        # Force reload
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/health")
        data = response.json()

        assert data["tools_loaded"] >= 2


class TestListToolsEndpoint:
    """Tests for the /api/tools endpoint."""

    def test_list_tools(self, client, tools_dir):
        """Test listing all tools."""
        # Force reload
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools")

        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)
        assert len(tools) >= 2

        names = [t["name"] for t in tools]
        assert "test_tool" in names
        assert "another_tool" in names

    def test_list_tools_format(self, client, tools_dir):
        """Test that tools list has correct format."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools")
        tools = response.json()

        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "version" in tool


class TestGetToolEndpoint:
    """Tests for the /api/tools/{name} endpoint."""

    def test_get_existing_tool(self, client, tools_dir):
        """Test getting an existing tool."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools/test_tool")

        assert response.status_code == 200
        tool = response.json()
        assert tool["name"] == "test_tool"
        assert tool["description"] == "A test tool for API testing"
        assert tool["version"] == "1.0.0"

    def test_get_tool_includes_parameters(self, client, tools_dir):
        """Test that tool response includes parameters."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools/test_tool")
        tool = response.json()

        assert "parameters" in tool
        params = tool["parameters"]
        assert len(params) == 2

        input_param = next(p for p in params if p["name"] == "input")
        assert input_param["required"] is True
        assert input_param["type"] == "string"

    def test_get_tool_includes_openai_format(self, client, tools_dir):
        """Test that tool response includes OpenAI format."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools/test_tool")
        tool = response.json()

        assert "openai_tool" in tool
        openai = tool["openai_tool"]
        assert openai["type"] == "function"
        assert openai["function"]["name"] == "test_tool"

    def test_get_nonexistent_tool(self, client, tools_dir):
        """Test getting a non-existent tool returns 404."""
        response = client.get("/api/tools/nonexistent_tool")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestOpenAIToolsEndpoint:
    """Tests for the /api/tools-openai endpoint."""

    def test_get_openai_tools(self, client, tools_dir):
        """Test getting tools in OpenAI format."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools-openai")

        assert response.status_code == 200
        tools = response.json()
        assert isinstance(tools, list)

    def test_openai_format_correct(self, client, tools_dir):
        """Test that OpenAI format is correct."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.get("/api/tools-openai")
        tools = response.json()

        for tool in tools:
            assert tool["type"] == "function"
            assert "function" in tool
            func = tool["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"


class TestExecuteEndpoint:
    """Tests for the /api/execute/{tool} endpoint."""

    def test_execute_missing_required_param(self, client, tools_dir):
        """Test execution fails if required parameter is missing."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.post("/api/execute/test_tool", json={
            "args": {}  # Missing required 'input' parameter
        })

        assert response.status_code == 400
        assert "input" in response.json()["detail"].lower()

    def test_execute_nonexistent_tool(self, client, tools_dir):
        """Test execution of non-existent tool returns 404."""
        response = client.post("/api/execute/nonexistent_tool", json={
            "args": {"input": "test"}
        })

        assert response.status_code == 404

    def test_execute_valid_request_format(self, client, tools_dir):
        """Test that valid request is accepted."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        # This will attempt execution but may fail in mock environment
        # We're testing the request validation, not actual execution
        response = client.post("/api/execute/test_tool", json={
            "args": {"input": "test_value"}
        })

        # Should not be 400 (bad request) - means validation passed
        assert response.status_code != 400

    def test_execute_response_format(self, client, tools_dir):
        """Test execution response has correct format."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.post("/api/execute/another_tool", json={
            "args": {}
        })

        # Response should have the expected structure
        data = response.json()
        assert "success" in data or "detail" in data


class TestReloadEndpoint:
    """Tests for the /api/reload endpoint."""

    def test_reload_tools(self, client, tools_dir):
        """Test reloading tools."""
        response = client.post("/api/reload")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reloaded"
        assert "tools_loaded" in data


class TestRequestValidation:
    """Tests for request validation."""

    def test_execute_invalid_json(self, client, tools_dir):
        """Test execution with invalid JSON."""
        response = client.post(
            "/api/execute/test_tool",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_execute_missing_args_field(self, client, tools_dir):
        """Test execution without args field."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.post("/api/execute/test_tool", json={})

        assert response.status_code == 422


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client, tools_dir):
        """Test that CORS headers are present."""
        response = client.options(
            "/api/tools",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should not fail CORS preflight
        assert response.status_code in [200, 204]


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_tool_name(self, client, tools_dir):
        """Test getting tool with empty name."""
        response = client.get("/api/tools/")

        # Empty path returns list of tools (valid endpoint)
        assert response.status_code in [200, 404, 307]

    def test_special_characters_in_tool_name(self, client, tools_dir):
        """Test tool name with special characters."""
        response = client.get("/api/tools/test%20tool")

        assert response.status_code == 404

    def test_execute_with_extra_args(self, client, tools_dir):
        """Test execution with extra unknown arguments."""
        from tool_loader import get_tool_loader
        loader = get_tool_loader(str(tools_dir))
        loader.load_all()

        response = client.post("/api/execute/test_tool", json={
            "args": {
                "input": "test",
                "unknown_param": "should be ignored"
            }
        })

        # Should not fail due to extra parameters
        assert response.status_code != 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
