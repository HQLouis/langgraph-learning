"""
Example client for testing the Lingolino API with SSE streaming.

This demonstrates how to interact with the API from a client application.
"""
import requests
import json
import sseclient  # pip install sseclient-py
from typing import Optional


class LingolinoClient:
    """Client for interacting with Lingolino API."""

    def __init__(self, base_url: str = "conversational-ai-alb-dev-1521590126.eu-central-1.elb.amazonaws.com"):
        self.base_url = base_url
        self.session = requests.Session()

    def create_conversation(self, child_id: str, game_id: str) -> dict:
        """
        Create a new conversation.

        Args:
            child_id: ID of the child
            game_id: ID of the game

        Returns:
            Dictionary with thread_id and metadata
        """
        response = self.session.post(
            f"{self.base_url}/conversations",
            json={"child_id": child_id, "game_id": game_id}
        )
        response.raise_for_status()
        return response.json()

    def send_message_streaming(self, thread_id: str, message: str):
        """
        Send a message and receive streaming response.

        Args:
            thread_id: Conversation thread ID
            message: User's message

        Yields:
            Chunks of the AI response as they arrive
        """
        response = self.session.post(
            f"{self.base_url}/conversations/{thread_id}/messages",
            json={"message": message},
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        response.raise_for_status()

        client = sseclient.SSEClient(response)

        for event in client.events():
            if event.data == "[DONE]":
                break
            yield event.data

    def get_conversation_history(self, thread_id: str) -> dict:
        """
        Get conversation history.

        Args:
            thread_id: Conversation thread ID

        Returns:
            Dictionary with conversation history
        """
        response = self.session.get(f"{self.base_url}/conversations/{thread_id}")
        response.raise_for_status()
        return response.json()

    def delete_conversation(self, thread_id: str):
        """
        Delete a conversation.

        Args:
            thread_id: Conversation thread ID
        """
        response = self.session.delete(f"{self.base_url}/conversations/{thread_id}")
        response.raise_for_status()

    def health_check(self) -> dict:
        """Check API health."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()


def main():
    """Example usage of the Lingolino client."""
    client = LingolinoClient()

    print("🏥 Checking API health...")
    health = client.health_check()
    print(f"✅ {health['app_name']} v{health['version']} is {health['status']}\n")

    print("📝 Creating conversation...")
    conversation = client.create_conversation(child_id="1", game_id="0")
    thread_id = conversation["thread_id"]
    print(f"✅ Conversation created: {thread_id}\n")

    # Interactive chat loop
    print("💬 Chat started! Type 'quit' to exit.\n")
    print("="*60)

    while True:
        user_input = input("\n👤 You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['quit', 'exit', 'bye']:
            break

        print("\n🤖 Lino: ", end="", flush=True)

        try:
            for chunk in client.send_message_streaming(thread_id, user_input):
                print(chunk, end="", flush=True)
            print()  # New line
        except Exception as e:
            print(f"\n❌ Error: {e}")

    # Show conversation history
    print("\n📜 Fetching conversation history...")
    history = client.get_conversation_history(thread_id)
    print(f"Conversation had {len(history['messages'])} messages")

    # Clean up
    print("\n🧹 Deleting conversation...")
    client.delete_conversation(thread_id)
    print("✅ Conversation deleted")

    print("\n👋 Goodbye!")


if __name__ == "__main__":
    main()

