# ⚠️ Deprecated — coverage moved to the matrix

This folder tests the "Geschichte nicht extra verlängern" Eigenschaft
(#8) via the legacy per-feature test pattern. Coverage has been moved
to the registry-driven matrix:

- **Requirement:** `R-08-03` — "End the conversation gently after the main scenes are covered"
- **Registry:** `tests/feature-testing/_registry/requirements.yaml`
- **Run the matrix cells for this requirement:**
  ```
  pytest tests/feature-testing/_matrix -m matrix \
      --matrix-tier=all -k R-08-03 \
      --matrix-n-runs=3
  ```

## Do NOT delete this folder yet

The matrix has **not yet been verified live** against this requirement.
Until a curator (a) runs the matrix with real LLMs, (b) confirms the
cells behave as expected, and (c) compares the matrix verdicts against
the legacy tests here, this folder must stay in place as a regression
safety net.

Planned retirement path (see `dialogue-system-engineering/example-centric-testing-draft.md`
Phases 4–5):

1. Live-run the matrix against R-08-03 and collect the HTML report.
2. Compare pass rates between this folder and the matrix cells.
3. If the matrix fully subsumes the legacy coverage, mark tests here
   with `@pytest.mark.skip(reason="subsumed by matrix R-08-03")` as a
   reversible deprecation step.
4. After two weeks of green matrix runs, delete this folder in a
   follow-up commit.

## Why the move?

The old Strategy A / Strategy B pattern ran one Anforderung per hand-
written script. The matrix runs every active Anforderung against every
SubExample (including the ones that used to live here), with a
PASS / FAIL / N/A judge. See `example-centric-testing-draft.md` for the
full rationale.
