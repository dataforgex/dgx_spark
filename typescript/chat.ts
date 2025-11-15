#!/usr/bin/env node

/**
 * Interactive Chat Interface for Local LLM
 * TypeScript implementation
 */

import * as readline from 'readline/promises';
import { stdin as input, stdout as output } from 'process';

interface Message {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

interface ChatRequest {
  model: string;
  messages: Message[];
  max_tokens: number;
  temperature: number;
}

interface ChatResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    message: Message;
    finish_reason: string;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}

interface ModelInfo {
  object: string;
  data: Array<{
    id: string;
    max_model_len?: number;
  }>;
}

class ChatInterface {
  private apiUrl: string;
  private model: string;
  private systemMessage: string;
  private maxTokens: number;
  private temperature: number;
  private messages: Message[];
  private maxContextLength: number | null = null;
  private rl: readline.Interface;

  constructor(
    apiUrl: string,
    model: string,
    systemMessage: string,
    maxTokens: number,
    temperature: number
  ) {
    this.apiUrl = apiUrl;
    this.model = model;
    this.systemMessage = systemMessage;
    this.maxTokens = maxTokens;
    this.temperature = temperature;
    this.messages = [{ role: 'system', content: systemMessage }];
    this.rl = readline.createInterface({ input, output });
  }

  async initialize(): Promise<void> {
    await this.fetchModelInfo();
  }

  private async fetchModelInfo(): Promise<void> {
    try {
      const baseUrl = this.apiUrl.replace(/\/v1\/chat\/completions$/, '');
      const modelsUrl = `${baseUrl}/v1/models`;

      const response = await fetch(modelsUrl, {
        signal: AbortSignal.timeout(5000),
      });

      if (!response.ok) return;

      const data = await response.json() as ModelInfo;
      const modelData = data.data.find(m => m.id === this.model);

      if (modelData?.max_model_len) {
        this.maxContextLength = modelData.max_model_len;
      }
    } catch {
      // Silently fail if we can't get model info
    }
  }

  private printBanner(): void {
    console.log('='.repeat(70));
    console.log('🤖  Interactive Chat with Local LLM');
    console.log('='.repeat(70));
    console.log(`Model: ${this.model}`);
    console.log(`API: ${this.apiUrl}`);
    if (this.maxContextLength) {
      console.log(`Max Context: ${this.formatNumber(this.maxContextLength)} tokens`);
    }
    console.log(`Max Output: ${this.formatNumber(this.maxTokens)} tokens`);
    console.log(`Temperature: ${this.temperature}`);
    console.log('\nCommands:');
    console.log('  - Type your message and press Enter to chat');
    console.log("  - Type '/exit' or '/quit' to end the conversation");
    console.log("  - Type '/clear' to clear conversation history");
    console.log("  - Type '/history' to see conversation history");
    console.log('='.repeat(70));
    console.log();
  }

  private async sendMessage(userInput: string): Promise<string> {
    // Add user message to history
    this.messages.push({ role: 'user', content: userInput });

    // Prepare API request
    const payload: ChatRequest = {
      model: this.model,
      messages: this.messages,
      max_tokens: this.maxTokens,
      temperature: this.temperature,
    };

    try {
      const response = await fetch(this.apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`API error: ${response.status} - ${errorText}`);
      }

      const result = await response.json() as ChatResponse;

      if (!result.choices || result.choices.length === 0) {
        throw new Error('No response from API');
      }

      const assistantMessage = result.choices[0].message.content;

      // Add assistant response to history
      this.messages.push({ role: 'assistant', content: assistantMessage });

      return assistantMessage;
    } catch (error) {
      // Remove the failed user message from history
      this.messages.pop();
      throw error;
    }
  }

  private clearHistory(): void {
    this.messages = [{ role: 'system', content: this.systemMessage }];
    console.log('✅ Conversation history cleared.');
  }

  private showHistory(): void {
    console.log();
    console.log('='.repeat(70));
    console.log('📜 Conversation History');
    console.log('='.repeat(70));

    for (const msg of this.messages) {
      const role = msg.role.toUpperCase();
      console.log(`\n[${role}]`);
      console.log(msg.content);
    }

    console.log('='.repeat(70));
    console.log();
  }

  private formatNumber(n: number): string {
    return n.toLocaleString();
  }

  private async typeEffect(text: string): Promise<void> {
    for (const char of text) {
      process.stdout.write(char);
      await new Promise(resolve => setTimeout(resolve, 5));
    }
    console.log();
  }

  async run(): Promise<void> {
    this.printBanner();

    try {
      while (true) {
        const userInput = (await this.rl.question('\n💬 You: ')).trim();

        // Handle empty input
        if (!userInput) {
          continue;
        }

        // Handle commands
        const lowerInput = userInput.toLowerCase();

        if (lowerInput === '/exit' || lowerInput === '/quit') {
          console.log('\n👋 Goodbye!');
          break;
        }

        if (lowerInput === '/clear') {
          this.clearHistory();
          continue;
        }

        if (lowerInput === '/history') {
          this.showHistory();
          continue;
        }

        // Send message and get response
        process.stdout.write('\n🤖 Assistant: ');

        try {
          const response = await this.sendMessage(userInput);
          await this.typeEffect(response);
        } catch (error) {
          console.log(`❌ Error: ${error instanceof Error ? error.message : String(error)}`);
        }
      }
    } finally {
      this.rl.close();
    }
  }
}

// Main execution
async function main() {
  const chat = new ChatInterface(
    'http://localhost:8100/v1/chat/completions',
    'Qwen/Qwen3-Coder-30B-A3B-Instruct',
    'You are a helpful AI assistant. You provide clear, concise, and accurate responses.',
    2048,
    0.7
  );

  await chat.initialize();
  await chat.run();
}

main().catch(console.error);
