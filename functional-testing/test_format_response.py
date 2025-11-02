import types

# Create minimal stub modules for external dependencies so we can import nodes.py in tests
import sys

# emoji stub
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

# langchain_core.messages stub
lc = types.ModuleType('langchain_core')
lc_messages = types.ModuleType('langchain_core.messages')
class SystemMessage:
    def __init__(self, content=None):
        self.content = content
class HumanMessage:
    def __init__(self, content=None):
        self.content = content
class AIMessage:
    def __init__(self, content=None):
        self.content = content
class RemoveMessage:
    def __init__(self, id=None):
        self.id = id
lc_messages.SystemMessage = SystemMessage
lc_messages.HumanMessage = HumanMessage
lc_messages.AIMessage = AIMessage
lc_messages.RemoveMessage = RemoveMessage
sys.modules['langchain_core'] = types.ModuleType('langchain_core')
sys.modules['langchain_core.messages'] = lc_messages

# langgraph.types stub
lg_types = types.ModuleType('langgraph.types')
class Command:
    def __init__(self, update=None):
        self.update = update
lg_types.Command = Command
sys.modules['langgraph.types'] = lg_types

# states stub
states_mod = types.ModuleType('states')
class State(dict):
    pass
class BackgroundState(dict):
    pass
states_mod.State = State
states_mod.BackgroundState = BackgroundState
sys.modules['states'] = states_mod

# data_loaders stub
dl = types.ModuleType('data_loaders')
def get_game_by_id(state):
    return ''
def get_child_profile(state):
    return ''
dl.get_game_by_id = get_game_by_id
dl.get_child_profile = get_child_profile
sys.modules['data_loaders'] = dl

# worker_prompts stub
wp = types.ModuleType('worker_prompts')
wp.speechVocabularyWorker_prompt = 'vocab prompt'
wp.speechGrammarWorker_prompt = 'grammar prompt'
wp.speechInteractionWorker_prompt = 'interaction prompt'
wp.speechComprehensionWorker_prompt = 'comprehension prompt'
wp.boredomWorker_prompt = 'boredom prompt'
sys.modules['worker_prompts'] = wp

# master_prompts stub
mp = types.ModuleType('master_prompts')
mp.master_prompt = 'master prompt'
sys.modules['master_prompts'] = mp

# Now import the target module by path
import importlib.util
from pathlib import Path
MODULE_PATH = Path(__file__).resolve().parents[1] / 'agentic-system' / 'nodes.py'
spec = importlib.util.spec_from_file_location('agentic_system_nodes', str(MODULE_PATH))
nodes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nodes)

format_response = nodes.format_response
AIMessage = nodes.AIMessage
RemoveMessage = nodes.RemoveMessage


def mk_msg(content, id='m1'):
    """Create a simple object with content and id attributes."""
    return types.SimpleNamespace(content=content, id=id)


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


def test_remove_emojis_and_newlines_object_message():
    """Test emoji and newline removal with object-style message."""
    input_content = 'Hello 😊\nHow are you?   '
    s = {'messages': [mk_msg(input_content, 'msg1')]}
    out = format_response(s, None)
    msgs = out['messages']

    # Should remove raw message and add cleaned AIMessage
    has_remove = any(isinstance(m, RemoveMessage) for m in msgs)
    ai = [m for m in msgs if isinstance(m, AIMessage)][0]

    expected = 'Hello How are you?'
    actual = ai.content

    passed = (
        has_remove and
        '\n' not in actual and
        '😊' not in actual and
        'How are you?' in actual and
        '  ' not in actual and
        actual == expected
    )

    log_test('test_remove_emojis_and_newlines_object_message', input_content, expected, actual, passed)

    assert has_remove, "Should contain RemoveMessage"
    assert '\n' not in actual, "Should not contain newlines"
    assert '😊' not in actual, "Should not contain emoji"
    assert 'How are you?' in actual, "Should contain the text"
    assert '  ' not in actual, "Should not contain double spaces"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_dict_message_input():
    """Test with dict-style message input."""
    input_content = 'Line1\nLine2\n🙂'
    s = {'messages': [{'content': input_content, 'id': 'msg2'}]}
    out = format_response(s, None)
    msgs = out['messages']
    ai = [m for m in msgs if isinstance(m, AIMessage)][0]

    expected = 'Line1 Line2'
    actual = ai.content

    passed = actual == expected
    log_test('test_dict_message_input', input_content, expected, actual, passed)

    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_empty_messages_returns_empty_dict():
    """Test that empty messages list returns empty dict."""
    s = {'messages': []}
    out = format_response(s, None)

    expected = {}
    actual = out

    passed = actual == expected
    log_test('test_empty_messages_returns_empty_dict', 'No messages', expected, actual, passed)

    assert actual == expected, f"Expected {expected}, got {actual}"


def test_non_string_content_handling():
    """Test that non-string content is converted to string."""
    input_content = 12345
    s = {'messages': [mk_msg(input_content, 'num1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = '12345'
    actual = ai.content

    passed = actual == expected
    log_test('test_non_string_content_handling', input_content, expected, actual, passed)

    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_zwj_emoji_sequences():
    """Test removal of Zero-Width Joiner (ZWJ) emoji sequences like family emojis."""
    input_content = 'Family time 👨‍👩‍👧‍👦 is great!'
    s = {'messages': [mk_msg(input_content, 'zwj1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Family time is great!'
    actual = ai.content

    passed = actual == expected and '👨' not in actual
    log_test('test_zwj_emoji_sequences', input_content, expected, actual, passed)

    assert '👨' not in actual, "Should not contain any part of ZWJ sequence"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_skin_tone_modifiers():
    """Test removal of emojis with skin tone modifiers."""
    input_content = 'Wave 👋🏽 hello!'
    s = {'messages': [mk_msg(input_content, 'skin1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Wave hello!'
    actual = ai.content

    passed = actual == expected and '👋' not in actual
    log_test('test_skin_tone_modifiers', input_content, expected, actual, passed)

    assert '👋' not in actual, "Should not contain emoji with skin tone"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_flag_emojis():
    """Test removal of flag emojis (regional indicator symbols)."""
    input_content = 'Hello from 🇺🇸 and 🇩🇪!'
    s = {'messages': [mk_msg(input_content, 'flag1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Hello from and !'
    actual = ai.content

    passed = '🇺🇸' not in actual and '🇩🇪' not in actual
    log_test('test_flag_emojis', input_content, expected, actual, passed)

    assert '🇺🇸' not in actual, "Should not contain US flag"
    assert '🇩🇪' not in actual, "Should not contain German flag"
    assert 'Hello from' in actual, "Should contain the text"


def test_mixed_emoji_types():
    """Test removal of multiple emoji types in one text."""
    input_content = '🎉 Party! 🥳 Time to celebrate 🎊 with friends 👯‍♀️'
    s = {'messages': [mk_msg(input_content, 'mixed1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Party! Time to celebrate with friends'
    actual = ai.content

    passed = all(e not in actual for e in ['🎉', '🥳', '🎊', '👯'])
    log_test('test_mixed_emoji_types', input_content, expected, actual, passed)

    assert '🎉' not in actual, "Should not contain party popper"
    assert '🥳' not in actual, "Should not contain party face"
    assert '🎊' not in actual, "Should not contain confetti"
    assert '👯' not in actual, "Should not contain dancers"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_multiple_consecutive_newlines():
    """Test removal of multiple consecutive newlines."""
    input_content = 'Line 1\n\n\nLine 2\n\n\n\nLine 3'
    s = {'messages': [mk_msg(input_content, 'multi_nl')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Line 1 Line 2 Line 3'
    actual = ai.content

    passed = '\n' not in actual and actual == expected
    log_test('test_multiple_consecutive_newlines', input_content, expected, actual, passed)

    assert '\n' not in actual, "Should not contain any newlines"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_carriage_return_handling():
    """Test removal of carriage returns (\\r)."""
    input_content = 'Text with\rcarriage\r\nreturns'
    s = {'messages': [mk_msg(input_content, 'cr1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Text with carriage returns'
    actual = ai.content

    passed = '\r' not in actual and '\n' not in actual and actual == expected
    log_test('test_carriage_return_handling', input_content, expected, actual, passed)

    assert '\r' not in actual, "Should not contain carriage returns"
    assert '\n' not in actual, "Should not contain newlines"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_excessive_whitespace_collapse():
    """Test that excessive whitespace is collapsed to single spaces."""
    input_content = 'Too    many        spaces     here'
    s = {'messages': [mk_msg(input_content, 'space1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Too many spaces here'
    actual = ai.content

    passed = '  ' not in actual and actual == expected
    log_test('test_excessive_whitespace_collapse', input_content, expected, actual, passed)

    assert '  ' not in actual, "Should not contain double spaces"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_leading_trailing_whitespace():
    """Test that leading and trailing whitespace is stripped."""
    input_content = '   Leading and trailing spaces   '
    s = {'messages': [mk_msg(input_content, 'trim1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = 'Leading and trailing spaces'
    actual = ai.content

    passed = actual == expected and not actual.startswith(' ') and not actual.endswith(' ')
    log_test('test_leading_trailing_whitespace', input_content, expected, actual, passed)

    assert not actual.startswith(' '), "Should not have leading spaces"
    assert not actual.endswith(' '), "Should not have trailing spaces"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_complex_real_world_example():
    """Test complex real-world scenario with emojis, newlines, and spacing."""
    input_content = '''🌟 Hello there! 👋

I hope you're doing well today! 😊

Let me share something exciting:
✨ New features coming soon! 🚀

Looking forward to it! 🎉🎊'''

    s = {'messages': [mk_msg(input_content, 'complex1')]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = "Hello there! I hope you're doing well today! Let me share something exciting: New features coming soon! Looking forward to it!"
    actual = ai.content

    # Check no emojis remain
    emojis = ['🌟', '👋', '😊', '✨', '🚀', '🎉', '🎊']
    has_no_emojis = all(e not in actual for e in emojis)
    has_no_newlines = '\n' not in actual

    passed = has_no_emojis and has_no_newlines and actual == expected
    log_test('test_complex_real_world_example', input_content[:50] + '...', expected, actual, passed)

    for emoji in emojis:
        assert emoji not in actual, f"Should not contain emoji {emoji}"
    assert '\n' not in actual, "Should not contain newlines"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_message_without_id():
    """Test that messages without ID don't cause RemoveMessage."""
    input_content = 'Test message 😊'
    msg = types.SimpleNamespace(content=input_content)  # No id attribute
    s = {'messages': [msg]}
    out = format_response(s, None)
    msgs = out['messages']

    has_remove = any(isinstance(m, RemoveMessage) for m in msgs)
    ai = [m for m in msgs if isinstance(m, AIMessage)][0]

    expected = 'Test message'
    actual = ai.content

    passed = not has_remove and actual == expected
    log_test('test_message_without_id', input_content, expected, actual, passed)

    assert not has_remove, "Should not contain RemoveMessage when no ID"
    assert actual == expected, f"Expected '{expected}', got '{actual}'"


def test_none_content():
    """Test handling of None content."""
    s = {'messages': [{'content': None, 'id': 'none1'}]}
    out = format_response(s, None)
    ai = [m for m in out['messages'] if isinstance(m, AIMessage)][0]

    expected = ''
    actual = ai.content

    passed = actual == expected
    log_test('test_none_content', 'None', expected, actual, passed)

    assert actual == expected, f"Expected empty string, got '{actual}'"


# Run all tests if executed directly
if __name__ == '__main__':
    print("\n" + "="*80)
    print("RUNNING FORMAT_RESPONSE TEST SUITE")
    print("="*80)

    test_functions = [
        test_remove_emojis_and_newlines_object_message,
        test_dict_message_input,
        test_empty_messages_returns_empty_dict,
        test_non_string_content_handling,
        test_zwj_emoji_sequences,
        test_skin_tone_modifiers,
        test_flag_emojis,
        test_mixed_emoji_types,
        test_multiple_consecutive_newlines,
        test_carriage_return_handling,
        test_excessive_whitespace_collapse,
        test_leading_trailing_whitespace,
        test_complex_real_world_example,
        test_message_without_id,
        test_none_content,
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
