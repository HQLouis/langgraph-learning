#!/usr/bin/env python3
"""
Simple test script to validate the prompt repository implementation.
Tests both S3 and fallback scenarios.
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

def test_fallback_mode():
    """Test that prompts work with S3 disabled (fallback mode)."""
    print("=" * 70)
    print("TEST 1: Fallback Mode (S3 Disabled)")
    print("=" * 70)

    try:
        from prompts import (
            getSpeechVocabularyWorker_prompt,
            getSpeechGrammarWorker_prompt,
            getSpeechInteractionWorker_prompt,
            getSpeechComprehensionWorker_prompt,
            getBoredomWorker_prompt
        )

        # Test all prompt functions
        prompts = {
            'Vocabulary': getSpeechVocabularyWorker_prompt,
            'Grammar': getSpeechGrammarWorker_prompt,
            'Interaction': getSpeechInteractionWorker_prompt,
            'Comprehension': getSpeechComprehensionWorker_prompt,
            'Boredom': getBoredomWorker_prompt
        }

        for name, func in prompts.items():
            prompt = func()
            print(f"✓ {name} Worker: {len(prompt)} characters loaded")
            assert len(prompt) > 0, f"{name} prompt is empty"
            assert "Rolle:" in prompt, f"{name} prompt doesn't contain expected content"

        print("\n✅ All prompts loaded successfully in fallback mode!\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_repository_cache():
    """Test that the repository caching works."""
    print("=" * 70)
    print("TEST 2: Repository Cache")
    print("=" * 70)

    try:
        from prompt_repository import get_prompt_repository

        repo = get_prompt_repository()

        # First call - should use fallback
        prompt1 = repo.get_prompt('speech_vocabulary_worker')
        print(f"✓ First call: {len(prompt1)} characters")

        # Second call - should hit cache
        prompt2 = repo.get_prompt('speech_vocabulary_worker')
        print(f"✓ Second call: {len(prompt2)} characters (cached)")

        # Verify they're the same
        assert prompt1 == prompt2, "Cached prompt differs from original"

        print("\n✅ Cache working correctly!\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_configuration():
    """Test that configuration is loaded correctly."""
    print("=" * 70)
    print("TEST 3: Configuration Loading")
    print("=" * 70)

    try:
        from backend.core.config import get_settings

        settings = get_settings()

        print(f"✓ App Name: {settings.app_name}")
        print(f"✓ AWS Region: {settings.aws_region}")
        print(f"✓ S3 Bucket: {settings.aws_s3_bucket_name or '(not set)'}")
        print(f"✓ S3 Prefix: {settings.aws_s3_prompts_prefix}")
        print(f"✓ Use S3 Prompts: {settings.use_s3_prompts}")
        print(f"✓ Cache TTL: {settings.prompts_cache_ttl} seconds")

        print("\n✅ Configuration loaded successfully!\n")
        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PROMPT REPOSITORY VALIDATION TESTS")
    print("=" * 70 + "\n")

    results = []

    # Run tests
    results.append(("Configuration", test_configuration()))
    results.append(("Fallback Mode", test_fallback_mode()))
    results.append(("Cache", test_repository_cache()))

    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    for name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{name}: {status}")

    all_passed = all(result[1] for result in results)

    print("=" * 70)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("=" * 70 + "\n")

    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())

