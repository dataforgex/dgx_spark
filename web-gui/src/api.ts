import type { ChatRequest, ModelInfo, SearchResult } from './types';

export interface ModelConfig {
  name: string;
  port: number;
  modelId: string;
  maxTokens: number;
}

// Use 127.0.0.1 for localhost to avoid IPv6 resolution issues
const getApiHost = () => {
  const hostname = window.location.hostname;
  return hostname === 'localhost' ? '127.0.0.1' : hostname;
};

const SEARCH_TOOL = {
  type: "function",
  function: {
    name: "web_search",
    description: "Search the web for current, real-time information. Use this tool whenever the user asks about: current time/date, today's weather, recent news, latest events, live scores, stock prices, or any information that changes over time. Also use for facts you're uncertain about or events after your knowledge cutoff. Always prefer using this tool when there's any doubt about information currency.",
    parameters: {
      type: "object",
      properties: {
        query: {
          type: "string",
          description: "The search query to find relevant information. Be specific and include relevant keywords."
        }
      },
      required: ["query"]
    }
  }
};

export const AVAILABLE_MODELS: Record<string, ModelConfig> = {
  'qwen3-coder-30b': {
    name: 'Qwen3-Coder-30B',
    port: 8100,
    modelId: 'Qwen/Qwen3-Coder-30B-A3B-Instruct',
    maxTokens: 2048,
  },
  'qwen2-vl-7b': {
    name: 'Qwen2-VL-7B',
    port: 8101,
    modelId: 'Qwen/Qwen2-VL-7B-Instruct',
    maxTokens: 2048,
  },
  'ministral3-14b': {
    name: 'Ministral-3-14B',
    port: 8103,
    modelId: 'mistralai/Ministral-3-14B-Instruct-2512',
    maxTokens: 2048,
  },
  'qwen3-vl-32b-ollama': {
    name: 'Qwen3-VL-32B (Ollama)',
    port: 11435,
    modelId: 'qwen3-vl:32b',
    maxTokens: 2048,
  },
  'qwen3-coder-30b-awq': {
    name: 'Qwen3-Coder-30B-AWQ (vLLM)',
    port: 8104,
    modelId: 'cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit',
    maxTokens: 2048,
  },
};

export class ChatAPI {
  private port: number;
  private model: string;
  private maxTokens: number;
  private temperature: number;

  constructor(
    modelKey: string = 'qwen3-coder-30b',
    temperature: number = 0.7
  ) {
    const config = AVAILABLE_MODELS[modelKey] || AVAILABLE_MODELS['qwen3-coder-30b'];
    this.port = config.port;
    this.model = config.modelId;
    this.maxTokens = config.maxTokens;
    this.temperature = temperature;
  }

  setModel(modelKey: string) {
    const config = AVAILABLE_MODELS[modelKey];
    if (config) {
      this.port = config.port;
      this.model = config.modelId;
      this.maxTokens = config.maxTokens;
    }
  }

  async fetchModelInfo(): Promise<number | null> {
    try {
      const modelsUrl = `http://${getApiHost()}:${this.port}/v1/models`;

      const response = await fetch(modelsUrl, {
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) return null;

      const data = await response.json() as ModelInfo;
      const modelData = data.data.find(m => m.id === this.model);

      return modelData?.max_model_len || null;
    } catch {
      return null;
    }
  }

  private async performWebSearch(query: string): Promise<SearchResult[]> {
    const apiBase = `http://${getApiHost()}:5174`;
    const response = await fetch(`${apiBase}/api/search`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query, max_results: 5 }),
      signal: AbortSignal.timeout(30000),
    });

    if (!response.ok) {
      throw new Error(`Search API error: ${response.status}`);
    }

    const data = await response.json();
    return data.results || [];
  }

  async sendMessage(
    messages: ChatRequest['messages'],
    enableSearch: boolean = false
  ): Promise<{ content: string; reasoning_content?: string; search_results?: SearchResult[] }> {
    let searchResults: SearchResult[] | undefined;
    let conversationMessages = [...messages];

    // Transform messages to handle images
    const apiMessages = conversationMessages.map(msg => {
      if (msg.role === 'user' && msg.image) {
        return {
          role: 'user',
          content: [
            { type: 'text', text: msg.content },
            { type: 'image_url', image_url: { url: msg.image } }
          ]
        };
      }
      // Remove internal fields that shouldn't go to API
      const { image, search_results, reasoning_content, ...rest } = msg;
      return rest;
    });

    // Initial request with tools if search is enabled
    const payload: any = {
      model: this.model,
      messages: apiMessages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
      repetition_penalty: 1.1,  // Prevent repetition loops (especially for TRT-LLM)
    };

    if (enableSearch) {
      payload.tools = [SEARCH_TOOL];
      payload.tool_choice = "auto";
    }

    // Call model server directly (CORS enabled on vLLM, nginx wrapper on TRT-LLM)
    const modelUrl = `http://${getApiHost()}:${this.port}/v1/chat/completions`;
    let response = await fetch(modelUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(1800000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }

    let result = await response.json() as any;

    if (!result.choices || result.choices.length === 0) {
      throw new Error('No response from API');
    }

    // Check if model wants to call a function
    const choice = result.choices[0];
    if (choice.message.tool_calls && choice.message.tool_calls.length > 0) {
      const toolCall = choice.message.tool_calls[0];

      if (toolCall.function.name === 'web_search') {
        const args = JSON.parse(toolCall.function.arguments);

        // Perform the search
        searchResults = await this.performWebSearch(args.query);
        console.log('🔍 Web Search Results:', searchResults);

        // Add assistant's function call to conversation
        conversationMessages.push({
          role: 'assistant',
          content: choice.message.content || '',
          tool_calls: choice.message.tool_calls
        } as any);

        // Add function result
        const toolResultContent = JSON.stringify({
          results: searchResults.map(r => ({
            title: r.title,
            url: r.url,
            snippet: r.snippet
          }))
        });

        conversationMessages.push({
          role: 'tool',
          tool_call_id: toolCall.id,
          name: toolCall.function.name,
          content: toolResultContent
        } as any);

        console.log('🔧 Tool Result Content:', toolResultContent);
        console.log('📝 Full conversation before second call:', JSON.stringify(conversationMessages, null, 2));

        // Make second request with function results
        const secondPayload = {
          model: this.model,
          messages: conversationMessages,
          max_tokens: this.maxTokens,
          temperature: this.temperature,
          repetition_penalty: 1.1,
        };

        console.log('📤 Second API call payload:', JSON.stringify(secondPayload, null, 2));

        response = await fetch(modelUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(secondPayload),
          signal: AbortSignal.timeout(1800000),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`API error: ${response.status} - ${errorText}`);
        }

        result = await response.json() as any;
      }
    }

    const finalMessage = result.choices[0].message;
    return {
      content: finalMessage.content,
      reasoning_content: finalMessage.reasoning_content,
      search_results: searchResults
    };
  }

  getModel(): string {
    return this.model;
  }

  getApiUrl(): string {
    return `http://${getApiHost()}:${this.port}/v1/chat/completions`;
  }

  getMaxTokens(): number {
    return this.maxTokens;
  }

  getTemperature(): number {
    return this.temperature;
  }
}
