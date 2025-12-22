"""
Pytest configuration and shared fixtures for E2E testing.
"""
import pytest
import sys
from pathlib import Path
from typing import Generator
import logging

# Add parent directories to path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(root_dir / "agentic-system"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# ============================================================================
# SESSION-SCOPED FIXTURES (Created once per test session)
# ============================================================================

@pytest.fixture(scope="session")
def llm_config():
    """LLM configuration for tests"""
    return {
        "model": "google_genai:gemini-2.0-flash",
        "temperature": 0.4,
        "max_tokens": 1000,
    }


@pytest.fixture(scope="session")
def judge_llm_config():
    """Judge LLM configuration (deterministic)"""
    return {
        "model": "google_genai:gemini-2.0-flash",
        "temperature": 0.0,  # Deterministic for judge
        "max_tokens": 2000,
    }


@pytest.fixture(scope="session")
def test_output_dir(tmp_path_factory) -> Path:
    """Create temporary directory for test outputs"""
    output_dir = tmp_path_factory.mktemp("e2e_test_results")
    return output_dir


# ============================================================================
# FUNCTION-SCOPED FIXTURES (Created for each test)
# ============================================================================

@pytest.fixture
def mock_llm():
    """
    Mock LLM for unit testing components without API calls.
    Returns predefined responses.
    """
    class MockLLM:
        def __init__(self):
            self.call_count = 0
            self.responses = []

        def invoke(self, prompt, **kwargs):
            self.call_count += 1
            if self.responses:
                response = self.responses.pop(0)
            else:
                response = "Mock response"

            class MockResponse:
                def __init__(self, content):
                    self.content = content

            return MockResponse(response)

        async def ainvoke(self, prompt, **kwargs):
            return self.invoke(prompt, **kwargs)

        def set_responses(self, responses: list):
            """Set predefined responses"""
            self.responses = responses.copy()

    return MockLLM()


@pytest.fixture
def sample_child_persona():
    """Sample child persona for testing"""
    from scenarios.base_scenario import (
        ChildPersona,
        LanguageLevel,
        EngagementLevel,
        ComprehensionLevel,
        EmotionState
    )

    return ChildPersona(
        age=7,
        name="TestChild",
        language_level=LanguageLevel.A2,
        personality_traits=["curious", "friendly"],
        interests=["animals", "stories"],
        initial_engagement=EngagementLevel.MEDIUM,
        initial_comprehension=ComprehensionLevel.GOOD,
        initial_emotion=EmotionState.NEUTRAL,
        typical_response_length=10,
        grammar_error_rate=0.2,
        common_errors=["verb_conjugation", "articles"]
    )


@pytest.fixture
def sample_conversation():
    """Sample conversation for testing judges"""
    from scenarios.base_scenario import Message

    return [
        {"role": "child", "content": "Ich haben einen Hund!"},
        {"role": "system", "content": "Oh toll! Du hast einen Hund? Das ist wunderbar! Wie heißt dein Hund?"},
        {"role": "child", "content": "Er heißt Max. Er ist groß."},
        {"role": "system", "content": "Max! Was für ein schöner Name! Große Hunde sind toll. Was macht Max gerne?"},
        {"role": "child", "content": "Er spielt gerne im Garten."},
        {"role": "system", "content": "Das klingt super! Im Garten spielen macht viel Spaß!"}
    ]


# ============================================================================
# MARKERS AND TEST SELECTION
# ============================================================================

def pytest_configure(config):
    """Configure custom markers"""
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (require system setup)"
    )
    config.addinivalue_line(
        "markers",
        "requires_api: Tests that require API keys and make real LLM calls"
    )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection:
    - Skip expensive tests if --run-expensive not specified
    - Skip tests requiring API if --no-api specified
    """
    skip_expensive = pytest.mark.skip(reason="Use --run-expensive to run")
    skip_api = pytest.mark.skip(reason="Use --run-api to run tests requiring API calls")

    run_expensive = config.getoption("--run-expensive", default=False)
    no_api = config.getoption("--no-api", default=False)

    for item in items:
        if "expensive" in item.keywords and not run_expensive:
            item.add_marker(skip_expensive)

        if "requires_api" in item.keywords and no_api:
            item.add_marker(skip_api)


def pytest_addoption(parser):
    """Add custom command-line options"""
    parser.addoption(
        "--run-expensive",
        action="store_true",
        default=False,
        help="Run expensive tests (high API cost)"
    )
    parser.addoption(
        "--no-api",
        action="store_true",
        default=False,
        help="Skip tests requiring API calls"
    )
    parser.addoption(
        "--priority",
        action="store",
        default=None,
        help="Run only tests with specified priority (critical, high, medium, low)"
    )


# ============================================================================
# REPORTING HOOKS
# ============================================================================

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """
    Add custom test result information.
    Track API costs, execution time, etc.
    """
    # Add custom attributes to test reports
    if call.when == "call":
        # Could track API costs here
        pass


@pytest.fixture(autouse=True)
def test_timer(request):
    """Automatically track test execution time"""
    import time
    start_time = time.time()

    yield

    duration = time.time() - start_time
    if duration > 60:  # Warn if test takes more than 1 minute
        logging.warning(f"Test {request.node.name} took {duration:.2f}s")


# ============================================================================
# CLEANUP
# ============================================================================

@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup resources after each test"""
    yield

    # Add cleanup logic here if needed
    # e.g., clear caches, close connections, etc.

