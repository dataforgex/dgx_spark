"""
Tool Loader - Loads tool definitions from TOOL.md files (skills-like pattern)

This module discovers and parses tool definitions using YAML frontmatter,
similar to how Claude Skills work.
"""

import os
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ToolParameter:
    """Represents a tool parameter definition."""
    name: str
    type: str
    required: bool = False
    description: str = ""
    default: Any = None
    enum: Optional[List[str]] = None


@dataclass
class SandboxConfig:
    """Sandbox execution configuration."""
    image: str = "sandbox-executor:latest"
    timeout: int = 30
    memory: str = "256m"
    cpu_percent: int = 50
    network: bool = False
    read_only: bool = True
    mount_workspace: bool = False


@dataclass
class ToolDefinition:
    """Complete tool definition loaded from TOOL.md."""
    name: str
    description: str
    version: str = "1.0.0"
    enabled: bool = True
    parameters: List[ToolParameter] = field(default_factory=list)
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    examples: List[Dict] = field(default_factory=list)
    instructions: str = ""  # Markdown content after frontmatter
    path: str = ""  # Path to TOOL.md file

    def to_openai_tool(self) -> Dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            if param.default is not None:
                prop["default"] = param.default

            properties[param.name] = prop
            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type,
                    "required": p.required,
                    "description": p.description,
                    "default": p.default,
                    "enum": p.enum
                }
                for p in self.parameters
            ],
            "sandbox": {
                "image": self.sandbox.image,
                "timeout": self.sandbox.timeout,
                "memory": self.sandbox.memory,
                "cpu_percent": self.sandbox.cpu_percent,
                "network": self.sandbox.network,
                "read_only": self.sandbox.read_only,
                "mount_workspace": self.sandbox.mount_workspace
            },
            "examples": self.examples,
            "openai_tool": self.to_openai_tool()
        }


class ToolLoader:
    """Discovers and loads tool definitions from TOOL.md files."""

    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL
    )

    def __init__(self, tools_dir: str = "tools"):
        self.tools_dir = Path(tools_dir)
        self.tools: Dict[str, ToolDefinition] = {}

    def discover_tools(self) -> List[str]:
        """Find all TOOL.md files in the tools directory."""
        tool_files = []
        if not self.tools_dir.exists():
            return tool_files

        for tool_dir in self.tools_dir.iterdir():
            if tool_dir.is_dir():
                tool_file = tool_dir / "TOOL.md"
                if tool_file.exists():
                    tool_files.append(str(tool_file))

        return tool_files

    def parse_tool_file(self, file_path: str) -> Optional[ToolDefinition]:
        """Parse a TOOL.md file and return a ToolDefinition."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            match = self.FRONTMATTER_PATTERN.match(content)
            if not match:
                print(f"Warning: No YAML frontmatter found in {file_path}")
                return None

            frontmatter_yaml = match.group(1)
            instructions = match.group(2).strip()

            # Parse YAML frontmatter
            metadata = yaml.safe_load(frontmatter_yaml)
            if not metadata:
                return None

            # Parse parameters
            parameters = []
            for param_data in metadata.get('parameters', []):
                parameters.append(ToolParameter(
                    name=param_data.get('name', ''),
                    type=param_data.get('type', 'string'),
                    required=param_data.get('required', False),
                    description=param_data.get('description', ''),
                    default=param_data.get('default'),
                    enum=param_data.get('enum')
                ))

            # Parse sandbox config
            sandbox_data = metadata.get('sandbox', {})
            sandbox = SandboxConfig(
                image=sandbox_data.get('image', 'sandbox-executor:latest'),
                timeout=sandbox_data.get('timeout', 30),
                memory=sandbox_data.get('memory', '256m'),
                cpu_percent=sandbox_data.get('cpu_percent', 50),
                network=sandbox_data.get('network', False),
                read_only=sandbox_data.get('read_only', True),
                mount_workspace=sandbox_data.get('mount_workspace', False)
            )

            return ToolDefinition(
                name=metadata.get('name', ''),
                description=metadata.get('description', ''),
                version=metadata.get('version', '1.0.0'),
                enabled=metadata.get('enabled', True),
                parameters=parameters,
                sandbox=sandbox,
                examples=metadata.get('examples', []),
                instructions=instructions,
                path=file_path
            )

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def load_all(self) -> Dict[str, ToolDefinition]:
        """Load all tools from the tools directory."""
        self.tools = {}

        for tool_file in self.discover_tools():
            tool = self.parse_tool_file(tool_file)
            if tool and tool.enabled:
                self.tools[tool.name] = tool
                print(f"Loaded tool: {tool.name} (v{tool.version})")

        return self.tools

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_openai_tools(self) -> List[Dict]:
        """Get all tools in OpenAI function calling format."""
        return [tool.to_openai_tool() for tool in self.tools.values()]

    def get_tools_summary(self) -> List[Dict]:
        """Get a summary of all tools (name + description only)."""
        return [
            {"name": t.name, "description": t.description, "version": t.version}
            for t in self.tools.values()
        ]


# Singleton instance
_loader: Optional[ToolLoader] = None


def get_tool_loader(tools_dir: str = "tools") -> ToolLoader:
    """Get or create the tool loader singleton."""
    global _loader
    if _loader is None:
        _loader = ToolLoader(tools_dir)
        _loader.load_all()
    return _loader


if __name__ == "__main__":
    # Test the loader
    loader = ToolLoader("tools")
    tools = loader.load_all()

    print(f"\nLoaded {len(tools)} tools:")
    for name, tool in tools.items():
        print(f"\n--- {name} ---")
        print(f"Description: {tool.description[:80]}...")
        print(f"Parameters: {[p.name for p in tool.parameters]}")
        print(f"Sandbox: network={tool.sandbox.network}, timeout={tool.sandbox.timeout}s")
