You are adding a new requirement to the Lingolino dialog-system test matrix.

## Inputs

- **Anforderung (German text)**: $ARGUMENTS
- **Eigenschaft / context**: $ARGUMENTS

The user typically hands you one paragraph in German (copied from
`tests/feature-testing/Dialogbeispiele für die Eigenschaften.md`) plus
optionally the Eigenschaft number and Beispiel labels.

## What this replaces

This command replaces `/create-feature-test`. The old command scaffolded
a whole pytest folder (`tests/feature-testing/<feature>/test_*.py`) with
hardcoded Strategy A + Strategy B classes and English criteria.

The new testing architecture makes that unnecessary:
- Requirements live in `tests/feature-testing/_registry/requirements.yaml`.
- A single parametrized matrix test (`tests/feature-testing/_matrix/test_matrix.py`)
  runs every active Requirement × every active SubExample.
- No Python file is ever created for a new Requirement.

## Your task

### Step 1 — Locate or create the Anforderung in the MD

The `Dialogbeispiele für die Eigenschaften.md` is the single source of
truth. If the Anforderung isn't already there:
1. Ask the user where it should be added (under which numbered
   Eigenschaft, and ideally which Beispiel illustrates it).
2. Add the Anforderung paragraph to the MD under the appropriate
   `## Anforderung für eine bessere KI Antwort:` marker.

Do NOT hand-write entries in `requirements.yaml` — always go through the MD.

### Step 2 — Regenerate the registry

Run:

```
PYTHONPATH=tests/feature-testing python -m _pipelines.run
```

This parses the MD, produces `examples.jsonl` and `requirements.yaml`,
and writes `_registry/extraction_log.md` with the diff. Look at the
diff: the new Anforderung should appear as an "added" Requirement with
a fresh `R-<eig>-<seq>` id and `status: draft`.

### Step 3 — Enrich the new Requirement via LLM

The new entry has `[DRAFT]` placeholders for `title_de`,
`applicability_rule_de`, and `judge_criterion_en`. Run:

```
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements \
    --only R-<eig>-<seq>
```

This calls the LLM once to draft the three fields. The entry stays at
`status: draft` — the LLM produces drafts, not truth.

### Step 4 — Human review

Read the enriched YAML entry. Specifically check:
- `applicability_rule_de` must say **when** the requirement applies
  (and when it does NOT). If it says "applies to every response" without
  qualification, rewrite it. Most requirements have situational
  applicability.
- `judge_criterion_en` must end with explicit `Return PASS if …`,
  `Return FAIL if …`, `Return N/A if …` clauses.
- `tier` — `core` if the rule is behavioural and testable every turn
  (e.g. "no repeat prompts"); `extended` if stylistic (e.g. "vary
  sentence starters").
- `profile_sensitivity` — `gender` / `age` / `none`.
- `needs_background_analysis` — currently always `true` in v1 (see
  `dialogue-system-engineering/example-centric-testing-draft.md` §2.5b).
  Leave it.

### Step 5 — Activate

Flip `status: draft` → `status: active`. Commit `requirements.yaml`.

### Step 6 — Smoke-run the matrix against just this new cell

```
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=all --matrix-profiles=default \
    --matrix-n-runs=1 \
    -k R-<eig>-<seq>
```

Look at the HTML report:
- `tests/feature-testing/reporting/output/report_latest.html` (per-Eigenschaft view)
- `tests/feature-testing/reporting/output/matrix_latest.html` (heatmap)

### Rules

1. **Never hand-write entries in `requirements.yaml`**. Always go via
   the MD + regen.
2. **Always stop after Step 4** to let the human review the enrichment
   before activation.
3. **No Python file is created** — the matrix test already covers every
   active Requirement × active SubExample.
4. **Preserved across regen**: once the curator has enriched a
   Requirement, `_pipelines.run` carries the enriched fields over on
   subsequent regens (unless the MD's Anforderung text changes, in
   which case the entry reverts to `draft`).

### Summary output

After you finish, print:
- The new Requirement id.
- Before / after of the enriched YAML fields.
- The pytest command to run the matrix against only this new cell.
