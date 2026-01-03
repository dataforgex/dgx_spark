---
name: file_analysis
description: Analyze file contents, extract metadata, parse structured data (JSON, YAML, CSV, XML), and perform content transformations. Use when you need to understand file structure or extract specific information from files.
version: 1.0.0
enabled: true
sandbox:
  image: sandbox-executor:latest
  timeout: 30
  memory: 256m
  cpu_percent: 50
  network: false
  read_only: true
parameters:
  - name: content
    type: string
    required: true
    description: The file content to analyze (passed as string)
  - name: file_type
    type: string
    required: false
    enum: [json, yaml, csv, xml, text, auto]
    default: auto
    description: Type of file content
  - name: operation
    type: string
    required: true
    enum: [parse, validate, extract, transform, summarize]
    description: Operation to perform on the content
  - name: query
    type: string
    required: false
    description: JSONPath, XPath, or field name for extraction
examples:
  - input:
      content: '{"users": [{"name": "Alice"}, {"name": "Bob"}]}'
      file_type: json
      operation: extract
      query: "$.users[*].name"
    description: Extract all user names from JSON
  - input:
      content: "name,age\nAlice,30\nBob,25"
      file_type: csv
      operation: summarize
    description: Get CSV summary statistics
---

# File Analysis Tool

## Purpose

Parse, validate, and analyze structured file contents without writing code.

## Operations

### parse
Parse content and return structured representation.

### validate
Check if content is valid for the specified format.

### extract
Extract specific values using queries:
- JSON: JSONPath expressions (`$.field.subfield`)
- XML: XPath expressions (`//element/@attr`)
- CSV: Column names

### transform
Convert between formats or restructure data.

### summarize
Generate summary statistics and overview.

## Supported Formats

| Format | Auto-detect | Query Language |
|--------|-------------|----------------|
| JSON | Yes | JSONPath |
| YAML | Yes | JSONPath |
| CSV | Yes | Column names |
| XML | Yes | XPath |
| Text | Fallback | Regex |

## Implementation Note

This tool uses Python internally:
- `json` / `pyyaml` for JSON/YAML
- `pandas` for CSV
- `lxml` for XML
- `jsonpath-ng` for JSONPath queries
