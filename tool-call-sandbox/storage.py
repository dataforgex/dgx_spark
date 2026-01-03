"""
Storage Manager - Manages persistent data storage for sandbox tools.

Provides:
- Key-value storage (in-memory + file-backed)
- SQLite database access
- File storage in workspace
- Session management
"""

import os
import json
import sqlite3
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading


@dataclass
class Session:
    """Represents a storage session."""
    session_id: str
    created_at: datetime
    workspace_dir: str
    data: Dict[str, Dict[str, str]] = field(default_factory=dict)  # namespace -> key -> value
    db_path: Optional[str] = None

    def get_db_connection(self) -> sqlite3.Connection:
        """Get SQLite connection for this session."""
        if self.db_path is None:
            self.db_path = os.path.join(self.workspace_dir, "session.db")
        return sqlite3.connect(self.db_path)


class StorageManager:
    """
    Manages storage across sessions.

    Storage options:
    1. In-memory key-value (fast, per-session)
    2. SQLite database (structured queries)
    3. File storage (workspace directory)
    """

    def __init__(self, base_workspace: str = "/tmp/sandbox_workspaces"):
        self.base_workspace = Path(base_workspace)
        self.base_workspace.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, Session] = {}
        self.lock = threading.Lock()

        # Session expiry (clean up old sessions)
        self.session_ttl = timedelta(hours=24)

    def get_or_create_session(self, session_id: str) -> Session:
        """Get existing session or create new one."""
        with self.lock:
            if session_id not in self.sessions:
                workspace = self.base_workspace / session_id
                workspace.mkdir(parents=True, exist_ok=True)

                self.sessions[session_id] = Session(
                    session_id=session_id,
                    created_at=datetime.now(),
                    workspace_dir=str(workspace),
                    data={"default": {}}
                )

            return self.sessions[session_id]

    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        now = datetime.now()
        with self.lock:
            expired = [
                sid for sid, session in self.sessions.items()
                if now - session.created_at > self.session_ttl
            ]
            for sid in expired:
                self._destroy_session(sid)

    def _destroy_session(self, session_id: str):
        """Destroy a session and its data."""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            # Clean up workspace directory
            if os.path.exists(session.workspace_dir):
                shutil.rmtree(session.workspace_dir, ignore_errors=True)
            del self.sessions[session_id]

    # --- Key-Value Operations ---

    def kv_set(self, session_id: str, key: str, value: str,
               namespace: str = "default") -> bool:
        """Set a key-value pair."""
        session = self.get_or_create_session(session_id)
        if namespace not in session.data:
            session.data[namespace] = {}
        session.data[namespace][key] = value
        return True

    def kv_get(self, session_id: str, key: str,
               namespace: str = "default") -> Optional[str]:
        """Get a value by key."""
        session = self.get_or_create_session(session_id)
        return session.data.get(namespace, {}).get(key)

    def kv_delete(self, session_id: str, key: str,
                  namespace: str = "default") -> bool:
        """Delete a key."""
        session = self.get_or_create_session(session_id)
        if namespace in session.data and key in session.data[namespace]:
            del session.data[namespace][key]
            return True
        return False

    def kv_list(self, session_id: str, namespace: str = "default") -> List[str]:
        """List all keys in a namespace."""
        session = self.get_or_create_session(session_id)
        return list(session.data.get(namespace, {}).keys())

    # --- SQLite Operations ---

    def db_query(self, session_id: str, sql: str) -> Dict[str, Any]:
        """Execute a SQL query."""
        session = self.get_or_create_session(session_id)

        try:
            conn = session.get_db_connection()
            cursor = conn.cursor()

            # Determine if it's a SELECT query
            sql_lower = sql.strip().lower()
            is_select = sql_lower.startswith("select")

            cursor.execute(sql)

            if is_select:
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = {
                    "success": True,
                    "columns": columns,
                    "rows": [dict(zip(columns, row)) for row in rows],
                    "row_count": len(rows)
                }
            else:
                conn.commit()
                result = {
                    "success": True,
                    "rows_affected": cursor.rowcount
                }

            conn.close()
            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    # --- File Operations ---

    def file_write(self, session_id: str, path: str, content: str) -> Dict[str, Any]:
        """Write content to a file in the workspace."""
        session = self.get_or_create_session(session_id)

        # Normalize and validate path
        safe_path = self._safe_path(session.workspace_dir, path)
        if safe_path is None:
            return {"success": False, "error": "Invalid path"}

        try:
            # Create parent directories
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)

            with open(safe_path, 'w', encoding='utf-8') as f:
                f.write(content)

            return {
                "success": True,
                "path": path,
                "size": len(content)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_read(self, session_id: str, path: str) -> Dict[str, Any]:
        """Read content from a file in the workspace."""
        session = self.get_or_create_session(session_id)

        safe_path = self._safe_path(session.workspace_dir, path)
        if safe_path is None:
            return {"success": False, "error": "Invalid path"}

        try:
            with open(safe_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return {
                "success": True,
                "path": path,
                "content": content,
                "size": len(content)
            }
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {path}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def file_list(self, session_id: str, path: str = "") -> Dict[str, Any]:
        """List files in a directory."""
        session = self.get_or_create_session(session_id)

        safe_path = self._safe_path(session.workspace_dir, path)
        if safe_path is None:
            return {"success": False, "error": "Invalid path"}

        try:
            if not os.path.exists(safe_path):
                return {"success": True, "files": [], "directories": []}

            files = []
            directories = []

            for entry in os.scandir(safe_path):
                if entry.is_file():
                    files.append({
                        "name": entry.name,
                        "size": entry.stat().st_size
                    })
                elif entry.is_dir():
                    directories.append(entry.name)

            return {
                "success": True,
                "path": path or "/",
                "files": files,
                "directories": directories
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _safe_path(self, workspace: str, path: str) -> Optional[str]:
        """Validate and resolve a path safely within workspace."""
        if not path:
            return workspace

        # Prevent path traversal
        path = path.lstrip("/")
        full_path = os.path.normpath(os.path.join(workspace, path))

        # Ensure path is within workspace
        if not full_path.startswith(os.path.normpath(workspace)):
            return None

        return full_path

    # --- Session Info ---

    def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """Get information about a session."""
        session = self.get_or_create_session(session_id)

        # Calculate storage usage
        total_kv_size = sum(
            sum(len(v) for v in ns.values())
            for ns in session.data.values()
        )

        workspace_size = 0
        if os.path.exists(session.workspace_dir):
            for dirpath, dirnames, filenames in os.walk(session.workspace_dir):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    workspace_size += os.path.getsize(fp)

        return {
            "session_id": session_id,
            "created_at": session.created_at.isoformat(),
            "namespaces": list(session.data.keys()),
            "kv_keys_count": sum(len(ns) for ns in session.data.values()),
            "kv_storage_bytes": total_kv_size,
            "workspace_bytes": workspace_size,
            "has_database": session.db_path is not None and os.path.exists(session.db_path or "")
        }


# Singleton instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get or create the storage manager singleton."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


def execute_storage_operation(session_id: str, operation: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a storage operation.

    This is the main entry point for the data_storage tool.
    """
    manager = get_storage_manager()
    namespace = kwargs.get("namespace", "default")

    try:
        if operation == "set":
            key = kwargs.get("key")
            value = kwargs.get("value")
            if not key or value is None:
                return {"success": False, "error": "Missing key or value"}
            manager.kv_set(session_id, key, value, namespace)
            return {"success": True, "key": key}

        elif operation == "get":
            key = kwargs.get("key")
            if not key:
                return {"success": False, "error": "Missing key"}
            value = manager.kv_get(session_id, key, namespace)
            if value is None:
                return {"success": False, "error": f"Key not found: {key}"}
            return {"success": True, "key": key, "value": value}

        elif operation == "delete":
            key = kwargs.get("key")
            if not key:
                return {"success": False, "error": "Missing key"}
            deleted = manager.kv_delete(session_id, key, namespace)
            return {"success": deleted, "key": key}

        elif operation == "list":
            keys = manager.kv_list(session_id, namespace)
            return {"success": True, "keys": keys, "count": len(keys)}

        elif operation == "query":
            sql = kwargs.get("sql")
            if not sql:
                return {"success": False, "error": "Missing SQL query"}
            return manager.db_query(session_id, sql)

        elif operation == "file_write":
            path = kwargs.get("path")
            content = kwargs.get("content")
            if not path or content is None:
                return {"success": False, "error": "Missing path or content"}
            return manager.file_write(session_id, path, content)

        elif operation == "file_read":
            path = kwargs.get("path")
            if not path:
                return {"success": False, "error": "Missing path"}
            return manager.file_read(session_id, path)

        elif operation == "file_list":
            path = kwargs.get("path", "")
            return manager.file_list(session_id, path)

        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    # Test the storage manager
    manager = StorageManager("/tmp/test_storage")

    session_id = "test_session"

    # Test key-value
    print("=== Key-Value Storage ===")
    manager.kv_set(session_id, "name", "Alice", "users")
    manager.kv_set(session_id, "age", "30", "users")
    print(f"Get name: {manager.kv_get(session_id, 'name', 'users')}")
    print(f"List keys: {manager.kv_list(session_id, 'users')}")

    # Test SQLite
    print("\n=== SQLite Storage ===")
    result = manager.db_query(session_id, "CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, name TEXT)")
    print(f"Create table: {result}")
    result = manager.db_query(session_id, "INSERT INTO items (name) VALUES ('Apple')")
    print(f"Insert: {result}")
    result = manager.db_query(session_id, "SELECT * FROM items")
    print(f"Select: {result}")

    # Test file storage
    print("\n=== File Storage ===")
    result = manager.file_write(session_id, "test/data.json", '{"hello": "world"}')
    print(f"Write: {result}")
    result = manager.file_read(session_id, "test/data.json")
    print(f"Read: {result}")
    result = manager.file_list(session_id, "test")
    print(f"List: {result}")

    # Session info
    print("\n=== Session Info ===")
    print(manager.get_session_info(session_id))
