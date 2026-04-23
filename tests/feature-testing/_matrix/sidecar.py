"""
Matrix sidecar writer — records per-cell evaluation details in the same
JSON sidecar the legacy framework uses, but with extra matrix metadata.

Schema (additive — legacy readers ignore the new fields):

  {
    "<pytest node id>": {
      "setting": {... human-readable summary ...},
      "runs": [
        {
          "passed": bool,               # legacy: verdict != "FAIL"
          "verdict": "PASS"|"FAIL"|"N/A", # NEW — first-class three-way verdict
          "response_text": str,
          "reason": str,
          "conversation": [{role, content}, ...],
        },
        ...
      ],
      "matrix": {                       # NEW — matrix metadata block
        "subexample_id": "S-...",
        "requirement_id": "R-...",
        "profile_id": "default",
        "eigenschaft": 19,
        "eigenschaft_title_de": "…",
        "tier": "core",
        "background_analysis_run": true
      }
    }
  }

The writer is defensive — any I/O failure is caught and logged; matrix
results are NEVER allowed to fail a test via sidecar problems.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from _matrix.engine import CellResult

logger = logging.getLogger(__name__)


def _build_runs(results: list[CellResult]) -> list[dict]:
    out: list[dict] = []
    for r in results:
        out.append({
            "passed": r.verdict.is_non_failing,      # N/A + PASS → True; FAIL → False
            "verdict": r.verdict.verdict,             # PASS | FAIL | N/A
            "response_text": r.response_text,
            "reason": r.verdict.reason,
            "conversation": list(r.cell.subexample.get("prefix_messages", [])),
        })
    return out


def _build_matrix_metadata(result: CellResult) -> dict:
    req = result.cell.requirement
    return {
        "subexample_id": result.cell.subexample.get("id", ""),
        "requirement_id": req.get("id", ""),
        "profile_id": result.cell.profile_key,
        "eigenschaft": req.get("eigenschaft"),
        "eigenschaft_title_de": req.get("eigenschaft_title_de", ""),
        "tier": result.cell.tier,
        "background_analysis_run": bool(result.bg_state_used),
    }


def _build_setting(results: list[CellResult]) -> dict:
    """Human-readable setting dict for the report UI."""
    first = results[0]
    req = first.cell.requirement
    sub = first.cell.subexample
    profile = first.cell.profile
    return {
        "Requirement": f"{req.get('id', '?')} — {req.get('title_de', '')}",
        "Eigenschaft": f"{req.get('eigenschaft', '?')} — {req.get('eigenschaft_title_de', '')}",
        "Anforderung (DE)": req.get("anforderung_de", ""),
        "Applicability rule (DE)": req.get("applicability_rule_de", ""),
        "Judge criterion (EN)": req.get("judge_criterion_en", ""),
        "SubExample": sub.get("id", ""),
        "Story": f"{sub.get('story_id', '?')} / {sub.get('chapter_id', '?')}",
        "Profile": f"{profile.get('name', '?')}, {profile.get('age', '?')} ({profile.get('gender', '?')})",
        "Tier": first.cell.tier,
        "BG run": "yes" if first.bg_state_used else "no",
        "__messages__": [
            {"role": "Child" if m["role"] == "child" else "System", "content": m["content"]}
            for m in sub.get("prefix_messages", [])
        ],
    }


def write_cell_results(
    sidecar_path: Path | None,
    node_id: str,
    results: list[CellResult],
) -> None:
    """Merge cell results into the sidecar JSON at ``sidecar_path``.

    When ``sidecar_path`` is ``None`` (no --json-report configured) this
    function is a no-op — the tests still run, we just don't persist.
    """

    if sidecar_path is None or not results:
        return
    try:
        sidecar: dict = {}
        if sidecar_path.exists():
            try:
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except Exception:
                sidecar = {}

        entry = {
            "setting": _build_setting(results),
            "runs": _build_runs(results),
            "matrix": _build_matrix_metadata(results[0]),
        }
        sidecar[node_id] = entry
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        sidecar_path.write_text(
            json.dumps(sidecar, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:  # noqa: BLE001 — never let sidecar I/O break the test
        logger.warning("matrix sidecar write failed for %s: %s", node_id, exc)
