import type { ChatRequest, ModelInfo, SearchResult } from './types';

export interface ModelConfig {
  name: string;
  port: number;
  modelId: string;
  maxTokens: number;
}

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

// Use 127.0.0.1 for localhost to avoid IPv6 resolution issues
const getApiHost = () => {
  const hostname = window.location.hostname;
  return hostname === 'localhost' ? '127.0.0.1' : hostname;
};

const SANDBOX_API_PORT = 5176;

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
  'qwen3-235b-awq': {
    name: 'Qwen3-235B-AWQ (Distributed)',
    port: 8235,
    modelId: 'qwen3-235b-awq',
    maxTokens: 2048,
  },
};

export class ChatAPI {
  private port: number;
  private model: string;
  private maxTokens: number;
  private temperature: number;
  private sandboxTools: SandboxTool[] = [];
  private sessionId: string;
  private maxContextLength: number = 32768; // Default, updated by fetchModelInfo

  constructor(
    modelKey: string = 'qwen3-coder-30b',
    temperature: number = 0.7
  ) {
    const config = AVAILABLE_MODELS[modelKey] || AVAILABLE_MODELS['qwen3-coder-30b'];
    this.port = config.port;
    this.model = config.modelId;
    this.maxTokens = config.maxTokens;
    this.temperature = temperature;
    this.sessionId = crypto.randomUUID();
  }

  // Estimate token count (very conservative: ~1.8 chars per token)
  private estimateTokens(messages: any[]): number {
    const text = JSON.stringify(messages);
    return Math.ceil(text.length / 1.8); // Very conservative to avoid context overflow
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

  async fetchSandboxTools(): Promise<SandboxTool[]> {
    try {
      const sandboxUrl = `http://${getApiHost()}:${SANDBOX_API_PORT}/api/tools-openai`;
      const response = await fetch(sandboxUrl, {
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
    const sandboxUrl = `http://${getApiHost()}:${SANDBOX_API_PORT}/api/execute/${toolName}`;
    const response = await fetch(sandboxUrl, {
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

  // Parse <tool_call> tags from model content (Qwen3 format)
  private parseToolCallsFromContent(content: string): any[] {
    const toolCalls: any[] = [];
    const regex = /<tool_call>\s*(\{[\s\S]*?\})\s*<\/tool_call>/g;
    let match;
    let index = 0;

    while ((match = regex.exec(content)) !== null) {
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
        console.warn('Failed to parse tool call:', match[1], e);
      }
    }

    return toolCalls;
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

      // Execute ALL tool calls in parallel
      const toolResults = await Promise.all(
        toolCalls.map(async (toolCall: any) => {
          const toolName = toolCall.function.name;
          const args = JSON.parse(toolCall.function.arguments);
          return this.executeToolByName(toolCall.id, toolName, args);
        })
      );

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
