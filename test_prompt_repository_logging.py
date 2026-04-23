#!/usr/bin/env python
"""
Test script to verify prompt_repository logging works correctly.
This demonstrates that prompt repository logs will appear in CloudWatch.
"""
import sys
sys.path.insert(0, '.')

# Setup logging first (as main.py would do)
from backend.core.logging_config import setup_logging
setup_logging()

# Now import and use the prompt repository
from agentic_system.prompt_repository import PromptRepository, get_prompt_repository

print("\n=== Testing Prompt Repository Logging ===\n")

# Get repository instance
repo = get_prompt_repository()

# Register a test fallback
def test_fallback():
    return "Test fallback prompt content"

repo.register_fallback('test_prompt', test_fallback)

# Try to get a prompt (will use fallback since S3 is likely not configured locally)
try:
    prompt = repo.get_prompt('test_prompt')
    print(f"\nRetrieved prompt: {prompt[:50]}...\n")
except Exception as e:
    print(f"\nError: {e}\n")

# Try to clear cache
repo.clear_cache()

print("\n=== Prompt Repository Logging Test Complete ===")
print("All logs above will appear in CloudWatch after deployment to AWS ECS")
print("CloudWatch Log Group: /ecs/conversational-ai-api\n")

