# Draft: Example-Centric Feature Testing Architecture

Status: **DRAFT v2 — open questions resolved, ready for implementation-plan pass**
Author: autonomous proposal (Opus 4.7)
Target reviewer: Louis
Scope: replace the feature-per-folder test layout with an example × requirement matrix fed by a single generation pipeline rooted in `Dialogbeispiele für die Eigenschaften.md`.

**v2 changes** — resolved open questions per reviewer feedback:
- Added §2.3a *Tiering (core vs extended)* to support fast iteration.
- Clarified §2.5 *Strategy A/B collapse*: it's really a per-cell `run_background_before_generation` flag, not a loss of functionality.
- Added §2.5a *Profile multiplier* with default profile + opt-in extended profiles.
- Expanded §2.6 *Judge prompt* — verdict is strictly `PASS | FAIL | N/A`, N/A rolls up as PASS.
- Added §2.8 *Report adjustments* — how `reporting/generate_report.py` changes for the matrix view.
- Added §2.9 *Regen strategy* — hard regen + diff report on every MD change.
- Open-question section rewritten as §6 *Resolved decisions*.

---

## 1. Current state (Ist-Zustand)

### 1.1 Source of truth
`tests/feature-testing/Dialogbeispiele für die Eigenschaften.md` (2246 lines) contains:
- **2 full story texts** — PIA (*Pia muss nicht perfekt sein*), BOBO (*Bobos Adventskalender*).
- **21 numbered Eigenschaften** (properties/features): `1. Übergang von einer Wortbedeutung` … `21. Namen nicht zu oft ansprechen`, plus appendix sections (Satzbau, Eröffnung, Reihenfolge der Ereignisse, Korrektives Feedback, Dialogführung-Konzept).
- Each Eigenschaft has multiple **Beispiele**. A Beispiel typically contains:
  - A full conversation (child ↔ KI, 5–30 turns).
  - A highlighted **actual KI turn** (bolded) that is "the moment" being illustrated.
  - A **mögliche KI Antwort** — the ideal response.
  - One or more **Anforderungen für eine bessere KI Antwort** — the actual requirements.

### 1.2 Test layout
```
tests/feature-testing/
├── <feature-name>/                   # 22 feature folders
│   ├── <feature>-test-spec.txt       # hand-copied from Dialogbeispiele.md
│   └── test_<feature>.py             # Strategy A (fixture) + Strategy B (simulated)
├── feature_testing_utils.py          # build_state, simulate_conversation, llm_judge, story fixtures
├── ft_config.py                      # N_RUNS, PASS_THRESHOLD, models
├── conftest.py                       # CLI options, fixtures, HTML reporting hook
└── Dialogbeispiele für die Eigenschaften.md
```

Every test file:
1. Hard-codes a conversation script (`SCRIPT_*`) or relies on `MESSAGES_TURN_*` fixtures.
2. Hard-codes English judge criteria (`CRITERION_*`).
3. Calls either `build_state_with_beats → masterChatbot` (A) or `simulate_conversation` (B).
4. Sends the generated response + criterion to `llm_judge`, N times, thresholded.

### 1.3 Cost of the current approach
- **Information loss**: each hand-written example tests **one requirement at one turn**. The other 20 requirements that could be evaluated on the same response are ignored.
- **Evolution loss**: a 15-turn dialogue has ~7 system turns; only the final one gets tested. The middle turns are "free" evaluation opportunities we discard.
- **Duplication**: every feature script starts with `"hallo"` and proceeds through similar PIA openings. Those prefixes are re-simulated by Strategy B tests in each folder.
- **Drift risk**: `Dialogbeispiele.md` is the PM's source of truth but test files hardcode English criteria that must be re-translated by hand whenever an Anforderung changes.
- **Feature-folder coupling**: a new Eigenschaft means a new folder, new `*-test-spec.txt`, new test module, new judge strings — high friction for PMs who just want to add an Anforderung.

### 1.4 Claude commands wired to this layout
| Command | Purpose | Coupling to feature folders |
|---|---|---|
| `/create-feature-test` | Scaffolds a new `tests/feature-testing/<feature>/test_*.py` | Hard-coded folder-per-feature |
| `/iterate-prompts` | Run full suite → analyse failures per feature → tweak prompt → re-run | Reasons about failures per feature |
| `/stabilize-tests` | 3 consecutive green full-suite runs | Same as above |

---

## 2. Target state (Soll-Zustand)

### 2.1 Guiding principle
> A human-authored example is an expensive artefact. One example should contribute to as many requirement evaluations as are logically testable on it, automatically — not just the one the PM had in mind when writing it.

### 2.2 Three primitives

| Primitive | Source | Lifetime | Cardinality |
|---|---|---|---|
| **Eigenschaft (category)** | `Dialogbeispiele.md` h1 sections | Stable; grows occasionally | ~22 |
| **Requirement** | "Anforderung für eine bessere KI Antwort" blocks | Mutable; PM edits | ~60–80 |
| **SubExample** | Every system turn inside every Beispiel becomes a candidate test input | Generated, deduplicated | ~300–600 (est.) |

### 2.3 The matrix

```
                  Requirement R-01.1   R-01.2   R-02.1   R-02.2   …   R-21.3
SubExample S-0001    PASS               N/A      N/A      N/A     …    PASS
SubExample S-0002    N/A                PASS     FAIL     N/A     …    PASS
SubExample S-0003    N/A                N/A      PASS     PASS    …    N/A
…
```

Cell semantics:
- **PASS / FAIL** — requirement is applicable to this response; judge verdict.
- **N/A** — requirement is not applicable (the response has no surface that this requirement governs). **N/A is treated as PASS** for all threshold math and aggregate metrics, but is visually distinct in the report (grey badge, not green).

Row aggregate → "does this response satisfy every applicable requirement?" (strictest view).
Column aggregate → "does the system satisfy this requirement across everything we throw at it?" (regression view).

### 2.3a Tiering — core vs extended

Both SubExamples and Requirements carry a **tier** flag:
- `tier: core` — tested on every iteration. Small enough to fit into a prompt-engineering inner loop (~minutes, not hours).
- `tier: extended` — tested only on full-coverage runs (manual trigger + nightly CI). The long tail.

Rules for what becomes core:
- A SubExample is `core` if it comes from a Beispiel that the PM marks as *central* for its Eigenschaft — typically the most pedagogically rich turn (often the highlighted/bolded KI turn in the MD).
- A Requirement is `core` if it expresses a hard behavioural rule (e.g. "do not ask the child to repeat words", "accept 'Nein'"). Soft stylistic requirements (e.g. "vary sentence openers") stay `extended` until core is green.

Inner loop during `/iterate-prompts` runs only `core × core`. Once that's green, the loop widens to `core × all` → `all × all`. This keeps the fast-feedback window honest: a dev iteration is minutes, not hours, and we don't chase stylistic flakes while regressing hard rules.

Tier is a simple field in both `examples.jsonl` and `requirements.yaml`, flippable via PR.

### 2.4 Two pipelines

**Pipeline A — Example Extraction & Deduplication**
1. Parse `Dialogbeispiele.md` → list of Beispiele, tagged with `Eigenschaft` and `story_id` (PIA / BOBO / OTHER).
2. For each Beispiel, tokenize the dialogue into alternating `child`/`system` turns.
3. For each system turn `T_k` (k ≥ 1), emit a SubExample with:
   - `prefix_messages = [turn_0, turn_1, …, turn_{k−1}, child_turn_k]`
   - `golden_system_response = T_k` (retained only for debugging; we never test against it directly).
   - `source_refs = [beispiel_id]`
   - `story_id`, `child_profile_hint` (defaulted if not specified in MD).
4. Normalize prefixes (trim whitespace, unify quotes) and hash.
5. **Deduplicate by prefix hash.** When two Beispiele share an opening, the SubExample carries both `source_refs`.
6. Emit `tests/feature-testing/_registry/examples.jsonl`.

**Pipeline B — Requirement Extraction & Registry**
1. Parse `Dialogbeispiele.md` → for each Eigenschaft section, extract every "Anforderung"-block.
2. For each Anforderung, an LLM-assisted generator writes a full YAML entry in `tests/feature-testing/_registry/requirements.yaml`:
   - `id`: `R-<eigenschaft#>-<seq>` (e.g. `R-02-1`, `R-21-3`)
   - `eigenschaft`: integer category
   - `title_de`: one-line summary (LLM-generated)
   - `anforderung_de`: verbatim German text from MD
   - `example_refs`: Beispiele that originally illustrated this Anforderung (traceability)
   - `applicability_rule_de`: LLM-drafted German rule for "when does this requirement apply to a response?" — seeded from the MD, grounded in the Beispiele and optionally the "mögliche KI Antwort" reference (which serves as a specification aid, not a comparison target).
   - `judge_criterion_en`: full English judge prompt emitting `PASS | FAIL | N/A`.
   - `tier`: `core | extended` (see §2.3a; LLM-proposed, human-confirmed).
   - `profile_sensitivity`: `none | gender | age` — drives §2.5a.
   - `needs_background_analysis`: `true | false` — drives the per-cell flag in §2.5. **Default `true` for v1** (see §2.5b); the field is kept in the schema as a future-optimisation hook.
   - `status`: `draft | active | deprecated`.
3. Human role is review-only: the PM / engineer approves or edits the draft, flips `status: active`, and merges. **No hand-authoring from scratch.**
4. The "mögliche KI Antwort" from the MD is used during generation as a specification aid (to infer intent when the Anforderung text is terse), but is never stored as a comparison target in the registry. This matches the reviewer's decision in §6.

Both pipelines are **idempotent and diff-friendly** — re-running them only changes entries whose source text changed in the MD. See §2.9 for regen policy.

### 2.5 The test engine — and why Strategy A/B collapses

Single pytest module: `tests/feature-testing/_matrix/test_matrix.py`, parametrized over `active_subexamples × active_requirements × active_profiles` (see §2.5a for the profile dimension).

Per cell:
1. **Build state** from `prefix_messages` using `build_state_with_beats`.
2. **Optional background analysis pass**. If the requirement has `needs_background_analysis: true`, run `run_background_analysis` once over the prefix to populate `aufgaben`, `satzbaubegrenzung`, and related fields. Otherwise skip — those fields stay empty.
3. **Generate** the system response with `masterChatbot`.
4. **One LLM judge call** emitting `PASS | FAIL | N/A` with a one-line reason (see §2.6).
5. Re-run `n` times (config-driven), aggregate by majority. `N/A` counts as PASS.

**Why Strategy A/B dissolves.** In the current framework, `simulate_conversation` (Strategy B) does NOT actually generate intermediate system turns live — those are already pre-written inside `child_inputs`. The only substantive difference between A and B is whether the background analysis graph runs once before the final generation to seed analysis fields. Everything else is bookkeeping. In the matrix model:
- The MD dialogue **is** the deterministic script — every prefix is fixed.
- "Strategy A" == run cell without background analysis (fast, most cells).
- "Strategy B" == run cell with background analysis (slower, only for requirements that depend on analysis output).
- This is now a **per-cell opt-in flag** (`needs_background_analysis`), not a per-test-file choice that duplicates scripts and judge criteria.

So we don't lose Strategy B's capability — we just stop paying for it on every requirement that doesn't need it, and we stop duplicating the prefix authoring across two folders.

Benefits:
- No per-example test authoring.
- No per-feature folder scaffolding.
- Changes in `requirements.yaml` ripple instantly.
- Changes in `Dialogbeispiele.md` ripple after re-running Pipeline A.
- Background analysis becomes a surgical cost, not a strategy-level one.

### 2.5b Background analysis — always on for v1

In the current dialogue-system architecture **every** background-graph worker output eventually flows into the next `masterChatbot` turn:
- `aufgaben` and `satzbaubegrenzung` are injected directly.
- The upstream analyses (`grammar_analysis`, `speech_comprehension_analysis`, `sprachhandlung_analysis`, `vocabulary_analysis`, `boredom_analysis`, `foerderfokus`) are consumed by `aufgabenWorker` and `foerderfokusWorker` and therefore reach the master indirectly but reliably. None of them is truly independent of the next master response.

Consequence for v1 of the matrix:
- All Requirements default to `needs_background_analysis: true`. Pipeline B seeds them that way and the human reviewer only flips to `false` when they have explicit evidence the BG output cannot influence the probed behavior.
- The field remains in the schema because the graph topology is expected to evolve: once a worker is confirmed to have no path to the master's next turn, requirements whose defect mode is independent of remaining BG outputs can be flipped `false` to cut cost.
- The flag is therefore **an optimization hook**, not a behavioural toggle, for v1.

This changes cost materially — see updated §2.7 — but **caching amortises it**: BG runs on a unique prefix, not per-cell. A prefix shared across 40 Requirements pays the BG cost once.

### 2.5a Profile multiplier — default + opt-in

Every SubExample carries:
- `default_profile`: the single most-representative `{name, age, gender}` for that example (usually the original profile from the Beispiel or a sensible default: Emma, 6, weiblich for PIA openings; Jonas, 7, männlich for BOBO openings).
- `profile_variants`: additional `{name, age, gender}` tuples used only when explicitly enabled.

Per-run flag `--profiles=default|extended|all` (default = `default`):
- `default` — each SubExample is instantiated once with its `default_profile`. Used in the inner iteration loop and core runs.
- `extended` — SubExamples whose matched Requirement has `profile_sensitivity != none` are instantiated with both genders (and optionally a second age bracket). Opt-in because of cost.
- `all` — every SubExample × every variant. Nightly/weekly only.

So: fast iteration stays single-profile, but gender- and age-sensitive requirements (`R-11-*`, `R-17-*`, etc.) can be exhaustively swept by flipping `--profiles=extended` without editing any test files.

### 2.6 Combined judge prompt (draft)

```text
You are evaluating a single system response from a German children's dialog system
against ONE requirement.

--- Conversation history (up to and including the last child utterance) ---
{prefix_conversation}

--- System response being evaluated ---
{response_text}

--- Requirement (original German) ---
{anforderung_de}

--- Applicability rule ---
{applicability_rule_de}

--- Your task ---
Step 1. Decide whether the requirement is APPLICABLE to this response,
        according to the applicability rule.
Step 2a. If NOT applicable, output exactly:
           N/A
           <one short sentence why>
Step 2b. If applicable, output exactly:
           PASS|FAIL
           <one short sentence why>

Do not output anything else.
```

Key points:
- Applicability and verdict collapsed into one call to save cost. Measured on the first 20 cells before rollout; split into two calls if verdicts drift.
- The judge **never sees the "mögliche KI Antwort"** reference — per §6 decision, the reference only informs *registry authoring*, not runtime judging.
- N/A is a first-class verdict with its own reason string, so reports can show *why* a requirement was skipped (debuggable) rather than silently counting it.

### 2.7 Cost analysis — with BG-always-on (v1)

Per §2.5b, v1 runs the background graph on every cell. BG = ~9 worker LLM calls per unique prefix (one per worker node). Post-dedup of PIA+BOBO:
- **Full matrix** — ~150 unique prefixes × ~60 Requirements = 9 000 cells.
- **Core matrix** — ~30 unique prefixes × ~15 Requirements = 450 cells.

Two-layer cache (see §3 file layout, `response_cache.py`):
- L1: `bg_cache[prefix_hash, bg_prompt_hashes, model, temp] → BackgroundState` — one BG run per unique prefix, reused across all Requirements that share the prefix.
- L2: `response_cache[prefix_hash, bg_state_hash, master_prompt_hash, profile_id, model, temp] → response_text` — one master generation per (prefix × profile), reused across all Requirements judging that response.

| Mode | Cells | LLM calls — cold cache | Warm cache (judge-prompt-only change) | Warm cache (master-prompt-only change) |
|---|---|---|---|---|
| Core iteration | ~450 | 30×9 (BG) + 30 (master) + 450 (judge) = **~750** | 450 | 30 + 450 = 480 |
| Full matrix | ~9 000 | 150×9 + 150 + 9 000 = **~10 500** | 9 000 | 150 + 9 000 = 9 150 |
| Extended profiles (opt-in) | ~9 000 × ~1.3 | ~13 650 | ~11 700 | ~11 850 |

Levers (unchanged from v1, plus tiering and BG caching):
- **Tiering** — core vs extended keeps the iteration loop at ~450 cells.
- **BG cache** — the big win. Because BG output only depends on the prefix (not on which Requirement is being evaluated), dedup collapses BG calls from `cells × 9` to `unique_prefixes × 9`.
- **n-runs** — 1 for the full matrix; re-run only FAIL cells with n=3 to separate flakes from defects.
- **Prompt-change locality** — editing only the judge prompt invalidates L2 for nothing and L1 for nothing; editing only a master prompt invalidates L2 for everything but L1 stays warm; editing a BG prompt invalidates both.
- **CI sampling** — stratified sample (one SubExample per Beispiel × all core Requirements) for per-PR runs.
- **Prioritisation** — schedule judge calls by `(requirement.tier, suspected_failure_likelihood)` so the first failures surface quickly.

### 2.8 Report adjustments (`reporting/generate_report.py`)

The current HTML report (`tests/feature-testing/reporting/generate_report.py`) groups tests by **feature folder** via `_feature_name(node_id)`, which extracts the folder name between `feature-testing/` and the next slash in the pytest node id. That slicing is hard-wired to the current folder-per-feature layout and will stop working once tests come from `_matrix/test_matrix.py` with parametrized IDs like:
```
tests/feature-testing/_matrix/test_matrix.py::test_cell[S-0042-R-07-2-default]
```

Changes required:
1. **New grouping strategy** — group primarily by **Eigenschaft** (from the requirement), not by folder. The test's node id + parametrization carries `(subexample_id, requirement_id, profile_id)`. Resolve `requirement_id → eigenschaft` via `requirements.yaml` at report build time. This gives the PM a familiar "per-feature" view even though folders are gone.
2. **New matrix page** — a heatmap view rendering the SubExample × Requirement grid: rows = SubExamples (grouped by source Beispiel), columns = Requirements (grouped by Eigenschaft), cells coloured green/red/grey (PASS/FAIL/N/A). Row and column aggregates shown on the margins. Click a cell → same run-details drawer we already render per-run today.
3. **Sidecar schema extended** — the current sidecar stores `{setting, runs[{passed, response_text, reason, conversation}]}`. We add:
   - `verdict`: one of `PASS | FAIL | N/A` (not just a bool) so N/A is first-class.
   - `subexample_id`, `requirement_id`, `profile_id`, `eigenschaft`, `tier` — for grouping and filtering.
   - `background_analysis_run`: bool (so you can see whether BG fed the generation).
4. **N/A styling** — new grey badge + "Not applicable" label, distinct from green PASS. The current `_RUN_CARD` css classes `.pass` / `.fail` get a sibling `.na`.
5. **Dual landing pages**:
   - `report_latest.html` — existing non-technical per-Eigenschaft view, now sourced from the matrix instead of folders.
   - `matrix_latest.html` — new technical heatmap for engineers.
6. **Backwards-compatible fallback** — for the migration window (Phases 0–4) the report still handles the existing folder-based node ids by using `_feature_name()` as the fallback path when `requirement_id` is missing from the sidecar. No existing test breaks.

Practical impact: `generate_report.py` gets a new helper module `matrix_report.py` (new heatmap), while the existing monolithic HTML builder is split into `report_per_eigenschaft.py` (Eigenschaft roll-up, refactored from today's logic) + a shared `render_run_card` utility. No user-visible feature is removed.

### 2.9 Regen strategy — hard regen + diff report

Whenever `Dialogbeispiele.md` changes:
1. `extract_examples.py` and `extract_requirements.py` regenerate `examples.jsonl` / `requirements.yaml` from scratch.
2. A diff is computed against the previous commit of each file and written to `_registry/extraction_log.md` as a human-readable report:
   - SubExamples added / removed / hash-shifted (and which source Beispiel moved)
   - Requirements added / modified / deprecated
   - Cells that will flip status from active → draft because their source Anforderung text changed enough to warrant re-review
3. Entries whose source changed materially revert to `status: draft` and require re-approval before re-entering the matrix.
4. There is **no silent carry-over** of SubExample IDs across MD rewrites. This is by design — if a Beispiel was reworded, the PM must confirm the new turn still embodies the same pedagogical point.

Tradeoff: a large MD rewrite triggers a large re-review pass. That's the cost of having the MD be the single source of truth; we don't paper over it with fuzzy matching.

### 2.10 Applicability — degenerate but intentional

Many requirements will be non-applicable to most responses. That's the point — we *want* broad coverage, accepting that most cells resolve to N/A. A row like "gender address" is applicable only when the response addresses the child directly; "word explanation" only when a word is being explained. N/A carries signal too: it tells us the system *didn't trigger the condition* the PM illustrated.

### 2.12 What stays the same

- `Dialogbeispiele für die Eigenschaften.md` is still the **only human-authored source**. It is updated by the PM periodically. Our pipelines consume it unchanged.
- `feature_testing_utils.py` stays (we still use `build_state_with_beats`, `masterChatbot`, the story fixtures).
- `ft_config.py` grows a few matrix flags, doesn't lose anything.
- HTML reporting keeps its existing machinery; we add a matrix view on top.
- Existing per-feature test folders **stay temporarily** for regression confidence during migration (Phase 0–3, see §5).

### 2.10 What changes

- No new "feature folder" for new requirements — PM adds an Anforderung in MD, we run Pipeline B, someone reviews it, it activates.
- Tests are parametrized, not hand-written per feature.
- Judge criteria live in `requirements.yaml` (YAML, human-readable, reviewable via PR) not in Python strings scattered across 22 test files.
- Strategy A / Strategy B distinction collapses: every cell is "generate from a fixed prefix, judge the response". We no longer regenerate earlier turns live — the MD dialogue IS our deterministic script.
- `/create-feature-test` becomes `/add-requirement` (see §4).

---

## 3. File layout (after migration)

```
tests/feature-testing/
├── Dialogbeispiele für die Eigenschaften.md       # unchanged, human source
├── _registry/                                     # NEW — generated + reviewed artefacts
│   ├── requirements.yaml                          # PM-reviewable requirement registry
│   ├── examples.jsonl                             # deduplicated SubExamples
│   └── extraction_log.md                          # Pipeline A/B diff report (§2.9)
├── _pipelines/                                    # NEW — parse & generate
│   ├── parse_dialogbeispiele.py                   # shared tokenizer
│   ├── extract_examples.py                        # Pipeline A
│   ├── extract_requirements.py                    # Pipeline B (seeds YAML via LLM)
│   ├── dedup_subexamples.py
│   └── regen_diff.py                              # emits extraction_log.md diff
├── _matrix/                                       # NEW — test engine
│   ├── conftest.py                                # parametrize, caching, tier/profile flags
│   ├── test_matrix.py                             # single matrix test
│   ├── judge_prompt.py                            # combined applicability+verdict prompt
│   └── response_cache.py                          # (prefix_hash, sys_prompt_hash, model) → response
├── feature_testing_utils.py                       # unchanged
├── ft_config.py                                   # +MATRIX_*, +TIER_*, +PROFILE_* flags
├── conftest.py                                    # unchanged; matrix conftest is scoped
├── reporting/                                     # extended — see §2.8
│   ├── generate_report.py                         # refactored: groups by Eigenschaft, renders N/A
│   ├── matrix_report.py                           # NEW — heatmap view
│   └── render_run_card.py                         # shared run-card util
└── <existing feature folders>/                    # kept until Phase 4
```

---

## 4. Claude command changes

### 4.1 `/create-feature-test` → `/add-requirement`
Old: scaffolded a feature folder with Strategy A/B tests.
New: given an Anforderung (German text) and optional Beispiel references:
1. Propose an entry for `requirements.yaml` (id, anforderung_de, applicability_rule, judge_criterion_en).
2. Verify the referenced Beispiele are already in `examples.jsonl` (re-run Pipeline A if new).
3. Mark the entry `status: draft` — requires human `status: active` flip before it runs.

No Python file is ever generated — the matrix test already covers it.

### 4.2 `/iterate-prompts` — refocus from feature to requirement, tier-aware
Old: "fix one feature folder at a time".
New:
1. Run **core matrix** first (`tier:core × tier:core`, `--profiles=default`, `n=1`) — fast inner loop.
2. Identify FAIL columns (requirements the system violates systematically) and FAIL rows (responses that violate many requirements).
3. Group failures by **root cause in the requirement**, not the feature folder.
4. Make one prompt change, re-run only the affected core column.
5. When core is green → widen to `core × all`, then `all × all` before declaring done.
6. `--profiles=extended` is run as a final regression pass once the matrix is green at default profile.

Docs, change-log entries, and the "prompt vs coded nudge" learnings all carry over unchanged.

### 4.3 `/stabilize-tests` — matrix-aware, tier-aware
Old: 3 consecutive full-suite green runs.
New:
1. Stage 1 target = 3 consecutive **core matrix** runs with zero FAIL cells (N/A is fine).
2. Stage 2 target = 3 consecutive **full matrix** runs with zero FAIL cells.
3. Stage 3 (optional) = 1 clean `--profiles=extended` run.
4. Per-cell flakiness is tracked; if a cell flips PASS↔FAIL across runs it is flagged as a known flake, counted separately, and does not reset the consecutive counter if under 10 % flake rate.
5. `needs_background_analysis: true` cells run inside the same stages — they're not their own strategy anymore.

### 4.4 New command: `/sync-registry`
1. Re-runs Pipeline A + Pipeline B against the current MD (§2.9: hard regen).
2. Writes the diff to `_registry/extraction_log.md`: new SubExamples, modified Anforderungen, orphaned requirements, hash-shifted SubExamples.
3. Moves affected entries to `status: draft`. A human must re-activate them.
4. Prints a one-line summary for the operator: `"+12 SubExamples, 3 modified Requirements, 2 orphaned — see extraction_log.md"`.

---

## 5. Migration plan (staged, non-breaking)

| Phase | Action | Success criterion |
|---|---|---|
| 0 | Land `_pipelines/` + `_registry/` (read-only artefacts, no tests yet) | `examples.jsonl` + seed `requirements.yaml` generated; nothing in CI runs them |
| 1 | Land `_matrix/` test engine, run manually for a single requirement across all SubExamples | Engine works end-to-end; cost measured |
| 2 | Activate ~5 requirements in YAML; run matrix weekly alongside legacy per-feature tests | Matrix and feature tests agree on overlapping cases |
| 3 | Migrate all 60+ Anforderungen into `requirements.yaml`; matrix becomes the primary gate in CI | Legacy feature tests marked `xfail` where subsumed |
| 4 | Retire legacy per-feature test files as each Eigenschaft is fully covered by matrix rows | `tests/feature-testing/<feature>/` folders deleted in batches |
| 5 | Matrix is the only suite | `/create-feature-test` removed; replaced by `/add-requirement` |

Non-breaking guarantee: **nothing is removed until its coverage is independently reproduced in the matrix**.

---

## 6. Resolved decisions (v2)

Reviewer verdict on the v1 open questions:

1. **Granularity: maximum coverage.** Emit one SubExample per system turn. Mark the most pedagogically relevant turns as `tier: core` so the inner iteration loop stays fast. CI uses a stratified sample. See §2.3a.
2. **Golden responses: never at judge time.** The judge evaluates live responses only against the Anforderung. The "mögliche KI Antwort" is used *only* during Pipeline B to disambiguate terse Anforderungen when seeding the registry. See §2.4 step 4 and §2.6.
3. **Applicability rule authorship: automated with human review.** Pipeline B drafts `applicability_rule_de` + `judge_criterion_en` automatically. Human role is review and activation only — no hand-authoring from scratch. See §2.4 step 3.
4. **Profile variants: default single, extended opt-in via flag.** Every SubExample carries a `default_profile` used in iteration. A `--profiles=extended|all` flag multiplies by gender (and optionally age) for requirements flagged `profile_sensitivity != none`. See §2.5a.
5. **Judge call: single combined applicability+verdict call.** Measure on first 20 cells; split only if verdicts drift. See §2.6.
6. **N/A semantics: counts as PASS for threshold math, visually distinct in reports.** No "neutral" tier. See §2.3.
7. **Beispiele drift: hard regen + diff report.** No silent carry-over. Changed entries revert to `status: draft`. See §2.9.
8. **Background analysis: always on for v1.** Because every BG worker output reaches the next master turn directly or via `aufgabenWorker` / `foerderfokusWorker`, every Requirement defaults to `needs_background_analysis: true`. The field stays in the schema as a future-optimisation hook once the graph is restructured. Caching keeps the cost bounded (§2.5b, §2.7).

---

## 7. What this proposal is NOT

- Not a rewrite of the dialogue system. Only tests and their inputs.
- Not a change to `feature_testing_utils.build_state_with_beats` or `masterChatbot`. They're called unchanged.
- Not a removal of the LLM judge — the judge prompt just gets enriched and now emits N/A.
- Not an immediate deletion of existing feature folders. They stay for regression confidence during migration.

---

## 8. Next step

v1 open questions are resolved in §6. Next deliverable: a concrete implementation plan (files, order, estimated effort, acceptance criteria per phase). Awaiting green light to write it.
