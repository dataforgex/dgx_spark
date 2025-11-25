# SearXNG Network Search Service

## Overview

SearXNG is deployed on the DGX Spark machine as a shared search service for all local LLM applications. It provides privacy-focused, self-hosted metasearch capabilities accessible across your local network.

## Service Details

**Host Machine**: DGX Spark
**IP Address**: `192.168.1.89`
**Port**: `8080`
**Protocol**: HTTP (local network only)

## API Endpoints

### Primary Search Endpoint

**URL**: `http://192.168.1.89:8080/search`
**Method**: `GET`

**Query Parameters**:
- `q` (required): Search query string
- `format` (optional): Response format. Use `json` for programmatic access
- `pageno` (optional): Page number for pagination (default: 1)
- `categories` (optional): Filter by category (e.g., `general`, `images`, `videos`)
- `engines` (optional): Comma-separated list of engines to use

**Example Request**:
```bash
curl "http://192.168.1.89:8080/search?q=artificial+intelligence&format=json"
```

**Example Response**:
```json
{
  "query": "artificial intelligence",
  "number_of_results": 20,
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "content": "Result snippet or description...",
      "engine": "duckduckgo",
      "engines": ["duckduckgo", "startpage"],
      "category": "general",
      "score": 4.0
    }
  ]
}
```

## Integration Examples

### Python (Using requests)

```python
import requests

SEARXNG_URL = "http://192.168.1.89:8080"

def search(query: str, max_results: int = 10):
    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={
            'q': query,
            'format': 'json',
            'pageno': 1
        },
        timeout=10
    )
    response.raise_for_status()
    data = response.json()

    return data['results'][:max_results]

# Example usage
results = search("machine learning")
for result in results:
    print(f"{result['title']}: {result['url']}")
```

### JavaScript/Node.js (Using fetch)

```javascript
const SEARXNG_URL = "http://192.168.1.89:8080";

async function search(query, maxResults = 10) {
    const url = new URL(`${SEARXNG_URL}/search`);
    url.searchParams.append('q', query);
    url.searchParams.append('format', 'json');

    const response = await fetch(url);
    const data = await response.json();

    return data.results.slice(0, maxResults);
}

// Example usage
const results = await search("machine learning");
results.forEach(result => {
    console.log(`${result.title}: ${result.url}`);
});
```

### cURL Examples

**Basic search**:
```bash
curl "http://192.168.1.89:8080/search?q=test&format=json"
```

**Search with specific engines**:
```bash
curl "http://192.168.1.89:8080/search?q=test&format=json&engines=duckduckgo,google"
```

**Image search**:
```bash
curl "http://192.168.1.89:8080/search?q=cats&format=json&categories=images"
```

## LLM Framework Integration

### LangChain

```python
from langchain.tools import Tool
import requests

SEARXNG_URL = "http://192.168.1.89:8080"

def searxng_search(query: str) -> str:
    """Search using SearXNG"""
    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={'q': query, 'format': 'json'},
        timeout=10
    )
    results = response.json()['results'][:5]

    formatted = []
    for r in results:
        formatted.append(f"Title: {r['title']}\nURL: {r['url']}\nSnippet: {r['content']}\n")

    return "\n\n".join(formatted)

# Create LangChain tool
search_tool = Tool(
    name="Web Search",
    func=searxng_search,
    description="Search the web for current information using SearXNG"
)
```

### LlamaIndex

```python
from llama_index.tools import FunctionTool
import requests

SEARXNG_URL = "http://192.168.1.89:8080"

def web_search(query: str) -> str:
    """Search the web using SearXNG"""
    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={'q': query, 'format': 'json'},
        timeout=10
    )
    results = response.json()['results'][:5]

    return "\n\n".join([
        f"{r['title']}\n{r['url']}\n{r['content']}"
        for r in results
    ])

# Create LlamaIndex tool
search_tool = FunctionTool.from_defaults(
    fn=web_search,
    name="web_search",
    description="Search the web for current information"
)
```

### OpenAI Function Calling

```python
import openai
import requests

SEARXNG_URL = "http://192.168.1.89:8080"

# Define the function
tools = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information using SearXNG",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def execute_web_search(query: str):
    """Execute search via SearXNG"""
    response = requests.get(
        f"{SEARXNG_URL}/search",
        params={'q': query, 'format': 'json'},
        timeout=10
    )
    return response.json()['results'][:5]
```

## Configuration

### Environment Variable

Set the SearXNG URL in your application's environment:

```bash
export SEARXNG_URL=http://192.168.1.89:8080
```

Or in a `.env` file:
```
SEARXNG_URL=http://192.168.1.89:8080
```

### Shared Config File

Create `/etc/llm-services/config.yml` (or similar):
```yaml
services:
  search:
    provider: searxng
    endpoint: http://192.168.1.89:8080
    format: json
    timeout: 10
```

## Search Engines

SearXNG aggregates results from multiple search engines including:
- DuckDuckGo
- Google
- Bing
- Startpage
- And many more...

You can customize which engines are used in `/home/dan/danProjects/dgx_spark/searxng-docker/searxng/settings.yml`

## Features

- **Privacy-focused**: No tracking, no data collection
- **Metasearch**: Combines results from multiple engines
- **Self-hosted**: Full control over search infrastructure
- **No rate limits**: Configure your own limits
- **JSON API**: Easy programmatic access
- **Multiple formats**: HTML, JSON, CSV, RSS
- **Category filtering**: General, images, videos, news, maps, etc.
- **Engine selection**: Choose which search engines to query

## Maintenance

### Check Service Status

```bash
docker ps --filter "name=searxng"
```

### View Logs

```bash
cd /home/dan/danProjects/dgx_spark/searxng-docker
docker logs searxng --tail 100
```

### Restart Service

```bash
cd /home/dan/danProjects/dgx_spark/searxng-docker
docker compose restart searxng
```

### Update SearXNG

```bash
cd /home/dan/danProjects/dgx_spark/searxng-docker
docker compose pull
docker compose up -d
```

## Network Access

The service is bound to `0.0.0.0:8080`, making it accessible from any device on the local network (`192.168.1.x`).

**Security Note**: This service is NOT exposed to the internet and should remain local network only. No authentication is configured.

## Troubleshooting

### Cannot Connect

1. Verify service is running:
   ```bash
   docker ps --filter "name=searxng"
   ```

2. Test locally first:
   ```bash
   curl "http://localhost:8080/search?q=test&format=json"
   ```

3. Check firewall rules:
   ```bash
   sudo ufw status
   ```

### 403 Forbidden Errors

SearXNG has bot detection. The current configuration has `link_token: false` to allow direct API access without reverse proxy headers.

### Slow Results

- SearXNG queries multiple engines, which can take 2-5 seconds
- Consider reducing the number of engines in settings.yml
- Use caching for repeated queries

## Technical Details

**Docker Compose Location**: `/home/dan/danProjects/dgx_spark/searxng-docker/`
**Configuration**: `/home/dan/danProjects/dgx_spark/searxng-docker/searxng/settings.yml`
**Container Name**: `searxng`
**Volumes**: `searxng-data`, `valkey-data2`
**Network**: `searxng-docker_searxng`
**Cache Backend**: Valkey (Redis fork)

## Support

For SearXNG documentation: https://docs.searxng.org/
For issues specific to this deployment, check the Docker logs or contact the system administrator.
