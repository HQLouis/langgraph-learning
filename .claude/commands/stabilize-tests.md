You are running an automated test stabilization loop for the Lingolino dialog-system matrix. Your goal is to drive the matrix to zero FAIL cells over 3 consecutive full runs.

## Goal

The matrix classifies every (SubExample × Requirement × profile) cell
as PASS, FAIL, or N/A. N/A counts as PASS for stability purposes. The
target is **zero FAIL cells across 3 consecutive runs** at the currently
configured tier.

Stabilization runs in three stages:
1. **Stage 1 — core** (`--matrix-tier=core --matrix-profiles=default`):
   the fast inner loop. Typical size ~450 cells.
2. **Stage 2 — extended** (`--matrix-tier=all --matrix-profiles=default`):
   the full matrix at default profiles. Typical size ~9 000 cells.
3. **Stage 3 — extended profiles** (`--matrix-profiles=extended`):
   adds gender / age variants for profile-sensitive requirements.

A cell that flips PASS ↔ FAIL across runs is treated as a flake; under
10 % flake rate it does NOT reset the consecutive-pass counter.

## Context files

- Prompts: `agentic-system/local_fallback_prompts.py`
- Master node: `agentic-system/nodes.py`
- Change log: `dialogue-system-engineering/change_log.md`
- Registry: `tests/feature-testing/_registry/requirements.yaml`, `.../examples.jsonl`
- Config: `tests/feature-testing/ft_config.py`

## Cycle protocol

### Step 1 — Pick the active stage

Start at Stage 1. Only advance when the current stage achieves 3
consecutive clean runs.

### Step 2 — Run

```bash
# Stage 1
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default \
    --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# Stage 2
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=all --matrix-profiles=default \
    --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# Stage 3
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=all --matrix-profiles=extended \
    --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30
```

After the run, open
`tests/feature-testing/reporting/output/matrix_latest.html` and count
FAIL cells.

### Step 3 — Advance or diagnose

- **Zero FAIL** → increment consecutive-pass counter.
  - Counter = 3 → stage done. Move to next stage (or stop if Stage 3).
  - Counter < 3 → rerun Step 2 to confirm stability.
- **≥ 1 FAIL** → reset counter to 0, go to Step 4.

### Step 4 — Analyse by column, fix, rerun

For each failing column (requirement), read the heatmap row-by-row to
see WHICH SubExamples trigger the failure. Classify:
- **Prompt gap** → add/tighten a rule in `local_fallback_prompts.py`.
- **Detection gap** → add or refine a `_detect_<condition>` nudge in
  `nodes.py`.
- **Flake** → if it only fails once across repeated runs, note as a
  known flake and continue.
- **Judge drift** → flag to the curator; do NOT edit the judge
  criterion yourself.

Make **one** change. Rerun only the affected requirement with
`--matrix-n-runs=3` and `-k R-XX-YY` to separate the fix from flakes.
If the fix holds, go back to Step 2 for the full stage rerun.

### Step 5 — Log

Append to `change_log.md`:
- Cycle number, active stage, change applied, before/after counts.
- Consecutive-pass counter.
- Known flakes.

## Cycle tracking

Use TaskCreate at the start to track: active stage, consecutive-pass
counter, list of FAIL cells, and the latest change applied. Update the
task after every cycle.

## Rules

1. **Maximum 10 cycles per stage**. If Stage 1 isn't clean after 10
   cycles, stop and report what's still failing.
2. **Never modify `requirements.yaml` or `examples.jsonl`** — those are
   curator state. If a judge criterion is the culprit, surface it and
   stop.
3. **Revert on regression** — `git checkout` a file if a change breaks
   more cells than it fixes.
4. **Strategy B equivalence** — cells already run BG when their
   requirement has `needs_background_analysis: true`; there is no
   separate simulation step.
5. **Temperature 0.0** — confirm via `ft_config.py::SYSTEM_TEMPERATURE`.

## Reporting

When the stage sequence completes (or the 10-cycle cap is hit), print:
- Total cycles per stage
- Final FAIL counts per stage
- Changes made (with cycle numbers)
- Known flakes and their frequencies
- Outstanding curator-facing issues (judge criteria, applicability
  rules, missing SubExamples)
