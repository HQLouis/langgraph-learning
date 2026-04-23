"""
Compute a human-readable diff between the previously-committed registry
artefacts (``examples.jsonl``, ``requirements.yaml``) and freshly
regenerated versions, and write it to ``_registry/extraction_log.md``.

The diff is keyed by stable IDs (SubExample.id, Requirement.id). Hash
shifts of a SubExample appear as one remove + one add (intentional — per
draft §2.9 "hard regen, no silent carry-over"). Requirement changes that
touch ``anforderung_de`` or ``applicability_rule_de`` are called out as
``modified`` entries that should revert to ``status: draft``.

The diff writer does NOT mutate status fields itself — it only reports.
The human-review or ``/sync-registry`` command flips statuses after
reading the report.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def _load_examples(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out[obj["id"]] = obj
    return out


def _load_requirements(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f) or {}
    return {r["id"]: r for r in doc.get("requirements", [])}


# ---------------------------------------------------------------------------
# Diff computation
# ---------------------------------------------------------------------------


@dataclass
class DiffBuckets:
    added_ids: list[str]
    removed_ids: list[str]
    modified_ids: list[str]


def _diff_by_id(
    old: dict[str, dict],
    new: dict[str, dict],
    material_keys: tuple[str, ...],
) -> DiffBuckets:
    old_ids = set(old.keys())
    new_ids = set(new.keys())
    added = sorted(new_ids - old_ids)
    removed = sorted(old_ids - new_ids)
    modified: list[str] = []
    for shared in sorted(old_ids & new_ids):
        old_view = {k: old[shared].get(k) for k in material_keys}
        new_view = {k: new[shared].get(k) for k in material_keys}
        if old_view != new_view:
            modified.append(shared)
    return DiffBuckets(added_ids=added, removed_ids=removed, modified_ids=modified)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def _render_examples_section(old: dict, new: dict, diff: DiffBuckets) -> str:
    lines: list[str] = ["## SubExamples (`examples.jsonl`)", ""]
    lines.append(f"- total before: **{len(old)}**, after: **{len(new)}**")
    lines.append(f"- added: **{len(diff.added_ids)}**, removed: **{len(diff.removed_ids)}**, modified: **{len(diff.modified_ids)}**")
    lines.append("")
    if diff.added_ids:
        lines.append("### Added")
        for sid in diff.added_ids[:20]:
            entry = new[sid]
            refs = entry.get("source_refs", [])
            first_ref = refs[0] if refs else {}
            label = first_ref.get("beispiel_label", "?")
            eig = first_ref.get("eigenschaft_title_de", "?")
            lines.append(f"- `{sid}` — from *{eig}* / `{label}`")
        if len(diff.added_ids) > 20:
            lines.append(f"- …and {len(diff.added_ids) - 20} more")
        lines.append("")
    if diff.removed_ids:
        lines.append("### Removed (hash-shifted or source Beispiel deleted)")
        for sid in diff.removed_ids[:20]:
            lines.append(f"- `{sid}`")
        if len(diff.removed_ids) > 20:
            lines.append(f"- …and {len(diff.removed_ids) - 20} more")
        lines.append("")
    if diff.modified_ids:
        lines.append("### Modified")
        for sid in diff.modified_ids[:20]:
            lines.append(f"- `{sid}`")
        lines.append("")
    return "\n".join(lines)


def _render_requirements_section(old: dict, new: dict, diff: DiffBuckets) -> str:
    lines: list[str] = ["## Requirements (`requirements.yaml`)", ""]
    lines.append(f"- total before: **{len(old)}**, after: **{len(new)}**")
    lines.append(f"- added: **{len(diff.added_ids)}**, removed: **{len(diff.removed_ids)}**, modified: **{len(diff.modified_ids)}**")
    lines.append("")
    if diff.added_ids:
        lines.append("### Added (status: draft)")
        for rid in diff.added_ids:
            entry = new[rid]
            lines.append(f"- `{rid}` — *{entry.get('eigenschaft_title_de', '?')}*: {entry.get('anforderung_de', '?')[:120]}")
        lines.append("")
    if diff.removed_ids:
        lines.append("### Removed (Anforderung no longer present in MD)")
        for rid in diff.removed_ids:
            lines.append(f"- `{rid}`")
        lines.append("")
    if diff.modified_ids:
        lines.append("### Modified — require re-review; curator should revert to `status: draft`")
        for rid in diff.modified_ids:
            lines.append(f"- `{rid}`")
        lines.append("")
    return "\n".join(lines)


def render_log(
    examples_old: dict,
    examples_new: dict,
    requirements_old: dict,
    requirements_new: dict,
) -> str:
    ex_diff = _diff_by_id(
        examples_old, examples_new,
        material_keys=("prefix_messages", "story_id", "chapter_id", "default_profile"),
    )
    rq_diff = _diff_by_id(
        requirements_old, requirements_new,
        material_keys=("anforderung_de", "applicability_rule_de", "judge_criterion_en", "eigenschaft"),
    )
    header = [
        f"# Registry regeneration log — {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        "Generated by `_pipelines.regen_diff`. Hard-regen policy per draft §2.9:",
        "rewording a Beispiel or an Anforderung in the MD causes the SubExample",
        "prefix hash to shift or a Requirement's material fields to change.",
        "Affected entries must be re-reviewed and their status flipped back to",
        "`draft` until the curator re-approves.",
        "",
    ]
    return "\n".join(header) + "\n".join([
        _render_examples_section(examples_old, examples_new, ex_diff),
        _render_requirements_section(requirements_old, requirements_new, rq_diff),
    ])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_diff_report(
    examples_path: Path,
    examples_new_path: Path,
    requirements_path: Path,
    requirements_new_path: Path,
    log_path: Path,
) -> tuple[DiffBuckets, DiffBuckets]:
    """Compute the diff between the committed and freshly-regenerated files.

    ``examples_path`` / ``requirements_path`` are the previously-committed
    files; the ``*_new_path`` variants point at the regenerated output.
    The regenerated files are read fresh so this function never depends
    on the in-memory state of the other pipelines.
    """

    ex_old = _load_examples(examples_path)
    ex_new = _load_examples(examples_new_path)
    rq_old = _load_requirements(requirements_path)
    rq_new = _load_requirements(requirements_new_path)

    ex_diff = _diff_by_id(ex_old, ex_new, material_keys=("prefix_messages", "story_id", "chapter_id", "default_profile"))
    rq_diff = _diff_by_id(rq_old, rq_new, material_keys=("anforderung_de", "applicability_rule_de", "judge_criterion_en", "eigenschaft"))

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(render_log(ex_old, ex_new, rq_old, rq_new), encoding="utf-8")
    return ex_diff, rq_diff
