# Web Search Implementation

This document explains how the web search feature works in the DGX Spark Chat application.

## Information Flow Diagram

![Search Flow Diagram](./public/search_flow_diagram.png)

## How It Works

The search feature uses the "Tool Calling" capability of the Qwen model. Here is the step-by-step process:

1.  **User Request**: The user asks a question (e.g., "What is the weather in Denmark?") with the "Web Search" toggle enabled.
2.  **Tool Definition**: The frontend sends the user's message to the AI model along with a definition of the `web_search` tool.
3.  **Decision**: The AI model analyzes the request and realizes it needs external information. Instead of answering, it returns a **Tool Call Request** (e.g., `web_search(query="weather in Denmark")`).
4.  **Execution**:
    *   The Frontend receives this request.
    *   It calls the Backend API (`/api/search`).
    *   The Backend queries the **SearXNG metasearch service** (running locally at `http://192.168.1.89:8080`) which aggregates results from multiple search engines (DuckDuckGo, Google, Bing, etc.).
    *   For the top 2 results, the Backend also **scrapes the content** of the pages to get detailed information using BeautifulSoup.
5.  **Response**: The Backend returns the enriched search results to the Frontend.
6.  **Final Answer**: The Frontend sends the search results back to the AI model. The AI reads the results and generates the final, natural language answer for the user.

## Technical Components

*   **Frontend (`src/api.ts`)**: Defines the tool structure and handles the loop of sending messages, executing tools, and sending results back.
*   **Backend (`metrics-api.py`)**: Implements the `/api/search` endpoint using **SearXNG API** and `BeautifulSoup` for page scraping.
*   **SearXNG Service**: Self-hosted metasearch engine accessible at `http://192.168.1.89:8080` that aggregates results from multiple search providers. See `SEARXNG_SERVICE.md` for details.
*   **AI Model (Qwen)**: The "brain" that decides when to search and synthesizes the final answer.

## SearXNG Integration

The chat application now uses **SearXNG** instead of directly querying DuckDuckGo. Benefits include:

- **Privacy-focused**: No tracking or data collection
- **Metasearch**: Combines results from multiple engines for better coverage
- **Self-hosted**: Full control over search infrastructure
- **Shared service**: Available to all LLM applications on the local network
- **No API limits**: Configure your own rate limits

For detailed information about the SearXNG service, including API endpoints and integration examples for other LLM applications, see `/home/dan/danProjects/dgx_spark/SEARXNG_SERVICE.md`.
