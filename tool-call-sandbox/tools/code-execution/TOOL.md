---
name: code_execution
description: Execute Python, JavaScript, or bash code in a secure sandboxed environment. Use this for calculations, data processing, file manipulation, or running scripts. The environment includes numpy, pandas, matplotlib, requests, and common utilities.
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
  - name: code
    type: string
    required: true
    description: The code to execute
  - name: language
    type: string
    required: false
    enum: [python, bash, node]
    default: python
    description: Programming language (python, bash, or node)
examples:
  - input:
      code: "print(sum(range(1, 101)))"
      language: python
    description: Calculate sum of numbers 1-100
  - input:
      code: "import pandas as pd; df = pd.DataFrame({'a': [1,2,3]}); print(df.describe())"
      language: python
    description: Create and analyze a DataFrame
  - input:
      code: "echo $((2**10))"
      language: bash
    description: Calculate 2^10 using bash
---

# Code Execution Tool

## Purpose

Execute arbitrary code in a secure, isolated Docker container. This tool is ideal for:

- Mathematical calculations
- Data analysis and transformation
- Text processing
- File format conversions
- Quick prototyping

## Available Libraries

### Python
- **Data**: numpy, pandas, scipy, scikit-learn
- **Visualization**: matplotlib, seaborn
- **Web**: requests, httpx, beautifulsoup4
- **Utilities**: pillow, pyyaml, rich, tabulate

### Node.js
- lodash, axios, cheerio, dayjs

### Bash
- Standard Unix utilities (curl, jq, wget, git, etc.)
- sqlite3, imagemagick, ffmpeg

## Security Notes

- Network access is disabled by default
- Filesystem is read-only
- Execution timeout: 30 seconds
- Memory limit: 256MB
- Runs as non-root user

## Output Format

Returns JSON with:
```json
{
  "success": true,
  "output": "stdout content here",
  "error": "stderr content if any",
  "execution_time": 0.123
}
```
