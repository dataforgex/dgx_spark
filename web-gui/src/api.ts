import type { ChatRequest, ModelInfo, SearchResult } from './types';

export interface ModelConfig {
  name: string;
  apiUrl: string;
  modelId: string;
  maxTokens: number;
}

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
    apiUrl: 'http://192.168.1.89:8100/v1/chat/completions',
    modelId: 'Qwen/Qwen3-Coder-30B-A3B-Instruct',
    maxTokens: 2048,
  },
  'qwen2-vl-7b': {
    name: 'Qwen2-VL-7B',
    apiUrl: 'http://192.168.1.89:8101/v1/chat/completions',
    modelId: 'Qwen/Qwen2-VL-7B-Instruct',
    maxTokens: 2048,
  },
  'qwen3-vl-30b': {
    name: 'Qwen3-VL-30B',
    apiUrl: 'http://192.168.1.89:8102/v1/chat/completions',
    modelId: 'Qwen/Qwen3-VL-30B',
    maxTokens: 2048,
  },
  'qwen3-32b-ngc': {
    name: 'Qwen3-32B (NGC)',
    apiUrl: 'http://192.168.1.89:8103/v1/chat/completions',
    modelId: 'Qwen/Qwen3-32B',
    maxTokens: 1500,
  },
};

export class ChatAPI {
  private apiUrl: string;
  private model: string;
  private maxTokens: number;
  private temperature: number;

  constructor(
    modelKey: string = 'qwen3-coder-30b',
    temperature: number = 0.7
  ) {
    const config = AVAILABLE_MODELS[modelKey] || AVAILABLE_MODELS['qwen3-coder-30b'];
    this.apiUrl = config.apiUrl;
    this.model = config.modelId;
    this.maxTokens = config.maxTokens;
    this.temperature = temperature;
  }

  setModel(modelKey: string) {
    const config = AVAILABLE_MODELS[modelKey];
    if (config) {
      this.apiUrl = config.apiUrl;
      this.model = config.modelId;
      this.maxTokens = config.maxTokens;
    }
  }

  async fetchModelInfo(): Promise<number | null> {
    try {
      const baseUrl = this.apiUrl.replace(/\/v1\/chat\/completions$/, '');
      const modelsUrl = `${baseUrl}/v1/models`;

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
    const apiBase = `http://${window.location.hostname}:5174`;
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

    // Initial request with tools if search is enabled
    const payload: any = {
      model: this.model,
      messages: conversationMessages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
    };

    if (enableSearch) {
      payload.tools = [SEARCH_TOOL];
      payload.tool_choice = "auto";
    }

    let response = await fetch(this.apiUrl, {
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
        };

        console.log('📤 Second API call payload:', JSON.stringify(secondPayload, null, 2));

        response = await fetch(this.apiUrl, {
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
    return this.apiUrl;
  }

  getMaxTokens(): number {
    return this.maxTokens;
  }

  getTemperature(): number {
    return this.temperature;
  }
}
