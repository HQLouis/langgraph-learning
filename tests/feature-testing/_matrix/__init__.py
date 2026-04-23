"""
Matrix test engine — Phase 1+.

Consumes the registry artefacts from ``_registry/`` and runs every active
(SubExample, Requirement, profile) cell through the dialog system, the
optional background-analysis graph, and a combined applicability + judge
LLM call that emits ``PASS | FAIL | N/A``.

Two-layer caching keeps re-runs cheap:
  - L1: prefix → BackgroundState  (one BG run per unique prefix+profile)
  - L2: prefix+bg+profile → system response text

N/A counts as PASS for threshold math but is visually distinct in reports.
"""
