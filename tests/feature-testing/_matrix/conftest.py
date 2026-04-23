"""
Matrix-scoped pytest configuration.

Registers matrix-specific CLI options (``--matrix-tier`` etc.) and
exposes fixtures the parametrized test consumes. The outer
``tests/feature-testing/conftest.py`` provides the system / judge LLM
fixtures plus beat-manager init, so this file only adds matrix-specific
glue.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from _matrix.engine import (
    MatrixCell,
    MatrixConfig,
    build_cells,
    load_examples,
    load_requirements,
)
from _matrix.response_cache import FilesystemCache

import ft_config as _cfg

logger = logging.getLogger(__name__)

_MATRIX_DIR = Path(__file__).resolve().parent
_REGISTRY_DIR = _MATRIX_DIR.parent / "_registry"


# ---------------------------------------------------------------------------
# CLI options
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("matrix", "Example × Requirement matrix engine")
    group.addoption(
        "--matrix-tier",
        choices=("core", "extended", "all"),
        default=None,
        help="Tier filter: 'core' (fast inner loop), 'extended' (adds non-core), or 'all'.",
    )
    group.addoption(
        "--matrix-profiles",
        choices=("default", "extended", "all"),
        default=None,
        help="Profile filter: 'default' single-profile; 'extended' adds variants for sensitive requirements; 'all' runs every variant.",
    )
    group.addoption(
        "--matrix-n-runs",
        type=int,
        default=None,
        help="Override MATRIX_N_RUNS. Keep at 1 for full scans; bump higher for targeted FAIL-cell investigation.",
    )
    group.addoption(
        "--matrix-pass-threshold",
        type=float,
        default=None,
        help="Override MATRIX_PASS_THRESHOLD: fraction of runs that must return PASS or N/A.",
    )
    group.addoption(
        "--matrix-no-cache",
        action="store_true",
        default=False,
        help="Disable the response cache — forces fresh BG + master generation.",
    )
    group.addoption(
        "--matrix-registry",
        default=None,
        help="Alternate registry directory (default: tests/feature-testing/_registry).",
    )


# ---------------------------------------------------------------------------
# Session-scoped resolved config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def matrix_tier(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--matrix-tier") or _cfg.MATRIX_TIER


@pytest.fixture(scope="session")
def matrix_profiles(request: pytest.FixtureRequest) -> str:
    return request.config.getoption("--matrix-profiles") or _cfg.MATRIX_PROFILES


@pytest.fixture(scope="session")
def matrix_n_runs(request: pytest.FixtureRequest) -> int:
    return request.config.getoption("--matrix-n-runs") or _cfg.MATRIX_N_RUNS


@pytest.fixture(scope="session")
def matrix_pass_threshold(request: pytest.FixtureRequest) -> float:
    opt = request.config.getoption("--matrix-pass-threshold")
    return opt if opt is not None else _cfg.MATRIX_PASS_THRESHOLD


@pytest.fixture(scope="session")
def matrix_cache(request: pytest.FixtureRequest) -> FilesystemCache:
    disabled = bool(request.config.getoption("--matrix-no-cache"))
    enabled = _cfg.MATRIX_CACHE_ENABLED and not disabled
    return FilesystemCache(root=Path(_cfg.MATRIX_CACHE_DIR), enabled=enabled)


@pytest.fixture(scope="session")
def matrix_config() -> MatrixConfig:
    return MatrixConfig(
        model_id=_cfg.SYSTEM_MODEL,
        temperature=_cfg.SYSTEM_TEMPERATURE,
    )


@pytest.fixture(scope="session")
def registry_dir(request: pytest.FixtureRequest) -> Path:
    override = request.config.getoption("--matrix-registry")
    return Path(override) if override else _REGISTRY_DIR


@pytest.fixture(scope="session")
def active_cells(
    registry_dir: Path,
    matrix_tier: str,
    matrix_profiles: str,
) -> list[MatrixCell]:
    examples = load_examples(registry_dir / "examples.jsonl")
    requirements = load_requirements(registry_dir / "requirements.yaml")
    cells = build_cells(
        examples,
        requirements,
        active_statuses=_cfg.MATRIX_ACTIVE_STATUSES,
        tier_filter=matrix_tier,
        profile_filter=matrix_profiles,
    )
    logger.info(
        "matrix: %d active cells (tier=%s, profiles=%s, registry=%s)",
        len(cells),
        matrix_tier,
        matrix_profiles,
        registry_dir,
    )
    return cells


# ---------------------------------------------------------------------------
# Parametrization hook — feeds cells into test_matrix.py
# ---------------------------------------------------------------------------


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """If a test asks for the ``cell`` fixture, expand the active matrix."""

    if "cell" not in metafunc.fixturenames:
        return

    # We need to peek at the CLI options / config at collection time —
    # pytest.Config is available via metafunc.config.
    config = metafunc.config
    tier = config.getoption("--matrix-tier") or _cfg.MATRIX_TIER
    profiles = config.getoption("--matrix-profiles") or _cfg.MATRIX_PROFILES
    override = config.getoption("--matrix-registry")
    registry = Path(override) if override else _REGISTRY_DIR

    examples = load_examples(registry / "examples.jsonl")
    requirements = load_requirements(registry / "requirements.yaml")
    cells = build_cells(
        examples,
        requirements,
        active_statuses=_cfg.MATRIX_ACTIVE_STATUSES,
        tier_filter=tier,
        profile_filter=profiles,
    )
    ids = [c.short_label() for c in cells]
    metafunc.parametrize("cell", cells, ids=ids)
