---
name: bash_command
description: Execute bash shell commands for system operations, file manipulation, text processing with sed/awk/grep, and running CLI tools. Use for tasks like listing files, searching content, transforming text, or running installed utilities.
version: 1.0.0
enabled: true
sandbox:
  image: sandbox-executor:latest
  timeout: 60
  memory: 512m
  cpu_percent: 50
  network: false
  read_only: false
  mount_workspace: true
parameters:
  - name: command
    type: string
    required: true
    description: The bash command to execute
  - name: working_dir
    type: string
    required: false
    default: /home/sandbox/workspace
    description: Working directory for command execution
examples:
  - input:
      command: "ls -la"
    description: List files with details
  - input:
      command: "echo 'hello world' | tr 'a-z' 'A-Z'"
    description: Convert text to uppercase
  - input:
      command: "curl -s https://api.github.com/zen"
    description: Fetch GitHub zen message (requires network enabled)
---

# Bash Command Tool

## Purpose

Execute shell commands for system-level operations:

- File system operations (ls, find, cp, mv, rm)
- Text processing (grep, sed, awk, sort, uniq)
- Data extraction and transformation
- Running CLI tools (jq, curl, wget)

## Available Commands

### File Operations
```bash
ls, find, cp, mv, rm, mkdir, cat, head, tail, wc
```

### Text Processing
```bash
grep, sed, awk, sort, uniq, cut, tr, xargs
```

### Data Tools
```bash
jq (JSON), sqlite3 (SQL), curl, wget
```

### Media Tools
```bash
ffmpeg (audio/video), imagemagick (images)
```

## Workspace

Commands run in `/home/sandbox/workspace` by default. This directory:
- Persists within a session
- Is writable (unlike the rest of the filesystem)
- Can store intermediate files

## Examples

### Process JSON
```bash
echo '{"name":"test","value":42}' | jq '.value * 2'
```

### Find and count
```bash
find . -name "*.py" | wc -l
```

### Text transformation
```bash
echo "hello,world,foo,bar" | tr ',' '\n' | sort
```
