"""
Feature Testing Framework — Global Configuration

These values control how probabilistic (LLM-based) tests are executed.
They can be overridden via pytest CLI options:

    pytest agentic-system/feature-testing/ --n-runs=10 --pass-threshold=0.9

See conftest.py for CLI option registration.
"""

# ---------------------------------------------------------------------------
# Probabilistic test execution
# ---------------------------------------------------------------------------

N_RUNS: int = 5
"""How many times each LLM-based test case is executed per test run.
Higher values increase confidence but cost more API calls."""

PASS_THRESHOLD: float = 0.80
"""Fraction of N_RUNS that must pass for a test to be considered passing.
Example: N_RUNS=5, PASS_THRESHOLD=0.80 → at least 4 out of 5 runs must pass."""

# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------

JUDGE_MODEL: str = "google_genai:gemini-2.0-flash"
"""Model used as judge for content-based (LLM-as-judge) assertions."""

JUDGE_TEMPERATURE: float = 0.0
"""Temperature for the judge LLM. Keep at 0.0 for maximum consistency."""

SYSTEM_MODEL: str = "google_genai:gemini-2.0-flash"
"""Model used to run the dialog system under test.
Feature tests always call the real LLM — there is no mocking."""

# ---------------------------------------------------------------------------
# Strategy B (fully-simulated) defaults
# ---------------------------------------------------------------------------

SIMULATED_N_RUNS: int = 3
"""Default N_RUNS for fully-simulated (Strategy B) tests.
Lower than fixture-based tests because each run involves multiple LLM calls."""

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

REPORT_OUTPUT_DIR: str = "agentic-system/feature-testing/reporting/output"
"""Directory where HTML reports are written after a test run."""

