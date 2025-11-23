export interface SearchResult {
  title: string;
  url: string;
  snippet: string;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  reasoning_content?: string;
  search_results?: SearchResult[];
  image?: string; // Base64 encoded image
}

export interface Conversation {
  id: string;
  title: string;
  messages: Message[];
  timestamp: number;
}

export interface ChatRequest {
  model: string;
  messages: Message[];
  max_tokens?: number;
  temperature?: number;
}

export interface ChatResponse {
  choices: Array<{
    message: {
      role: string;
      content: string;
      reasoning_content?: string;
    };
  }>;
}

export interface ModelInfo {
  data: Array<{
    id: string;
    max_model_len?: number;
  }>;
}
