"""
Tests for the real-time streaming chunk formatter in ConversationService.

This tests the _format_chunk method that processes LLM output chunks
incrementally to minimize latency for TTS.
"""
from backend.services.conversation_service import ConversationService


def test_format_chunk_removes_emojis():
    """Test that emojis are removed from chunks."""

    input_chunk = "Hello 😊 there! 🎉"
    result = ConversationService._format_chunk(input_chunk)

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_removes_emojis")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr('Hello there! ')}")
    print(f"STATUS:   {'✓ PASSED' if result == 'Hello there! ' else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '😊' not in result, "Should not contain smiley emoji"
    assert '🎉' not in result, "Should not contain party emoji"
    assert 'Hello' in result, "Should contain text"
    assert 'there!' in result, "Should contain text"


def test_format_chunk_replaces_newlines():
    """Test that newlines are replaced with spaces."""
    input_chunk = "Line 1\nLine 2\nLine 3"
    result = ConversationService._format_chunk(input_chunk)

    expected = "Line 1 Line 2 Line 3"

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_replaces_newlines")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"STATUS:   {'✓ PASSED' if result == expected else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '\n' not in result, "Should not contain newlines"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_format_chunk_collapses_spaces():
    """Test that multiple spaces are collapsed to single spaces."""
    input_chunk = "Too    many     spaces"
    result = ConversationService._format_chunk(input_chunk)

    expected = "Too many spaces"

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_collapses_spaces")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"STATUS:   {'✓ PASSED' if result == expected else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '  ' not in result, "Should not contain double spaces"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_format_chunk_handles_mixed_content():
    """Test chunk with emojis, newlines, and multiple spaces."""
    input_chunk = "Hello! 😊\n\nHow are    you? 🎉"
    result = ConversationService._format_chunk(input_chunk)

    expected = "Hello! How are you?"

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_handles_mixed_content")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"STATUS:   {'✓ PASSED' if result == expected else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '😊' not in result, "Should not contain emoji"
    assert '🎉' not in result, "Should not contain emoji"
    assert '\n' not in result, "Should not contain newlines"
    assert '  ' not in result, "Should not contain double spaces"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_format_chunk_incremental_processing():
    """Test that chunks can be processed incrementally and concatenated."""
    # Simulate streaming chunks
    chunk1 = "Hello 😊"
    chunk2 = " how\nare"
    chunk3 = " you? 🎉"

    result1 = ConversationService._format_chunk(chunk1)
    result2 = ConversationService._format_chunk(chunk2)
    result3 = ConversationService._format_chunk(chunk3)

    combined = result1 + result2 + result3
    expected = "Hello how are you?"

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_incremental_processing")
    print(f"{'-'*80}")
    print(f"CHUNK 1:  {repr(chunk1)} -> {repr(result1)}")
    print(f"CHUNK 2:  {repr(chunk2)} -> {repr(result2)}")
    print(f"CHUNK 3:  {repr(chunk3)} -> {repr(result3)}")
    print(f"COMBINED: {repr(combined)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"STATUS:   {'✓ PASSED' if combined == expected else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '😊' not in combined, "Should not contain emoji"
    assert '🎉' not in combined, "Should not contain emoji"
    assert '\n' not in combined, "Should not contain newlines"
    assert combined == expected, f"Expected '{expected}', got '{combined}'"


def test_format_chunk_empty_string():
    """Test that empty chunks return empty strings."""
    result = ConversationService._format_chunk("")

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_empty_string")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr('')}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr('')}")
    print(f"STATUS:   {'✓ PASSED' if result == '' else '✗ FAILED'}")
    print(f"{'='*80}")

    assert result == "", f"Expected empty string, got '{result}'"


def test_format_chunk_zwj_emoji():
    """Test removal of complex emoji sequences (ZWJ)."""
    input_chunk = "Family 👨‍👩‍👧‍👦 time!"
    result = ConversationService._format_chunk(input_chunk)

    expected = "Family time!"

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_zwj_emoji")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"STATUS:   {'✓ PASSED' if result == expected else '✗ FAILED'}")
    print(f"{'='*80}")

    assert '👨' not in result, "Should not contain any part of family emoji"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_format_chunk_preserves_punctuation():
    """Test that punctuation is preserved."""
    input_chunk = "Hello! How are you? I'm fine, thanks."
    result = ConversationService._format_chunk(input_chunk)

    print(f"\n{'='*80}")
    print(f"TEST: test_format_chunk_preserves_punctuation")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_chunk)}")
    print(f"OUTPUT:   {repr(result)}")
    print(f"STATUS:   {'✓ PASSED' if result == input_chunk else '✗ FAILED'}")
    print(f"{'='*80}")

    assert result == input_chunk, "Should preserve punctuation exactly"
    assert '!' in result and '?' in result and ',' in result and "'" in result


if __name__ == '__main__':
    print("\n" + "="*80)
    print("RUNNING STREAMING CHUNK FORMATTER TEST SUITE")
    print("="*80)

    test_functions = [
        test_format_chunk_removes_emojis,
        test_format_chunk_replaces_newlines,
        test_format_chunk_collapses_spaces,
        test_format_chunk_handles_mixed_content,
        test_format_chunk_incremental_processing,
        test_format_chunk_empty_string,
        test_format_chunk_zwj_emoji,
        test_format_chunk_preserves_punctuation,
    ]

    passed = 0
    failed = 0

    for test_func in test_functions:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"\n❌ FAILED: {test_func.__name__}")
            print(f"   Error: {e}")
        except Exception as e:
            failed += 1
            print(f"\n💥 ERROR: {test_func.__name__}")
            print(f"   {type(e).__name__}: {e}")

    print("\n" + "="*80)
    print(f"TEST SUITE COMPLETE")
    print(f"PASSED: {passed}/{len(test_functions)}")
    print(f"FAILED: {failed}/{len(test_functions)}")
    print("="*80 + "\n")

    if failed > 0:
        raise SystemExit(1)
