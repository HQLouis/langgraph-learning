"""
Feature Testing Framework — HTML Report Generator

Reads pytest's JSON report (produced by pytest-json-report) and generates
a simple, non-technical HTML report designed for non-technical stakeholders.

Usage (called automatically by pytest via conftest hook, or manually):

    python reporting/generate_report.py --input .report.json --output reporting/output/report.html

The report shows:
  - Overall PASS / FAIL summary
  - Per-feature results with pass-rate per test
  - Per-run expandable dropdown with AI response + judge reasoning (drill-down)
  - Run metadata (date, model, N_RUNS, threshold)
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# HTML templates
# ---------------------------------------------------------------------------

_HTML_PAGE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Feature Test Report — {report_date}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: #f5f7fa; color: #333; padding: 24px; }}
    h1 {{ font-size: 1.6rem; margin-bottom: 4px; color: #1a1a2e; }}
    .meta {{ font-size: 0.85rem; color: #666; margin-bottom: 24px; }}
    .summary-box {{ display: flex; align-items: center; gap: 16px;
                    background: white; border-radius: 10px; padding: 20px 28px;
                    box-shadow: 0 2px 8px rgba(0,0,0,.07); margin-bottom: 28px; }}
    .summary-icon {{ font-size: 2.4rem; }}
    .summary-text {{ font-size: 1.2rem; font-weight: 600; }}
    .summary-count {{ font-size: 0.95rem; color: #555; }}
    .feature-block {{ background: white; border-radius: 10px;
                      box-shadow: 0 2px 8px rgba(0,0,0,.07); margin-bottom: 20px;
                      overflow: hidden; }}
    .feature-header {{ padding: 14px 20px; font-weight: 600; font-size: 1rem;
                       border-bottom: 1px solid #eee; background: #fafbfc; }}
    .test-row {{ display: flex; align-items: flex-start; gap: 12px;
                 padding: 12px 20px; border-bottom: 1px solid #f0f0f0; }}
    .test-row:last-child {{ border-bottom: none; }}
    .badge {{ flex-shrink: 0; width: 28px; text-align: center; font-size: 1.1rem; padding-top: 2px; }}
    .test-body {{ flex: 1; min-width: 0; }}
    .test-name {{ font-size: 0.9rem; font-weight: 500; }}
    .run-rate {{ font-size: 0.82rem; color: #888; margin-top: 2px; margin-bottom: 8px; }}

    /* Runs dropdown */
    .runs-toggle {{ display: inline-flex; align-items: center; gap: 5px;
                    cursor: pointer; font-size: 0.8rem; color: #4a6fa5;
                    background: #eef2f9; border: 1px solid #d0daea;
                    border-radius: 20px; padding: 3px 10px; margin-bottom: 6px;
                    user-select: none; }}
    .runs-toggle:hover {{ background: #dce6f5; }}
    .runs-toggle .arrow {{ transition: transform 0.2s; display: inline-block; }}
    .runs-content {{ display: none; margin-top: 4px; }}
    .runs-content.open {{ display: block; }}

    /* Individual run card */
    .run-card {{ border: 1px solid #e8ecf0; border-radius: 8px;
                 margin-bottom: 8px; overflow: hidden; }}
    .run-card-header {{ display: flex; align-items: center; gap: 8px;
                        padding: 7px 12px; font-size: 0.82rem; font-weight: 600; }}
    .run-card.pass .run-card-header {{ background: #f0faf4; color: #1e7e45; border-bottom: 1px solid #c8ead5; }}
    .run-card.fail .run-card-header {{ background: #fff5f5; color: #c0392b; border-bottom: 1px solid #f5c6c6; }}
    .run-card-body {{ padding: 10px 12px; font-size: 0.82rem; color: #444; background: #fefefe; }}
    .run-response {{ font-style: italic; color: #333; white-space: pre-wrap;
                     word-break: break-word; border-left: 3px solid #c8d8e8;
                     padding-left: 8px; margin-bottom: 6px; }}
    .run-verdict-label {{ font-size: 0.75rem; font-weight: 600; color: #888;
                          text-transform: uppercase; letter-spacing: 0.04em;
                          margin-bottom: 3px; }}
    .run-verdict {{ color: #555; }}

    details summary {{ cursor: pointer; color: #888; font-size: 0.8rem; margin-top: 12px; }}
    .adv-table {{ width: 100%; border-collapse: collapse; font-size: 0.82rem; margin-top: 8px; }}
    .adv-table th, .adv-table td {{ text-align: left; padding: 4px 8px;
                                    border-bottom: 1px solid #eee; }}
    .adv-table th {{ font-weight: 600; color: #555; }}
    footer {{ text-align: center; font-size: 0.78rem; color: #aaa; margin-top: 32px; }}
  </style>
</head>
<body>
  <h1>🎓 Dialog System — Feature Test Report</h1>
  <p class="meta">Run date: <strong>{report_date}</strong> &nbsp;·&nbsp;
                  Model: <strong>{model}</strong> &nbsp;·&nbsp;
                  Runs per test: <strong>{n_runs}</strong> &nbsp;·&nbsp;
                  Pass threshold: <strong>{threshold_pct}%</strong></p>

  <div class="summary-box">
    <span class="summary-icon">{overall_icon}</span>
    <div>
      <div class="summary-text">Overall Result: {overall_label}</div>
      <div class="summary-count">{passed_tests} of {total_tests} test groups passed</div>
    </div>
  </div>

  {feature_blocks}

  <details>
    <summary>Advanced details (run configuration)</summary>
    <table class="adv-table" style="margin-top:8px;">
      <tr><th>Setting</th><th>Value</th></tr>
      <tr><td>N_RUNS</td><td>{n_runs}</td></tr>
      <tr><td>PASS_THRESHOLD</td><td>{threshold_pct}%</td></tr>
      <tr><td>System model</td><td>{model}</td></tr>
      <tr><td>Report generated</td><td>{report_date}</td></tr>
    </table>
  </details>

  <footer>Generated by the Lingolino Feature Testing Framework</footer>

  <script>
    document.querySelectorAll('.runs-toggle').forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        var content = btn.nextElementSibling;
        var arrow = btn.querySelector('.arrow');
        var isOpen = content.classList.toggle('open');
        arrow.style.transform = isOpen ? 'rotate(90deg)' : '';
        btn.querySelector('.toggle-label').textContent = isOpen ? 'Hide runs' : btn.dataset.label;
      }});
    }});
  </script>
</body>
</html>"""

_FEATURE_BLOCK = """\
<div class="feature-block">
  <div class="feature-header">{feature_name}</div>
  {test_rows}
</div>"""

_TEST_ROW = """\
<div class="test-row">
  <span class="badge">{badge}</span>
  <div class="test-body">
    <div class="test-name">{test_label}</div>
    <div class="run-rate">{run_rate}</div>
    {runs_dropdown}
  </div>
</div>"""

_RUNS_DROPDOWN = """\
<button class="runs-toggle" data-label="Show all {n_runs} runs" onclick="void(0)">
  <span class="arrow">▶</span>
  <span class="toggle-label">Show all {n_runs} runs</span>
</button>
<div class="runs-content">
  {run_cards}
</div>"""

_RUN_CARD = """\
<div class="run-card {css_class}">
  <div class="run-card-header">{icon} Run {num} — {verdict}</div>
  <div class="run-card-body">
    <div class="run-response">{response_text}</div>
    <div class="run-verdict-label">Judge reasoning</div>
    <div class="run-verdict">{reason}</div>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _test_label(node_id: str) -> str:
    """Convert a pytest node ID into a readable label for non-technical readers."""
    parts = node_id.split("::")
    func = parts[-1] if parts else node_id
    label = func.replace("test_", "").replace("_", " ").capitalize()
    return label


def _feature_name(node_id: str) -> str:
    """Extract feature directory name and humanise it."""
    parts = node_id.replace("\\", "/").split("/")
    try:
        idx = next(i for i, p in enumerate(parts) if p == "feature-testing")
        raw = parts[idx + 1] if idx + 1 < len(parts) else "Unknown Feature"
    except StopIteration:
        raw = parts[0] if parts else "Unknown Feature"
    return raw.replace("-", " ").title()


def _extract_run_details(crash_message: str) -> tuple[str, list[tuple[bool, str, str]]]:
    """
    Parse run-level PASS/FAIL entries from crash.message produced by run_n_times().

    Format (each run may span multiple lines because the response text itself
    can contain newlines):

        AssertionError: Only X/N runs passed (required: Y%)
          Run 1: PASS — <response_text (may be multiline)> — <judge_reason>
          Run 2: FAIL — <response_text (may be multiline)> — <judge_reason>

    Strategy:
      1. Find the summary line ("Only X/N runs passed").
      2. Split the remainder into per-run chunks on the "  Run N:" boundary.
      3. For each chunk, strip the "Run N: PASS/FAIL — " prefix, then split on
         the LAST em-dash to separate response_text from judge_reason.
    """
    runs: list[tuple[bool, str, str]] = []
    summary = ""

    # ── 1. Extract summary line ──────────────────────────────────────────────
    for line in crash_message.splitlines():
        if re.search(r"runs passed", line, re.IGNORECASE):
            summary = line.strip()
            break

    # ── 2. Split into per-run blocks on "Run N:" boundaries ─────────────────
    # Use a regex that matches the start of a run entry (possibly indented)
    run_header_re = re.compile(
        r"(?:^|\n)\s*Run\s+(\d+):\s+(PASS|FAIL)\s*[—–-]\s*",
        re.IGNORECASE,
    )

    # Find all header positions
    headers = list(run_header_re.finditer(crash_message))
    for idx, match in enumerate(headers):
        verdict_str = match.group(2).upper()
        passed = verdict_str == "PASS"

        # Text after the header up to the next header (or end of string)
        body_start = match.end()
        body_end = headers[idx + 1].start() if idx + 1 < len(headers) else len(crash_message)
        body = crash_message[body_start:body_end].strip()

        # Split on the LAST em-dash (or en-dash / hyphen-minus) to get reason
        # The judge reason never contains newlines; the response text might.
        last_sep = re.search(r"\s*[—–]\s*(?=[^\n—–]*$)", body)
        if last_sep:
            response_text = body[: last_sep.start()].strip()
            reason = body[last_sep.end() :].strip()
        else:
            response_text = body
            reason = ""

        runs.append((passed, response_text, reason))

    return summary, runs


def _build_runs_dropdown(runs: list[tuple[bool, str, str]]) -> str:
    """Build the HTML for the collapsible runs dropdown."""
    if not runs:
        return ""
    cards_html: list[str] = []
    for i, (passed, response_text, reason) in enumerate(runs):
        css_class = "pass" if passed else "fail"
        icon = "✅" if passed else "❌"
        verdict = "PASS" if passed else "FAIL"
        cards_html.append(
            _RUN_CARD.format(
                css_class=css_class,
                icon=icon,
                num=i + 1,
                verdict=verdict,
                response_text=response_text.replace("<", "&lt;").replace(">", "&gt;"),
                reason=reason.replace("<", "&lt;").replace(">", "&gt;"),
            )
        )
    return _RUNS_DROPDOWN.format(
        n_runs=len(runs),
        run_cards="\n  ".join(cards_html),
    )


# ---------------------------------------------------------------------------
# Core report builder
# ---------------------------------------------------------------------------

def build_report(
        json_path: Path,
        output_path: Path,
        n_runs: int,
        threshold: float,
        model: str,
        sidecar_path: Path | None = None,
) -> None:
    """Read pytest JSON report and write an HTML report."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    # Load sidecar run details (keyed by node ID) if available
    sidecar: dict[str, list[dict]] = {}
    if sidecar_path and sidecar_path.exists():
        with open(sidecar_path, encoding="utf-8") as f:
            sidecar = json.load(f)

    tests = data.get("tests", [])
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M")
    threshold_pct = int(threshold * 100)

    from collections import defaultdict
    feature_groups: dict[str, list[dict]] = defaultdict(list)
    for t in tests:
        node_id = t.get("nodeid", "")
        fname = _feature_name(node_id)
        feature_groups[fname].append(t)

    passed_tests = 0
    total_tests = len(tests)
    feature_html_parts: list[str] = []

    for feature, group in feature_groups.items():
        rows_html: list[str] = []
        for t in group:
            outcome = t.get("outcome", "failed")
            node_id = t.get("nodeid", "")
            label = _test_label(node_id)
            call = t.get("call", {}) if isinstance(t.get("call"), dict) else {}

            # Try to get run details from sidecar first (available for all tests)
            sidecar_runs = sidecar.get(node_id)
            if sidecar_runs:
                run_details: list[tuple[bool, str, str]] = [
                    (r["passed"], r["response_text"], r["reason"])
                    for r in sidecar_runs
                ]
            else:
                run_details = []

            if outcome == "passed":
                passed_tests += 1
                run_rate = f"All {len(run_details) or n_runs} runs passed ✓"
                runs_dropdown = _build_runs_dropdown(run_details)
                rows_html.append(
                    _TEST_ROW.format(
                        badge="✅",
                        test_label=label,
                        run_rate=run_rate,
                        runs_dropdown=runs_dropdown,
                    )
                )
            else:
                # For failing tests: prefer sidecar (has full data), fall back
                # to parsing crash.message then longrepr.
                if not run_details:
                    crash_message = call.get("crash", {}).get("message", "")
                    run_summary, run_details = _extract_run_details(crash_message)
                    if not run_details:
                        longrepr = call.get("longrepr", "") if isinstance(call.get("longrepr"), str) else ""
                        run_summary, run_details = _extract_run_details(longrepr)
                else:
                    # Derive summary from sidecar counts
                    passes = sum(1 for p, _, _ in run_details if p)
                    run_summary = f"Only {passes}/{len(run_details)} runs passed (required: {threshold_pct}%)"

                run_rate = run_summary or "Failed (no run details available)"
                runs_dropdown = _build_runs_dropdown(run_details)

                rows_html.append(
                    _TEST_ROW.format(
                        badge="❌",
                        test_label=label,
                        run_rate=run_rate,
                        runs_dropdown=runs_dropdown,
                    )
                )

        feature_html_parts.append(
            _FEATURE_BLOCK.format(
                feature_name=feature,
                test_rows="\n".join(rows_html),
            )
        )

    overall_pass = passed_tests == total_tests
    overall_icon = "✅" if overall_pass else "❌"
    overall_label = "PASSED" if overall_pass else "FAILED"

    html = _HTML_PAGE.format(
        report_date=report_date,
        model=model,
        n_runs=n_runs,
        threshold_pct=threshold_pct,
        overall_icon=overall_icon,
        overall_label=overall_label,
        passed_tests=passed_tests,
        total_tests=total_tests,
        feature_blocks="\n".join(feature_html_parts),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ HTML report written to: {output_path}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate HTML feature test report.")
    parser.add_argument("--input", required=True, help="Path to pytest JSON report (.report.json)")
    parser.add_argument("--output", default="reporting/output/report.html", help="Output HTML file path")
    parser.add_argument("--n-runs", type=int, default=5, help="N_RUNS used in the test run")
    parser.add_argument("--pass-threshold", type=float, default=0.80, help="Pass threshold used (0.0–1.0)")
    parser.add_argument("--model", default="gemini-2.0-flash", help="Model name used")
    parser.add_argument("--run-details", default=None,
                        help="Path to sidecar run-details JSON (default: <input>.run_details.json)")
    args = parser.parse_args()

    input_path = Path(args.input)
    sidecar_path = Path(args.run_details) if args.run_details else input_path.with_suffix(".run_details.json")

    build_report(
        json_path=input_path,
        output_path=Path(args.output),
        n_runs=args.n_runs,
        threshold=args.pass_threshold,
        model=args.model,
        sidecar_path=sidecar_path,
    )


if __name__ == "__main__":
    main()

