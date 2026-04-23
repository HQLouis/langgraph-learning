"""
Matrix heatmap HTML renderer.

Reads the sidecar JSON (``.run_details.json``) emitted by the matrix
engine and writes a standalone HTML page that renders a
``SubExample × Requirement`` heatmap. Cells are coloured:

  * green  = PASS  (or "legacy passed: true" for non-matrix tests)
  * red    = FAIL
  * grey   = N/A (not applicable)
  * white  = missing (cell not run this session)

Rows are SubExamples (grouped by their source Eigenschaft); columns are
Requirements (grouped by Eigenschaft). Each cell tooltip shows the
verdict + one-line reason. Clicking a cell scrolls to the run-detail
card in the main report.

Entry point::

    from reporting.matrix_report import build_matrix_report
    build_matrix_report(sidecar_path, output_path)
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# HTML shell
# ---------------------------------------------------------------------------

_HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Matrix heatmap — {report_date}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f5f7fa; color: #222; padding: 24px; margin: 0; }}
    h1 {{ font-size: 1.4rem; margin-bottom: 4px; }}
    .meta {{ font-size: 0.85rem; color: #666; margin-bottom: 18px; }}
    .legend {{ display: flex; gap: 12px; font-size: 0.78rem; color: #444;
                margin-bottom: 16px; align-items: center; }}
    .legend-swatch {{ display: inline-block; width: 16px; height: 16px;
                       border-radius: 3px; border: 1px solid rgba(0,0,0,.15);
                       margin-right: 5px; vertical-align: -3px; }}
    table.matrix {{ border-collapse: collapse; background: white;
                     box-shadow: 0 2px 8px rgba(0,0,0,.06); }}
    table.matrix th, table.matrix td {{
        border: 1px solid #e6ebf0;
        font-size: 0.75rem;
        text-align: center;
        vertical-align: middle;
    }}
    table.matrix th {{ background: #fafbfc; font-weight: 600; padding: 6px 8px;
                        position: sticky; top: 0; z-index: 2; }}
    table.matrix th.row-header {{ text-align: left; padding: 6px 10px;
                                   position: sticky; left: 0; z-index: 1;
                                   background: #fafbfc; max-width: 260px;
                                   overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    table.matrix th.corner {{ position: sticky; top: 0; left: 0; z-index: 3;
                                background: #f0f2f5; }}
    table.matrix th.group {{ background: #edf1f6; font-size: 0.72rem; color: #445; }}
    td.cell {{ width: 34px; height: 28px; cursor: default; }}
    td.cell.pass {{ background: #6fcf97; }}
    td.cell.fail {{ background: #eb5757; }}
    td.cell.na   {{ background: #cccccc; }}
    td.cell.miss {{ background: #ffffff; }}
    td.aggregate {{ font-weight: 600; font-size: 0.72rem; padding: 4px 8px; color: #334; }}
    .row-summary {{ background: #f0f2f5; }}
    footer {{ text-align: center; font-size: 0.78rem; color: #888; margin-top: 24px; }}
    .summary-card {{ display: inline-block; background: white; padding: 10px 16px;
                      border-radius: 8px; margin-bottom: 14px; font-size: 0.85rem;
                      box-shadow: 0 1px 4px rgba(0,0,0,.06); }}
  </style>
</head>
<body>
  <h1>🔥 Matrix heatmap</h1>
  <p class="meta">Generated: <strong>{report_date}</strong> &nbsp;·&nbsp;
                  SubExamples: <strong>{subexample_count}</strong> &nbsp;·&nbsp;
                  Requirements: <strong>{requirement_count}</strong> &nbsp;·&nbsp;
                  Cells: <strong>{cell_count}</strong></p>

  <div class="summary-card">
    ✅ PASS: <strong>{pass_count}</strong> &nbsp;·&nbsp;
    ❌ FAIL: <strong>{fail_count}</strong> &nbsp;·&nbsp;
    ⭕ N/A: <strong>{na_count}</strong> &nbsp;·&nbsp;
    ⚪ missing: <strong>{miss_count}</strong>
  </div>

  <div class="legend">
    <span><span class="legend-swatch" style="background:#6fcf97"></span>PASS</span>
    <span><span class="legend-swatch" style="background:#eb5757"></span>FAIL</span>
    <span><span class="legend-swatch" style="background:#cccccc"></span>N/A (not applicable)</span>
    <span><span class="legend-swatch" style="background:#ffffff"></span>not run this session</span>
  </div>

  <div style="overflow:auto; max-height: 80vh;">
    <table class="matrix">
      {head_html}
      {body_html}
    </table>
  </div>

  <footer>Lingolino matrix engine — heatmap generator</footer>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


def _summarise_cell(runs: list[dict]) -> tuple[str, str]:
    """Collapse multiple runs of the same cell into a single verdict.

    If any run is FAIL → FAIL.
    Else if all are N/A → N/A.
    Else → PASS.
    """

    if not runs:
        return "miss", ""
    verdicts = [(r.get("verdict") or ("PASS" if r.get("passed") else "FAIL")).upper() for r in runs]
    if any(v == "FAIL" for v in verdicts):
        first_fail = next(r for r, v in zip(runs, verdicts) if v == "FAIL")
        return "fail", first_fail.get("reason", "")
    if all(v == "N/A" for v in verdicts):
        return "na", runs[0].get("reason", "")
    return "pass", runs[-1].get("reason", "")


def _load_matrix_entries(sidecar: dict) -> list[dict]:
    """Return only entries that carry matrix metadata (i.e. produced by the matrix engine)."""
    out: list[dict] = []
    for node_id, entry in sidecar.items():
        if not isinstance(entry, dict):
            continue
        meta = entry.get("matrix")
        if not isinstance(meta, dict):
            continue
        verdict, reason = _summarise_cell(entry.get("runs", []))
        out.append({
            "node_id": node_id,
            "subexample_id": meta.get("subexample_id", ""),
            "requirement_id": meta.get("requirement_id", ""),
            "eigenschaft": meta.get("eigenschaft"),
            "eigenschaft_title_de": meta.get("eigenschaft_title_de", ""),
            "profile_id": meta.get("profile_id", "default"),
            "tier": meta.get("tier", ""),
            "verdict": verdict,
            "reason": reason,
        })
    return out


# ---------------------------------------------------------------------------
# Table construction
# ---------------------------------------------------------------------------


def _build_head(requirements_in_order: list[tuple[str, str]]) -> str:
    """Two header rows: Eigenschaft groups, then the individual requirement IDs."""
    groups: list[tuple[str, int]] = []
    current_group: str | None = None
    current_span = 0
    for _, eig_title in requirements_in_order:
        if eig_title != current_group:
            if current_group is not None:
                groups.append((current_group, current_span))
            current_group = eig_title
            current_span = 1
        else:
            current_span += 1
    if current_group is not None:
        groups.append((current_group, current_span))

    group_cells = "".join(
        f'<th class="group" colspan="{span}">{_esc(title)}</th>'
        for title, span in groups
    )
    req_cells = "".join(
        f'<th title="{_esc(eig_title)}">{_esc(req_id)}</th>'
        for req_id, eig_title in requirements_in_order
    )
    return (
        f'<thead>'
        f'<tr><th class="corner" rowspan="2">SubExample ↓ / Requirement →</th>{group_cells}<th rowspan="2">row</th></tr>'
        f'<tr>{req_cells}</tr>'
        f'</thead>'
    )


def _build_body(
    subexamples_in_order: list[str],
    requirements_in_order: list[tuple[str, str]],
    grid: dict[tuple[str, str], tuple[str, str]],
) -> str:
    req_ids = [r for r, _ in requirements_in_order]
    rows_html: list[str] = []
    for sid in subexamples_in_order:
        cells = []
        counts = {"pass": 0, "fail": 0, "na": 0, "miss": 0}
        for rid in req_ids:
            verdict, reason = grid.get((sid, rid), ("miss", ""))
            counts[verdict] += 1
            tooltip = _esc(f"{sid} × {rid} → {verdict.upper()}: {reason[:120]}" if reason else f"{sid} × {rid} → {verdict.upper()}")
            cells.append(f'<td class="cell {verdict}" title="{tooltip}"></td>')
        row_summary = _row_summary(counts)
        cells_html = "".join(cells)
        rows_html.append(
            f'<tr><th class="row-header" title="{_esc(sid)}">{_esc(sid)}</th>{cells_html}'
            f'<td class="aggregate row-summary">{row_summary}</td></tr>'
        )
    return f'<tbody>{"".join(rows_html)}</tbody>'


def _row_summary(counts: dict[str, int]) -> str:
    if counts["fail"]:
        return f"❌ {counts['fail']}"
    if counts["pass"]:
        return f"✅ {counts['pass']}"
    if counts["na"]:
        return f"⭕ {counts['na']}"
    return "—"


def _esc(s: str) -> str:
    return (
        (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_matrix_report(sidecar_path: Path, output_path: Path) -> None:
    """Read ``sidecar_path`` and write the heatmap HTML to ``output_path``."""

    if not sidecar_path.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            "<html><body><p>No matrix sidecar found at "
            f"<code>{sidecar_path}</code>. Run the matrix first with "
            "<code>pytest -m matrix --json-report --json-report-file=.report.json</code>.</p></body></html>",
            encoding="utf-8",
        )
        return

    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    entries = _load_matrix_entries(sidecar)

    # Axis ordering.
    subexamples_in_order: list[str] = []
    requirements_by_eig: dict[int | None, list[str]] = defaultdict(list)
    req_titles: dict[str, str] = {}

    seen_subs: set[str] = set()
    seen_reqs: set[str] = set()
    for e in entries:
        sid = e["subexample_id"]
        if sid and sid not in seen_subs:
            seen_subs.add(sid)
            subexamples_in_order.append(sid)
        rid = e["requirement_id"]
        if rid and rid not in seen_reqs:
            seen_reqs.add(rid)
            requirements_by_eig[e["eigenschaft"]].append(rid)
            req_titles[rid] = e.get("eigenschaft_title_de", "")

    # Flatten requirements ordered by Eigenschaft number (None last).
    requirements_in_order: list[tuple[str, str]] = []
    for eig in sorted(requirements_by_eig.keys(), key=lambda x: (x is None, x or 0)):
        for rid in sorted(requirements_by_eig[eig]):
            requirements_in_order.append((rid, req_titles.get(rid, "")))

    grid: dict[tuple[str, str], tuple[str, str]] = {}
    counts = {"pass": 0, "fail": 0, "na": 0}
    for e in entries:
        key = (e["subexample_id"], e["requirement_id"])
        grid[key] = (e["verdict"], e["reason"])
        if e["verdict"] in counts:
            counts[e["verdict"]] += 1

    head_html = _build_head(requirements_in_order)
    body_html = _build_body(subexamples_in_order, requirements_in_order, grid)

    cell_total = len(subexamples_in_order) * len(requirements_in_order)
    miss_count = cell_total - len(grid)

    html = _HTML_PAGE.format(
        report_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        subexample_count=len(subexamples_in_order),
        requirement_count=len(requirements_in_order),
        cell_count=cell_total,
        pass_count=counts["pass"],
        fail_count=counts["fail"],
        na_count=counts["na"],
        miss_count=miss_count,
        head_html=head_html,
        body_html=body_html,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")
