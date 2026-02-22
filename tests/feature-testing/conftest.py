"""
Feature Testing Framework — Shared Pytest Fixtures

This conftest.py is discovered automatically by pytest for all tests under
feature-testing/. It registers CLI options, exposes session-scoped LLM
fixtures, and re-exports utilities from feature_testing_utils so test files
can import them from a single known module.

Pure helper functions (build_state, run_n_times, llm_judge,
simulate_conversation) and conversation-history constants live in
feature_testing_utils.py so they can be imported directly by test files
without going through pytest's conftest machinery.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup
# Location: tests/feature-testing/
#   _FEATURE_TESTING_DIR  →  <root>/tests/feature-testing
#   _PROJECT_ROOT         →  <root>               (two levels up)
#   _AGENTIC_SYSTEM       →  <root>/agentic-system
# ---------------------------------------------------------------------------
_FEATURE_TESTING_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _FEATURE_TESTING_DIR.parent.parent.resolve()
_AGENTIC_SYSTEM = _PROJECT_ROOT / "agentic-system"

for _p in [str(_AGENTIC_SYSTEM), str(_PROJECT_ROOT), str(_FEATURE_TESTING_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

load_dotenv(_PROJECT_ROOT / ".env")

import ft_config as _cfg

# ---------------------------------------------------------------------------
# pytest CLI option registration
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register custom CLI options for the feature testing framework."""
    parser.addoption(
        "--n-runs",
        action="store",
        type=int,
        default=None,
        help="Override N_RUNS: number of times each probabilistic test is executed.",
    )
    parser.addoption(
        "--pass-threshold",
        action="store",
        type=float,
        default=None,
        help="Override PASS_THRESHOLD: fraction of runs that must pass (0.0–1.0).",
    )


# ---------------------------------------------------------------------------
# Session-scoped fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def n_runs(request: pytest.FixtureRequest) -> int:
    """Resolved N_RUNS: CLI override takes priority over config.py."""
    return request.config.getoption("--n-runs") or _cfg.N_RUNS


@pytest.fixture(scope="session")
def pass_threshold(request: pytest.FixtureRequest) -> float:
    """Resolved PASS_THRESHOLD: CLI override takes priority over config.py."""
    return request.config.getoption("--pass-threshold") or _cfg.PASS_THRESHOLD


@pytest.fixture(scope="session")
def system_llm():
    """Real LLM instance used to run the dialog system under test."""
    from langchain.chat_models import init_chat_model
    return init_chat_model(_cfg.SYSTEM_MODEL)


@pytest.fixture(scope="session")
def judge_llm():
    """Real LLM instance used as quality judge (low temperature for consistency)."""
    from langchain.chat_models import init_chat_model
    return init_chat_model(_cfg.JUDGE_MODEL, temperature=_cfg.JUDGE_TEMPERATURE)


# ---------------------------------------------------------------------------
# Auto HTML report generation after every test session
# ---------------------------------------------------------------------------


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """
    After the test session finishes, auto-generate an HTML report if a JSON
    report was produced by pytest-json-report (i.e. --json-report was passed).

    The HTML report is written to:
        tests/feature-testing/reporting/output/report_<timestamp>.html
    and a symlink is updated at:
        tests/feature-testing/reporting/output/report_latest.html
    """
    import time
    from pathlib import Path as _Path

    json_report_path_str: str | None = session.config.getoption(
        "--json-report-file", default=None
    )
    if not json_report_path_str:
        # --json-report was not passed — skip HTML generation
        return

    json_path = _Path(json_report_path_str)
    if not json_path.exists():
        return

    try:
        # Import here to avoid polluting the top-level namespace
        from reporting.generate_report import build_report

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_dir = _FEATURE_TESTING_DIR / "reporting" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        stamped_path = output_dir / f"report_{timestamp}.html"
        latest_path = output_dir / "report_latest.html"

        n_runs: int = session.config.getoption("--n-runs") or _cfg.N_RUNS
        threshold: float = (
            session.config.getoption("--pass-threshold") or _cfg.PASS_THRESHOLD
        )

        build_report(
            json_path=json_path,
            output_path=stamped_path,
            n_runs=n_runs,
            threshold=threshold,
            model=_cfg.SYSTEM_MODEL,
        )
        # Symlink latest → stamped for easy access
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(stamped_path.name)
        print(f"\n📊 HTML report: {latest_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"\n⚠️  HTML report generation failed: {exc}")


