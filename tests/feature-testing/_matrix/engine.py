"""
Matrix engine — generate a response for a (SubExample × profile) cell and
judge it against a Requirement.

The engine is intentionally kept separate from pytest plumbing so it can
be unit-tested without a pytest session. ``conftest.py`` builds the
objects in this module and hands them to the parametrized test.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from langchain_core.messages import AIMessage, HumanMessage

from _matrix.judge_prompt import JudgeVerdict, build_prompt, invoke_judge
from _matrix.response_cache import (
    FilesystemCache,
    bg_cache_key,
    bg_state_hash,
    response_cache_key,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Registry loaders
# ---------------------------------------------------------------------------


def load_examples(path: Path) -> list[dict]:
    """Load ``examples.jsonl`` into a list of dicts.

    Returns an empty list if the file does not exist — useful before
    Phase-0 artefacts are committed.
    """

    if not path.exists():
        return []
    import json

    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def load_requirements(path: Path) -> list[dict]:
    if not path.exists():
        return []
    import yaml

    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(doc.get("requirements", []))


# ---------------------------------------------------------------------------
# Cell parametrization
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixCell:
    """One test instance in the matrix — SubExample × Requirement × profile."""

    subexample: dict
    requirement: dict
    profile: dict
    profile_key: str           # "default" | "variant_N"
    tier: str                  # effective tier after applying the cell filter

    @property
    def cell_id(self) -> str:
        return f"{self.subexample['id']}|{self.requirement['id']}|{self.profile_key}"

    def short_label(self) -> str:
        """Pytest-friendly id used by parametrize(ids=...)."""
        s = self.subexample["id"]
        r = self.requirement["id"]
        return f"{s}×{r}×{self.profile_key}"


def build_cells(
    examples: Iterable[dict],
    requirements: Iterable[dict],
    *,
    active_statuses: tuple[str, ...] = ("active",),
    tier_filter: str = "core",
    profile_filter: str = "default",
) -> list[MatrixCell]:
    """Expand (examples × requirements × profiles) into concrete cells.

    Only entries whose ``status`` is in ``active_statuses`` are kept for
    both examples and requirements. If either list is empty after
    filtering we return no cells — the matrix is idle by design until
    the curator flips entries active (Phase 2).
    """

    examples_active = [e for e in examples if e.get("status", "active") in active_statuses]
    requirements_active = [r for r in requirements if r.get("status", "active") in active_statuses]

    if not examples_active or not requirements_active:
        return []

    cells: list[MatrixCell] = []
    for sub in examples_active:
        sub_tier = sub.get("tier", "extended")
        for req in requirements_active:
            req_tier = req.get("tier", "extended")
            effective_tier = _max_tier(sub_tier, req_tier)
            if not _tier_passes(effective_tier, tier_filter):
                continue
            for profile_key, profile in _iter_profiles(sub, req, profile_filter):
                cells.append(
                    MatrixCell(
                        subexample=sub,
                        requirement=req,
                        profile=profile,
                        profile_key=profile_key,
                        tier=effective_tier,
                    )
                )
    return cells


def _max_tier(a: str, b: str) -> str:
    """If either side is ``extended`` the cell is ``extended``; otherwise ``core``."""
    return "core" if (a == "core" and b == "core") else "extended"


def _tier_passes(effective_tier: str, filter_: str) -> bool:
    if filter_ == "all":
        return True
    if filter_ == "extended":
        return True  # extended filter includes both
    if filter_ == "core":
        return effective_tier == "core"
    raise ValueError(f"unknown tier filter: {filter_!r}")


def _iter_profiles(sub: dict, req: dict, profile_filter: str):
    """Yield ``(profile_key, profile)`` pairs for this SubExample and requirement.

    - ``default`` — yields only the default profile.
    - ``extended`` — also yields ``profile_variants`` iff
      ``req.profile_sensitivity != 'none'``.
    - ``all`` — yields every variant regardless of sensitivity.
    """

    default = sub["default_profile"]
    yield "default", default

    if profile_filter == "default":
        return

    sensitivity = req.get("profile_sensitivity", "none")
    if profile_filter == "extended" and sensitivity == "none":
        return

    for idx, variant in enumerate(sub.get("profile_variants") or []):
        yield f"variant_{idx}", variant


# ---------------------------------------------------------------------------
# Response generation
# ---------------------------------------------------------------------------


def _prefix_to_messages(prefix_messages: list[dict]) -> list[Any]:
    """Convert registry {role, content} dicts into LangChain messages."""
    out: list[Any] = []
    for m in prefix_messages:
        if m["role"] == "child":
            out.append(HumanMessage(content=m["content"]))
        else:
            out.append(AIMessage(content=m["content"]))
    return out


@dataclass
class MatrixConfig:
    model_id: str
    temperature: float
    bg_prompt_version: str = "v1"
    master_prompt_version: str = "v1"


def generate_response(
    cell: MatrixCell,
    *,
    config: MatrixConfig,
    cache: FilesystemCache,
    run_background: Callable[[MatrixCell, list], dict] | None,
    run_master: Callable[[MatrixCell, list, dict | None], str],
) -> tuple[str, dict | None]:
    """Produce the system response for a cell, using the two-layer cache.

    ``run_background`` is called when the requirement has
    ``needs_background_analysis: true``. It receives the cell and the
    LangChain-message-shaped prefix and must return a BackgroundState
    dict (or an empty ``{}`` if BG should be skipped).

    ``run_master`` receives the cell, the prefix messages, and the BG
    state (or None) and must return the generated response text.
    """

    prefix_messages = _prefix_to_messages(cell.subexample["prefix_messages"])
    needs_bg = bool(cell.requirement.get("needs_background_analysis", False))

    bg_state: dict | None = None
    if needs_bg and run_background is not None:
        bg_key = bg_cache_key(
            prefix_messages=cell.subexample["prefix_messages"],
            profile=cell.profile,
            story_id=cell.subexample["story_id"],
            chapter_id=cell.subexample["chapter_id"],
            bg_prompt_version=config.bg_prompt_version,
            model_id=config.model_id,
            temperature=config.temperature,
        )
        bg_state = cache.get_or_compute_bg(
            bg_key,
            lambda: run_background(cell, prefix_messages) or {},
        )

    bg_hash = bg_state_hash(bg_state or {})
    response_key = response_cache_key(
        prefix_messages=cell.subexample["prefix_messages"],
        profile=cell.profile,
        story_id=cell.subexample["story_id"],
        chapter_id=cell.subexample["chapter_id"],
        bg_state_hash=bg_hash,
        master_prompt_version=config.master_prompt_version,
        model_id=config.model_id,
        temperature=config.temperature,
    )
    response_text = cache.get_or_compute_response(
        response_key,
        lambda: run_master(cell, prefix_messages, bg_state),
    )
    return response_text, bg_state


# ---------------------------------------------------------------------------
# Judge call
# ---------------------------------------------------------------------------


def judge_response(
    cell: MatrixCell,
    response_text: str,
    judge_llm,
) -> JudgeVerdict:
    prompt = build_prompt(
        prefix_messages=cell.subexample["prefix_messages"],
        response_text=response_text,
        anforderung_de=cell.requirement.get("anforderung_de", ""),
        applicability_rule_de=cell.requirement.get("applicability_rule_de", ""),
        judge_criterion_en=cell.requirement.get("judge_criterion_en", ""),
    )
    return invoke_judge(judge_llm, prompt)


# ---------------------------------------------------------------------------
# End-to-end cell evaluation
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    cell: MatrixCell
    verdict: JudgeVerdict
    response_text: str
    bg_state_used: bool


def evaluate_cell(
    cell: MatrixCell,
    *,
    config: MatrixConfig,
    cache: FilesystemCache,
    run_background: Callable[[MatrixCell, list], dict] | None,
    run_master: Callable[[MatrixCell, list, dict | None], str],
    judge_llm,
) -> CellResult:
    response_text, bg_state = generate_response(
        cell,
        config=config,
        cache=cache,
        run_background=run_background,
        run_master=run_master,
    )
    verdict = judge_response(cell, response_text, judge_llm)
    return CellResult(
        cell=cell,
        verdict=verdict,
        response_text=response_text,
        bg_state_used=bg_state is not None,
    )
