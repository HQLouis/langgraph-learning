"""
Phase-0 pipelines that parse the Dialogbeispiele MD into a deduplicated
SubExample bank (examples.jsonl) and a Requirement registry
(requirements.yaml). See
``dialogue-system-engineering/example-centric-testing-draft.md`` for the
overall design.

These pipelines are read-only producers: they never run tests, they only
materialise registry artefacts. Phase 1+ consumes those artefacts.
"""
