---
name: web_fetch
description: Fetch content from URLs and extract information. Use for retrieving web pages, API responses, downloading files, or scraping specific content. Supports HTML parsing and JSON APIs.
version: 1.0.0
enabled: true
sandbox:
  image: sandbox-executor:latest
  timeout: 30
  memory: 256m
  cpu_percent: 50
  network: true  # Network required for this tool
  read_only: true
parameters:
  - name: url
    type: string
    required: true
    description: The URL to fetch
  - name: method
    type: string
    required: false
    enum: [GET, POST, PUT, DELETE]
    default: GET
    description: HTTP method
  - name: headers
    type: object
    required: false
    description: HTTP headers as key-value pairs
  - name: body
    type: string
    required: false
    description: Request body for POST/PUT
  - name: extract
    type: string
    required: false
    enum: [text, json, html, links, images, meta]
    default: text
    description: What to extract from response
  - name: selector
    type: string
    required: false
    description: CSS selector for HTML extraction
examples:
  - input:
      url: "https://api.github.com/users/octocat"
      extract: json
    description: Fetch GitHub user data as JSON
  - input:
      url: "https://news.ycombinator.com"
      extract: links
      selector: ".titleline a"
    description: Extract Hacker News headlines
---

# Web Fetch Tool

## Purpose

Retrieve and process content from the web:

- Fetch API responses (JSON, XML)
- Scrape web pages
- Extract specific elements (links, images, text)
- Make authenticated requests

## Extract Modes

### text
Returns plain text content, HTML stripped.

### json
Parses response as JSON, returns structured data.

### html
Returns raw HTML content.

### links
Extracts all links, optionally filtered by CSS selector.

### images
Extracts all image URLs from the page.

### meta
Extracts page metadata (title, description, OpenGraph tags).

## CSS Selectors

When `extract` is `links`, `images`, or `html`, use `selector` to target specific elements:

```
# Class selector
.article-title

# ID selector
#main-content

# Attribute selector
a[href^="https://"]

# Nested selector
div.content > p.intro
```

## Security

- Requests timeout after 30 seconds
- Only HTTP/HTTPS protocols allowed
- Response size limited to 10MB
- No cookie persistence between calls
