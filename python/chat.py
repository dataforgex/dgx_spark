#!/usr/bin/env python3
"""
Interactive Chat Interface for Local LLM
Similar to ChatGPT/Claude web interface
"""

import requests
import json
from typing import List, Dict

class ChatInterface:
    def __init__(self,
                 api_url: str = "http://localhost:8100/v1/chat/completions",
                 model: str = "Qwen/Qwen3-Coder-30B-A3B-Instruct",
                 system_message: str = "You are a helpful AI assistant.",
                 max_tokens: int = 2048,
                 temperature: float = 0.7):
        """
        Initialize the chat interface.

        Args:
            api_url: The API endpoint URL
            model: The model name to use
            system_message: System message to set assistant behavior
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0 to 1.0)
        """
        self.api_url = api_url
        self.model = model
        self.system_message = system_message
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_message}
        ]
        self.max_context_length = None
        self._fetch_model_info()

    def _fetch_model_info(self):
        """Fetch model information including max context length."""
        try:
            base_url = self.api_url.rsplit('/v1/', 1)[0]
            models_url = f"{base_url}/v1/models"
            response = requests.get(models_url, timeout=5)
            response.raise_for_status()
            data = response.json()

            # Find our model in the list
            for model_data in data.get("data", []):
                if model_data.get("id") == self.model:
                    self.max_context_length = model_data.get("max_model_len")
                    break
        except Exception:
            # Silently fail if we can't get model info
            pass

    def print_banner(self):
        """Print welcome banner."""
        print("=" * 70)
        print("🤖  Interactive Chat with Local LLM")
        print("=" * 70)
        print(f"Model: {self.model}")
        print(f"API: {self.api_url}")
        if self.max_context_length:
            print(f"Max Context: {self.max_context_length:,} tokens")
        print(f"Max Output: {self.max_tokens:,} tokens")
        print(f"Temperature: {self.temperature}")
        print("\nCommands:")
        print("  - Type your message and press Enter to chat")
        print("  - Type '/exit' or '/quit' to end the conversation")
        print("  - Type '/clear' to clear conversation history")
        print("  - Type '/history' to see conversation history")
        print("=" * 70)
        print()

    def send_message(self, user_input: str) -> str:
        """
        Send a message to the LLM and get response.

        Args:
            user_input: The user's message

        Returns:
            The assistant's response
        """
        # Add user message to history
        self.messages.append({"role": "user", "content": user_input})

        # Prepare API request
        payload = {
            "model": self.model,
            "messages": self.messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature
        }

        try:
            # Send request
            response = requests.post(
                self.api_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60
            )
            response.raise_for_status()

            # Parse response
            result = response.json()
            assistant_message = result["choices"][0]["message"]["content"]

            # Add assistant response to history
            self.messages.append({"role": "assistant", "content": assistant_message})

            return assistant_message

        except requests.exceptions.RequestException as e:
            return f"❌ Error communicating with API: {str(e)}"
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            return f"❌ Error parsing API response: {str(e)}"

    def clear_history(self):
        """Clear conversation history but keep system message."""
        self.messages = [{"role": "system", "content": self.system_message}]
        print("✅ Conversation history cleared.")

    def show_history(self):
        """Display conversation history."""
        print("\n" + "=" * 70)
        print("📜 Conversation History")
        print("=" * 70)
        for msg in self.messages:
            role = msg["role"].upper()
            content = msg["content"]
            if role == "SYSTEM":
                print(f"\n[{role}]")
                print(f"{content}")
            else:
                print(f"\n[{role}]")
                print(f"{content}")
        print("=" * 70 + "\n")

    def run(self):
        """Main chat loop."""
        self.print_banner()

        while True:
            try:
                # Get user input
                user_input = input("\n💬 You: ").strip()

                # Handle empty input
                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ['/exit', '/quit']:
                    print("\n👋 Goodbye!")
                    break

                elif user_input.lower() == '/clear':
                    self.clear_history()
                    continue

                elif user_input.lower() == '/history':
                    self.show_history()
                    continue

                # Send message and get response
                print("\n🤖 Assistant: ", end="", flush=True)
                response = self.send_message(user_input)

                # Print response with typing effect
                for char in response:
                    print(char, end="", flush=True)
                print()  # New line after response

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except EOFError:
                print("\n\n👋 Goodbye!")
                break


def main():
    """Main entry point."""
    # You can customize these parameters
    chat = ChatInterface(
        api_url="http://localhost:8100/v1/chat/completions",
        model="Qwen/Qwen3-Coder-30B-A3B-Instruct",
        system_message="You are a helpful AI assistant. You provide clear, concise, and accurate responses.",
        max_tokens=2048,
        temperature=0.7
    )

    chat.run()


if __name__ == "__main__":
    main()
