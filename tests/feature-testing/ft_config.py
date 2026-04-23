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

N_RUNS: int = 1
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

SYSTEM_TEMPERATURE: float = 0.0
"""Temperature for the system LLM during testing. Keep at 0.0 for
deterministic, reproducible behavior during prompt iteration."""

# ---------------------------------------------------------------------------
# LangSmith tracing for judge calls
# ---------------------------------------------------------------------------

import os as _os

JUDGE_LANGSMITH_TRACING: bool = _os.environ.get("JUDGE_LANGSMITH_TRACING", "false").lower() == "true"
"""Whether judge LLM calls are traced in LangSmith.
Defaults to false to avoid polluting traces with evaluation calls.
Set JUDGE_LANGSMITH_TRACING=true to enable."""

# ---------------------------------------------------------------------------
# Strategy B (fully-simulated) defaults
# ---------------------------------------------------------------------------

SIMULATED_N_RUNS: int = 1
"""Default N_RUNS for fully-simulated (Strategy B) tests.
Lower than fixture-based tests because each run involves multiple LLM calls."""

# ---------------------------------------------------------------------------
# Matrix engine (Phase 1+) — defaults only; CLI flags can override each one.
# ---------------------------------------------------------------------------

MATRIX_ACTIVE_STATUSES: tuple[str, ...] = ("active",)
"""Requirement / SubExample statuses that the matrix test engine considers.
Keeps `status: draft` entries out of the test run by default."""

MATRIX_TIER: str = "core"
"""Tier filter for the matrix engine: 'core' | 'extended' | 'all'.
Matches the draft §2.3a tiering model. CLI override: ``--matrix-tier``."""

MATRIX_PROFILES: str = "default"
"""Profile filter: 'default' | 'extended' | 'all'.
'default' runs each SubExample once with its default profile.
'extended' additionally runs profile_variants for requirements whose
``profile_sensitivity`` is not 'none'. 'all' runs every variant.
CLI override: ``--matrix-profiles``."""

MATRIX_N_RUNS: int = 1
"""Default N_RUNS for matrix cells. Keep at 1 for full-matrix scans; only
bump higher for targeted FAIL-cell investigation.
CLI override: ``--matrix-n-runs``."""

MATRIX_PASS_THRESHOLD: float = 1.0
"""Fraction of runs that must return a non-FAIL verdict (PASS or N/A).
At N_RUNS=1 this effectively means: any FAIL fails the cell.
CLI override: ``--matrix-pass-threshold``."""

MATRIX_CACHE_DIR: str = "tests/feature-testing/_matrix/.cache"
"""Filesystem cache directory for the two-layer response cache.
Safe to delete; the cache will be repopulated on the next run."""

MATRIX_CACHE_ENABLED: bool = True
"""Set False via ``--matrix-no-cache`` to force fresh generation.
Useful when prompt files on disk changed but their hash wasn't invalidated."""

# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

REPORT_OUTPUT_DIR: str = "agentic-system/feature-testing/reporting/output"
"""Directory where HTML reports are written after a test run."""

