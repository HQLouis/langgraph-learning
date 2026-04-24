# Feature Testing Framework — Matrix Architecture

> **Single go-to document** for the Lingolino dialog-system test matrix.
> Covers the design, the file layout, every script and pytest invocation,
> the iteration / stabilisation loops, and the migration history of the
> `feature/utilizing-examples-more-efficiently` branch.

If you only read one section, read **§3 "Quick reference — what to run"**.

---

## 1. Branch summary — what changed and why

The branch `feature/utilizing-examples-more-efficiently` replaced the
old "one folder per feature" test layout with an **example × requirement
matrix** fed by a single generation pipeline rooted in
`tests/feature-testing/Dialogbeispiele für die Eigenschaften.md`.

### 1.1 Motivation

The old framework hand-wrote one pytest file per Eigenschaft. Each test
exercised exactly one Anforderung at one turn. Consequences:
- Every other Anforderung that *could* have been judged on the same
  generated response was discarded.
- A 15-turn dialogue exercised one judge call; the other 6 system turns
  were unused signal.
- The PM's source of truth (`Dialogbeispiele.md`) and the judge criteria
  (English strings hard-coded in Python) drifted apart.
- Adding a new Anforderung meant scaffolding a new folder and rewriting
  English judge text by hand.

The new design treats the human-authored MD as expensive and the
machine-generated combinations as cheap: every system turn becomes a
candidate test input (a SubExample), every Anforderung becomes a
matrix column (a Requirement), and a single parametrized pytest test
runs every active SubExample × Requirement × profile combination.

### 1.2 Branch commits (chronological)

| Commit | Phase | Summary |
|---|---|---|
| `f63731c` | 0 | Seed pipelines + registry (`_pipelines/`, `_registry/examples.jsonl`, `_registry/requirements.yaml` as drafts) |
| `e838a81` | 1 | Matrix test engine + two-layer filesystem cache (`_matrix/`) |
| `3afa2f7` | 2 | Activate 5 seed requirements; parser bug-fixes; curator-state preservation across regen |
| `3d71340` | 3 | Reporting refactor (Eigenschaft grouping + matrix heatmap) and the LLM enrichment pipeline |
| `b903e36` | 5 | Matrix-aware Claude commands (`/add-requirement`, `/sync-registry`, rewritten `/iterate-prompts`, `/stabilize-tests`) |
| `3cfe68e` | 4a | Non-destructive `DEPRECATION.md` markers on legacy folders |
| `5fefd39` | — | Centralise LLM model config in `agentic-system/model_config.py`; bump `gemini-2.0-flash → 2.5-flash` everywhere |
| `a1087c1` | — | Enrich 77 draft requirements via Gemini 2.5 Flash (LLM-drafted `applicability_rule_de` + `judge_criterion_en`) |
| `961b1d1` | 4b | Delete 5 legacy folders (`accept-no`, `no-repeat-prompts`, `sentence-structure`, `story-not-extended`, `transition-between-tasks`) — coverage verified by live matrix run |
| `3e40f4a` | 4c | Activate 6 anchor requirements for E02, E07, E09, E21 (incl. tier promotion R-09-01, R-21-01 → core) |
| `d2c2f3a` | 4d | Delete 4 more legacy folders (`respond-to-dont-know`, `story-summary`, `different-sentence-starters`, `name-usage-frequency`) |
| `c718ace` | — | Comprehensive go-to doc (this file) + CLAUDE.md update |
| `d1af8e3` | 4e | Activate 4 anchor requirements for E04, E05, E15, E18 |
| `dd38567` | 4f | Delete 4 more legacy folders (`ensure-clarity`, `answers-have-sufficient-context`, `clear-references`, `child-interests`) |
| `7bbf753` | 4g | Activate 4 anchor requirements for E10, E14, E17, E20 |
| `ac31320` | 4h | Delete 4 more legacy folders (`incorrect-story-facts`, `concrete-language`, `no-role-transfer`, `make-suggestions`) |
| `1cc443d` | 4i | Activate 4 anchor requirements for E03, E11, E12, E13 |
| `1fb6479` | 4j | Delete 4 more legacy folders (`responding-to-answer`, `child-name-and-gender`, `child-prompts-ai`, `stick-to-story-content`) |
| `4f77f94` | 4k | Activate 2 anchor requirements for E01 + Satzbau appendix |
| `457a333` | 4l | Delete final 2 legacy folders (`corrective-feedback`, `explanation-correction-verification`) — matrix is now sole suite |
| `c4733b1` | — | Docs: Phase 4 complete — update CLAUDE.md and go-to doc |
| `4b3b49c` | Iter-1 | `/iterate-prompts` cycle 1: REGEL 13 one-info rule for short child answers |
| `c6f65b2` | Iter-2 | Cycle 2: parser drops `Anmerkung:` lines; regen fixes role inversion (−6 R-19-01 FAIL) |
| `700dc28` | Iter-3 | Cycle 3: `_detect_short_child_utterance` coded nudge |
| `746d2ad` | Iter-4 | Cycle 4: R-05-01 diagnosis — judge drift, flagged to curator |

### 1.3 Current state on this branch

- **82 requirements** in `requirements.yaml` (across 22 Eigenschaften).
  - **25 active**, 57 draft (all LLM-enriched, awaiting curator review before joining the matrix).
- **293 SubExamples** in `examples.jsonl` (regen after cycle 2 parser fix: 10 `tier: core`, 283 `tier: extended`).
- **0 legacy feature folders** remain — Phase 4 complete. The matrix is the sole suite for LLM-behaviour signal.
- **Full-core baseline after 4 iteration cycles** (n=1, pass_threshold=1.0): 228 passed / 22 failed across 250 cells in 33 min. FAIL count down from ~47 pre-cycles.
- **Curator escalations open** (do not edit `requirements.yaml` during prompt iteration):
  - R-00-03 `applicability_rule_de` is too broad: overlaps with R-02-03, R-04-04, R-19-01, R-01-02 and fires on "nein"/"weiß nicht"/"vergessen"/word-clarification child turns that are primarily governed by those other requirements.
  - R-05-01 `judge_criterion_en` enforces location+character+object on EVERY new question-task, not honouring the applicability rule's "simple confirmations / clarifications" carve-out.
  - Both proposals are drafted in `dialogue-system-engineering/change_log.md` under the Cycle 3 and Cycle 4 entries.

---

## 2. How the matrix works

### 2.1 Three primitives

| Primitive | Source | Cardinality | Edited by |
|---|---|---|---|
| **Eigenschaft** | `Dialogbeispiele.md` h1 sections | ~22 | PM, in MD |
| **Requirement** | "Anforderung für eine bessere KI Antwort" blocks in MD | ~80 | PM in MD; curator in `requirements.yaml` |
| **SubExample** | Every system turn inside every Beispiel becomes a candidate test input | ~295 (after dedup) | Generated, never hand-edited |

### 2.2 The matrix

```
                    R-02-01   R-07-01   R-19-01   …
SubExample S-001    PASS      N/A       N/A       …
SubExample S-002    N/A       PASS      FAIL      …
SubExample S-003    N/A       N/A       PASS      …
…
```

- **PASS / FAIL** — requirement is applicable; judge verdict.
- **N/A** — requirement does not apply to this response (e.g. a "weiß-nicht" rule on a turn where the child did not say "weiß nicht"). **N/A counts as PASS for threshold math** but is rendered as a grey badge (not green) in the report.
- Row aggregate → "does this response satisfy every applicable requirement?"
- Column aggregate → "does the system satisfy this requirement across everything we throw at it?"

### 2.3 End-to-end flow per cell

```
SubExample.prefix_messages
        │
        ▼
┌────────────────────────────────┐
│ build_state_with_beats         │  same code-path as production
└────────────┬───────────────────┘
             │
             ▼
   needs_background_analysis?
             │
   ┌─────────┴─────────┐
   │ yes               │ no
   ▼                   │
run_background  ─►  bg_state
(9 worker LLMs)        │
   │                   │
   ▼                   ▼
 ┌──────────────────────────┐
 │ masterChatbot            │  generates response_text
 └────────────┬─────────────┘
              │
              ▼
 ┌──────────────────────────┐
 │ judge_llm                │  one combined applicability+verdict call
 └────────────┬─────────────┘
              │
              ▼
   PASS | FAIL | N/A  (+ one-line reason)
```

Both BG state and the master response are routed through a content-addressable cache (see §2.6) so re-runs are cheap.

### 2.4 Tiering — `core` vs `extended`

Both SubExamples and Requirements carry a `tier` field.

- `tier: core` — exercised on every iteration, small enough to fit a prompt-engineering inner loop (~minutes).
- `tier: extended` — exercised only on full-coverage runs.

The cell tier is `max(sub.tier, req.tier)`: if either side is `extended`,
the cell is `extended` and only runs under `--matrix-tier=extended` or
`all`. This keeps the inner loop honest — a SubExample tagged `core`
because it carries a hard rule does not contaminate the inner loop with
soft stylistic requirements that share its prefix.

A Requirement is `core` iff it expresses a hard behavioural rule
("must accept Nein", "do not repeat the child's name"). Soft stylistic
rules ("vary sentence openers") stay `extended` until the core matrix
is green.

### 2.5 Profiles — default + opt-in variants

Every SubExample carries:
- `default_profile`: one `{name, age, gender}`. Defaults: Emma/6/weiblich for PIA, Jonas/7/männlich for BOBO.
- `profile_variants`: opt-in extra profiles for gender / age sweeps.

`--matrix-profiles=…`:
- `default` — each SubExample once with its default profile.
- `extended` — also runs `profile_variants` for cells whose Requirement has `profile_sensitivity != none`.
- `all` — every variant for every cell.

### 2.6 Two-layer cache

Located at `tests/feature-testing/_matrix/.cache/`. Purely content-addressable, so any input change automatically invalidates the relevant key.

```
cache_key = sha256(prefix_messages + profile + story + bg_prompt_version + model + temperature)        ─► bg/<sha256>.json   (Layer 1)
cache_key = sha256(prefix_messages + profile + story + bg_state_hash + master_prompt_version + ...)    ─► response/<sha256>.json (Layer 2)
```

| Edit kind | L1 (BG) | L2 (response) | Effect |
|---|---|---|---|
| Judge prompt only | warm | warm | only judge calls re-run |
| Master prompt | warm | cold | master + judge re-run; BG reused |
| BG prompt | cold | cold | full re-run |
| Code in `nodes.py` impacting BG output | cold | cold | full re-run |

Judge calls are **not** cached (verdicts must be reproducible per change). The cache is safe to delete; it repopulates on the next run.

### 2.7 Combined judge prompt

One LLM call per cell decides applicability AND verdict in the same shot. Output is two lines:

```
Line 1: PASS | FAIL | N/A
Line 2: one short sentence (max 25 words) explaining the verdict
```

The judge:
- Sees the conversation prefix, the generated response, the German Anforderung, the German `applicability_rule_de`, and the English `judge_criterion_en`.
- **Never** sees the "mögliche KI Antwort" reference — that lives in the MD only as an authoring aid. No comparison against gold.
- Cell passes when `pass_rate ≥ matrix_pass_threshold` (default 1.0 at `n_runs=1` — any FAIL flips the cell red; PASS and N/A both count as non-FAIL).

### 2.8 Background-analysis-always-on (v1)

Per `dialogue-system-engineering/example-centric-testing-draft.md` §2.5b: in the current graph topology every BG worker output reaches the next master turn (directly via `aufgaben` / `satzbaubegrenzung`, indirectly via `aufgabenWorker` / `foerderfokusWorker`). Every Requirement therefore defaults to `needs_background_analysis: true`.

The flag is an **optimisation hook**, not a behavioural toggle. When the graph topology changes (a worker is removed or its output stops flowing to the master) the flag must be revisited alongside the code change.

---

## 3. Quick reference — what to run

| Goal | Command |
|---|---|
| Regenerate registry from MD | `PYTHONPATH=tests/feature-testing python -m _pipelines.run` |
| …dry-run preview | `PYTHONPATH=tests/feature-testing python -m _pipelines.run --dry-run` |
| LLM-enrich draft requirements | `PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements` |
| …only specific ids | `PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements --only R-19-02,R-19-03` |
| Run inner-loop matrix (core × default profile) | `pytest tests/feature-testing/_matrix -m matrix --matrix-tier=core --matrix-profiles=default --matrix-n-runs=1 --json-report --json-report-file=.matrix.json 2>&1 \| tail -30` |
| Run extended-tier regression (full matrix) | `pytest tests/feature-testing/_matrix -m matrix --matrix-tier=all --matrix-profiles=default --matrix-n-runs=1 --json-report --json-report-file=.matrix.json` |
| Run gender-sensitive sweep (extended profiles) | `pytest tests/feature-testing/_matrix -m matrix --matrix-tier=all --matrix-profiles=extended --json-report --json-report-file=.matrix.json` |
| Re-run only one requirement at n=3 | `pytest tests/feature-testing/_matrix -m matrix --matrix-n-runs=3 -k R-XX-YY --json-report --json-report-file=.matrix.json` |
| Force fresh generation (skip cache) | append `--matrix-no-cache` |
| Run only matrix unit tests (no LLM) | `pytest tests/feature-testing/_matrix/test_engine_unit.py tests/feature-testing/_matrix/test_sidecar_unit.py` |
| Run pipeline unit tests | `pytest tests/feature-testing/_pipelines/` |
| HTML reports written to | `tests/feature-testing/reporting/output/report_latest.html` (per-Eigenschaft) and `matrix_latest.html` (heatmap) |

> Matrix cells make real LLM calls and are **off by default**. They run only with `-m matrix` or `--matrix-run`. A bare `pytest tests/` does not hit the matrix.

---

## 4. Processes & scripts in detail

### 4.1 Generate / regenerate the registry from the MD

**What it does.** Parses `Dialogbeispiele für die Eigenschaften.md` and (re)writes:
- `tests/feature-testing/_registry/examples.jsonl`
- `tests/feature-testing/_registry/requirements.yaml`
- `tests/feature-testing/_registry/extraction_log.md` (diff vs the committed version)

**Trigger.**
```bash
PYTHONPATH=tests/feature-testing python -m _pipelines.run
# or, dry-run preview only:
PYTHONPATH=tests/feature-testing python -m _pipelines.run --dry-run
```

**Slash command alias:** `/sync-registry` walks through diff preview → real regen → review → commit.

**Idempotency & curator preservation.** Re-running on an unchanged MD produces byte-stable artefacts (except the `generated_at` timestamp). Curator-edited fields (`applicability_rule_de`, `judge_criterion_en`, `title_de`, `status`, `tier`, `profile_sensitivity`, `needs_background_analysis`) are preserved iff the entry's `anforderung_de` is byte-identical to the previously committed version.

**Hard-regen rule.** If the MD's Anforderung text changes even slightly, the Requirement reverts to `status: draft` and must be re-enriched + re-activated. This is by design — a reworded Anforderung may mean a different applicability rule, so we force re-review rather than silently carry forward stale enrichment.

**Scripts involved.**
- `_pipelines/parse_dialogbeispiele.py` — MD parser (handles implicit alternation and explicit `KI:` / `Kind:` markers).
- `_pipelines/extract_examples.py` — Pipeline A. Walks every Beispiel, emits one SubExample per system turn, deduplicates by prefix hash.
- `_pipelines/extract_requirements.py` — Pipeline B. Seeds Requirements with `[DRAFT]` placeholder fields and a status of `draft`.
- `_pipelines/regen_diff.py` — Computes the added/removed/modified diff, emits `extraction_log.md`.
- `_pipelines/run.py` — Orchestrator that runs all of the above.

### 4.2 Generate examples (Pipeline A in isolation)

Normally you don't run this alone; `_pipelines.run` calls it. Standalone use:

```bash
PYTHONPATH=tests/feature-testing python -m _pipelines.extract_examples \
    --md "tests/feature-testing/Dialogbeispiele für die Eigenschaften.md" \
    --out tests/feature-testing/_registry/examples.jsonl
```

**Output schema (`examples.jsonl`, one JSON per line):**

```jsonc
{
  "id": "S-<10-hex>",                      // stable across regens iff the prefix is byte-identical
  "prefix_hash": "<sha256>",
  "story_id": "pia_muss_nicht_perfekt_sein" | "bobos_adventskalender" | ...,
  "chapter_id": "chapter_01",
  "default_profile": {"name":"Emma","age":6,"gender":"weiblich"},
  "profile_variants": [{"name":"Jonas","age":7,"gender":"männlich"}],
  "prefix_messages": [{"role":"child","content":"hallo"}, ...],
  "golden_system_response": "...",         // debug-only; never shown to the judge
  "tier": "core" | "extended",
  "source_refs": [{eigenschaft_number, eigenschaft_title_de, beispiel_label, target_turn_index}]
}
```

**Never hand-edit `examples.jsonl`** — it's a generated artefact. Edit the MD and regen.

### 4.3 Generate / seed requirements (Pipeline B in isolation)

```bash
PYTHONPATH=tests/feature-testing python -m _pipelines.extract_requirements \
    --md "tests/feature-testing/Dialogbeispiele für die Eigenschaften.md" \
    --out tests/feature-testing/_registry/requirements.yaml
```

Seeds requirements with `[DRAFT]` placeholders. Curator state is preserved iff `anforderung_de` is unchanged.

**Output schema (`requirements.yaml`):**

```yaml
version: 1
metadata: {source, generated_at, generator, count}
requirements:
  - id: R-<eigenschaft>-<seq>            # stable across regens
    eigenschaft: <int>                   # Eigenschaft number, or null for appendix
    eigenschaft_title_de: <string>
    title_de: <string>                   # one-line German summary
    anforderung_de: <string>             # verbatim from the MD
    example_refs: [<Beispiel labels>]    # traceability only
    applicability_rule_de: <string>      # WHEN this requirement applies (German, 2-4 sentences)
    judge_criterion_en: <string>         # PASS/FAIL/N/A criterion (English; must contain all 3 return clauses)
    tier: core | extended
    profile_sensitivity: none | gender | age
    needs_background_analysis: bool      # v1: always true
    status: draft | active | deprecated
```

**Edit by hand only when activating or curating.** Adding new requirements always goes through the MD + regen.

### 4.4 LLM-enrich draft requirements

Drafts seeded by Pipeline B carry `[DRAFT]` placeholders. The enrichment pipeline calls Gemini 2.5 Flash to produce production-quality `title_de`, `applicability_rule_de`, and `judge_criterion_en`.

```bash
# Enrich every draft entry
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements

# Enrich specific entries
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements --only R-19-02,R-19-03

# Dry-run (no file write)
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements --dry-run
```

**Validation rules (from `_pipelines/enrich_requirements.py::parse_enrichment`):**
- Output must be valid JSON with three keys: `title_de`, `applicability_rule_de`, `judge_criterion_en`.
- No field may start with `[DRAFT`.
- `judge_criterion_en` must contain the three return clauses: `Return PASS if …`, `Return FAIL if …`, `Return N/A if …`.

**Status remains `draft` after enrichment.** A human curator must read the entry and flip to `status: active` before it joins the matrix.

**Slash command alias:** `/add-requirement` (covers MD edit → regen → enrich → review → activate).

### 4.5 Run tests

The repo has three test categories:

```bash
# 1. Deterministic unit tests (no LLM, fast)
pytest tests/agentic_system/                                  # ~6s
pytest tests/feature-testing/_pipelines/                      # ~2s
pytest tests/feature-testing/_matrix/test_engine_unit.py      # engine unit tests
pytest tests/feature-testing/_matrix/test_sidecar_unit.py     # sidecar + report unit tests

# 2. Matrix cells (LIVE LLM — expensive, off by default)
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default \
    --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# 3. Functional / streaming tests
pytest functional-testing/
```

**Matrix opt-in.** `tests/feature-testing/_matrix/conftest.py::pytest_collection_modifyitems` skips every `@pytest.mark.matrix` test unless the user opted in via `-m matrix` or `--matrix-run`. So a bare `pytest tests/` does not burn API credits.

**Sidecar persistence.** When the matrix runs with `--json-report --json-report-file=<path>.json`, every cell writes a sidecar entry to `<path>.run_details.json` containing `verdict`, `matrix.requirement_id`, `matrix.subexample_id`, `matrix.profile`, and the run details (response, BG state used, judge reason). The HTML reporter consumes this sidecar.

**Without `--json-report` the sidecar is not written** — pytest will still PASS/FAIL but the heatmap won't have data. Always pass `--json-report` for runs you want to inspect afterwards.

### 4.6 Run prompt optimisation / iteration

**Slash command:** `/iterate-prompts` — full protocol in `.claude/commands/iterate-prompts.md`.

**Manual loop (one cycle):**

```bash
# 1. Inner-loop baseline
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# 2. Inspect the heatmap
open tests/feature-testing/reporting/output/matrix_latest.html

# 3. Diagnose failures BY COLUMN (not by folder):
#    - mostly-red column = systematic prompt gap; one prompt change can flip many cells
#    - mostly-red row    = the SubExample's prefix is producing a uniformly bad response
# Group failures into:
#    - prompt gap     -> edit agentic-system/local_fallback_prompts.py
#    - detection gap  -> add or refine a _detect_<condition> nudge in agentic-system/nodes.py
#    - judge drift    -> flag to curator; do NOT edit requirements.yaml during iteration
#    - flake          -> note and continue

# 4. Make ONE change. Re-run only that requirement at n=3 to separate fix from flake:
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-n-runs=3 \
    -k R-XX-YY \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# 5. If targeted re-run is green, full-core regression to catch side-effects:
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json

# 6. Log to dialogue-system-engineering/change_log.md:
#    cycle, date, rule/nudge changed, before/after counts, known flakes
```

**Rules during iteration (from `/iterate-prompts`):**
1. **No overfitting.** Prompt rules must be general — never reference specific SubExample ids, story names, or character names.
2. **One change per cycle.** Impact must be measurable.
3. **Revert on regression.** If a change breaks more cells than it fixes, `git checkout` the file immediately.
4. **Never modify `requirements.yaml` or `examples.jsonl` during iteration.** Those are the curator's surface — flag the issue and stop.
5. **Temperature 0.0** — confirm via `ft_config.py::SYSTEM_TEMPERATURE`.

**Stabilisation loop.** `/stabilize-tests` runs the iteration loop in three stages (core → extended → extended-profiles) and targets **3 consecutive zero-FAIL runs per stage** before advancing.

### 4.7 Adjust DS structure (curator workflow)

**The PM's surface:** edit `tests/feature-testing/Dialogbeispiele für die Eigenschaften.md`. Every fact in the registry must trace back to the MD.

**The curator's surface:** edit `tests/feature-testing/_registry/requirements.yaml` to:
- flip `status: draft → active` after reviewing an LLM-enriched entry,
- adjust `tier` (core ↔ extended) when the inner loop's coverage decision changes,
- adjust `profile_sensitivity` (none / gender / age),
- adjust `needs_background_analysis` (only when graph topology changes — see §2.8).

**Never** hand-edit `examples.jsonl`. **Never** add a new entry to `requirements.yaml` without going through the MD + regen.

**End-to-end flow when the data structure changes:**

```
1. PM edits Dialogbeispiele.md (adds/edits an Eigenschaft, Beispiel, or Anforderung)
2. /sync-registry             # PYTHONPATH=tests/feature-testing python -m _pipelines.run
3. Open _registry/extraction_log.md → review added / removed / modified
4. For each new/reworded requirement:
   - LLM-enrich:   /add-requirement (or python -m _pipelines.enrich_requirements --only R-XX-YY)
   - Human review: applicability_rule_de must say WHEN; judge_criterion_en must end with three Return clauses
   - Activate:     status: draft → status: active
5. Smoke-test the new column:
   pytest tests/feature-testing/_matrix -m matrix \
       --matrix-tier=all --matrix-n-runs=1 -k R-XX-YY \
       --json-report --json-report-file=.matrix.json
6. Open the heatmap; commit registry + change_log entry.
```

---

## 5. Reporting

The reporting machinery is unchanged in spirit but has two output pages:

| File | Audience | Source |
|---|---|---|
| `tests/feature-testing/reporting/output/report_latest.html` | Non-technical roll-up grouped by Eigenschaft (per-feature view, matrix-aware) | sidecar `.run_details.json` |
| `tests/feature-testing/reporting/output/matrix_latest.html` | Engineer heatmap: SubExample × Requirement grid, green / red / grey for PASS / FAIL / N/A | sidecar `.run_details.json` |

The HTML hook fires automatically at the end of any `pytest tests/feature-testing/...` run that uses `--json-report`. Backwards-compatible: legacy folder-based node ids still render via the `_feature_name()` fallback.

**N/A is rendered as a grey badge** (`.run-card.na` in `generate_report.py`) — visually distinct from green PASS so a reader can tell "applied and passed" from "did not apply".

---

## 6. File layout

```
tests/feature-testing/
├── Dialogbeispiele für die Eigenschaften.md       # human source of truth (PM edits)
├── ft_config.py                                   # global + matrix config (CLI overrides registered in conftest)
├── conftest.py                                    # outer pytest fixtures (LLMs, beat manager init, HTML hook)
├── feature_testing_utils.py                       # build_state, story fixtures, simulate_conversation (legacy use)
│
├── _registry/                                     # generated + curator-reviewed artefacts
│   ├── examples.jsonl                             # SubExamples (regenerate via _pipelines.run)
│   ├── requirements.yaml                          # Requirements (curator edits enrichments + status)
│   ├── extraction_log.md                          # diff report (regenerate via _pipelines.run)
│   └── README.md                                  # schema reference for curators
│
├── _pipelines/                                    # extraction + enrichment scripts
│   ├── parse_dialogbeispiele.py                   # shared MD parser
│   ├── extract_examples.py                        # Pipeline A
│   ├── extract_requirements.py                    # Pipeline B (curator-state preservation)
│   ├── enrich_requirements.py                     # LLM enrichment (Gemini 2.5 Flash)
│   ├── regen_diff.py                              # extraction_log.md writer
│   ├── run.py                                     # orchestrator entry point
│   ├── test_pipelines.py                          # pipeline unit tests
│   └── test_enrichment.py                         # enrichment unit tests
│
├── _matrix/                                       # the test engine
│   ├── conftest.py                                # CLI options, fixtures, parametrize hook
│   ├── test_matrix.py                             # ONE parametrized test_cell function
│   ├── engine.py                                  # build_cells, generate_response, judge_response, evaluate_cell
│   ├── judge_prompt.py                            # combined applicability+verdict prompt + parser
│   ├── response_cache.py                          # two-layer filesystem cache
│   ├── production_runners.py                      # make_run_master / make_run_background factories
│   ├── sidecar.py                                 # writes per-cell run details for the report
│   ├── test_engine_unit.py                        # engine unit tests (no LLM)
│   ├── test_sidecar_unit.py                       # sidecar + report unit tests
│   └── .cache/                                    # gitignored response/BG cache
│
├── reporting/
│   ├── generate_report.py                         # per-Eigenschaft HTML (refactored, matrix-aware)
│   ├── matrix_report.py                           # NEW heatmap renderer
│   └── output/                                    # gitignored HTML output
│
                                                    # (no legacy feature folders — Phase 4 retired all of them)
```

---

## 7. Configuration

### 7.1 Global LLM model

`agentic-system/model_config.py`:

```python
DEFAULT_LLM_MODEL: str = "google_genai:gemini-2.5-flash"
def resolve_model() -> str:
    return os.environ.get("LINGOLINO_LLM_MODEL") or DEFAULT_LLM_MODEL
```

Overridable per-environment via `LINGOLINO_LLM_MODEL`. Used by:
- `ft_config.py` (`JUDGE_MODEL`, `SYSTEM_MODEL`)
- `agentic-system/chat.py`
- `_pipelines/enrich_requirements.py`
- `backend/core/config.py::Settings.llm_model`
- All three `functional-testing/test_*.py` smoke scripts.

`gemini-2.0-flash` is retired; the entire stack is on Gemini 2.5 Flash.

### 7.2 Matrix flags (`tests/feature-testing/ft_config.py`)

```python
MATRIX_ACTIVE_STATUSES: tuple[str, ...] = ("active",)   # which statuses are picked up
MATRIX_TIER: str = "core"                               # default tier filter
MATRIX_PROFILES: str = "default"                        # default profile filter
MATRIX_N_RUNS: int = 1                                  # 1 for full scans; bump for targeted reruns
MATRIX_PASS_THRESHOLD: float = 1.0                      # any FAIL flips the cell red at n=1
MATRIX_CACHE_DIR: str = "tests/feature-testing/_matrix/.cache"
MATRIX_CACHE_ENABLED: bool = True                       # disable via --matrix-no-cache
```

CLI overrides: `--matrix-tier`, `--matrix-profiles`, `--matrix-n-runs`, `--matrix-pass-threshold`, `--matrix-no-cache`, `--matrix-registry`, `--matrix-run`.

### 7.3 Probabilistic test execution (legacy fields kept for the remaining feature folders)

```python
N_RUNS: int = 1
PASS_THRESHOLD: float = 0.80
JUDGE_TEMPERATURE: float = 0.0
SYSTEM_TEMPERATURE: float = 0.0
```

---

## 8. Slash commands

| Command | Purpose | Source |
|---|---|---|
| `/sync-registry` | Re-run the extraction pipelines after a MD change. Diff preview → real regen → curator review → commit. | `.claude/commands/sync-registry.md` |
| `/add-requirement` | Add a new Anforderung end-to-end: MD edit → regen → enrich → human review → activate → smoke-test. | `.claude/commands/add-requirement.md` |
| `/iterate-prompts` | Tier-aware inner loop: core matrix → diagnose by column → one change → targeted rerun → log. | `.claude/commands/iterate-prompts.md` |
| `/stabilize-tests` | Three-stage zero-FAIL stabilisation (core → extended → extended-profiles), 3 consecutive clean runs per stage. | `.claude/commands/stabilize-tests.md` |
| `/create-feature-test` | **DEPRECATED** — replaced by `/add-requirement`. Kept for reference. | `.claude/commands/create-feature-test.md` |

---

## 9. Migration status (where we are now)

Per `dialogue-system-engineering/example-centric-testing-draft.md` §5:

| Phase | Status | Notes |
|---|---|---|
| 0 — Pipelines + registry | **DONE** | `f63731c` |
| 1 — Matrix engine + cache | **DONE** | `e838a81` |
| 2 — Activate seed requirements | **DONE** | 25 active requirements of 82 (Phases 2, 4c, 4e, 4g, 4i, 4k). |
| 3 — Migrate all Anforderungen | **DONE for extraction**; LLM-enrichment ran for all 77 drafts (`a1087c1`); curator review pending for the 57 still drafts. |
| 4 — Retire legacy folders in batches | **DONE** — all legacy folders retired across `961b1d1`, `d2c2f3a`, `dd38567`, `ac31320`, `1fb6479`, `457a333`. |
| 5 — Matrix is the only suite | **DONE** — no legacy per-feature pytest folders remain. |

---

## 10. Cost notes

Per `example-centric-testing-draft.md` §2.7:

| Mode | Cells | Cold cache | Warm (judge-prompt change only) | Warm (master-prompt change) |
|---|---|---|---|---|
| Core inner loop | ~450 | ~750 LLM calls | 450 | 480 |
| Full matrix | ~9 000 | ~10 500 | 9 000 | 9 150 |
| Extended profiles | ~9 000 × ~1.3 | ~13 650 | ~11 700 | ~11 850 |

Levers if costs spike:
- Tighten what's `tier: core`.
- Flip `needs_background_analysis: false` on Requirements where the BG output cannot influence the probed behaviour (only after graph-topology evidence — see CLAUDE.md note in §2.8).
- Use `--matrix-no-cache` only when verifying real changes; default keeps the cache warm.
- For per-PR CI, run a stratified sample (one SubExample per Beispiel × all core Requirements).

---

## 11. Where to look next

| Question | File |
|---|---|
| Why does the matrix exist? | `dialogue-system-engineering/example-centric-testing-draft.md` |
| What changed in the registry on the last regen? | `tests/feature-testing/_registry/extraction_log.md` |
| What does each requirement actually test? | `tests/feature-testing/_registry/requirements.yaml` |
| What SubExamples exist? | `tests/feature-testing/_registry/examples.jsonl` |
| What's failing right now? | `tests/feature-testing/reporting/output/matrix_latest.html` (heatmap) |
| What changed in iteration cycle N? | `dialogue-system-engineering/change_log.md` |
| What's the architectural debt? | `dialogue-system-engineering/architectural-improvements.md` |
| How is the dialog system itself wired? | `agentic-system/immediate_graph.py`, `background_graph.py`, `nodes.py`, `local_fallback_prompts.py` |
