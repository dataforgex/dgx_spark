import type { ChatRequest, ModelInfo, SearchResult } from './types';
import { getApiHost, SERVICES } from './config';
import { encode } from 'gpt-tokenizer';

// UUID generator with fallback for browsers without crypto.randomUUID (e.g., HTTP contexts)
function generateUUID(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older browsers or non-secure contexts
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

// Model config from model-manager API
export interface ModelConfig {
  id: string;
  name: string;
  port: number;
  modelId: string;
  maxTokens: number;
  maxContextLength: number;
  supportsTools: boolean;
  toolCallParser: string | null;
  status?: string;
}

// Model registry - fetches from API and caches
class ModelRegistry {
  private models: Map<string, ModelConfig> = new Map();
  private lastFetch: number = 0;
  private fetchPromise: Promise<void> | null = null;
  private readonly CACHE_TTL = 30000; // 30 seconds
  private hasLoggedInitialLoad: boolean = false;

  async getModel(modelKey: string): Promise<ModelConfig | null> {
    await this.ensureFresh();
    return this.models.get(modelKey) || null;
  }

  async getAllModels(): Promise<ModelConfig[]> {
    await this.ensureFresh();
    return Array.from(this.models.values());
  }

  private async ensureFresh(): Promise<void> {
    const now = Date.now();
    if (now - this.lastFetch < this.CACHE_TTL && this.models.size > 0) {
      return;
    }

    // Prevent multiple concurrent fetches
    if (this.fetchPromise) {
      return this.fetchPromise;
    }

    this.fetchPromise = this.fetchModels();
    try {
      await this.fetchPromise;
    } finally {
      this.fetchPromise = null;
    }
  }

  private async fetchModels(): Promise<void> {
    try {
      const response = await fetch(`${SERVICES.MODEL_MANAGER}/api/models`);
      if (!response.ok) {
        console.warn('Failed to fetch models from API, using fallback');
        this.loadFallbackModels();
        return;
      }

      const data = await response.json();
      this.models.clear();

      for (const model of data) {
        this.models.set(model.id, {
          id: model.id,
          name: model.name,
          port: model.port,
          modelId: model.model_id || model.id,
          maxTokens: 2048, // Default, model doesn't expose this
          maxContextLength: model.max_context_length || 32768,
          supportsTools: model.supports_tools || false,
          toolCallParser: model.tool_call_parser || null,
          status: model.status,
        });
      }

      this.lastFetch = Date.now();
      // Only log on first load
      if (!this.hasLoggedInitialLoad && this.models.size > 0) {
        console.log(`📋 Loaded ${this.models.size} models from API`);
        this.hasLoggedInitialLoad = true;
      }
    } catch (error) {
      console.warn('Error fetching models:', error);
      this.loadFallbackModels();
    }
  }

  private loadFallbackModels(): void {
    // Fallback for when API is unavailable
    const fallback: Record<string, Omit<ModelConfig, 'id'>> = {
      'qwen3-coder-30b-awq': {
        name: 'Qwen3-Coder-30B-AWQ',
        port: 8104,
        modelId: 'cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit',
        maxTokens: 2048,
        maxContextLength: 65536,
        supportsTools: true,
        toolCallParser: 'qwen3_coder',
      },
      'ministral3-14b': {
        name: 'Ministral-3-14B',
        port: 8103,
        modelId: 'mistralai/Ministral-3-14B-Instruct-2512',
        maxTokens: 2048,
        maxContextLength: 32768,
        supportsTools: true,
        toolCallParser: 'mistral',
      },
      'chandra-ocr': {
        name: 'Chandra OCR',
        port: 8106,
        modelId: 'datalab-to/chandra',
        maxTokens: 2048,
        maxContextLength: 8192,
        supportsTools: false,
        toolCallParser: null,
      },
    };

    this.models.clear();
    for (const [id, config] of Object.entries(fallback)) {
      this.models.set(id, { id, ...config });
    }
    this.lastFetch = Date.now();
  }

  invalidate(): void {
    this.lastFetch = 0;
  }
}

export const modelRegistry = new ModelRegistry();

// Track which models have been logged (module-level to survive instance recreation)
const loggedModels = new Set<string>();

export interface SandboxTool {
  type: "function";
  function: {
    name: string;
    description: string;
    parameters: {
      type: "object";
      properties: Record<string, unknown>;
      required: string[];
    };
  };
}

export interface SandboxExecuteResult {
  success: boolean;
  output: string;
  error: string;
  execution_time: number;
  exec_id: string;
}

// Result from executing a single tool
interface ToolExecutionResult {
  toolCallId: string;
  toolName: string;
  content: string;
  searchResults?: SearchResult[];
  sandboxOutput?: string;
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

// AVAILABLE_MODELS is now fetched from model-manager API via modelRegistry
// This export provides synchronous fallback for backward compatibility
export const AVAILABLE_MODELS: Record<string, { name: string; port: number; modelId: string; maxTokens: number }> = new Proxy({} as any, {
  get(_target, prop: string) {
    const fallback: Record<string, any> = {
      'qwen3-coder-30b-awq': { name: 'Qwen3-Coder-30B-AWQ', port: 8104, modelId: 'cpatonn/Qwen3-Coder-30B-A3B-Instruct-AWQ-4bit', maxTokens: 2048 },
      'ministral3-14b': { name: 'Ministral-3-14B', port: 8103, modelId: 'mistralai/Ministral-3-14B-Instruct-2512', maxTokens: 2048 },
      'qwen3-coder-30b': { name: 'Qwen3-Coder-30B', port: 8100, modelId: 'Qwen/Qwen3-Coder-30B-A3B-Instruct', maxTokens: 2048 },
      'qwen2-vl-7b': { name: 'Qwen2-VL-7B', port: 8101, modelId: 'Qwen/Qwen2-VL-7B-Instruct', maxTokens: 2048 },
      'qwen3-235b-awq': { name: 'Qwen3-235B-AWQ', port: 8235, modelId: 'qwen3-235b-awq', maxTokens: 2048 },
      'qwen3-vl-32b-ollama': { name: 'Qwen3-VL-32B (Ollama)', port: 11435, modelId: 'qwen3-vl:32b', maxTokens: 4096 },
      'chandra-ocr': { name: 'Chandra OCR', port: 8106, modelId: 'datalab-to/chandra', maxTokens: 2048 },
    };
    return fallback[prop];
  },
  ownKeys() {
    return ['qwen3-coder-30b-awq', 'ministral3-14b', 'qwen3-coder-30b', 'qwen2-vl-7b', 'qwen3-235b-awq', 'qwen3-vl-32b-ollama', 'chandra-ocr'];
  },
  getOwnPropertyDescriptor() {
    return { enumerable: true, configurable: true };
  },
});

export class ChatAPI {
  private port: number;
  private model: string;
  private modelKey: string;
  private maxTokens: number;
  private temperature: number;
  private sandboxTools: SandboxTool[] = [];
  private sessionId: string;
  private maxContextLength: number = 32768; // Default, updated by fetchModelInfo
  private supportsTools: boolean = true; // Assume true until we know otherwise
  private toolCallParser: string | null = null;

  constructor(
    modelKey: string = 'qwen3-coder-30b-awq',
    temperature: number = 0.7
  ) {
    // Use synchronous fallback for immediate init, then async update
    const fallback = AVAILABLE_MODELS[modelKey] || AVAILABLE_MODELS['qwen3-coder-30b-awq'];
    this.modelKey = modelKey;
    this.port = fallback?.port || 8104;
    this.model = fallback?.modelId || modelKey;
    this.maxTokens = fallback?.maxTokens || 2048;
    this.temperature = temperature;
    this.sessionId = generateUUID();

    // Async load full config from registry
    this.loadModelConfig(modelKey);
  }

  private async loadModelConfig(modelKey: string): Promise<void> {
    const config = await modelRegistry.getModel(modelKey);
    if (config) {
      this.port = config.port;
      this.model = config.modelId;
      this.maxTokens = config.maxTokens;
      this.maxContextLength = config.maxContextLength;
      this.supportsTools = config.supportsTools;
      this.toolCallParser = config.toolCallParser;

      // Only log once per model (module-level dedup survives React re-renders)
      if (!loggedModels.has(modelKey)) {
        console.log(`🔧 Model ${modelKey}: supportsTools=${this.supportsTools}, parser=${this.toolCallParser}`);
        loggedModels.add(modelKey);
      }
    }
  }

  // Estimate token count using GPT tokenizer (good approximation for Qwen/Mistral models)
  // Handles images separately since base64 data would give incorrect token counts
  private estimateTokens(messages: any[]): number {
    const TOKENS_PER_IMAGE = 1000; // Vision models typically use ~1000 tokens per image
    let imageCount = 0;

    // Deep clone and strip image data for accurate text token counting
    const messagesWithoutImages = messages.map(msg => {
      // Handle direct image field (our internal format)
      if (msg.image) {
        imageCount++;
        const { image, ...rest } = msg;
        return rest;
      }

      // Handle OpenAI vision format (content array with image_url)
      if (Array.isArray(msg.content)) {
        const filteredContent = msg.content.map((part: any) => {
          if (part.type === 'image_url') {
            imageCount++;
            return { type: 'image_url', image_url: { url: '[IMAGE]' } };
          }
          return part;
        });
        return { ...msg, content: filteredContent };
      }

      return msg;
    });

    try {
      const text = JSON.stringify(messagesWithoutImages);
      const textTokens = encode(text).length;
      const totalTokens = textTokens + (imageCount * TOKENS_PER_IMAGE);
      if (imageCount > 0) {
        console.log(`📊 Token estimate: ${textTokens} text + ${imageCount} image(s) × ${TOKENS_PER_IMAGE} = ${totalTokens}`);
      }
      return totalTokens;
    } catch {
      // Fallback to character-based estimate if tokenizer fails
      const text = JSON.stringify(messagesWithoutImages);
      const textTokens = Math.ceil(text.length / 3.5); // Average ~3.5 chars per token
      return textTokens + (imageCount * TOKENS_PER_IMAGE);
    }
  }

  // Calculate safe max_tokens based on estimated input tokens
  private calculateMaxTokens(messages: any[]): number {
    const estimatedInputTokens = this.estimateTokens(messages);
    const availableTokens = this.maxContextLength - estimatedInputTokens - 300; // 300 token buffer
    // Cap max_tokens to leave room for input growth
    const maxAllowed = Math.min(this.maxTokens, Math.floor(this.maxContextLength * 0.4));
    const safeMaxTokens = Math.max(256, Math.min(maxAllowed, availableTokens));
    console.log(`📊 Token estimate: ~${estimatedInputTokens} input, ${safeMaxTokens} max output`);
    return safeMaxTokens;
  }

  // Truncate tool result to prevent context overflow
  private truncateToolResult(result: string, maxChars: number = 3000): string {
    if (result.length <= maxChars) return result;
    const truncated = result.slice(0, maxChars);
    return truncated + `\n...[truncated, ${result.length - maxChars} chars omitted]`;
  }

  // Summarize old messages to compress context
  private async summarizeMessages(messages: any[]): Promise<string> {
    const modelUrl = `http://${getApiHost()}:${this.port}/v1/chat/completions`;

    // Build a summary prompt
    const conversationText = messages
      .filter(m => m.role !== 'system')
      .map(m => {
        if (m.role === 'tool') {
          // Compress tool results heavily
          const content = typeof m.content === 'string' ? m.content : JSON.stringify(m.content);
          return `[Tool ${m.name}]: ${content.slice(0, 200)}...`;
        }
        if (m.tool_calls) {
          const tools = m.tool_calls.map((tc: any) => tc.function.name).join(', ');
          return `Assistant: [Called tools: ${tools}] ${m.content || ''}`;
        }
        return `${m.role}: ${m.content}`;
      })
      .join('\n');

    const summaryPrompt = [
      {
        role: 'system',
        content: 'You are a conversation summarizer. Create a concise summary of the conversation that preserves: 1) Key topics discussed, 2) Important facts/data mentioned (prices, calculations, etc), 3) Decisions made, 4) Current task state. Be brief but comprehensive. Output only the summary, no preamble.'
      },
      {
        role: 'user',
        content: `Summarize this conversation:\n\n${conversationText}`
      }
    ];

    try {
      const response = await fetch(modelUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.model,
          messages: summaryPrompt,
          max_tokens: 500,  // Keep summary short
          temperature: 0.3,  // More deterministic
        }),
        signal: AbortSignal.timeout(30000),
      });

      if (!response.ok) {
        console.warn('Summarization failed, using truncation fallback');
        return this.fallbackSummary(messages);
      }

      const result = await response.json() as any;
      const summary = result.choices?.[0]?.message?.content || this.fallbackSummary(messages);
      console.log('📝 Context summarized:', summary.slice(0, 100) + '...');
      return summary;
    } catch (error) {
      console.warn('Summarization error:', error);
      return this.fallbackSummary(messages);
    }
  }

  // Fallback: simple truncation-based summary
  private fallbackSummary(messages: any[]): string {
    const userMessages = messages.filter(m => m.role === 'user');
    const lastAssistant = messages.filter(m => m.role === 'assistant' && m.content).slice(-1)[0];

    return `Previous topics: ${userMessages.map(m => m.content.slice(0, 50)).join('; ')}. ` +
           `Last response: ${lastAssistant?.content?.slice(0, 200) || 'N/A'}`;
  }

  // Compress context if it's getting too large
  async compressContextIfNeeded(messages: any[]): Promise<any[]> {
    const estimatedTokens = this.estimateTokens(messages);
    const threshold = this.maxContextLength * 0.7;  // Compress at 70% capacity

    if (estimatedTokens < threshold) {
      return messages;  // No compression needed
    }

    console.log(`🗜️ Context compression triggered: ~${estimatedTokens} tokens (threshold: ${Math.round(threshold)})`);

    // Keep system message and last N messages
    const KEEP_RECENT = 6;  // Keep last 6 messages (3 turns)
    const systemMsg = messages.find(m => m.role === 'system');
    const recentMessages = messages.slice(-KEEP_RECENT);
    const oldMessages = messages.slice(1, -KEEP_RECENT);  // Exclude system and recent

    if (oldMessages.length === 0) {
      return messages;  // Nothing to summarize
    }

    // Summarize old messages
    const summary = await this.summarizeMessages(oldMessages);

    // Build compressed context
    const compressed = [
      systemMsg,
      {
        role: 'assistant',
        content: `[Previous conversation summary]\n${summary}\n[End of summary - continuing conversation]`
      },
      ...recentMessages
    ].filter(Boolean);

    const newTokens = this.estimateTokens(compressed);
    console.log(`🗜️ Context compressed: ${estimatedTokens} → ${newTokens} tokens`);

    return compressed;
  }

  setModel(modelKey: string) {
    this.modelKey = modelKey;
    // Synchronous fallback
    const fallback = AVAILABLE_MODELS[modelKey];
    if (fallback) {
      this.port = fallback.port;
      this.model = fallback.modelId;
      this.maxTokens = fallback.maxTokens;
    }
    // Async update with full config
    this.loadModelConfig(modelKey);
  }

  // Check if current model supports tool calling
  getSupportsTools(): boolean {
    return this.supportsTools;
  }

  // Get context usage info for UI display
  getContextInfo(messages: any[]): { tokens: number; maxContext: number; percentUsed: number } {
    const tokens = this.estimateTokens(messages);
    return {
      tokens,
      maxContext: this.maxContextLength,
      percentUsed: Math.round((tokens / this.maxContextLength) * 100)
    };
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

      if (modelData?.max_model_len) {
        this.maxContextLength = modelData.max_model_len;
        console.log(`📏 Model context length: ${this.maxContextLength}`);
      }

      return modelData?.max_model_len || null;
    } catch {
      return null;
    }
  }

  private async performWebSearch(query: string): Promise<SearchResult[]> {
    const response = await fetch(`${SERVICES.METRICS_API}/api/search`, {
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

  async fetchSandboxTools(): Promise<SandboxTool[]> {
    try {
      const response = await fetch(`${SERVICES.SANDBOX}/api/tools-openai`, {
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) {
        console.warn('Sandbox API not available');
        return [];
      }

      this.sandboxTools = await response.json();
      console.log('📦 Loaded sandbox tools:', this.sandboxTools.map(t => t.function.name));
      return this.sandboxTools;
    } catch (error) {
      console.warn('Failed to fetch sandbox tools:', error);
      return [];
    }
  }

  private async executeSandboxTool(toolName: string, args: Record<string, unknown>): Promise<SandboxExecuteResult> {
    const response = await fetch(`${SERVICES.SANDBOX}/api/execute/${toolName}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Session-Id': this.sessionId,
      },
      body: JSON.stringify({ args, session_id: this.sessionId }),
      signal: AbortSignal.timeout(60000),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return {
        success: false,
        output: '',
        error: `Sandbox API error: ${response.status} - ${errorText}`,
        execution_time: 0,
        exec_id: '',
      };
    }

    return await response.json();
  }

  private isSandboxTool(toolName: string): boolean {
    return this.sandboxTools.some(t => t.function.name === toolName);
  }

  // Parse <tool_call> tags from model content (legacy fallback)
  // NOTE: This should rarely be needed if vLLM's tool_call_parser is configured correctly.
  // If you see "WARN: Falling back to content parsing" frequently, check the model's
  // tool_call_parser setting in models.yaml
  private parseToolCallsFromContent(content: string): any[] {
    const toolCalls: any[] = [];

    // Try Qwen3 XML format: <tool_call>{"name": "...", "arguments": {...}}</tool_call>
    const qwenRegex = /<tool_call>\s*(\{[\s\S]*?\})\s*<\/tool_call>/g;
    let match;
    let index = 0;

    while ((match = qwenRegex.exec(content)) !== null) {
      try {
        const parsed = JSON.parse(match[1]);
        if (parsed.name && parsed.arguments) {
          toolCalls.push({
            id: `call_${Date.now()}_${index}`,
            type: 'function',
            function: {
              name: parsed.name,
              arguments: typeof parsed.arguments === 'string'
                ? parsed.arguments
                : JSON.stringify(parsed.arguments)
            }
          });
          index++;
        }
      } catch (e) {
        console.warn('Failed to parse tool call from content:', match[1], e);
      }
    }

    if (toolCalls.length > 0) {
      console.warn(`⚠️ WARN: Falling back to content parsing for ${toolCalls.length} tool call(s). ` +
        `This indicates vLLM's tool_call_parser may not be working correctly for model ${this.modelKey}`);
    }

    return toolCalls;
  }

  // Safely parse tool call arguments (handles both string and object)
  private parseToolArguments(args: string | object): Record<string, any> {
    if (typeof args === 'object') {
      return args as Record<string, any>;
    }
    try {
      return JSON.parse(args);
    } catch (e) {
      console.error('Failed to parse tool arguments:', args, e);
      return {};
    }
  }

  // Execute a single tool by name and return structured result
  private async executeToolByName(
    toolCallId: string,
    toolName: string,
    args: Record<string, any>
  ): Promise<ToolExecutionResult> {
    if (toolName === 'web_search') {
      const searchResults = await this.performWebSearch(args.query);
      console.log(`🔍 Web Search [${toolCallId}]:`, args.query);
      return {
        toolCallId,
        toolName,
        content: JSON.stringify({
          results: searchResults.map(r => ({
            title: r.title,
            url: r.url,
            snippet: r.snippet
          }))
        }),
        searchResults
      };
    } else if (this.isSandboxTool(toolName)) {
      console.log(`🔧 Sandbox [${toolCallId}]: ${toolName}`, args);
      const sandboxResult = await this.executeSandboxTool(toolName, args);

      if (sandboxResult.success) {
        return {
          toolCallId,
          toolName,
          content: JSON.stringify({
            success: true,
            output: sandboxResult.output,
            execution_time: sandboxResult.execution_time
          }),
          sandboxOutput: sandboxResult.output
        };
      } else {
        return {
          toolCallId,
          toolName,
          content: JSON.stringify({
            success: false,
            error: sandboxResult.error
          })
        };
      }
    } else {
      return {
        toolCallId,
        toolName,
        content: JSON.stringify({ error: `Unknown tool: ${toolName}` })
      };
    }
  }

  getSandboxTools(): SandboxTool[] {
    return this.sandboxTools;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  async sendMessage(
    messages: ChatRequest['messages'],
    enableSearch: boolean = false,
    enableSandbox: boolean = false
  ): Promise<{ content: string; reasoning_content?: string; search_results?: SearchResult[]; sandbox_outputs?: string[]; context_compressed?: boolean }> {
    let allSearchResults: SearchResult[] = [];
    let allSandboxOutputs: string[] = [];
    let contextCompressed = false;

    // Compress context if needed before processing
    let conversationMessages = [...messages];
    const compressedMessages = await this.compressContextIfNeeded(conversationMessages);
    if (compressedMessages.length !== conversationMessages.length) {
      conversationMessages = compressedMessages;
      contextCompressed = true;
    }

    // Transform messages to handle images
    let apiMessages = conversationMessages.map(msg => {
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

    // Build tools list
    const tools: any[] = [];
    if (enableSearch) {
      tools.push(SEARCH_TOOL);
    }
    if (enableSandbox && this.sandboxTools.length > 0) {
      tools.push(...this.sandboxTools);
    }

    // Initial request with tools if any are enabled
    const payload: any = {
      model: this.model,
      messages: apiMessages,
      max_tokens: this.calculateMaxTokens(apiMessages),
      temperature: this.temperature,
      repetition_penalty: 1.1,  // Prevent repetition loops (especially for TRT-LLM)
    };

    if (tools.length > 0) {
      payload.tools = tools;
      payload.tool_choice = "auto";
    }

    // For Ollama models (ports 114xx), use proxy to avoid browser CORS issues
    // For other models (vLLM, TRT-LLM), call directly
    const isOllamaPort = this.port >= 11434 && this.port <= 11499;
    const modelUrl = isOllamaPort
      ? `${SERVICES.METRICS_API}/api/chat/proxy/${this.port}`
      : `http://${getApiHost()}:${this.port}/v1/chat/completions`;

    const bodyStr = JSON.stringify(payload);
    console.log(`🌐 Fetching: ${modelUrl} (body: ${(bodyStr.length / 1024).toFixed(1)}KB)${isOllamaPort ? ' [via proxy]' : ''}`);

    let response: Response;
    try {
      response = await fetch(modelUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: bodyStr,
        signal: AbortSignal.timeout(1800000),
      });
    } catch (fetchError: any) {
      // Log detailed error info for debugging
      console.error('🔴 Fetch failed:', {
        url: modelUrl,
        error: fetchError.message,
        name: fetchError.name,
        bodySize: bodyStr.length,
      });
      throw fetchError;
    }

    if (!response.ok) {
      const errorText = await response.text();
      console.error('🔴 API returned error:', {
        status: response.status,
        statusText: response.statusText,
        body: errorText.slice(0, 500),
        headers: Object.fromEntries(response.headers.entries()),
      });
      throw new Error(`API error: ${response.status} - ${errorText}`);
    }

    let result = await response.json() as any;

    if (!result.choices || result.choices.length === 0) {
      throw new Error('No response from API');
    }

    // Handle tool calls in a loop (max 10 iterations to prevent infinite loops)
    const MAX_TOOL_ITERATIONS = 10;
    let iteration = 0;

    while (iteration < MAX_TOOL_ITERATIONS) {
      const choice = result.choices[0];

      // Check if model wants to call any functions
      // Also parse <tool_call> tags from content if tool_calls array is empty (Qwen3 format)
      let toolCalls = choice.message.tool_calls || [];
      if (toolCalls.length === 0 && choice.message.content) {
        const parsedCalls = this.parseToolCallsFromContent(choice.message.content);
        if (parsedCalls.length > 0) {
          toolCalls = parsedCalls;
          console.log('📝 Parsed tool calls from content:', toolCalls.length);
        }
      }

      if (toolCalls.length === 0) {
        break; // No more tool calls, exit loop
      }

      // Update the message's tool_calls for downstream processing
      choice.message.tool_calls = toolCalls;

      iteration++;
      console.log(`🔄 Tool call iteration ${iteration}: ${toolCalls.length} tool(s) requested`);

      // Execute ALL tool calls in parallel with error handling
      const toolResults: ToolExecutionResult[] = [];
      try {
        const results = await Promise.all(
          toolCalls.map(async (toolCall: any) => {
            try {
              const toolName = toolCall.function.name;
              const args = this.parseToolArguments(toolCall.function.arguments);
              return await this.executeToolByName(toolCall.id, toolName, args);
            } catch (toolError) {
              console.error(`Error executing tool ${toolCall.function?.name}:`, toolError);
              return {
                toolCallId: toolCall.id || `error_${Date.now()}`,
                toolName: toolCall.function?.name || 'unknown',
                content: JSON.stringify({ error: `Tool execution failed: ${toolError}` }),
              };
            }
          })
        );
        toolResults.push(...results);
      } catch (allError) {
        console.error('Critical error in tool execution:', allError);
        break; // Exit loop on critical error
      }

      // Aggregate results from all tools
      for (const result of toolResults) {
        if (result.searchResults) {
          allSearchResults.push(...result.searchResults);
        }
        if (result.sandboxOutput) {
          allSandboxOutputs.push(result.sandboxOutput);
        }
      }

      // Add assistant's message with ALL tool calls
      conversationMessages.push({
        role: 'assistant',
        content: choice.message.content || '',
        tool_calls: toolCalls
      } as any);

      // Add each tool result as separate message
      for (const result of toolResults) {
        const truncatedResult = this.truncateToolResult(result.content);
        conversationMessages.push({
          role: 'tool',
          tool_call_id: result.toolCallId,
          name: result.toolName,
          content: truncatedResult
        } as any);
        console.log(`📦 [${result.toolName}]:`, truncatedResult.length > 200 ? truncatedResult.slice(0, 200) + '...' : truncatedResult);
      }

      // Make next request with function results - include tools for additional tool calls
      const nextPayload: any = {
        model: this.model,
        messages: conversationMessages,
        max_tokens: this.calculateMaxTokens(conversationMessages),
        temperature: this.temperature,
        repetition_penalty: 1.1,
      };

      // Include tools so model can make additional tool calls if needed
      if (tools.length > 0) {
        nextPayload.tools = tools;
        nextPayload.tool_choice = "auto";
      }

      response = await fetch(modelUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(nextPayload),
        signal: AbortSignal.timeout(1800000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API error: ${response.status} - ${errorText}`);
      }

      result = await response.json() as any;

      if (!result.choices || result.choices.length === 0) {
        throw new Error('No response from API');
      }
    }

    if (iteration >= MAX_TOOL_ITERATIONS) {
      console.warn('⚠️ Reached maximum tool call iterations');
    }

    const finalMessage = result.choices[0].message;
    return {
      content: finalMessage.content,
      reasoning_content: finalMessage.reasoning_content,
      search_results: allSearchResults.length > 0 ? allSearchResults : undefined,
      sandbox_outputs: allSandboxOutputs.length > 0 ? allSandboxOutputs : undefined,
      context_compressed: contextCompressed || undefined
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
