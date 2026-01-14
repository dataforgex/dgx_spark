"""
Sandboxed Executor - Runs tools in isolated Docker containers

Security features:
- Seccomp profile restricts syscalls
- Dangerous Python imports blocked
- No network access by default
- Read-only filesystem option
- Non-root user execution
- Resource limits (CPU, memory, timeout)
"""

import docker
import uuid
import time
import json
import tempfile
import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from tool_loader import ToolDefinition, SandboxConfig

# Path to seccomp profile
SECCOMP_PROFILE_PATH = Path(__file__).parent / "sandbox" / "seccomp-profile.json"

# Dangerous Python imports that should be blocked
DANGEROUS_IMPORTS = [
    "subprocess",
    "os.system",
    "os.popen",
    "os.spawn",
    "commands",
    "pty",
    "pexpect",
    "paramiko",
    "fabric",
    "socket",  # Allow only via web_fetch tool
    "ctypes",
    "cffi",
    "multiprocessing",
    "threading",  # Allow for now, can be restricted
    "__builtins__",
    "builtins",
    "importlib",
    "pickle",  # Can execute arbitrary code
    "marshal",
    "shelve",
    "tempfile",
    "shutil.rmtree",
    "os.remove",
    "os.unlink",
    "os.rmdir",
]

# Regex patterns for detecting dangerous code
DANGEROUS_PATTERNS = [
    r"eval\s*\(",
    r"exec\s*\(",
    r"compile\s*\(",
    r"__import__\s*\(",
    r"open\s*\([^)]*['\"][wa]",  # open() with write mode
    r"getattr\s*\(\s*__builtins__",
    r"globals\s*\(\s*\)",
    r"locals\s*\(\s*\)",
]


def check_dangerous_code(code: str, language: str) -> Tuple[bool, str]:
    """
    Check if code contains dangerous patterns.

    Returns:
        Tuple of (is_safe, reason)
    """
    if language != "python":
        # For bash, we rely on container isolation
        return True, ""

    # Check for dangerous imports
    for dangerous in DANGEROUS_IMPORTS:
        if dangerous in code:
            # More precise check to avoid false positives
            patterns = [
                rf"import\s+{re.escape(dangerous)}",
                rf"from\s+{re.escape(dangerous.split('.')[0])}\s+import",
                rf"__import__\s*\(\s*['\"]{ re.escape(dangerous)}['\"]",
            ]
            for pattern in patterns:
                if re.search(pattern, code):
                    return False, f"Blocked import: {dangerous}"

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, code, re.IGNORECASE):
            return False, f"Blocked pattern detected"

    return True, ""


@dataclass
class ExecutionResult:
    """Result of a tool execution."""
    success: bool
    output: str
    error: str = ""
    execution_time: float = 0.0
    exec_id: str = ""

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "execution_time": self.execution_time,
            "exec_id": self.exec_id
        }


class SandboxExecutor:
    """Executes tools in sandboxed Docker containers."""

    def __init__(self):
        self.client = docker.from_env()
        self.workspace_dir = tempfile.mkdtemp(prefix="sandbox_")

    def _build_command(self, tool: ToolDefinition, args: Dict[str, Any]) -> list:
        """Build the command to run based on tool type."""
        tool_name = tool.name

        if tool_name == "code_execution":
            code = args.get("code", "")
            language = args.get("language", "python")

            if language == "python":
                return ["python3", "-c", code]
            elif language == "bash":
                return ["bash", "-c", code]
            elif language == "node":
                return ["node", "-e", code]
            else:
                raise ValueError(f"Unsupported language: {language}")

        elif tool_name == "bash_command":
            command = args.get("command", "")
            return ["bash", "-c", command]

        elif tool_name == "file_analysis":
            # Build a Python script for file analysis
            content = args.get("content", "")
            file_type = args.get("file_type", "auto")
            operation = args.get("operation", "parse")
            query = args.get("query", "")

            script = self._build_file_analysis_script(content, file_type, operation, query)
            return ["python3", "-c", script]

        elif tool_name == "web_fetch":
            # Build a Python script for web fetching
            url = args.get("url", "")
            method = args.get("method", "GET")
            headers = args.get("headers", {})
            body = args.get("body", "")
            extract = args.get("extract", "text")
            selector = args.get("selector", "")

            script = self._build_web_fetch_script(url, method, headers, body, extract, selector)
            return ["python3", "-c", script]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _build_file_analysis_script(self, content: str, file_type: str,
                                     operation: str, query: str) -> str:
        """Build Python script for file analysis."""
        # Escape content for Python string
        content_escaped = content.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")

        return f'''
import json
import yaml
import csv
import io

content = \'\'\'{content_escaped}\'\'\'
file_type = "{file_type}"
operation = "{operation}"
query = "{query}"

def detect_type(c):
    c = c.strip()
    if c.startswith("{{") or c.startswith("["):
        return "json"
    if c.startswith("---") or ": " in c.split("\\n")[0]:
        return "yaml"
    if "," in c.split("\\n")[0]:
        return "csv"
    return "text"

if file_type == "auto":
    file_type = detect_type(content)

result = {{"type": file_type, "operation": operation}}

try:
    if file_type == "json":
        data = json.loads(content)
    elif file_type == "yaml":
        data = yaml.safe_load(content)
    elif file_type == "csv":
        reader = csv.DictReader(io.StringIO(content))
        data = list(reader)
    else:
        data = content

    if operation == "parse":
        result["data"] = data
    elif operation == "validate":
        result["valid"] = True
    elif operation == "summarize":
        if isinstance(data, list):
            result["count"] = len(data)
            if data:
                result["fields"] = list(data[0].keys()) if isinstance(data[0], dict) else None
        elif isinstance(data, dict):
            result["keys"] = list(data.keys())
        else:
            result["length"] = len(str(data))
    elif operation == "extract" and query:
        # Simple path extraction
        parts = query.replace("$.", "").split(".")
        current = data
        for part in parts:
            if "[" in part:
                key, idx = part.rstrip("]").split("[")
                current = current[key] if key else current
                if idx == "*":
                    current = [item for item in current]
                else:
                    current = current[int(idx)]
            else:
                current = current[part]
        result["extracted"] = current

    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    print(json.dumps({{"error": str(e), "operation": operation}}))
'''

    def _build_web_fetch_script(self, url: str, method: str, headers: Dict,
                                 body: str, extract: str, selector: str) -> str:
        """Build Python script for web fetching."""
        headers_json = json.dumps(headers)

        return f'''
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

url = "{url}"
method = "{method}"
headers = json.loads(\'{headers_json}\')
body = """{body}"""
extract = "{extract}"
selector = "{selector}"

try:
    if method == "GET":
        resp = requests.get(url, headers=headers, timeout=25)
    elif method == "POST":
        resp = requests.post(url, headers=headers, data=body, timeout=25)
    elif method == "PUT":
        resp = requests.put(url, headers=headers, data=body, timeout=25)
    elif method == "DELETE":
        resp = requests.delete(url, headers=headers, timeout=25)

    result = {{"status": resp.status_code, "url": url}}

    if extract == "json":
        result["data"] = resp.json()
    elif extract == "html":
        result["html"] = resp.text[:50000]  # Limit size
    elif extract == "text":
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        result["text"] = soup.get_text(separator="\\n", strip=True)[:20000]
    elif extract == "links":
        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.select(selector) if selector else soup.find_all("a", href=True)
        links = []
        for el in elements[:100]:
            href = el.get("href", "")
            if href:
                links.append({{
                    "text": el.get_text(strip=True)[:100],
                    "href": urljoin(url, href)
                }})
        result["links"] = links
    elif extract == "images":
        soup = BeautifulSoup(resp.text, "html.parser")
        elements = soup.select(selector) if selector else soup.find_all("img", src=True)
        result["images"] = [urljoin(url, img.get("src", "")) for img in elements[:50]]
    elif extract == "meta":
        soup = BeautifulSoup(resp.text, "html.parser")
        result["meta"] = {{
            "title": soup.title.string if soup.title else None,
            "description": soup.find("meta", attrs={{"name": "description"}})["content"] if soup.find("meta", attrs={{"name": "description"}}) else None,
        }}

    print(json.dumps(result, indent=2, default=str))

except Exception as e:
    print(json.dumps({{"error": str(e), "url": url}}))
'''

    def execute(self, tool: ToolDefinition, args: Dict[str, Any]) -> ExecutionResult:
        """Execute a tool in a sandboxed container."""
        exec_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        try:
            # Check for dangerous code patterns before execution
            if tool.name == "code_execution":
                code = args.get("code", "")
                language = args.get("language", "python")
                is_safe, reason = check_dangerous_code(code, language)
                if not is_safe:
                    return ExecutionResult(
                        success=False,
                        output="",
                        error=f"Security violation: {reason}",
                        execution_time=0.0,
                        exec_id=exec_id
                    )

            cmd = self._build_command(tool, args)
            sandbox = tool.sandbox

            # Parse memory limit
            mem_limit = sandbox.memory

            # Calculate CPU quota (percentage to Docker's 100000 period)
            cpu_quota = int(sandbox.cpu_percent * 1000)

            # Build security options
            security_opts = ["no-new-privileges"]

            # Add seccomp profile if available
            if SECCOMP_PROFILE_PATH.exists():
                with open(SECCOMP_PROFILE_PATH) as f:
                    seccomp_json = f.read()
                security_opts.append(f"seccomp={seccomp_json}")

            # Build container config
            container_config = {
                "image": sandbox.image,
                "command": cmd,
                "remove": True,
                "mem_limit": mem_limit,
                "cpu_period": 100000,
                "cpu_quota": cpu_quota,
                "user": "1000:1000",
                "security_opt": security_opts,
                "stdout": True,
                "stderr": True,
                "cap_drop": ["ALL"],  # Drop all capabilities
                "pids_limit": 100,     # Limit number of processes
                "environment": {
                    "MPLCONFIGDIR": "/tmp",  # Matplotlib config dir (writable)
                    "HOME": "/tmp",  # Some libs need writable HOME
                },
            }

            # Network setting
            if not sandbox.network:
                container_config["network_disabled"] = True

            # Read-only filesystem
            if sandbox.read_only:
                container_config["read_only"] = True
                # Add tmpfs for /tmp when read-only
                container_config["tmpfs"] = {"/tmp": "size=64m,mode=1777"}

            # Mount workspace if needed
            if sandbox.mount_workspace:
                container_config["volumes"] = {
                    self.workspace_dir: {"bind": "/home/sandbox/workspace", "mode": "rw"}
                }

            # Run container with timeout using detached mode
            try:
                # Start container in detached mode
                container_config["detach"] = True
                container_config["remove"] = False  # Don't auto-remove, we need logs

                container = self.client.containers.run(**container_config)

                try:
                    # Wait for container with timeout
                    result = container.wait(timeout=sandbox.timeout)
                    exit_code = result.get("StatusCode", 1)

                    # Get logs
                    stdout = container.logs(stdout=True, stderr=False).decode("utf-8")
                    stderr = container.logs(stdout=False, stderr=True).decode("utf-8")

                    execution_time = time.time() - start_time

                    if exit_code == 0:
                        return ExecutionResult(
                            success=True,
                            output=stdout,
                            error=stderr,
                            execution_time=execution_time,
                            exec_id=exec_id
                        )
                    else:
                        return ExecutionResult(
                            success=False,
                            output=stdout,
                            error=stderr or f"Exit code: {exit_code}",
                            execution_time=execution_time,
                            exec_id=exec_id
                        )
                except Exception as wait_error:
                    # Timeout or other error - kill the container
                    execution_time = time.time() - start_time
                    try:
                        container.kill()
                    except Exception:
                        pass
                    return ExecutionResult(
                        success=False,
                        output="",
                        error=f"Timeout after {sandbox.timeout}s: {str(wait_error)}",
                        execution_time=execution_time,
                        exec_id=exec_id
                    )
                finally:
                    # Always remove container
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

            except docker.errors.ContainerError as e:
                execution_time = time.time() - start_time
                stderr = e.stderr.decode("utf-8") if e.stderr else str(e)
                return ExecutionResult(
                    success=False,
                    output="",
                    error=stderr,
                    execution_time=execution_time,
                    exec_id=exec_id
                )

        except Exception as e:
            execution_time = time.time() - start_time
            return ExecutionResult(
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
                exec_id=exec_id
            )

    def cleanup(self):
        """Clean up workspace directory."""
        import shutil
        if os.path.exists(self.workspace_dir):
            shutil.rmtree(self.workspace_dir)


# Singleton instance
_executor: Optional[SandboxExecutor] = None


def get_executor() -> SandboxExecutor:
    """Get or create the executor singleton."""
    global _executor
    if _executor is None:
        _executor = SandboxExecutor()
    return _executor


if __name__ == "__main__":
    from tool_loader import ToolLoader

    # Test execution
    loader = ToolLoader("tools")
    tools = loader.load_all()

    executor = SandboxExecutor()

    # Test code execution
    if "code_execution" in tools:
        result = executor.execute(
            tools["code_execution"],
            {"code": "print('Hello from sandbox!')", "language": "python"}
        )
        print(f"Code execution: {result.to_dict()}")
