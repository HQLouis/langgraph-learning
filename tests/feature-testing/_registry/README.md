# Test matrix registry

Generated artefacts that drive the example × requirement matrix test at
`tests/feature-testing/_matrix/test_matrix.py`. These files are read by
the test engine; do not hand-write them directly unless you are the
curator reviewing requirements.

## Files

| File | Source of truth | Edit by hand? |
|---|---|---|
| `examples.jsonl` | Generated from `../Dialogbeispiele für die Eigenschaften.md` by `_pipelines.run` | **No** — regenerate |
| `requirements.yaml` | Seeded by `_pipelines.run`, reviewed by a curator, enriched by `_pipelines.enrich_requirements` | **Yes** — curator edits |
| `extraction_log.md` | Diff report emitted by every run of `_pipelines.run` | **No** — regenerated |
| `README.md` | This file | Yes |

## Typical workflows

**"The PM updated Dialogbeispiele.md"** →
Run `/sync-registry`. Review the diff in `extraction_log.md`.
Anforderungen whose source text changed revert to `status: draft` and
must be re-enriched before they re-enter the matrix.

**"I want to add a new Anforderung"** → Run `/add-requirement`. It walks
through adding the paragraph to the MD, regenerating the registry,
enriching the new Requirement via the LLM, and activating it.

**"I want to run the matrix"** →
```
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default \
    --json-report --json-report-file=.matrix.json
```
Open `tests/feature-testing/reporting/output/matrix_latest.html` for
the heatmap view, `report_latest.html` for the per-Eigenschaft view.

## Schema — `requirements.yaml`

```yaml
version: 1
metadata: {source, generated_at, generator, count}
requirements:
  - id: R-<eigenschaft>-<seq>            # stable across regens
    eigenschaft: <int>                   # Eigenschaft number, or null for appendix
    eigenschaft_title_de: <string>
    title_de: <string>                   # one-line summary, German
    anforderung_de: <string>             # verbatim from the MD
    example_refs: [<Beispiel labels>]    # traceability only
    applicability_rule_de: <string>      # WHEN this requirement applies (German)
    judge_criterion_en: <string>         # PASS/FAIL/N/A criterion (English)
    tier: core | extended                # core = fast inner loop
    profile_sensitivity: none | gender | age
    needs_background_analysis: bool      # v1: always true — see draft §2.5b
    status: draft | active | deprecated
```

## Schema — `examples.jsonl`

One JSON object per line:

```jsonc
{
  "id": "S-<10-hex>",                    // stable across regens iff prefix unchanged
  "prefix_hash": "<sha256>",
  "story_id": "pia_muss_nicht_perfekt_sein" | "bobos_adventskalender" | ...,
  "chapter_id": "chapter_01",
  "default_profile": {"name": "Emma", "age": 6, "gender": "weiblich"},
  "profile_variants": [{"name": "Jonas", "age": 7, "gender": "männlich"}],
  "prefix_messages": [{"role": "child", "content": "hallo"}, ...],
  "golden_system_response": "...",       // debug-only; never shown to the judge
  "tier": "core" | "extended",
  "source_refs": [{eigenschaft_number, eigenschaft_title_de, beispiel_label, target_turn_index}]
}
```

## Hard-regen rule

Per `dialogue-system-engineering/example-centric-testing-draft.md` §2.9,
the registry is regenerated from scratch whenever the MD changes.
Curator-edited fields (`applicability_rule_de`, `judge_criterion_en`,
`title_de`, `status`, `tier`, `profile_sensitivity`,
`needs_background_analysis`) are preserved iff the entry's
`anforderung_de` is byte-identical to the last committed version.

If the Anforderung text changes even slightly, the Requirement reverts
to `status: draft`. This is by design — a reworded Anforderung may
mean a different applicability rule, so we force re-review rather than
silently carry forward stale enrichment.
