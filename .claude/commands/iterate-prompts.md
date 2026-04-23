You are guiding the iterative prompt engineering loop for the Lingolino dialog system, using the example-centric matrix test architecture.

## Goal

Adjust prompts in `agentic-system/local_fallback_prompts.py` (and related
coded nudges in `agentic-system/nodes.py` when prompt changes aren't
enough) so that as many matrix cells as possible pass. Prompts must stay
general — never overfit to a specific SubExample.

## Context files

- Architecture draft: `dialogue-system-engineering/example-centric-testing-draft.md`
- Change log: `dialogue-system-engineering/change_log.md` — append every change
- Architectural improvements: `dialogue-system-engineering/architectural-improvements.md` — for changes beyond prompt engineering
- Prompts: `agentic-system/local_fallback_prompts.py`
- Master node: `agentic-system/nodes.py`
- Test config: `tests/feature-testing/ft_config.py`
- Registry: `tests/feature-testing/_registry/requirements.yaml`, `.../examples.jsonl`

## Tiered inner loop

Per the draft §2.3a, iteration works on two tiers:

1. **Core × Core** (inner loop) — `~450` cells, finishes in minutes.
   This is where most prompt iteration happens.
2. **Extended / All** (regression loop) — full matrix (`~9000` cells).
   Runs only after core is green, to catch regressions in softer rules.

Run commands:

```bash
# Inner loop: core tier, default profile
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# Regression: full matrix
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=all --matrix-profiles=default --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30
```

The cache (`tests/feature-testing/_matrix/.cache/`) makes re-runs cheap
when prompts haven't changed in the paths we're testing.

## Cycle protocol

### Phase 1 — Baseline (skip if baseline is already logged)

Run the core matrix. Record results in `change_log.md` under a timestamped
"Baseline" entry, with:
- total cells
- cells by verdict (PASS / FAIL / N/A)
- the list of FAIL cells with their requirement ids

### Phase 2 — Diagnose by column, not by folder

Open `tests/feature-testing/reporting/output/matrix_latest.html`. Look
at the **heatmap column view**:

- Requirement columns that are mostly red → the system systematically
  violates that rule. **Column-level failures are the highest-leverage
  targets** — one prompt change can flip many cells at once.
- Rows that are mostly red → the SubExample's prefix is producing an
  especially bad response across many requirements. Often a single
  underlying bug (e.g. wrong task from `aufgaben`) drives this.

Group FAIL cells by:
- **Prompt gap** — a rule is missing or conflicting in
  `local_fallback_prompts.py`.
- **Detection gap** — the LLM ignores the prompt; a coded nudge in
  `nodes.py` (pattern: `_detect_<condition>`) is needed.
- **Judge drift** — the judge is being overly strict or inconsistent.
  Document but do NOT edit the judge criterion without the curator's
  approval (the curator owns `requirements.yaml`).
- **Engine flake** — cell flips verdict across runs; note as a known
  flake, move on.

### Phase 3 — One change, targeted rerun

Make ONE logical change (a prompt rule, OR a new `_detect_*` function,
OR a tweak to an existing detection nudge). Then rerun the affected
requirement ONLY:

```bash
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-n-runs=3 \
    -k R-XX-YY \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30
```

`--matrix-n-runs=3` is important for targeted reruns — it distinguishes
fixes from flakes.

### Phase 4 — Full-core regression

If the targeted rerun goes green, rerun the full core matrix to catch
regressions elsewhere. If no regressions, move to Phase 5.

### Phase 5 — Log the change

Append to `change_log.md`:
- Cycle number, date, what rule/nudge changed and WHY
- Before and after counts per verdict
- Any known flakes or new failures

### Phase 6 — Widen

Once core × core is green for 3 consecutive runs, widen to
`--matrix-tier=extended --matrix-profiles=default`. Same loop. Then
`--matrix-profiles=extended` for the gender-sensitive sweep.

## Rules

1. **No overfitting**. Rules must be general conversation principles —
   never reference specific stories, character names, or SubExample ids.
2. **One change per cycle** so impact is measurable.
3. **Revert on regression**. If a change breaks more cells than it fixes,
   `git checkout` the changed file immediately.
4. **Strategy B-equivalent** — cells with `needs_background_analysis:
   true` already include a BG pass; no separate strategy is needed.
5. **Never modify `requirements.yaml` or `examples.jsonl` during
   iteration**. Those are the curator's surface — tell the user if a
   judge criterion seems wrong.
6. **Temperature 0.0** — check `ft_config.py::SYSTEM_TEMPERATURE`.

## Learnings carried over from the old `/iterate-prompts`

- **Prompt rules can conflict**. When two prompt rules point in
  opposite directions, the LLM picks unpredictably. Coded detection
  nudges in `nodes.py` that fire AFTER generation as SystemMessages are
  more reliable (examples: `_detect_repetitive_starters`,
  `_detect_repeated_disengagement`, `_detect_story_end`).
- **Grammar glitches → post-processing**, not prompt tweaks. See
  `german_grammar_postprocess.py` for the pattern.
- **Beat system, not keywords**, for story-end detection. Don't add
  story-specific keywords to `_detect_story_end`.
- **Simulated-style cells are more variable**. A cell that passes with
  `needs_background_analysis: false` but fails with it `true` means
  the BG graph is the problem — inspect `aufgaben` / `satzbaubegrenzung`.

## Escalation

After 5 cycles with a requirement column still red, consider:
1. A new `_detect_*` nudge in `nodes.py`.
2. An architectural fix (document in `architectural-improvements.md`).
3. Whether the requirement's applicability rule or judge criterion is
   the actual problem — flag it to the curator.
