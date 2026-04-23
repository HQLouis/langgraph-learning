"""
Unit tests for the matrix engine.

All LLM interactions are stubbed — these tests run in milliseconds and
validate the wiring (cell building, caching, verdict parsing, cell
evaluation) without touching a real model.
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

from _matrix.engine import (
    MatrixCell,
    MatrixConfig,
    build_cells,
    evaluate_cell,
    load_examples,
    load_requirements,
)
from _matrix.judge_prompt import JudgeVerdict, build_prompt, parse_verdict
from _matrix.response_cache import (
    FilesystemCache,
    bg_cache_key,
    bg_state_hash,
    response_cache_key,
)


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("PASS\nBecause everything looked fine.", "PASS"),
        ("FAIL\nResponse repeated the child's word.", "FAIL"),
        ("N/A\nThe requirement does not apply here.", "N/A"),
        ("pass\nlower case still ok", "PASS"),
        ("PASS:\nstray punctuation", "PASS"),
        ("NOT_APPLICABLE\nunusual spelling", "N/A"),
        ("NA\nabbreviated", "N/A"),
    ],
)
def test_parse_verdict_happy_paths(raw, expected):
    v = parse_verdict(raw)
    assert v.verdict == expected
    assert v.raw == raw


def test_parse_verdict_empty_input_is_fail():
    v = parse_verdict("")
    assert v.verdict == "FAIL"
    assert "no output" in v.reason


def test_parse_verdict_unparseable_first_line_is_fail():
    v = parse_verdict("Maybe?\nNot sure")
    assert v.verdict == "FAIL"
    assert "unparseable" in v.reason


def test_na_is_non_failing_and_flagged():
    v = parse_verdict("N/A\nno trigger")
    assert v.is_non_failing
    assert v.is_not_applicable


def test_fail_is_failing():
    v = parse_verdict("FAIL\nbroken")
    assert not v.is_non_failing


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def test_build_prompt_renders_all_sections():
    prompt = build_prompt(
        prefix_messages=[{"role": "child", "content": "hallo"}],
        response_text="Hi!",
        anforderung_de="KI soll freundlich sein.",
        applicability_rule_de="Gilt immer bei Begrüßung.",
        judge_criterion_en="PASS if greeting is friendly.",
    )
    for fragment in [
        "Child: hallo",
        "Hi!",
        "KI soll freundlich sein.",
        "Gilt immer bei Begrüßung.",
        "PASS if greeting is friendly.",
        "PASS, FAIL, N/A",
    ]:
        assert fragment in prompt


def test_build_prompt_handles_empty_prefix():
    prompt = build_prompt(
        prefix_messages=[],
        response_text="x",
        anforderung_de="a",
        applicability_rule_de="a",
        judge_criterion_en="a",
    )
    assert "no prior conversation" in prompt


# ---------------------------------------------------------------------------
# Cache key stability
# ---------------------------------------------------------------------------


def test_bg_cache_key_is_deterministic():
    a = bg_cache_key(
        prefix_messages=[{"role": "child", "content": "hi"}],
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        story_id="s", chapter_id="c",
        bg_prompt_version="v1", model_id="m", temperature=0.0,
    )
    b = bg_cache_key(
        prefix_messages=[{"role": "child", "content": "hi"}],
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        story_id="s", chapter_id="c",
        bg_prompt_version="v1", model_id="m", temperature=0.0,
    )
    assert a == b


def test_bg_cache_key_differs_for_different_prefix():
    a = bg_cache_key(
        prefix_messages=[{"role": "child", "content": "hi"}],
        profile={"n": 1}, story_id="s", chapter_id="c",
        bg_prompt_version="v1", model_id="m", temperature=0.0,
    )
    b = bg_cache_key(
        prefix_messages=[{"role": "child", "content": "hallo"}],
        profile={"n": 1}, story_id="s", chapter_id="c",
        bg_prompt_version="v1", model_id="m", temperature=0.0,
    )
    assert a != b


def test_response_cache_key_depends_on_bg_state_hash():
    base = dict(
        prefix_messages=[{"role": "child", "content": "x"}],
        profile={"n": 1}, story_id="s", chapter_id="c",
        master_prompt_version="v1", model_id="m", temperature=0.0,
    )
    a = response_cache_key(bg_state_hash="h1", **base)
    b = response_cache_key(bg_state_hash="h2", **base)
    assert a != b


# ---------------------------------------------------------------------------
# Filesystem cache
# ---------------------------------------------------------------------------


def test_filesystem_cache_hit_and_miss(tmp_path):
    cache = FilesystemCache(tmp_path)
    calls = []
    v1 = cache.get_or_compute_bg("k1", lambda: (calls.append(1), {"a": 1})[1])
    v2 = cache.get_or_compute_bg("k1", lambda: (calls.append(2), {"a": 999})[1])
    assert v1 == {"a": 1}
    assert v2 == {"a": 1}
    assert len(calls) == 1
    assert cache.bg_stats.hits == 1
    assert cache.bg_stats.misses == 1


def test_filesystem_cache_disabled_always_computes(tmp_path):
    cache = FilesystemCache(tmp_path, enabled=False)
    calls = []
    cache.get_or_compute_response("k", lambda: (calls.append(1), "one")[1])
    cache.get_or_compute_response("k", lambda: (calls.append(2), "two")[1])
    assert len(calls) == 2


def test_filesystem_cache_rejects_wrong_type(tmp_path):
    cache = FilesystemCache(tmp_path)
    with pytest.raises(TypeError):
        cache.get_or_compute_bg("k", lambda: "not-a-dict")
    with pytest.raises(TypeError):
        cache.get_or_compute_response("k", lambda: {"wrong": "type"})


# ---------------------------------------------------------------------------
# Cell building
# ---------------------------------------------------------------------------


def _mk_example(id_="S-aaaaaaaaaa", tier="core", status="active", story="s", chapter="c") -> dict:
    return {
        "id": id_,
        "prefix_hash": "h",
        "story_id": story,
        "chapter_id": chapter,
        "default_profile": {"name": "Emma", "age": 6, "gender": "weiblich"},
        "profile_variants": [{"name": "Jonas", "age": 7, "gender": "männlich"}],
        "prefix_messages": [{"role": "child", "content": "hallo"}],
        "golden_system_response": "Hi!",
        "tier": tier,
        "status": status,
        "source_refs": [],
    }


def _mk_requirement(
    id_="R-01-01",
    tier="core",
    status="active",
    profile_sensitivity="none",
    needs_bg=True,
) -> dict:
    return {
        "id": id_,
        "eigenschaft": 1,
        "anforderung_de": "do X",
        "applicability_rule_de": "applies",
        "judge_criterion_en": "PASS/FAIL/N/A",
        "tier": tier,
        "profile_sensitivity": profile_sensitivity,
        "needs_background_analysis": needs_bg,
        "status": status,
    }


def test_build_cells_skips_draft_entries():
    cells = build_cells(
        [_mk_example(status="draft"), _mk_example("S-b")],
        [_mk_requirement(status="draft")],
    )
    assert cells == []  # requirement filtered out


def test_build_cells_default_profile_only_without_variants_flag():
    cells = build_cells(
        [_mk_example()],
        [_mk_requirement(profile_sensitivity="gender")],
        tier_filter="core",
        profile_filter="default",
    )
    assert len(cells) == 1
    assert cells[0].profile_key == "default"


def test_build_cells_extended_profiles_only_for_sensitive_requirements():
    # insensitive → still just default
    cells = build_cells(
        [_mk_example()],
        [_mk_requirement(profile_sensitivity="none")],
        profile_filter="extended",
    )
    assert [c.profile_key for c in cells] == ["default"]
    # sensitive → default + variant
    cells = build_cells(
        [_mk_example()],
        [_mk_requirement(profile_sensitivity="gender")],
        profile_filter="extended",
    )
    assert sorted(c.profile_key for c in cells) == ["default", "variant_0"]


def test_build_cells_tier_filter_core_keeps_only_core():
    cells = build_cells(
        [_mk_example(tier="core"), _mk_example("S-b", tier="extended")],
        [_mk_requirement(tier="core")],
        tier_filter="core",
    )
    # The extended SubExample × core Requirement → effective tier extended → excluded
    assert len(cells) == 1
    assert cells[0].subexample["id"] == "S-aaaaaaaaaa"


# ---------------------------------------------------------------------------
# End-to-end evaluation with mocks
# ---------------------------------------------------------------------------


class _StubJudge:
    def __init__(self, response: str) -> None:
        self._response = response

    def invoke(self, _messages):
        class _R:
            def __init__(self, content):
                self.content = content
        return _R(self._response)


def test_evaluate_cell_pass_case(tmp_path, monkeypatch):
    cache = FilesystemCache(tmp_path)
    config = MatrixConfig(model_id="test-model", temperature=0.0)
    cell = MatrixCell(
        subexample=_mk_example(),
        requirement=_mk_requirement(needs_bg=False),
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        profile_key="default",
        tier="core",
    )
    calls = {"master": 0}

    def fake_master(_cell, _prefix, _bg):
        calls["master"] += 1
        return "Hallo Emma! Das ist eine freundliche Antwort."

    # Disable judge tracing path; our _StubJudge returns a raw content string.
    monkeypatch.setenv("JUDGE_LANGSMITH_TRACING", "false")
    result = evaluate_cell(
        cell,
        config=config,
        cache=cache,
        run_background=None,
        run_master=fake_master,
        judge_llm=_StubJudge("PASS\nAll good."),
    )
    assert result.verdict.verdict == "PASS"
    assert result.response_text.startswith("Hallo Emma")
    assert calls["master"] == 1


def test_evaluate_cell_na_case(tmp_path, monkeypatch):
    cache = FilesystemCache(tmp_path)
    config = MatrixConfig(model_id="m", temperature=0.0)
    cell = MatrixCell(
        subexample=_mk_example(),
        requirement=_mk_requirement(needs_bg=False),
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        profile_key="default",
        tier="core",
    )
    monkeypatch.setenv("JUDGE_LANGSMITH_TRACING", "false")
    result = evaluate_cell(
        cell, config=config, cache=cache,
        run_background=None,
        run_master=lambda *_: "irrelevant",
        judge_llm=_StubJudge("N/A\nRequirement does not apply."),
    )
    assert result.verdict.verdict == "N/A"
    assert result.verdict.is_non_failing


def test_evaluate_cell_with_bg_caches_bg_and_response(tmp_path, monkeypatch):
    cache = FilesystemCache(tmp_path)
    config = MatrixConfig(model_id="m", temperature=0.0)
    cell = MatrixCell(
        subexample=_mk_example(),
        requirement=_mk_requirement(needs_bg=True),
        profile={"name": "Emma", "age": 6, "gender": "weiblich"},
        profile_key="default",
        tier="core",
    )
    counter = {"bg": 0, "master": 0}

    def fake_bg(_cell, _prefix):
        counter["bg"] += 1
        return {"aufgaben": "t", "satzbaubegrenzung": ""}

    def fake_master(_cell, _prefix, bg_state):
        counter["master"] += 1
        # Response depends on the BG state so we know it flowed through.
        return f"response with aufgaben={bg_state['aufgaben']}"

    monkeypatch.setenv("JUDGE_LANGSMITH_TRACING", "false")
    # First run: cold cache.
    evaluate_cell(
        cell, config=config, cache=cache,
        run_background=fake_bg, run_master=fake_master,
        judge_llm=_StubJudge("PASS\nok"),
    )
    # Second run with same cell: both caches hit.
    evaluate_cell(
        cell, config=config, cache=cache,
        run_background=fake_bg, run_master=fake_master,
        judge_llm=_StubJudge("PASS\nok"),
    )
    assert counter["bg"] == 1, "BG was re-run despite identical inputs"
    assert counter["master"] == 1, "master was re-run despite identical inputs"


# ---------------------------------------------------------------------------
# Registry loaders
# ---------------------------------------------------------------------------


def test_load_examples_handles_missing_file(tmp_path):
    assert load_examples(tmp_path / "does-not-exist.jsonl") == []


def test_load_requirements_handles_missing_file(tmp_path):
    assert load_requirements(tmp_path / "does-not-exist.yaml") == []


def test_load_examples_roundtrip(tmp_path):
    path = tmp_path / "examples.jsonl"
    path.write_text(json.dumps(_mk_example()) + "\n", encoding="utf-8")
    assert load_examples(path)[0]["id"] == "S-aaaaaaaaaa"


def test_load_requirements_roundtrip(tmp_path):
    path = tmp_path / "r.yaml"
    path.write_text(yaml.safe_dump({"version": 1, "requirements": [_mk_requirement()]}), encoding="utf-8")
    loaded = load_requirements(path)
    assert loaded[0]["id"] == "R-01-01"
