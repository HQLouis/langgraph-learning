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

    /* Setting dropdown */
    .setting-toggle {{ display: inline-flex; align-items: center; gap: 5px;
                       cursor: pointer; font-size: 0.8rem; color: #6b5ea8;
                       background: #f2f0fb; border: 1px solid #d8d2f0;
                       border-radius: 20px; padding: 3px 10px; margin-bottom: 6px;
                       margin-right: 6px; user-select: none; }}
    .setting-toggle:hover {{ background: #e6e0f8; }}
    .setting-toggle .arrow {{ transition: transform 0.2s; display: inline-block; }}
    .setting-content {{ display: none; margin-bottom: 6px; }}
    .setting-content.open {{ display: block; }}
    .setting-table {{ border-collapse: collapse; font-size: 0.8rem; width: 100%;
                      background: #faf9ff; border: 1px solid #e4dff5;
                      border-radius: 6px; overflow: hidden; }}
    .setting-table td {{ padding: 5px 10px; vertical-align: top; }}
    .setting-table td:first-child {{ font-weight: 600; color: #6b5ea8; white-space: nowrap;
                                     width: 1%; padding-right: 16px; }}
    .setting-table tr {{ border-bottom: 1px solid #ede9f9; }}
    .setting-table tr:last-child {{ border-bottom: none; }}

    /* Chat transcript inside setting dropdown */
    .chat-transcript {{ padding: 6px 0; }}
    .chat-turn {{ display: flex; gap: 6px; margin-bottom: 5px; align-items: flex-start; }}
    .chat-turn.empty {{ color: #aaa; font-style: italic; font-size: 0.78rem; padding: 4px 0; }}
    .chat-role {{ font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
                  letter-spacing: 0.05em; white-space: nowrap; padding-top: 3px; min-width: 52px; }}
    .chat-role.system {{ color: #4a6fa5; }}
    .chat-role.child  {{ color: #2e8b57; }}
    .chat-bubble {{ font-size: 0.8rem; border-radius: 8px; padding: 5px 9px;
                    white-space: pre-wrap; word-break: break-word; max-width: 90%; }}
    .chat-bubble.system {{ background: #eef2f9; color: #333; }}
    .chat-bubble.child  {{ background: #edf7f0; color: #333; }}

    /* Individual run card */
    .run-card {{ border: 1px solid #e8ecf0; border-radius: 8px;
                 margin-bottom: 8px; overflow: hidden; }}
    .run-card-header {{ display: flex; align-items: center; gap: 8px;
                        padding: 7px 12px; font-size: 0.82rem; font-weight: 600; }}
    .run-card.pass .run-card-header {{ background: #f0faf4; color: #1e7e45; border-bottom: 1px solid #c8ead5; }}
    .run-card.fail .run-card-header {{ background: #fff5f5; color: #c0392b; border-bottom: 1px solid #f5c6c6; }}
    .run-card.na   .run-card-header {{ background: #f5f5f5; color: #555555; border-bottom: 1px solid #dcdcdc; }}
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
    document.querySelectorAll('.runs-toggle, .setting-toggle').forEach(function(btn) {{
      btn.addEventListener('click', function() {{
        var content = btn.nextElementSibling;
        var arrow = btn.querySelector('.arrow');
        var isOpen = content.classList.toggle('open');
        arrow.style.transform = isOpen ? 'rotate(90deg)' : '';
        btn.querySelector('.toggle-label').textContent = isOpen ? 'Hide' : btn.dataset.label;
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
    {setting_dropdown}
    {runs_dropdown}
  </div>
</div>"""

_SETTING_DROPDOWN = """\
<button class="setting-toggle" data-label="Test setting" onclick="void(0)">
  <span class="arrow">▶</span>
  <span class="toggle-label">Test setting</span>
</button>
<div class="setting-content">
  <table class="setting-table">
    {rows}
  </table>
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
    {conversation_html}
  </div>
</div>"""

_RUN_CONVERSATION = """\
<div style="margin-top:8px;">
  <div class="run-verdict-label" style="margin-bottom:4px;">Full conversation</div>
  <div class="chat-transcript">
    {turns}
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


def _resolve_group_label(node_id: str, sidecar_entry: dict | list | None) -> str:
    """Prefer matrix.eigenschaft_title_de when present; fall back to folder.

    During migration both legacy per-feature tests and matrix cells share
    the same report. Matrix cells carry a ``matrix.eigenschaft_title_de``
    block in the sidecar; legacy cells don't, so we use the folder
    extractor.
    """

    if isinstance(sidecar_entry, dict):
        matrix_meta = sidecar_entry.get("matrix", {})
        if isinstance(matrix_meta, dict):
            number = matrix_meta.get("eigenschaft")
            title = matrix_meta.get("eigenschaft_title_de", "")
            if title:
                return (
                    f"Eigenschaft {number}: {title}" if number is not None
                    else f"Eigenschaft: {title}"
                )
    return _feature_name(node_id)


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


def _build_runs_dropdown(runs: list[dict]) -> str:
    """Build the HTML for the collapsible runs dropdown.

    Each entry in ``runs`` is a dict with keys:
      passed, response_text, reason, conversation (optional list of {role, content}).
    """
    if not runs:
        return ""

    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    cards_html: list[str] = []
    for i, run in enumerate(runs):
        passed       = run["passed"]
        response_text = run["response_text"]
        reason       = run["reason"]
        conversation  = run.get("conversation", [])

        # verdict is PASS | FAIL | N/A when the matrix engine populates
        # it; legacy tests only emit bool passed and we fall back to a
        # two-way classification.
        raw_verdict = (run.get("verdict") or "").upper()
        if raw_verdict == "N/A":
            css_class, icon, verdict = "na", "⭕", "N/A"
        elif raw_verdict == "PASS" or (not raw_verdict and passed):
            css_class, icon, verdict = "pass", "✅", "PASS"
        else:
            css_class, icon, verdict = "fail", "❌", "FAIL"

        # ── Per-run conversation transcript ──────────────────────────────
        if conversation:
            turns_html = "\n    ".join(
                f'<div class="chat-turn">'
                f'<span class="chat-role {"system" if m["role"] == "System" else "child"}">{m["role"]}</span>'
                f'<span class="chat-bubble {"system" if m["role"] == "System" else "child"}">{_esc(m["content"])}</span>'
                f'</div>'
                for m in conversation
            )
            conversation_html = _RUN_CONVERSATION.format(turns=turns_html)
        else:
            conversation_html = ""

        cards_html.append(
            _RUN_CARD.format(
                css_class=css_class,
                icon=icon,
                num=i + 1,
                verdict=verdict,
                response_text=_esc(response_text),
                reason=_esc(reason),
                conversation_html=conversation_html,
            )
        )
    return _RUNS_DROPDOWN.format(
        n_runs=len(runs),
        run_cards="\n  ".join(cards_html),
    )


def _build_setting_dropdown(setting: dict) -> str:
    """Build the HTML for the collapsible test-setting dropdown.

    The special key ``__messages__`` is rendered as a chat transcript with
    per-turn labelled bubbles rather than a flat table row.  All other keys
    are rendered as normal label → value table rows.
    """
    if not setting:
        return ""

    def _esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ── Regular metadata rows ────────────────────────────────────────────────
    rows_html = "\n    ".join(
        f"<tr><td>{_esc(key)}</td><td>{_esc(str(val))}</td></tr>"
        for key, val in setting.items()
        if key != "__messages__"
    )

    # ── Conversation transcript row ──────────────────────────────────────────
    messages: list[dict] = setting.get("__messages__", [])
    if messages:
        turns_html: list[str] = []
        for msg in messages:
            role = msg.get("role", "")
            content = _esc(msg.get("content", ""))
            css = "system" if role == "System" else "child"
            turns_html.append(
                f'<div class="chat-turn">'
                f'<span class="chat-role {css}">{role}</span>'
                f'<span class="chat-bubble {css}">{content}</span>'
                f'</div>'
            )
        transcript_inner = "\n          ".join(turns_html)
        transcript_row = (
            f'<tr><td>Conversation</td>'
            f'<td><div class="chat-transcript">\n          {transcript_inner}\n        </div></td></tr>'
        )
    else:
        transcript_row = (
            '<tr><td>Conversation</td>'
            '<td><div class="chat-turn empty">No prior conversation — first turn</div></td></tr>'
        )

    rows_html = rows_html + "\n    " + transcript_row if rows_html else transcript_row

    return _SETTING_DROPDOWN.format(rows=rows_html)


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
        fname = _resolve_group_label(node_id, sidecar.get(node_id))
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
            sidecar_entry = sidecar.get(node_id)
            # Support both old flat-list format and new {setting, runs} format
            if isinstance(sidecar_entry, dict):
                setting = sidecar_entry.get("setting", {})
                raw_runs = sidecar_entry.get("runs", [])
            elif isinstance(sidecar_entry, list):
                setting = {}
                raw_runs = sidecar_entry
            else:
                setting = {}
                raw_runs = []

            run_details: list[dict] = [
                {
                    "passed":        r["passed"],
                    "verdict":       r.get("verdict"),
                    "response_text": r["response_text"],
                    "reason":        r["reason"],
                    "conversation":  r.get("conversation", []),
                }
                for r in raw_runs
            ]
            setting_dropdown = _build_setting_dropdown(setting)

            if outcome == "passed":
                passed_tests += 1
                run_rate = f"All {len(run_details) or n_runs} runs passed ✓"
                runs_dropdown = _build_runs_dropdown(run_details)
                rows_html.append(
                    _TEST_ROW.format(
                        badge="✅",
                        test_label=label,
                        run_rate=run_rate,
                        setting_dropdown=setting_dropdown,
                        runs_dropdown=runs_dropdown,
                    )
                )
            else:
                # For failing tests: prefer sidecar, fall back to crash.message / longrepr.
                if not run_details:
                    crash_message = call.get("crash", {}).get("message", "")
                    run_summary, parsed = _extract_run_details(crash_message)
                    if not parsed:
                        longrepr = call.get("longrepr", "") if isinstance(call.get("longrepr"), str) else ""
                        run_summary, parsed = _extract_run_details(longrepr)
                    # Convert parsed tuples to the dict format
                    run_details = [
                        {"passed": p, "response_text": rt, "reason": rs, "conversation": []}
                        for p, rt, rs in parsed
                    ]
                else:
                    passes = sum(1 for r in run_details if r["passed"])
                    run_summary = f"Only {passes}/{len(run_details)} runs passed (required: {threshold_pct}%)"

                run_rate = run_summary or "Failed (no run details available)"
                runs_dropdown = _build_runs_dropdown(run_details)

                rows_html.append(
                    _TEST_ROW.format(
                        badge="❌",
                        test_label=label,
                        run_rate=run_rate,
                        setting_dropdown=setting_dropdown,
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

