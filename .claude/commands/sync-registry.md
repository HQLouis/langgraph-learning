You are synchronising the Lingolino test registry with the Dialogbeispiele markdown.

## What this does

Runs the two extraction pipelines against the current
`tests/feature-testing/Dialogbeispiele für die Eigenschaften.md` and
updates the registry under `tests/feature-testing/_registry/`:

- `examples.jsonl` — deduplicated SubExamples
- `requirements.yaml` — Anforderungen (curator-edited fields preserved
  when the source Anforderung text is unchanged)
- `extraction_log.md` — a diff report describing what changed

## When to run

- The PM updated `Dialogbeispiele.md` (added a new Eigenschaft, added
  Anforderungen, reworded a Beispiel).
- You suspect the registry is stale (e.g. `/add-requirement` says the
  Anforderung isn't in `requirements.yaml`).

## What to do

### Step 1 — Diff preview

```
PYTHONPATH=tests/feature-testing python -m _pipelines.run --dry-run
```

This writes to a temp dir and prints the diff summary:
```
diff — examples: +N / -N / ~N   requirements: +N / -N / ~N
```

Inspect the output. If only additions appear, regen is safe. If there
are removals or modifications, they mean:

- **Removed SubExample**: its prefix no longer exists in the MD (the
  Beispiel was deleted or the prefix text was reworded). Any active
  Requirement that referenced it only runs against the remaining
  SubExamples.
- **Modified Requirement**: the Anforderung text in the MD was
  reworded. The entry will revert to `status: draft` after regen and
  must be re-enriched + re-activated by a curator. This is the hard-
  regen rule from the architecture draft §2.9.

### Step 2 — Commit the MD change (if any)

If you changed the MD yourself in this turn, commit the MD edit
separately BEFORE running the regen. That way the registry diff is
clean and traceable.

### Step 3 — Real regen

```
PYTHONPATH=tests/feature-testing python -m _pipelines.run
```

Confirm the output matches the dry-run preview.

### Step 4 — Review extraction_log.md

Open `tests/feature-testing/_registry/extraction_log.md`. Walk through
the "Added", "Removed", and "Modified" sections. For each modified
Requirement that was previously `status: active`, plan to:

1. Re-enrich it with the LLM pipeline:
   ```
   PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements \
       --only R-XX-YY
   ```
2. Human-review the new applicability rule and judge criterion.
3. Flip `status: active` again once reviewed.

### Step 5 — Commit

Commit `_registry/*` and the CLAUDE-facing change logs together:

```
git add tests/feature-testing/_registry/ dialogue-system-engineering/change_log.md
git commit -m "sync-registry: <one-line summary of the diff>"
```

## Rules

1. **Never hand-edit `examples.jsonl`**. It's regenerated from the MD.
2. **Do hand-edit `requirements.yaml`** — that's how curator reviews and
   activations happen. `_pipelines.run` preserves curator edits when
   the source Anforderung text is unchanged.
3. **Revert on material damage**: if a regen deactivates many
   previously-active requirements (because many Anforderungen got
   reworded), pause and confirm with the user before the commit.
4. **The MD is the source of truth**. Registry artefacts are generated
   outputs. Any fact in the registry that isn't backed by the MD is a
   bug.
