/**
 * Example integration with the Chat App
 *
 * This shows how to integrate the Tool Call Sandbox with your existing
 * web-gui chat application.
 */

// Types for the sandbox API
interface ToolSummary {
  name: string;
  description: string;
  version: string;
}

interface OpenAITool {
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

interface ExecuteResponse {
  success: boolean;
  output: string;
  error: string;
  execution_time: number;
  exec_id: string;
}

// Sandbox API client
class ToolSandboxClient {
  private baseUrl: string;

  constructor(host: string = "localhost", port: number = 5176) {
    this.baseUrl = `http://${host}:${port}`;
  }

  // Get all available tools
  async getTools(): Promise<ToolSummary[]> {
    const response = await fetch(`${this.baseUrl}/api/tools`);
    return response.json();
  }

  // Get tools in OpenAI function calling format
  async getOpenAITools(): Promise<OpenAITool[]> {
    const response = await fetch(`${this.baseUrl}/api/tools-openai`);
    return response.json();
  }

  // Execute a tool
  async execute(toolName: string, args: Record<string, unknown>): Promise<ExecuteResponse> {
    const response = await fetch(`${this.baseUrl}/api/execute/${toolName}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ args }),
    });
    return response.json();
  }
}

// Example: Integrate with your existing Chat.tsx
/*

In your Chat.tsx or api.ts, add something like this:

```typescript
import { ToolSandboxClient } from './sandbox-client';

const sandboxClient = new ToolSandboxClient();

// When initializing chat, load available tools
const [availableTools, setAvailableTools] = useState<OpenAITool[]>([]);

useEffect(() => {
  async function loadTools() {
    const tools = await sandboxClient.getOpenAITools();
    setAvailableTools(tools);
  }
  loadTools();
}, []);

// In your sendMessage function, include sandbox tools
const payload = {
  model: currentModel,
  messages: conversationMessages,
  tools: [
    SEARCH_TOOL,  // Your existing web search tool
    ...availableTools  // Sandbox tools loaded dynamically
  ],
  tool_choice: "auto"
};

// Handle tool calls from the LLM
if (choice.message.tool_calls) {
  for (const toolCall of choice.message.tool_calls) {
    const { name, arguments: argsStr } = toolCall.function;
    const args = JSON.parse(argsStr);

    let result;

    // Check if it's a sandbox tool
    if (availableTools.some(t => t.function.name === name)) {
      result = await sandboxClient.execute(name, args);
    } else if (name === 'web_search') {
      result = await performWebSearch(args.query);
    }

    // Add tool result to conversation
    conversationMessages.push({
      role: 'tool',
      tool_call_id: toolCall.id,
      name: name,
      content: JSON.stringify(result)
    });
  }

  // Continue conversation with tool results
  // ... make another API call to get final response
}
```

*/

// Test the integration
async function testSandbox() {
  const client = new ToolSandboxClient();

  // List available tools
  console.log("Available tools:");
  const tools = await client.getTools();
  tools.forEach((t) => console.log(`  - ${t.name}: ${t.description}`));

  // Execute code
  console.log("\nExecuting Python code:");
  const result = await client.execute("code_execution", {
    code: "import math; print(f'Pi = {math.pi}')",
    language: "python",
  });
  console.log(result);

  // Execute bash
  console.log("\nExecuting bash command:");
  const bashResult = await client.execute("bash_command", {
    command: "echo 'Hello from sandbox!' && date",
  });
  console.log(bashResult);
}

// Export for use in React app
export { ToolSandboxClient };
export type { ToolSummary, OpenAITool, ExecuteResponse };
