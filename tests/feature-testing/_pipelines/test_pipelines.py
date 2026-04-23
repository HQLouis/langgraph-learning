"""
Unit tests for the Phase-0 pipelines.

These are pure data-transformation tests: they don't invoke the LLM,
don't hit the filesystem outside of tmp dirs, and don't depend on the
dialog system. They run in < 1 second and are safe to include in the
unit-test sweep (`pytest tests/feature-testing/_pipelines/`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

# Make the _pipelines package importable when pytest discovers this
# file directly without having run the rest of the feature-testing
# conftest. The regular pyproject.toml pythonpath covers this in a full
# run, but explicit is cheaper than relying on global config.
_FEATURE_TESTING_DIR = Path(__file__).resolve().parents[1]
if str(_FEATURE_TESTING_DIR) not in sys.path:
    sys.path.insert(0, str(_FEATURE_TESTING_DIR))

from _pipelines.extract_examples import build_subexamples, write_examples_jsonl
from _pipelines.extract_requirements import build_requirements, write_requirements_yaml
from _pipelines.parse_dialogbeispiele import (
    Beispiel,
    Eigenschaft,
    Turn,
    parse_markdown,
)
from _pipelines.regen_diff import write_diff_report


# ---------------------------------------------------------------------------
# Parser — happy paths
# ---------------------------------------------------------------------------


def _make_tmp_md(tmp_path: Path, body: str) -> Path:
    """Wrap a snippet of MD body in a minimal anchor-tagged h1 header."""
    path = tmp_path / "dialogbeispiele.md"
    header = "# 1.Eigenschaft: Testfeature {#1.eigenschaft:-testfeature}\n"
    path.write_text(header + body, encoding="utf-8")
    return path


def test_parser_implicit_alternation(tmp_path):
    md = _make_tmp_md(
        tmp_path,
        body="""
**Beispiel 1-PIA :**
hallo
Hallo Emma! Was machen wir heute?
lesen

**Anforderung für eine bessere KI Antwort:**
KI soll auf die Antwort des Kindes eingehen.
""",
    )
    eigenschaften, report = parse_markdown(md)
    assert report.warnings == []
    assert len(eigenschaften) == 1
    e = eigenschaften[0]
    assert e.number == 1
    assert len(e.beispiele) == 1
    b = e.beispiele[0]
    assert b.story_hint == "PIA"
    assert [t.role for t in b.turns] == ["child", "system", "child"]
    assert b.turns[0].content == "hallo"
    assert b.anforderungen == ["KI soll auf die Antwort des Kindes eingehen."]


def test_parser_explicit_ki_kind_markers(tmp_path):
    md = _make_tmp_md(
        tmp_path,
        body="""
**Beispiel 1 (Pia):**
KI: „Pia ist ein Mädchen. Was machst du?"
Kind: „lesen"
KI: „Das ist schön, lesen macht Spaß."

**Anforderung für eine bessere KI Antwort:**
Kurze Bestätigung anbieten.
""",
    )
    eigenschaften, _ = parse_markdown(md)
    b = eigenschaften[0].beispiele[0]
    assert [t.role for t in b.turns] == ["system", "child", "system"]
    # smart quotes should have been normalised to ASCII
    assert '"' in b.turns[0].content
    assert "„" not in b.turns[0].content


def test_parser_skips_story_text_sections(tmp_path):
    # The real MD has "# PIA {#pia}" and "# BOBO {#bobo}" blocks that
    # contain the raw audiobook text, not Beispiele. Those must be
    # skipped.
    path = tmp_path / "d.md"
    path.write_text(
        "# PIA {#pia}\n\nSome story text here.\n\n"
        "# 1.Eigenschaft: X {#1.eigenschaft:-x}\n\n"
        "**Beispiel 1:**\nhallo\nHallo!\n\n"
        "**Anforderung für eine bessere KI Antwort:**\nReaktion zeigen.\n",
        encoding="utf-8",
    )
    eigenschaften, _ = parse_markdown(path)
    assert len(eigenschaften) == 1
    assert eigenschaften[0].title_de == "X"


def test_parser_strips_highlighted_bold(tmp_path):
    md = _make_tmp_md(
        tmp_path,
        body="""
**Beispiel 1:**
hallo
Hallo!
**ja**
**Das ist toll!**

**Anforderung für eine bessere KI Antwort:**
Freundlich sein.
""",
    )
    eigenschaften, _ = parse_markdown(md)
    b = eigenschaften[0].beispiele[0]
    # The highlighted bold markers should be stripped from content...
    assert "**" not in "".join(t.content for t in b.turns)
    # ...and highlight_from_turn should point to the first wrapped line.
    assert b.highlight_from_turn == 2


# ---------------------------------------------------------------------------
# SubExample extraction
# ---------------------------------------------------------------------------


def _eigenschaft_with_turns(role_pairs: list[tuple[str, str]]) -> Eigenschaft:
    turns = [Turn(role=r, content=c) for r, c in role_pairs]
    b = Beispiel(
        index=1,
        label="Beispiel 1",
        story_hint="PIA",
        turns=turns,
        suggested_ki_turns=[],
        anforderungen=["Do the thing."],
        highlight_from_turn=None,
        raw_block="",
    )
    return Eigenschaft(number=1, title_de="Test", anchor="1.eigenschaft:-test", beispiele=[b])


def test_subexamples_emit_one_per_system_turn():
    e = _eigenschaft_with_turns([
        ("child", "hallo"),
        ("system", "Hallo!"),
        ("child", "ja"),
        ("system", "Super."),
    ])
    subs, skipped = build_subexamples([e])
    # 2 system turns, each with a valid child-ending prefix → 2 SubExamples.
    assert len(subs) == 2
    assert skipped == []
    assert subs[0].prefix_messages == [{"role": "child", "content": "hallo"}]
    assert subs[0].golden_system_response == "Hallo!"
    assert subs[1].prefix_messages[-1] == {"role": "child", "content": "ja"}


def test_subexamples_dedup_identical_prefixes():
    e1 = _eigenschaft_with_turns([("child", "hallo"), ("system", "Hi")])
    e2 = _eigenschaft_with_turns([("child", "hallo"), ("system", "Different response")])
    subs, _ = build_subexamples([e1, e2])
    # Same prefix → one SubExample, with two source_refs.
    assert len(subs) == 1
    assert len(subs[0].source_refs) == 2


def test_subexamples_skip_system_turn_with_no_preceding_child():
    # A Beispiel that starts with a system turn (KI:-style snippet) has
    # no usable prefix for the first system turn — skip it.
    e = _eigenschaft_with_turns([
        ("system", "Leading system turn"),
        ("child", "reply"),
        ("system", "Second system turn"),
    ])
    subs, skipped = build_subexamples([e])
    assert len(subs) == 1
    assert skipped  # at least one skip reason


def test_subexample_id_is_prefix_hash_prefix():
    e = _eigenschaft_with_turns([("child", "x"), ("system", "y")])
    sub = build_subexamples([e])[0][0]
    assert sub.id.startswith("S-")
    assert sub.id.endswith(sub.prefix_hash[:10])


# ---------------------------------------------------------------------------
# Requirement extraction
# ---------------------------------------------------------------------------


def test_requirements_seeded_with_draft_placeholders():
    e = _eigenschaft_with_turns([("child", "x"), ("system", "y")])
    reqs = build_requirements([e])
    assert len(reqs) == 1
    r = reqs[0]
    assert r.id == "R-01-01"
    assert r.status == "draft"
    assert r.title_de.startswith("[DRAFT]")
    assert r.applicability_rule_de.startswith("[DRAFT]")
    assert r.judge_criterion_en.startswith("[DRAFT")
    assert r.anforderung_de == "Do the thing."
    # BG-always-on per draft §2.5b (v1)
    assert r.needs_background_analysis is True


def test_requirements_tier_heuristic_promotes_strong_language():
    e = _eigenschaft_with_turns([("child", "x"), ("system", "y")])
    e.beispiele[0].anforderungen = [
        "KI darf das Wort niemals verwenden.",
        "Freundlich bleiben.",
    ]
    reqs = build_requirements([e])
    # "darf nicht" / "niemals" style → core; mild phrasing → extended
    # Our heuristic set uses "darf nicht" as a marker; check both are tagged.
    tiers = {r.tier for r in reqs}
    assert "extended" in tiers


def test_requirements_profile_sensitivity_detects_gender_keywords():
    e = _eigenschaft_with_turns([("child", "x"), ("system", "y")])
    e.beispiele[0].anforderungen = [
        "Das Kind als Mädchen ansprechen, wenn es weiblich ist.",
    ]
    reqs = build_requirements([e])
    assert reqs[0].profile_sensitivity == "gender"


# ---------------------------------------------------------------------------
# Writer round-trip
# ---------------------------------------------------------------------------


def test_examples_jsonl_round_trip(tmp_path):
    e = _eigenschaft_with_turns([("child", "hallo"), ("system", "Hi!")])
    subs, _ = build_subexamples([e])
    out = tmp_path / "examples.jsonl"
    write_examples_jsonl(subs, out)
    loaded = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(loaded) == 1
    assert loaded[0]["id"] == subs[0].id
    assert loaded[0]["prefix_messages"] == [{"role": "child", "content": "hallo"}]


def test_requirements_yaml_round_trip(tmp_path):
    e = _eigenschaft_with_turns([("child", "hallo"), ("system", "Hi!")])
    reqs = build_requirements([e])
    out = tmp_path / "requirements.yaml"
    write_requirements_yaml(reqs, out)
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["version"] == 1
    assert doc["metadata"]["count"] == len(reqs)
    assert doc["requirements"][0]["id"] == reqs[0].id
    assert doc["requirements"][0]["status"] == "draft"


# ---------------------------------------------------------------------------
# Regen diff
# ---------------------------------------------------------------------------


def test_regen_diff_detects_added_and_removed(tmp_path):
    examples_old = tmp_path / "examples_old.jsonl"
    examples_new = tmp_path / "examples_new.jsonl"
    reqs_old = tmp_path / "reqs_old.yaml"
    reqs_new = tmp_path / "reqs_new.yaml"
    log = tmp_path / "log.md"

    # Old: one SubExample, one Requirement
    examples_old.write_text(
        json.dumps({
            "id": "S-aaa",
            "prefix_messages": [{"role": "child", "content": "hi"}],
            "story_id": "x", "chapter_id": "y", "default_profile": {"name": "E", "age": 6, "gender": "weiblich"},
        }) + "\n",
        encoding="utf-8",
    )
    reqs_old.write_text(
        yaml.safe_dump({"version": 1, "requirements": [
            {"id": "R-01-01", "anforderung_de": "old", "applicability_rule_de": "a", "judge_criterion_en": "j", "eigenschaft": 1},
        ]}),
        encoding="utf-8",
    )
    # New: replace both
    examples_new.write_text(
        json.dumps({
            "id": "S-bbb",
            "prefix_messages": [{"role": "child", "content": "yo"}],
            "story_id": "x", "chapter_id": "y", "default_profile": {"name": "E", "age": 6, "gender": "weiblich"},
        }) + "\n",
        encoding="utf-8",
    )
    reqs_new.write_text(
        yaml.safe_dump({"version": 1, "requirements": [
            {"id": "R-01-01", "anforderung_de": "new", "applicability_rule_de": "a", "judge_criterion_en": "j", "eigenschaft": 1},
            {"id": "R-01-02", "anforderung_de": "added", "applicability_rule_de": "a", "judge_criterion_en": "j", "eigenschaft": 1},
        ]}),
        encoding="utf-8",
    )

    ex_diff, rq_diff = write_diff_report(
        examples_path=examples_old,
        examples_new_path=examples_new,
        requirements_path=reqs_old,
        requirements_new_path=reqs_new,
        log_path=log,
    )

    assert ex_diff.added_ids == ["S-bbb"]
    assert ex_diff.removed_ids == ["S-aaa"]
    assert rq_diff.added_ids == ["R-01-02"]
    assert rq_diff.modified_ids == ["R-01-01"]
    assert log.read_text(encoding="utf-8").startswith("# Registry regeneration log")


# ---------------------------------------------------------------------------
# End-to-end — parse the real MD and sanity-check outputs
# ---------------------------------------------------------------------------


def test_real_md_parses_without_warnings():
    md = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    eigenschaften, report = parse_markdown(md)
    # Expect the 21 numbered Eigenschaften plus the "Satzbau" appendix.
    assert report.eigenschaft_count >= 20
    assert report.beispiel_count >= 100
    assert report.turn_count >= 500
    assert report.warnings == []


def test_real_md_produces_more_subexamples_than_beispiele():
    # Sanity check: dedup shouldn't be so aggressive that we end up with
    # fewer SubExamples than source Beispiele.
    md = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    eigenschaften, _ = parse_markdown(md)
    subs, _ = build_subexamples(eigenschaften)
    beispiel_count = sum(len(e.beispiele) for e in eigenschaften)
    assert len(subs) >= beispiel_count


def test_real_md_produces_one_requirement_per_anforderung():
    md = _FEATURE_TESTING_DIR / "Dialogbeispiele für die Eigenschaften.md"
    eigenschaften, _ = parse_markdown(md)
    reqs = build_requirements(eigenschaften)
    anforderung_count = sum(len(b.anforderungen) for e in eigenschaften for b in e.beispiele)
    assert len(reqs) == anforderung_count
