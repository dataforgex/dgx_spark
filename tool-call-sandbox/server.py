"""
Tool Call Sandbox API Server

FastAPI server that provides endpoints for tool discovery and execution.
Includes session-based storage for persistent data across tool calls.
"""

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Add parent directory to path for shared module
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import add_auth_middleware

from tool_loader import get_tool_loader, ToolDefinition
from executor import get_executor, ExecutionResult
from storage import get_storage_manager, execute_storage_operation


# --- Pydantic Models ---

class ExecuteRequest(BaseModel):
    """Request to execute a tool."""
    args: Dict[str, Any]
    session_id: Optional[str] = None  # Optional session for storage tools


class ExecuteResponse(BaseModel):
    """Response from tool execution."""
    success: bool
    output: str
    error: str = ""
    execution_time: float = 0.0
    exec_id: str = ""


class ToolSummary(BaseModel):
    """Summary of a tool."""
    name: str
    description: str
    version: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    tools_loaded: int
    sandbox_image: str
    active_sessions: int = 0


class StorageRequest(BaseModel):
    """Request for storage operations."""
    operation: str
    key: Optional[str] = None
    value: Optional[str] = None
    path: Optional[str] = None
    content: Optional[str] = None
    sql: Optional[str] = None
    namespace: str = "default"


class SessionInfo(BaseModel):
    """Session information."""
    session_id: str
    created_at: str
    namespaces: List[str]
    kv_keys_count: int
    kv_storage_bytes: int
    workspace_bytes: int
    has_database: bool


# --- FastAPI App ---

app = FastAPI(
    title="Tool Call Sandbox API",
    description="Execute LLM tools in sandboxed Docker containers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authentication and rate limiting (optional, enabled via DGX_API_KEY env var)
add_auth_middleware(app, skip_paths={"/tools"})


# --- Endpoints ---

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check API health and tool status."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    storage = get_storage_manager()
    return HealthResponse(
        status="healthy",
        tools_loaded=len(loader.tools),
        sandbox_image="sandbox-executor:latest",
        active_sessions=len(storage.sessions)
    )


@app.get("/api/tools", response_model=List[ToolSummary])
async def list_tools():
    """List all available tools."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    return [
        ToolSummary(name=t.name, description=t.description, version=t.version)
        for t in loader.tools.values()
    ]


@app.get("/api/tools/{tool_name}")
async def get_tool(tool_name: str):
    """Get detailed information about a tool."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    tool = loader.get_tool(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    return tool.to_dict()


@app.get("/api/tools-openai")
async def get_openai_tools():
    """Get all tools in OpenAI function calling format."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    return loader.get_openai_tools()


@app.post("/api/execute/{tool_name}", response_model=ExecuteResponse)
async def execute_tool(
    tool_name: str,
    request: ExecuteRequest,
    x_session_id: Optional[str] = Header(None)
):
    """Execute a tool with the given arguments."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    tool = loader.get_tool(tool_name)

    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")

    # Validate required parameters
    for param in tool.parameters:
        if param.required and param.name not in request.args:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required parameter: {param.name}"
            )

    # Get or create session ID
    session_id = request.session_id or x_session_id or str(uuid.uuid4())

    # Handle storage tool specially (no Docker needed)
    if tool_name == "data_storage":
        import json
        result = execute_storage_operation(session_id, **request.args)
        return ExecuteResponse(
            success=result.get("success", False),
            output=json.dumps(result, indent=2),
            error=result.get("error", ""),
            execution_time=0.0,
            exec_id=session_id[:8]
        )

    # Execute in sandbox
    executor = get_executor()
    result = executor.execute(tool, request.args)

    return ExecuteResponse(
        success=result.success,
        output=result.output,
        error=result.error,
        execution_time=result.execution_time,
        exec_id=result.exec_id
    )


@app.post("/api/reload")
async def reload_tools():
    """Reload tool definitions from disk."""
    loader = get_tool_loader(os.environ.get("TOOLS_DIR", "tools"))
    tools = loader.load_all()
    return {"status": "reloaded", "tools_loaded": len(tools)}


# --- Session & Storage Endpoints ---

@app.post("/api/sessions")
async def create_session():
    """Create a new storage session."""
    session_id = str(uuid.uuid4())
    storage = get_storage_manager()
    storage.get_or_create_session(session_id)
    return {"session_id": session_id}


@app.get("/api/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get session information."""
    storage = get_storage_manager()
    info = storage.get_session_info(session_id)
    return SessionInfo(**info)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its data."""
    storage = get_storage_manager()
    storage._destroy_session(session_id)
    return {"status": "deleted", "session_id": session_id}


@app.post("/api/storage/{session_id}")
async def storage_operation(session_id: str, request: StorageRequest):
    """Execute a storage operation for a session."""
    result = execute_storage_operation(
        session_id,
        operation=request.operation,
        key=request.key,
        value=request.value,
        path=request.path,
        content=request.content,
        sql=request.sql,
        namespace=request.namespace
    )
    return result


@app.get("/api/storage/{session_id}/keys")
async def list_keys(session_id: str, namespace: str = "default"):
    """List all keys in a session namespace."""
    storage = get_storage_manager()
    keys = storage.kv_list(session_id, namespace)
    return {"keys": keys, "namespace": namespace}


@app.get("/api/storage/{session_id}/files")
async def list_files(session_id: str, path: str = ""):
    """List files in session workspace."""
    storage = get_storage_manager()
    return storage.file_list(session_id, path)


# --- Main ---

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5176))
    uvicorn.run(app, host="0.0.0.0", port=port)
