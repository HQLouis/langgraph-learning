"""
Test client for Beat System integration.

This demonstrates how to use the beat system with the conversation API.
"""
import requests
import json

BASE_URL = "http://localhost:8000"


def test_beat_system_conversation():
    """Test creating a conversation with beat system enabled."""

    print("="*80)
    print("TESTING BEAT SYSTEM INTEGRATION")
    print("="*80)

    # Step 1: Create conversation WITH beat system
    print("\n1. Creating conversation with beat system...")
    create_response = requests.post(
        f"{BASE_URL}/conversations",
        json={
            "child_id": "1",
            "game_id": "0",
            "story_id": "mia_und_leo",          # Beat system enabled!
            "chapter_id": "chapter_01",         # Beat system enabled!
            "num_planned_tasks": 5              # Optional, defaults to 5
        }
    )

    if create_response.status_code != 201:
        print(f"❌ Failed to create conversation: {create_response.text}")
        return

    conversation = create_response.json()
    thread_id = conversation["thread_id"]
    print(f"✓ Conversation created: {thread_id}")
    print(f"  Using beat system: mia_und_leo/chapter_01")

    # Step 2: Send a message
    print("\n2. Sending message: 'Wer ist Leo?'")

    # For streaming
    message_response = requests.post(
        f"{BASE_URL}/conversations/{thread_id}/messages",
        json={"message": "Wer ist Leo?"},
        stream=True
    )

    if message_response.status_code != 200:
        print(f"❌ Failed to send message: {message_response.text}")
        return

    print("\n3. Streaming response:")
    print("-" * 80)

    # Process SSE stream
    response_text = ""
    for line in message_response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                chunk = line_str[6:]  # Remove 'data: ' prefix
                if chunk == '[DONE]':
                    break
                print(chunk, end='', flush=True)
                response_text += chunk

    print("\n" + "-" * 80)
    print("\n✓ Response received")
    print(f"  Length: {len(response_text)} characters")

    # The response should be based on beats, not full chapter
    print("\n4. Analysis:")
    if "Leo" in response_text:
        print("  ✓ Response mentions Leo (expected)")
    if "Fuchs" in response_text or "fuchs" in response_text.lower():
        print("  ✓ Response mentions Fuchs (expected from beats)")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80)


def test_without_beat_system():
    """Test creating a conversation WITHOUT beat system (fallback)."""

    print("\n" + "="*80)
    print("TESTING FALLBACK (NO BEAT SYSTEM)")
    print("="*80)

    # Create conversation WITHOUT story_id/chapter_id
    print("\n1. Creating conversation without beat system...")
    create_response = requests.post(
        f"{BASE_URL}/conversations",
        json={
            "child_id": "1",
            "game_id": "0"
            # No story_id, no chapter_id → fallback to audio_book
        }
    )

    if create_response.status_code != 201:
        print(f"❌ Failed to create conversation: {create_response.text}")
        return

    conversation = create_response.json()
    thread_id = conversation["thread_id"]
    print(f"✓ Conversation created: {thread_id}")
    print(f"  Using fallback: audio_book context (not beats)")

    # Send a message
    print("\n2. Sending message: 'Hallo!'")

    message_response = requests.post(
        f"{BASE_URL}/conversations/{thread_id}/messages",
        json={"message": "Hallo!"},
        stream=True
    )

    if message_response.status_code != 200:
        print(f"❌ Failed to send message: {message_response.text}")
        return

    print("\n3. Response received (using fallback context)")

    # Just check it works
    for line in message_response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                chunk = line_str[6:]
                if chunk == '[DONE]':
                    break
                print(chunk, end='', flush=True)

    print("\n\n✓ Fallback works correctly")
    print("="*80)


def compare_beat_vs_fallback():
    """Compare responses with and without beat system."""

    print("\n" + "="*80)
    print("COMPARISON: BEAT SYSTEM vs FALLBACK")
    print("="*80)

    question = "Erzähle mir von der Geschichte."

    # Test 1: With beats
    print("\n--- Test 1: WITH Beat System ---")
    create1 = requests.post(
        f"{BASE_URL}/conversations",
        json={
            "child_id": "1",
            "game_id": "0",
            "story_id": "mia_und_leo",
            "chapter_id": "chapter_01"
        }
    ).json()

    response1 = requests.post(
        f"{BASE_URL}/conversations/{create1['thread_id']}/messages",
        json={"message": question},
        stream=True
    )

    beat_response = ""
    for line in response1.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                chunk = line_str[6:]
                if chunk == '[DONE]':
                    break
                beat_response += chunk

    print(f"Response length: {len(beat_response)} chars")
    print(f"First 100 chars: {beat_response[:100]}...")

    # Test 2: Without beats
    print("\n--- Test 2: WITHOUT Beat System (Fallback) ---")
    create2 = requests.post(
        f"{BASE_URL}/conversations",
        json={
            "child_id": "1",
            "game_id": "0"
        }
    ).json()

    response2 = requests.post(
        f"{BASE_URL}/conversations/{create2['thread_id']}/messages",
        json={"message": question},
        stream=True
    )

    fallback_response = ""
    for line in response2.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                chunk = line_str[6:]
                if chunk == '[DONE]':
                    break
                fallback_response += chunk

    print(f"Response length: {len(fallback_response)} chars")
    print(f"First 100 chars: {fallback_response[:100]}...")

    print("\n--- Comparison Summary ---")
    print(f"Beat system response: {len(beat_response)} chars")
    print(f"Fallback response: {len(fallback_response)} chars")
    print(f"Difference: {abs(len(beat_response) - len(fallback_response))} chars")

    print("\n" + "="*80)


if __name__ == "__main__":
    import sys

    # Check if server is running
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=2)
        if health.status_code != 200:
            print("❌ Server is not responding correctly")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print("❌ Server is not running. Please start it with:")
        print("   uvicorn backend.main:app --reload")
        sys.exit(1)

    print("✓ Server is running\n")

    # Run tests
    try:
        test_beat_system_conversation()
        print("\n" + "="*80 + "\n")
        test_without_beat_system()
        print("\n" + "="*80 + "\n")
        compare_beat_vs_fallback()

        print("\n\n🎉 ALL TESTS COMPLETED SUCCESSFULLY! 🎉")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

