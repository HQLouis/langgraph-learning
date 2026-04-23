"""
Unit tests for the matrix sidecar writer and the heatmap report
generator. All I/O goes through tmp_path; no LLMs are invoked.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_FEATURE_TESTING_DIR = Path(__file__).resolve().parents[1]
if str(_FEATURE_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(_FEATURE_TESTING_DIR))

from _matrix.engine import CellResult, MatrixCell
from _matrix.judge_prompt import JudgeVerdict
from _matrix.sidecar import write_cell_results


def _make_cell(*, needs_bg=True) -> MatrixCell:
    return MatrixCell(
        subexample={
            "id": "S-abc",
            "prefix_messages": [{"role": "child", "content": "hallo"}],
            "story_id": "pia",
            "chapter_id": "chapter_01",
        },
        requirement={
            "id": "R-19-01",
            "eigenschaft": 19,
            "eigenschaft_title_de": "Nein akzeptieren",
            "anforderung_de": "Accept nein.",
            "applicability_rule_de": "Gilt wenn child gesagt hat 'Nein'.",
            "judge_criterion_en": "PASS if accepted.",
            "needs_background_analysis": needs_bg,
        },
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        profile_key="default",
        tier="core",
    )


def _make_result(verdict: str, response_text: str = "ok", reason: str = "fine") -> CellResult:
    return CellResult(
        cell=_make_cell(),
        verdict=JudgeVerdict(verdict=verdict, reason=reason, raw=verdict),
        response_text=response_text,
        bg_state_used=True,
    )


def test_sidecar_writes_verdict_and_matrix_metadata(tmp_path):
    path = tmp_path / "sidecar.json"
    node_id = "tests/feature-testing/_matrix/test_matrix.py::test_cell[S-abc×R-19-01×default]"
    write_cell_results(path, node_id, [_make_result("PASS"), _make_result("PASS")])

    data = json.loads(path.read_text(encoding="utf-8"))
    entry = data[node_id]
    assert entry["runs"][0]["verdict"] == "PASS"
    assert entry["runs"][0]["passed"] is True
    assert entry["matrix"]["subexample_id"] == "S-abc"
    assert entry["matrix"]["requirement_id"] == "R-19-01"
    assert entry["matrix"]["eigenschaft"] == 19
    assert entry["matrix"]["background_analysis_run"] is True
    assert entry["matrix"]["tier"] == "core"


def test_sidecar_na_verdict_is_non_failing(tmp_path):
    path = tmp_path / "sidecar.json"
    write_cell_results(path, "node1", [_make_result("N/A")])
    data = json.loads(path.read_text(encoding="utf-8"))
    run = data["node1"]["runs"][0]
    assert run["verdict"] == "N/A"
    assert run["passed"] is True  # N/A counts as non-failing


def test_sidecar_missing_path_is_noop(tmp_path):
    # Should not raise even though we pass an unwritable path.
    write_cell_results(None, "node1", [_make_result("PASS")])


def test_sidecar_merges_preserving_other_entries(tmp_path):
    path = tmp_path / "sidecar.json"
    path.write_text(json.dumps({"legacy_node": {"setting": {}, "runs": []}}), encoding="utf-8")
    write_cell_results(path, "matrix_node", [_make_result("FAIL", reason="repeat prompt")])
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data.keys()) == {"legacy_node", "matrix_node"}
    assert data["matrix_node"]["runs"][0]["verdict"] == "FAIL"
    assert data["matrix_node"]["runs"][0]["passed"] is False


# ---------------------------------------------------------------------------
# Matrix heatmap report
# ---------------------------------------------------------------------------


def test_matrix_report_renders_heatmap(tmp_path):
    from reporting.matrix_report import build_matrix_report

    sidecar = tmp_path / "sidecar.json"
    payload = {
        "node1": {
            "setting": {},
            "runs": [{"passed": True, "verdict": "PASS", "response_text": "ok", "reason": "fine"}],
            "matrix": {
                "subexample_id": "S-aaa", "requirement_id": "R-19-01",
                "eigenschaft": 19, "eigenschaft_title_de": "Nein akzeptieren",
                "profile_id": "default", "tier": "core", "background_analysis_run": True,
            },
        },
        "node2": {
            "setting": {},
            "runs": [{"passed": False, "verdict": "FAIL", "response_text": "bad", "reason": "repeats"}],
            "matrix": {
                "subexample_id": "S-aaa", "requirement_id": "R-16-01",
                "eigenschaft": 16, "eigenschaft_title_de": "Keine Wiederholung",
                "profile_id": "default", "tier": "core", "background_analysis_run": True,
            },
        },
        "node3": {
            "setting": {},
            "runs": [{"passed": True, "verdict": "N/A", "response_text": "ok", "reason": "not applicable"}],
            "matrix": {
                "subexample_id": "S-bbb", "requirement_id": "R-19-01",
                "eigenschaft": 19, "eigenschaft_title_de": "Nein akzeptieren",
                "profile_id": "default", "tier": "core", "background_analysis_run": True,
            },
        },
    }
    sidecar.write_text(json.dumps(payload), encoding="utf-8")

    out = tmp_path / "matrix.html"
    build_matrix_report(sidecar, out)
    html = out.read_text(encoding="utf-8")
    assert "Matrix heatmap" in html
    assert "S-aaa" in html and "S-bbb" in html
    assert "R-19-01" in html and "R-16-01" in html
    assert 'class="cell pass"' in html
    assert 'class="cell fail"' in html
    assert 'class="cell na"' in html


def test_matrix_report_handles_empty_sidecar(tmp_path):
    from reporting.matrix_report import build_matrix_report

    sidecar = tmp_path / "sidecar.json"
    sidecar.write_text("{}", encoding="utf-8")
    out = tmp_path / "matrix.html"
    build_matrix_report(sidecar, out)
    html = out.read_text(encoding="utf-8")
    assert "Matrix heatmap" in html  # header renders even with zero entries


def test_matrix_report_handles_missing_sidecar(tmp_path):
    from reporting.matrix_report import build_matrix_report

    out = tmp_path / "matrix.html"
    build_matrix_report(tmp_path / "does-not-exist.json", out)
    html = out.read_text(encoding="utf-8")
    assert "No matrix sidecar found" in html


# ---------------------------------------------------------------------------
# generate_report refactor — group-by-eigenschaft + N/A badge
# ---------------------------------------------------------------------------


def test_generate_report_groups_matrix_entries_by_eigenschaft(tmp_path):
    from reporting.generate_report import build_report

    json_report = tmp_path / "report.json"
    sidecar = tmp_path / "report.run_details.json"

    # Minimal pytest-json-report payload with one matrix test.
    json_report.write_text(json.dumps({
        "tests": [{
            "nodeid": "tests/feature-testing/_matrix/test_matrix.py::test_cell[S-a×R-19-01×default]",
            "outcome": "passed",
            "call": {},
        }],
    }), encoding="utf-8")
    sidecar.write_text(json.dumps({
        "tests/feature-testing/_matrix/test_matrix.py::test_cell[S-a×R-19-01×default]": {
            "setting": {},
            "runs": [{"passed": True, "verdict": "PASS", "response_text": "ok", "reason": "fine"}],
            "matrix": {
                "subexample_id": "S-a", "requirement_id": "R-19-01",
                "eigenschaft": 19, "eigenschaft_title_de": "Nein akzeptieren",
                "profile_id": "default", "tier": "core", "background_analysis_run": True,
            },
        },
    }), encoding="utf-8")

    out = tmp_path / "report.html"
    build_report(
        json_path=json_report, output_path=out,
        n_runs=1, threshold=1.0, model="m", sidecar_path=sidecar,
    )
    html = out.read_text(encoding="utf-8")
    assert "Eigenschaft 19: Nein akzeptieren" in html


def test_generate_report_na_verdict_renders_na_card(tmp_path):
    from reporting.generate_report import build_report

    json_report = tmp_path / "report.json"
    sidecar = tmp_path / "report.run_details.json"
    json_report.write_text(json.dumps({
        "tests": [{
            "nodeid": "tests/feature-testing/_matrix/test_matrix.py::test_cell[S-a×R-19-01×default]",
            "outcome": "passed",
            "call": {},
        }],
    }), encoding="utf-8")
    sidecar.write_text(json.dumps({
        "tests/feature-testing/_matrix/test_matrix.py::test_cell[S-a×R-19-01×default]": {
            "setting": {},
            "runs": [{"passed": True, "verdict": "N/A", "response_text": "ok", "reason": "does not apply"}],
            "matrix": {
                "subexample_id": "S-a", "requirement_id": "R-19-01",
                "eigenschaft": 19, "eigenschaft_title_de": "Nein akzeptieren",
                "profile_id": "default", "tier": "core", "background_analysis_run": True,
            },
        },
    }), encoding="utf-8")
    out = tmp_path / "report.html"
    build_report(
        json_path=json_report, output_path=out,
        n_runs=1, threshold=1.0, model="m", sidecar_path=sidecar,
    )
    html = out.read_text(encoding="utf-8")
    assert 'class="run-card na"' in html
    assert "N/A" in html
