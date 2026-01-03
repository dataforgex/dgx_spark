---
name: data_storage
description: Store and retrieve data that persists across tool calls within a session. Use for saving intermediate results, caching API responses, storing user preferences, or maintaining state. Supports key-value storage, files, and SQLite databases.
version: 1.0.0
enabled: true
sandbox:
  image: sandbox-executor:latest
  timeout: 30
  memory: 256m
  network: false
  read_only: false
  mount_workspace: true
parameters:
  - name: operation
    type: string
    required: true
    enum: [get, set, delete, list, query, file_read, file_write, file_list]
    description: "Storage operation: get/set/delete for key-value, query for SQLite, file_* for files"
  - name: key
    type: string
    required: false
    description: Key name for key-value operations
  - name: value
    type: string
    required: false
    description: Value to store (for set operation)
  - name: path
    type: string
    required: false
    description: File path for file operations (relative to workspace)
  - name: content
    type: string
    required: false
    description: Content for file_write operation
  - name: sql
    type: string
    required: false
    description: SQL query for query operation (uses SQLite)
  - name: namespace
    type: string
    required: false
    default: default
    description: Namespace to organize data (like a folder)
examples:
  - input:
      operation: set
      key: user_preference
      value: '{"theme": "dark", "language": "en"}'
    description: Store a JSON value
  - input:
      operation: get
      key: user_preference
    description: Retrieve a stored value
  - input:
      operation: query
      sql: "SELECT * FROM data WHERE key LIKE 'user_%'"
    description: Query stored data with SQL
  - input:
      operation: file_write
      path: results/analysis.json
      content: '{"result": 42}'
    description: Write data to a file
---

# Data Storage Tool

## Purpose

Persist and retrieve data across tool calls within a conversation session. This enables:

- Saving intermediate calculation results
- Caching expensive API responses
- Storing user preferences
- Building up datasets incrementally
- Maintaining conversation state

## Storage Backends

### 1. Key-Value Storage
Fast, simple storage for JSON-serializable data.

```
operation: set, key: "my_key", value: "my_value"
operation: get, key: "my_key"
operation: delete, key: "my_key"
operation: list  # List all keys
```

### 2. SQLite Database
Full SQL support for structured data queries.

```
operation: query, sql: "CREATE TABLE users (id INTEGER, name TEXT)"
operation: query, sql: "INSERT INTO users VALUES (1, 'Alice')"
operation: query, sql: "SELECT * FROM users WHERE id = 1"
```

### 3. File Storage
Read and write files in the workspace directory.

```
operation: file_write, path: "data/output.txt", content: "Hello"
operation: file_read, path: "data/output.txt"
operation: file_list, path: "data/"
```

## Namespaces

Use namespaces to organize data:

```
operation: set, namespace: "session_123", key: "state", value: "..."
operation: set, namespace: "cache", key: "api_response", value: "..."
```

## Data Lifecycle

- **Session Storage**: Data persists for the duration of the sandbox session
- **Workspace Files**: Files persist in the mounted workspace directory
- **Database**: SQLite database stored in workspace, queryable between calls

## Security Notes

- Data is isolated per session
- No access to host filesystem
- All data stored in sandboxed workspace
- Keys and values are stored as strings (serialize complex objects as JSON)
