"""
Tests for the Sandbox Executor module.

These tests verify:
- Command building for different languages
- Docker container execution
- Security constraints enforcement
- Error handling and timeouts
- Result parsing

NOTE: These tests require Docker to be running and the sandbox image to be built.
Run `docker build -t sandbox-executor:latest sandbox/` before running these tests.
"""

import pytest
import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tool_loader import ToolDefinition, ToolParameter, SandboxConfig
from executor import SandboxExecutor, ExecutionResult


def check_docker_available():
    """Check if Docker is available."""
    try:
        import docker
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def check_sandbox_image_exists():
    """Check if the sandbox image is built."""
    try:
        import docker
        client = docker.from_env()
        client.images.get("sandbox-executor:latest")
        return True
    except Exception:
        return False


# Skip all tests if Docker is not available
pytestmark = pytest.mark.skipif(
    not check_docker_available(),
    reason="Docker is not available"
)


class TestExecutionResult:
    """Test suite for ExecutionResult dataclass."""

    def test_successful_result(self):
        """Test creating a successful result."""
        result = ExecutionResult(
            success=True,
            output="Hello World",
            execution_time=0.5,
            exec_id="abc123"
        )

        assert result.success is True
        assert result.output == "Hello World"
        assert result.error == ""
        assert result.execution_time == 0.5

    def test_failed_result(self):
        """Test creating a failed result."""
        result = ExecutionResult(
            success=False,
            output="",
            error="Command not found",
            execution_time=0.1,
            exec_id="def456"
        )

        assert result.success is False
        assert result.error == "Command not found"

    def test_to_dict(self):
        """Test dictionary conversion."""
        result = ExecutionResult(
            success=True,
            output="test",
            error="",
            execution_time=1.23,
            exec_id="xyz789"
        )

        d = result.to_dict()

        assert d["success"] is True
        assert d["output"] == "test"
        assert d["execution_time"] == 1.23
        assert d["exec_id"] == "xyz789"


@pytest.mark.skipif(
    not check_sandbox_image_exists(),
    reason="Sandbox image not built. Run: docker build -t sandbox-executor:latest sandbox/"
)
class TestSandboxExecutor:
    """Test suite for SandboxExecutor class."""

    @pytest.fixture
    def executor(self):
        """Create an executor instance."""
        return SandboxExecutor()

    @pytest.fixture
    def code_execution_tool(self):
        """Create a code execution tool definition."""
        return ToolDefinition(
            name="code_execution",
            description="Execute code",
            parameters=[
                ToolParameter(name="code", type="string", required=True),
                ToolParameter(name="language", type="string", default="python"),
            ],
            sandbox=SandboxConfig(
                timeout=10,
                memory="128m",
                network=False,
                read_only=True
            )
        )

    @pytest.fixture
    def bash_tool(self):
        """Create a bash command tool definition."""
        return ToolDefinition(
            name="bash_command",
            description="Run bash commands",
            parameters=[
                ToolParameter(name="command", type="string", required=True),
            ],
            sandbox=SandboxConfig(
                timeout=10,
                memory="128m",
                network=False,
                read_only=False
            )
        )

    # --- Python Execution Tests ---

    def test_python_simple_print(self, executor, code_execution_tool):
        """Test simple Python print statement."""
        result = executor.execute(code_execution_tool, {
            "code": "print('Hello from Python!')",
            "language": "python"
        })

        assert result.success is True
        assert "Hello from Python!" in result.output
        assert result.execution_time > 0

    def test_python_math_calculation(self, executor, code_execution_tool):
        """Test Python mathematical calculation."""
        result = executor.execute(code_execution_tool, {
            "code": "import math; print(f'Pi = {math.pi:.6f}')",
            "language": "python"
        })

        assert result.success is True
        assert "3.141592" in result.output

    def test_python_numpy_available(self, executor, code_execution_tool):
        """Test that numpy is available in sandbox."""
        result = executor.execute(code_execution_tool, {
            "code": "import numpy as np; print(np.array([1,2,3]).sum())",
            "language": "python"
        })

        assert result.success is True
        assert "6" in result.output

    def test_python_pandas_available(self, executor, code_execution_tool):
        """Test that pandas is available in sandbox."""
        result = executor.execute(code_execution_tool, {
            "code": "import pandas as pd; df = pd.DataFrame({'a': [1,2,3]}); print(df.sum().values[0])",
            "language": "python"
        })

        assert result.success is True
        assert "6" in result.output

    def test_python_multiline_code(self, executor, code_execution_tool):
        """Test multiline Python code execution."""
        code = """
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

for i in range(10):
    print(fibonacci(i), end=' ')
"""
        result = executor.execute(code_execution_tool, {
            "code": code,
            "language": "python"
        })

        assert result.success is True
        assert "0 1 1 2 3 5 8 13 21 34" in result.output

    def test_python_syntax_error(self, executor, code_execution_tool):
        """Test Python syntax error handling."""
        result = executor.execute(code_execution_tool, {
            "code": "print('unclosed",
            "language": "python"
        })

        assert result.success is False
        assert "SyntaxError" in result.error or "EOL" in result.error

    def test_python_runtime_error(self, executor, code_execution_tool):
        """Test Python runtime error handling."""
        result = executor.execute(code_execution_tool, {
            "code": "1/0",
            "language": "python"
        })

        assert result.success is False
        assert "ZeroDivisionError" in result.error

    def test_python_import_error(self, executor, code_execution_tool):
        """Test handling of missing module import."""
        result = executor.execute(code_execution_tool, {
            "code": "import nonexistent_module_12345",
            "language": "python"
        })

        assert result.success is False
        assert "ModuleNotFoundError" in result.error or "No module named" in result.error

    # --- Bash Execution Tests ---

    def test_bash_simple_command(self, executor, bash_tool):
        """Test simple bash command."""
        result = executor.execute(bash_tool, {
            "command": "echo 'Hello from Bash!'"
        })

        assert result.success is True
        assert "Hello from Bash!" in result.output

    def test_bash_piped_commands(self, executor, bash_tool):
        """Test piped bash commands."""
        result = executor.execute(bash_tool, {
            "command": "echo -e 'banana\\napple\\ncherry' | sort"
        })

        assert result.success is True
        lines = result.output.strip().split('\n')
        assert lines == ['apple', 'banana', 'cherry']

    def test_bash_arithmetic(self, executor, bash_tool):
        """Test bash arithmetic."""
        result = executor.execute(bash_tool, {
            "command": "echo $((2**10))"
        })

        assert result.success is True
        assert "1024" in result.output

    def test_bash_jq_available(self, executor, bash_tool):
        """Test that jq is available."""
        result = executor.execute(bash_tool, {
            "command": "echo '{\"name\": \"test\", \"value\": 42}' | jq '.value'"
        })

        assert result.success is True
        assert "42" in result.output

    def test_bash_command_not_found(self, executor, bash_tool):
        """Test handling of non-existent command."""
        result = executor.execute(bash_tool, {
            "command": "nonexistent_command_12345"
        })

        assert result.success is False
        assert "not found" in result.error.lower() or "command not found" in result.output.lower()

    def test_bash_exit_code(self, executor, bash_tool):
        """Test that non-zero exit code is treated as failure."""
        result = executor.execute(bash_tool, {
            "command": "exit 1"
        })

        assert result.success is False

    # --- Node.js Execution Tests ---

    def test_node_simple_output(self, executor, code_execution_tool):
        """Test simple Node.js execution."""
        result = executor.execute(code_execution_tool, {
            "code": "console.log('Hello from Node!')",
            "language": "node"
        })

        assert result.success is True
        assert "Hello from Node!" in result.output

    def test_node_json_manipulation(self, executor, code_execution_tool):
        """Test Node.js JSON manipulation."""
        result = executor.execute(code_execution_tool, {
            "code": "const data = {a: 1, b: 2}; console.log(JSON.stringify(data))",
            "language": "node"
        })

        assert result.success is True
        assert '{"a":1,"b":2}' in result.output

    def test_node_syntax_error(self, executor, code_execution_tool):
        """Test Node.js syntax error handling."""
        result = executor.execute(code_execution_tool, {
            "code": "console.log('unclosed",
            "language": "node"
        })

        assert result.success is False

    # --- Security Tests ---

    def test_network_disabled(self, executor, code_execution_tool):
        """Test that network access is blocked when disabled."""
        result = executor.execute(code_execution_tool, {
            "code": "import socket; s = socket.socket(); s.connect(('8.8.8.8', 53))",
            "language": "python"
        })

        assert result.success is False
        # Should fail with network error
        assert any(x in result.error.lower() for x in ["network", "unreachable", "connect", "errno"])

    def test_filesystem_read_only(self, executor, code_execution_tool):
        """Test that filesystem is read-only."""
        result = executor.execute(code_execution_tool, {
            "code": "open('/tmp/test.txt', 'w').write('test')",
            "language": "python"
        })

        assert result.success is False
        assert "read-only" in result.error.lower() or "permission" in result.error.lower()

    def test_cannot_access_host_filesystem(self, executor, code_execution_tool):
        """Test that host filesystem is not accessible."""
        result = executor.execute(code_execution_tool, {
            "code": "import os; print(os.listdir('/home'))",
            "language": "python"
        })

        # Should succeed but only see sandbox user
        if result.success:
            assert "sandbox" in result.output
            # Should NOT see host user directories
            assert "dan" not in result.output

    def test_runs_as_non_root(self, executor, bash_tool):
        """Test that code runs as non-root user."""
        result = executor.execute(bash_tool, {
            "command": "id"
        })

        assert result.success is True
        assert "root" not in result.output
        assert "1000" in result.output  # Our sandbox user UID

    # --- Resource Limit Tests ---

    def test_memory_limit_enforced(self, executor):
        """Test that memory limit is enforced."""
        tool = ToolDefinition(
            name="code_execution",
            description="Test",
            parameters=[
                ToolParameter(name="code", type="string", required=True),
                ToolParameter(name="language", type="string", default="python"),
            ],
            sandbox=SandboxConfig(
                timeout=10,
                memory="32m",  # Very low memory limit
                network=False,
                read_only=True
            )
        )

        # Try to allocate more memory than allowed
        result = executor.execute(tool, {
            "code": "x = 'A' * (100 * 1024 * 1024)",  # 100MB
            "language": "python"
        })

        # Should fail due to OOM
        assert result.success is False

    def test_timeout_enforced(self, executor):
        """Test that timeout is enforced."""
        tool = ToolDefinition(
            name="code_execution",
            description="Test",
            parameters=[
                ToolParameter(name="code", type="string", required=True),
                ToolParameter(name="language", type="string", default="python"),
            ],
            sandbox=SandboxConfig(
                timeout=2,  # 2 second timeout
                memory="128m",
                network=False,
                read_only=True
            )
        )

        result = executor.execute(tool, {
            "code": "import time; time.sleep(60)",  # Sleep for 60 seconds
            "language": "python"
        })

        assert result.success is False
        # Execution time should be around timeout value
        assert result.execution_time < 10  # Should not take 60 seconds

    # --- Edge Cases ---

    def test_empty_output(self, executor, code_execution_tool):
        """Test code that produces no output."""
        result = executor.execute(code_execution_tool, {
            "code": "x = 1 + 1",  # No print
            "language": "python"
        })

        assert result.success is True
        assert result.output.strip() == ""

    def test_large_output(self, executor, code_execution_tool):
        """Test handling of large output."""
        result = executor.execute(code_execution_tool, {
            "code": "print('x' * 10000)",
            "language": "python"
        })

        assert result.success is True
        assert len(result.output) >= 10000

    def test_unicode_handling(self, executor, code_execution_tool):
        """Test Unicode input and output."""
        result = executor.execute(code_execution_tool, {
            "code": "print('Hello 世界 🌍 émoji')",
            "language": "python"
        })

        assert result.success is True
        assert "世界" in result.output
        assert "🌍" in result.output

    def test_unsupported_language(self, executor, code_execution_tool):
        """Test handling of unsupported language."""
        result = executor.execute(code_execution_tool, {
            "code": "print('test')",
            "language": "ruby"
        })

        assert result.success is False
        assert "unsupported" in result.error.lower()

    def test_cleanup(self, executor):
        """Test executor cleanup."""
        workspace_dir = executor.workspace_dir
        assert os.path.exists(workspace_dir)

        executor.cleanup()
        assert not os.path.exists(workspace_dir)


class TestCommandBuilding:
    """Test command building for different tool types."""

    @pytest.fixture
    def executor(self):
        return SandboxExecutor()

    def test_build_python_command(self, executor):
        tool = ToolDefinition(
            name="code_execution",
            description="",
            parameters=[],
            sandbox=SandboxConfig()
        )

        cmd = executor._build_command(tool, {
            "code": "print(1)",
            "language": "python"
        })

        assert cmd == ["python3", "-c", "print(1)"]

    def test_build_bash_command(self, executor):
        tool = ToolDefinition(
            name="bash_command",
            description="",
            parameters=[],
            sandbox=SandboxConfig()
        )

        cmd = executor._build_command(tool, {
            "command": "echo hello"
        })

        assert cmd == ["bash", "-c", "echo hello"]

    def test_build_node_command(self, executor):
        tool = ToolDefinition(
            name="code_execution",
            description="",
            parameters=[],
            sandbox=SandboxConfig()
        )

        cmd = executor._build_command(tool, {
            "code": "console.log(1)",
            "language": "node"
        })

        assert cmd == ["node", "-e", "console.log(1)"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
