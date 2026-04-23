"""
The single parametrized matrix test.

One test function, one pytest case per active matrix cell. ``cell`` is
parametrized by ``conftest.py::pytest_generate_tests`` which reads the
registry at collection time.

Markers:
  - ``matrix``        — matrix cells (select with ``-m matrix``)
  - ``llm_feature``   — real dialog system LLM runs here
  - ``llm_judge``     — real judge LLM runs here

Run tips:
  # Just the matrix, default config (core tier, default profile):
  pytest tests/feature-testing/_matrix -m matrix

  # Extended tier across gender-sensitive requirements:
  pytest tests/feature-testing/_matrix -m matrix --matrix-tier=extended --matrix-profiles=extended

When the registry has no ``status: active`` entries (as of Phase 0-1),
parametrize produces zero cases and this file contributes nothing to
the session.
"""

from __future__ import annotations

import pytest

from _matrix.engine import MatrixCell, evaluate_cell
from _matrix.production_runners import make_run_background, make_run_master


@pytest.mark.matrix
@pytest.mark.llm_feature
@pytest.mark.llm_judge
def test_cell(
    cell: MatrixCell,
    system_llm,
    judge_llm,
    matrix_config,
    matrix_cache,
    matrix_n_runs: int,
    matrix_pass_threshold: float,
):
    """Evaluate one (SubExample × Requirement × profile) cell.

    Runs ``matrix_n_runs`` times. The cell passes when the fraction of
    non-failing runs (PASS + N/A) meets or exceeds
    ``matrix_pass_threshold``.
    """

    run_master = make_run_master(system_llm)
    run_background = make_run_background(system_llm) if cell.requirement.get("needs_background_analysis") else None

    results = []
    for _ in range(matrix_n_runs):
        result = evaluate_cell(
            cell,
            config=matrix_config,
            cache=matrix_cache,
            run_background=run_background,
            run_master=run_master,
            judge_llm=judge_llm,
        )
        results.append(result)

    non_failing = sum(1 for r in results if r.verdict.is_non_failing)
    pass_rate = non_failing / len(results)

    if pass_rate < matrix_pass_threshold:
        failure_details = "\n".join(
            f"  run {i + 1}: {r.verdict.verdict} — {r.verdict.reason} — response: {r.response_text[:140]!r}"
            for i, r in enumerate(results)
        )
        raise AssertionError(
            f"Cell {cell.cell_id} failed.\n"
            f"Pass rate {pass_rate * 100:.0f}% < required {matrix_pass_threshold * 100:.0f}%.\n"
            f"Requirement: {cell.requirement.get('anforderung_de', '')[:180]}\n"
            f"{failure_details}"
        )
