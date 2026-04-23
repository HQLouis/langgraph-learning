"""
Unit tests for the LLM enrichment pipeline.

The LLM transport is stubbed via a plain callable, so these tests run
offline and in milliseconds. They cover:
  - is_draft() detection
  - prompt construction
  - parse_enrichment() happy path + every failure mode
  - end-to-end enrich_requirements() against a tmp YAML
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

_FEATURE_TESTING_DIR = Path(__file__).resolve().parents[1]
if str(_FEATURE_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(_FEATURE_TESTING_DIR))

from _pipelines.enrich_requirements import (
    EnrichmentError,
    build_beispiel_context,
    build_prompt,
    enrich_requirements,
    is_draft,
    parse_enrichment,
)


# ---------------------------------------------------------------------------
# is_draft
# ---------------------------------------------------------------------------


def test_is_draft_detects_draft_in_any_field():
    assert is_draft({"title_de": "[DRAFT] x", "applicability_rule_de": "good", "judge_criterion_en": "good"})
    assert is_draft({"title_de": "ok", "applicability_rule_de": "[DRAFT] x", "judge_criterion_en": "good"})
    assert is_draft({"title_de": "ok", "applicability_rule_de": "ok", "judge_criterion_en": "[DRAFT — review] x"})
    assert not is_draft({"title_de": "ok", "applicability_rule_de": "ok", "judge_criterion_en": "ok"})


# ---------------------------------------------------------------------------
# build_prompt
# ---------------------------------------------------------------------------


def test_build_prompt_injects_context_and_anforderung():
    req = {
        "eigenschaft_title_de": "Nein akzeptieren",
        "anforderung_de": "Dialog fortsetzen nach Nein.",
    }
    prompt = build_prompt(req, "[Beispiel 1]\n  Kind: hallo\n  KI: Hi!")
    assert "Nein akzeptieren" in prompt
    assert "Dialog fortsetzen nach Nein." in prompt
    assert "Beispiel 1" in prompt
    assert "Return PASS" in prompt
    assert "Return FAIL" in prompt
    assert "Return N/A" in prompt


# ---------------------------------------------------------------------------
# parse_enrichment
# ---------------------------------------------------------------------------


def _valid_json_response() -> str:
    return json.dumps({
        "title_de": "KI akzeptiert Nein und setzt Gespräch fort",
        "applicability_rule_de": "Gilt nur, wenn das Kind im letzten Turn 'Nein' sagt.",
        "judge_criterion_en": (
            "Check whether the child said 'Nein' and whether the system accepted it. "
            "Return PASS if the system briefly acknowledges and continues. "
            "Return FAIL if it insists. "
            "Return N/A if the child did not say 'Nein'."
        ),
    })


def test_parse_enrichment_happy_path():
    r = parse_enrichment(_valid_json_response())
    assert r.title_de.startswith("KI akzeptiert")
    assert "Return N/A" in r.judge_criterion_en


def test_parse_enrichment_strips_markdown_fence():
    fenced = "```json\n" + _valid_json_response() + "\n```"
    r = parse_enrichment(fenced)
    assert r.title_de


def test_parse_enrichment_rejects_non_json():
    with pytest.raises(EnrichmentError, match="valid JSON"):
        parse_enrichment("not-json-at-all")


def test_parse_enrichment_rejects_missing_keys():
    with pytest.raises(EnrichmentError, match="missing keys"):
        parse_enrichment(json.dumps({"title_de": "x"}))


def test_parse_enrichment_rejects_empty_fields():
    payload = json.loads(_valid_json_response())
    payload["title_de"] = ""
    with pytest.raises(EnrichmentError, match="empty"):
        parse_enrichment(json.dumps(payload))


def test_parse_enrichment_rejects_leftover_draft_marker():
    payload = json.loads(_valid_json_response())
    payload["title_de"] = "[DRAFT] still drafty"
    with pytest.raises(EnrichmentError, match="DRAFT"):
        parse_enrichment(json.dumps(payload))


def test_parse_enrichment_rejects_missing_return_clauses():
    payload = json.loads(_valid_json_response())
    payload["judge_criterion_en"] = "Only PASS and FAIL here, no N/A."
    # This one keeps "fail" but removes "n/a" entirely.
    payload["judge_criterion_en"] = "Only PASS and FAIL here."
    with pytest.raises(EnrichmentError, match="N/A return clause"):
        parse_enrichment(json.dumps(payload))


# ---------------------------------------------------------------------------
# build_beispiel_context
# ---------------------------------------------------------------------------


def test_build_beispiel_context_picks_matching_beispiele():
    from _pipelines.parse_dialogbeispiele import Beispiel, Eigenschaft, Turn

    eig = Eigenschaft(
        number=19, title_de="Nein", anchor="x",
        beispiele=[
            Beispiel(1, "Beispiel 1", "PIA",
                     turns=[Turn("child", "hallo"), Turn("system", "Hi!")],
                     suggested_ki_turns=[],
                     anforderungen=["x"],
                     highlight_from_turn=None, raw_block=""),
            Beispiel(2, "Beispiel 2", "PIA",
                     turns=[Turn("child", "nein"), Turn("system", "Okay.")],
                     suggested_ki_turns=[Turn("system", "Alles klar.")],
                     anforderungen=["y"],
                     highlight_from_turn=None, raw_block=""),
        ],
    )
    req = {
        "eigenschaft": 19,
        "example_refs": ["Beispiel 1", "Beispiel 2"],
    }
    ctx = build_beispiel_context(req, [eig])
    assert "Beispiel 1" in ctx
    assert "Beispiel 2" in ctx
    assert "[mögliche KI Antwort]" in ctx
    assert "Alles klar" in ctx


def test_build_beispiel_context_empty_when_no_refs():
    req = {"eigenschaft": 19, "example_refs": []}
    assert build_beispiel_context(req, []) == ""


# ---------------------------------------------------------------------------
# End-to-end driver
# ---------------------------------------------------------------------------


def _stub_llm(response: str):
    calls = []

    def _call(prompt: str) -> str:
        calls.append(prompt)
        return response

    _call.calls = calls  # type: ignore[attr-defined]
    return _call


def _seed_yaml(tmp_path: Path) -> Path:
    registry = tmp_path / "requirements.yaml"
    doc = {
        "version": 1,
        "requirements": [
            {
                "id": "R-19-02",
                "eigenschaft": 19,
                "eigenschaft_title_de": "Nein akzeptieren",
                "title_de": "[DRAFT] Kurze Bestätigung der Akzeptanz...",
                "anforderung_de": "Kurze Bestätigung der Akzeptanz, einen eigenen Vorschlag anbieten.",
                "example_refs": [],
                "applicability_rule_de": "[DRAFT] Applies to every response.",
                "judge_criterion_en": "[DRAFT — review before activation] placeholder",
                "tier": "extended",
                "profile_sensitivity": "none",
                "needs_background_analysis": True,
                "status": "draft",
            },
            {
                "id": "R-19-03",
                "eigenschaft": 19,
                "eigenschaft_title_de": "Nein akzeptieren",
                "title_de": "Short help after no",   # already enriched
                "anforderung_de": "kurze Hilfestellung anbieten.",
                "example_refs": [],
                "applicability_rule_de": "Real rule.",
                "judge_criterion_en": "PASS if. FAIL if. N/A if.",
                "tier": "extended",
                "profile_sensitivity": "none",
                "needs_background_analysis": True,
                "status": "active",
            },
        ],
    }
    registry.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return registry


def test_enrich_requirements_updates_only_drafts(tmp_path, monkeypatch):
    registry = _seed_yaml(tmp_path)
    md_path = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    llm = _stub_llm(_valid_json_response())

    changed = enrich_requirements(registry, md_path, llm)
    assert changed == ["R-19-02"]
    # Only one LLM call — R-19-03 was already enriched, so it's skipped.
    assert len(llm.calls) == 1  # type: ignore[attr-defined]

    doc = yaml.safe_load(registry.read_text(encoding="utf-8"))
    r = next(r for r in doc["requirements"] if r["id"] == "R-19-02")
    assert not r["title_de"].startswith("[DRAFT")
    assert not r["applicability_rule_de"].startswith("[DRAFT")
    # Status stays "draft" — the curator still flips to "active" after review.
    assert r["status"] == "draft"


def test_enrich_requirements_dry_run_does_not_write(tmp_path):
    registry = _seed_yaml(tmp_path)
    md_path = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    before = registry.read_text(encoding="utf-8")
    llm = _stub_llm(_valid_json_response())

    changed = enrich_requirements(registry, md_path, llm, dry_run=True)
    assert changed == ["R-19-02"]
    assert registry.read_text(encoding="utf-8") == before


def test_enrich_requirements_skips_on_llm_error(tmp_path):
    registry = _seed_yaml(tmp_path)
    md_path = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    llm = _stub_llm("not-json")  # will fail parse_enrichment

    changed = enrich_requirements(registry, md_path, llm)
    assert changed == []  # the draft entry is left untouched


def test_enrich_requirements_only_filter_limits_scope(tmp_path):
    registry = _seed_yaml(tmp_path)
    md_path = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    llm = _stub_llm(_valid_json_response())

    changed = enrich_requirements(registry, md_path, llm, only_ids=["NOPE"])
    assert changed == []  # the requested ID doesn't exist
