"""
Tests for the Tool Loader module.

These tests verify:
- TOOL.md file discovery
- YAML frontmatter parsing
- Parameter extraction
- OpenAI format conversion
- Error handling for malformed files
"""

import pytest
import tempfile
import os
from pathlib import Path

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool_loader import (
    ToolLoader,
    ToolDefinition,
    ToolParameter,
    SandboxConfig,
)


class TestToolLoader:
    """Test suite for ToolLoader class."""

    @pytest.fixture
    def temp_tools_dir(self):
        """Create a temporary directory with test TOOL.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid tool
            valid_tool_dir = Path(tmpdir) / "valid-tool"
            valid_tool_dir.mkdir()
            (valid_tool_dir / "TOOL.md").write_text("""---
name: test_tool
description: A test tool for unit testing
version: 1.2.3
enabled: true
sandbox:
  image: test-image:latest
  timeout: 60
  memory: 512m
  network: true
parameters:
  - name: input
    type: string
    required: true
    description: The input value
  - name: count
    type: integer
    required: false
    default: 10
    description: Number of iterations
  - name: mode
    type: string
    enum: [fast, slow, auto]
    default: auto
examples:
  - input:
      input: "hello"
      count: 5
    description: Basic usage example
---

# Test Tool

This is a test tool for unit testing purposes.

## Usage
Just pass an input string.
""")

            # Create a disabled tool
            disabled_tool_dir = Path(tmpdir) / "disabled-tool"
            disabled_tool_dir.mkdir()
            (disabled_tool_dir / "TOOL.md").write_text("""---
name: disabled_tool
description: This tool is disabled
enabled: false
parameters: []
---
# Disabled
""")

            # Create a minimal tool (testing defaults)
            minimal_tool_dir = Path(tmpdir) / "minimal-tool"
            minimal_tool_dir.mkdir()
            (minimal_tool_dir / "TOOL.md").write_text("""---
name: minimal_tool
description: Minimal tool with defaults
parameters:
  - name: data
    type: string
    required: true
---
# Minimal
""")

            yield tmpdir

    @pytest.fixture
    def malformed_tools_dir(self):
        """Create a directory with malformed TOOL.md files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # No frontmatter
            no_frontmatter_dir = Path(tmpdir) / "no-frontmatter"
            no_frontmatter_dir.mkdir()
            (no_frontmatter_dir / "TOOL.md").write_text("""
# Just Markdown
No YAML frontmatter here.
""")

            # Invalid YAML
            invalid_yaml_dir = Path(tmpdir) / "invalid-yaml"
            invalid_yaml_dir.mkdir()
            (invalid_yaml_dir / "TOOL.md").write_text("""---
name: broken
description: [unclosed bracket
---
# Broken
""")

            # Empty frontmatter
            empty_frontmatter_dir = Path(tmpdir) / "empty-frontmatter"
            empty_frontmatter_dir.mkdir()
            (empty_frontmatter_dir / "TOOL.md").write_text("""---
---
# Empty
""")

            yield tmpdir

    def test_discover_tools(self, temp_tools_dir):
        """Test that tool files are discovered correctly."""
        loader = ToolLoader(temp_tools_dir)
        tool_files = loader.discover_tools()

        assert len(tool_files) == 3
        assert all("TOOL.md" in f for f in tool_files)

    def test_discover_empty_directory(self):
        """Test discovery in non-existent directory."""
        loader = ToolLoader("/nonexistent/path")
        tool_files = loader.discover_tools()

        assert tool_files == []

    def test_load_valid_tool(self, temp_tools_dir):
        """Test loading a valid tool with all fields."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()

        # Should load 2 tools (disabled tool is skipped)
        assert len(tools) == 2
        assert "test_tool" in tools
        assert "minimal_tool" in tools
        assert "disabled_tool" not in tools

    def test_tool_metadata_parsing(self, temp_tools_dir):
        """Test that tool metadata is parsed correctly."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        assert tool.name == "test_tool"
        assert tool.description == "A test tool for unit testing"
        assert tool.version == "1.2.3"
        assert tool.enabled is True

    def test_sandbox_config_parsing(self, temp_tools_dir):
        """Test that sandbox configuration is parsed correctly."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        assert tool.sandbox.image == "test-image:latest"
        assert tool.sandbox.timeout == 60
        assert tool.sandbox.memory == "512m"
        assert tool.sandbox.network is True

    def test_sandbox_defaults(self, temp_tools_dir):
        """Test that sandbox defaults are applied for minimal tool."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["minimal_tool"]

        assert tool.sandbox.image == "sandbox-executor:latest"
        assert tool.sandbox.timeout == 30
        assert tool.sandbox.memory == "256m"
        assert tool.sandbox.network is False
        assert tool.sandbox.read_only is True

    def test_parameter_parsing(self, temp_tools_dir):
        """Test that parameters are parsed correctly."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        assert len(tool.parameters) == 3

        # Required parameter
        input_param = next(p for p in tool.parameters if p.name == "input")
        assert input_param.type == "string"
        assert input_param.required is True
        assert input_param.description == "The input value"

        # Optional parameter with default
        count_param = next(p for p in tool.parameters if p.name == "count")
        assert count_param.type == "integer"
        assert count_param.required is False
        assert count_param.default == 10

        # Enum parameter
        mode_param = next(p for p in tool.parameters if p.name == "mode")
        assert mode_param.enum == ["fast", "slow", "auto"]
        assert mode_param.default == "auto"

    def test_examples_parsing(self, temp_tools_dir):
        """Test that examples are parsed correctly."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        assert len(tool.examples) == 1
        assert tool.examples[0]["input"]["input"] == "hello"
        assert tool.examples[0]["description"] == "Basic usage example"

    def test_instructions_parsing(self, temp_tools_dir):
        """Test that markdown instructions are extracted."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        assert "# Test Tool" in tool.instructions
        assert "unit testing purposes" in tool.instructions

    def test_openai_format_conversion(self, temp_tools_dir):
        """Test conversion to OpenAI function calling format."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        openai_tool = tool.to_openai_tool()

        assert openai_tool["type"] == "function"
        assert openai_tool["function"]["name"] == "test_tool"
        assert openai_tool["function"]["description"] == "A test tool for unit testing"

        params = openai_tool["function"]["parameters"]
        assert params["type"] == "object"
        assert "input" in params["properties"]
        assert "count" in params["properties"]
        assert params["required"] == ["input"]

        # Check enum is included
        assert params["properties"]["mode"]["enum"] == ["fast", "slow", "auto"]

    def test_get_openai_tools(self, temp_tools_dir):
        """Test getting all tools in OpenAI format."""
        loader = ToolLoader(temp_tools_dir)
        loader.load_all()
        openai_tools = loader.get_openai_tools()

        assert len(openai_tools) == 2
        names = [t["function"]["name"] for t in openai_tools]
        assert "test_tool" in names
        assert "minimal_tool" in names

    def test_malformed_no_frontmatter(self, malformed_tools_dir):
        """Test handling of files without frontmatter."""
        loader = ToolLoader(malformed_tools_dir)
        tools = loader.load_all()

        # Should not crash, but should not load the invalid tool
        assert "broken" not in tools

    def test_malformed_invalid_yaml(self, malformed_tools_dir):
        """Test handling of invalid YAML."""
        loader = ToolLoader(malformed_tools_dir)
        tools = loader.load_all()

        # Should not crash
        assert len(tools) == 0

    def test_get_tool_by_name(self, temp_tools_dir):
        """Test retrieving a specific tool by name."""
        loader = ToolLoader(temp_tools_dir)
        loader.load_all()

        tool = loader.get_tool("test_tool")
        assert tool is not None
        assert tool.name == "test_tool"

        missing = loader.get_tool("nonexistent")
        assert missing is None

    def test_to_dict(self, temp_tools_dir):
        """Test dictionary serialization."""
        loader = ToolLoader(temp_tools_dir)
        tools = loader.load_all()
        tool = tools["test_tool"]

        d = tool.to_dict()

        assert d["name"] == "test_tool"
        assert d["version"] == "1.2.3"
        assert len(d["parameters"]) == 3
        assert "openai_tool" in d
        assert d["sandbox"]["timeout"] == 60


class TestToolParameter:
    """Test suite for ToolParameter dataclass."""

    def test_parameter_defaults(self):
        """Test default values for ToolParameter."""
        param = ToolParameter(name="test", type="string")

        assert param.required is False
        assert param.description == ""
        assert param.default is None
        assert param.enum is None

    def test_parameter_with_all_fields(self):
        """Test ToolParameter with all fields set."""
        param = ToolParameter(
            name="mode",
            type="string",
            required=True,
            description="Operation mode",
            default="auto",
            enum=["auto", "manual"]
        )

        assert param.name == "mode"
        assert param.type == "string"
        assert param.required is True
        assert param.enum == ["auto", "manual"]


class TestSandboxConfig:
    """Test suite for SandboxConfig dataclass."""

    def test_sandbox_defaults(self):
        """Test default values for SandboxConfig."""
        config = SandboxConfig()

        assert config.image == "sandbox-executor:latest"
        assert config.timeout == 30
        assert config.memory == "256m"
        assert config.cpu_percent == 50
        assert config.network is False
        assert config.read_only is True
        assert config.mount_workspace is False

    def test_sandbox_custom_values(self):
        """Test SandboxConfig with custom values."""
        config = SandboxConfig(
            image="custom:v1",
            timeout=120,
            memory="1g",
            network=True
        )

        assert config.image == "custom:v1"
        assert config.timeout == 120
        assert config.memory == "1g"
        assert config.network is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
