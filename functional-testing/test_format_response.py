"""
Tests for the text formatting logic used in streaming responses.

This tests the formatting logic that removes emojis and normalizes whitespace.
The logic is now implemented in ConversationService._format_chunk for real-time streaming,
but we test the same functionality here to ensure correctness.
"""
import types

# Create minimal stub for emoji library
import sys
emoji_mod = types.ModuleType('emoji')
def replace_emoji(string, replace=''):
    """Stub that removes emoji using a comprehensive regex pattern."""
    import re
    # Comprehensive emoji pattern covering all Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "\U00002600-\U000026FF"  # miscellaneous symbols
        "\U00002B00-\U00002BFF"  # miscellaneous symbols and arrows
        "\U0001F200-\U0001F2FF"  # enclosed ideographic supplement
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0000200D"              # zero width joiner
        "\U0000FE0F"              # variation selector
        "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub(replace, string)

emoji_mod.replace_emoji = replace_emoji
sys.modules['emoji'] = emoji_mod


def format_text_for_tts(text: str) -> str:
    """
    Format text for TTS by removing emojis and normalizing whitespace.
    This replicates the logic used in ConversationService._format_chunk.

    :param text: Raw text to format
    :return: Formatted text suitable for TTS
    """
    import re
    import emoji

    if not text:
        return ""

    # Remove all emojis using the emoji library for comprehensive coverage
    without_emoji = emoji.replace_emoji(str(text), replace='')

    # Remove all line breaks and collapse consecutive whitespace to single spaces
    single_line = re.sub(r"[\r\n]+", " ", without_emoji)
    single_line = re.sub(r"\s+", " ", single_line).strip()

    return single_line


def log_test(test_name, input_content, expected, actual, passed):
    """Log test execution details for visual feedback."""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print(f"{'-'*80}")
    print(f"INPUT:    {repr(input_content)}")
    print(f"EXPECTED: {repr(expected)}")
    print(f"ACTUAL:   {repr(actual)}")
    print(f"STATUS:   {'✓ PASSED' if passed else '✗ FAILED'}")
    print(f"{'='*80}")


def test_remove_emojis_and_newlines():
    """Test emoji and newline removal."""
    input_content = 'Hello 😊\nHow are you?   '
    result = format_text_for_tts(input_content)
    expected = 'Hello How are you?'

    passed = (
        '\n' not in result and
        '😊' not in result and
        'How are you?' in result and
        '  ' not in result and
        result == expected
    )

    log_test('test_remove_emojis_and_newlines', input_content, expected, result, passed)

    assert '\n' not in result, "Should not contain newlines"
    assert '😊' not in result, "Should not contain emoji"
    assert 'How are you?' in result, "Should contain the text"
    assert '  ' not in result, "Should not contain double spaces"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_multiple_lines_with_emoji():
    """Test with multiple lines and emojis."""
    input_content = 'Line1\nLine2\n🙂'
    result = format_text_for_tts(input_content)
    expected = 'Line1 Line2'

    passed = result == expected
    log_test('test_multiple_lines_with_emoji', input_content, expected, result, passed)

    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_empty_string():
    """Test that empty string returns empty."""
    result = format_text_for_tts("")
    expected = ""

    passed = result == expected
    log_test('test_empty_string', '', expected, result, passed)

    assert result == expected, f"Expected empty string, got '{result}'"


def test_zwj_emoji_sequences():
    """Test removal of Zero-Width Joiner (ZWJ) emoji sequences like family emojis."""
    input_content = 'Family time 👨‍👩‍👧‍👦 is great!'
    result = format_text_for_tts(input_content)
    expected = 'Family time is great!'

    passed = result == expected and '👨' not in result
    log_test('test_zwj_emoji_sequences', input_content, expected, result, passed)

    assert '👨' not in result, "Should not contain any part of ZWJ sequence"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_skin_tone_modifiers():
    """Test removal of emojis with skin tone modifiers."""
    input_content = 'Wave 👋🏽 hello!'
    result = format_text_for_tts(input_content)
    expected = 'Wave hello!'

    passed = result == expected and '👋' not in result
    log_test('test_skin_tone_modifiers', input_content, expected, result, passed)

    assert '👋' not in result, "Should not contain emoji with skin tone"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_flag_emojis():
    """Test removal of flag emojis (regional indicator symbols)."""
    input_content = 'Hello from 🇺🇸 and 🇩🇪!'
    result = format_text_for_tts(input_content)
    expected = 'Hello from and !'

    passed = '🇺🇸' not in result and '🇩🇪' not in result
    log_test('test_flag_emojis', input_content, expected, result, passed)

    assert '🇺🇸' not in result, "Should not contain US flag"
    assert '🇩🇪' not in result, "Should not contain German flag"
    assert 'Hello from' in result, "Should contain the text"


def test_mixed_emoji_types():
    """Test removal of multiple emoji types in one text."""
    input_content = '🎉 Party! 🥳 Time to celebrate 🎊 with friends 👯‍♀️'
    result = format_text_for_tts(input_content)
    expected = 'Party! Time to celebrate with friends'

    passed = all(e not in result for e in ['🎉', '🥳', '🎊', '👯'])
    log_test('test_mixed_emoji_types', input_content, expected, result, passed)

    assert '🎉' not in result, "Should not contain party popper"
    assert '🥳' not in result, "Should not contain party face"
    assert '🎊' not in result, "Should not contain confetti"
    assert '👯' not in result, "Should not contain dancers"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_multiple_consecutive_newlines():
    """Test removal of multiple consecutive newlines."""
    input_content = 'Line 1\n\n\nLine 2\n\n\n\nLine 3'
    result = format_text_for_tts(input_content)
    expected = 'Line 1 Line 2 Line 3'

    passed = '\n' not in result and result == expected
    log_test('test_multiple_consecutive_newlines', input_content, expected, result, passed)

    assert '\n' not in result, "Should not contain any newlines"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_carriage_return_handling():
    """Test removal of carriage returns (\\r)."""
    input_content = 'Text with\rcarriage\r\nreturns'
    result = format_text_for_tts(input_content)
    expected = 'Text with carriage returns'

    passed = '\r' not in result and '\n' not in result and result == expected
    log_test('test_carriage_return_handling', input_content, expected, result, passed)

    assert '\r' not in result, "Should not contain carriage returns"
    assert '\n' not in result, "Should not contain newlines"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_excessive_whitespace_collapse():
    """Test that excessive whitespace is collapsed to single spaces."""
    input_content = 'Too    many        spaces     here'
    result = format_text_for_tts(input_content)
    expected = 'Too many spaces here'

    passed = '  ' not in result and result == expected
    log_test('test_excessive_whitespace_collapse', input_content, expected, result, passed)

    assert '  ' not in result, "Should not contain double spaces"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_leading_trailing_whitespace():
    """Test that leading and trailing whitespace is stripped."""
    input_content = '   Leading and trailing spaces   '
    result = format_text_for_tts(input_content)
    expected = 'Leading and trailing spaces'

    passed = result == expected and not result.startswith(' ') and not result.endswith(' ')
    log_test('test_leading_trailing_whitespace', input_content, expected, result, passed)

    assert not result.startswith(' '), "Should not have leading spaces"
    assert not result.endswith(' '), "Should not have trailing spaces"
    assert result == expected, f"Expected '{expected}', got '{result}'"


def test_complex_real_world_example():
    """Test complex real-world scenario with emojis, newlines, and spacing."""
    input_content = '''🌟 Hello there! 👋

I hope you're doing well today! 😊

Let me share something exciting:
✨ New features coming soon! 🚀

Looking forward to it! 🎉🎊'''

    result = format_text_for_tts(input_content)
    expected = "Hello there! I hope you're doing well today! Let me share something exciting: New features coming soon! Looking forward to it!"

    # Check no emojis remain
    emojis = ['🌟', '👋', '😊', '✨', '🚀', '🎉', '🎊']
    has_no_emojis = all(e not in result for e in emojis)
    has_no_newlines = '\n' not in result

    passed = has_no_emojis and has_no_newlines and result == expected
    log_test('test_complex_real_world_example', input_content[:50] + '...', expected, result, passed)

    for emoji in emojis:
        assert emoji not in result, f"Should not contain emoji {emoji}"
    assert '\n' not in result, "Should not contain newlines"
    assert result == expected, f"Expected '{expected}', got '{result}'"


# Run all tests if executed directly
if __name__ == '__main__':
    print("\n" + "="*80)
    print("RUNNING TEXT FORMATTING TEST SUITE")
    print("Testing the formatting logic used in ConversationService._format_chunk")
    print("="*80)

    test_functions = [
        test_remove_emojis_and_newlines,
        test_multiple_lines_with_emoji,
        test_empty_string,
        test_zwj_emoji_sequences,
        test_skin_tone_modifiers,
        test_flag_emojis,
        test_mixed_emoji_types,
        test_multiple_consecutive_newlines,
        test_carriage_return_handling,
        test_excessive_whitespace_collapse,
        test_leading_trailing_whitespace,
        test_complex_real_world_example,
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
