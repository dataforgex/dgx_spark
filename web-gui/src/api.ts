import type { ChatRequest, ChatResponse, ModelInfo } from './types';

export class ChatAPI {
  private apiUrl: string;
  private model: string;
  private maxTokens: number;
  private temperature: number;

  constructor(
    apiUrl: string = 'http://localhost:8100/v1/chat/completions',
    model: string = 'Qwen/Qwen3-Coder-30B-A3B-Instruct',
    maxTokens: number = 2048,
    temperature: number = 0.7
  ) {
    this.apiUrl = apiUrl;
    this.model = model;
    this.maxTokens = maxTokens;
    this.temperature = temperature;
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

  async sendMessage(messages: ChatRequest['messages']): Promise<string> {
    const payload: ChatRequest = {
      model: this.model,
      messages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
    };

    const response = await fetch(this.apiUrl, {
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

    const result = await response.json() as ChatResponse;

    if (!result.choices || result.choices.length === 0) {
      throw new Error('No response from API');
    }

    return result.choices[0].message.content;
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
