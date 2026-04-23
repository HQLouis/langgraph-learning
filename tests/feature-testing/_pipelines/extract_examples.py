"""
Pipeline A — turn every Beispiel into one or more deduplicated
SubExamples and write ``examples.jsonl``.

For every Beispiel we walk the turn list and, at each system turn
``T_k``, emit a SubExample consisting of::

    prefix_messages = [turn_0, turn_1, ..., turn_{k-1}]   # must end with a child turn
    target_system_turn = T_k                              # golden (debug-only)

SubExamples whose normalised prefix hashes to the same value are merged:
the later entry inherits the earlier id and both source Beispiele are
recorded under ``source_refs``.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from _pipelines.parse_dialogbeispiele import (
    Beispiel,
    Eigenschaft,
    ParseReport,
    Turn,
    parse_markdown,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default story / profile resolution
# ---------------------------------------------------------------------------

# Keep these in sync with feature_testing_utils.FIXTURE_* constants.
_STORY_MAP = {
    "PIA": ("pia_muss_nicht_perfekt_sein", "chapter_01"),
    "BOBO": ("bobos_adventskalender", "chapter_01"),
}

# Sensible defaults used when the Beispiel gives no story hint. The fallback
# profile is the same Emma-6-weiblich used across existing fixture tests.
_FALLBACK_STORY = ("pia_muss_nicht_perfekt_sein", "chapter_01")
_FALLBACK_PROFILE = {"name": "Emma", "age": 6, "gender": "weiblich"}

# A second profile we enable under --profiles=extended for gender-sensitive
# requirements.
_EXTENDED_PROFILES = [
    {"name": "Jonas", "age": 7, "gender": "männlich"},
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SourceRef:
    eigenschaft_number: int | None
    eigenschaft_title_de: str
    beispiel_label: str
    target_turn_index: int    # 0-based index of the system turn that was the live-evaluation point


@dataclass
class SubExample:
    id: str
    prefix_hash: str
    story_id: str
    chapter_id: str
    default_profile: dict
    profile_variants: list[dict]
    prefix_messages: list[dict]      # list of {role, content}
    golden_system_response: str      # the turn the MD authored next — debug-only, never used at judge time
    tier: str                        # "core" | "extended" — all start "extended", curator promotes to "core"
    source_refs: list[SourceRef] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            "id": self.id,
            "prefix_hash": self.prefix_hash,
            "story_id": self.story_id,
            "chapter_id": self.chapter_id,
            "default_profile": self.default_profile,
            "profile_variants": self.profile_variants,
            "prefix_messages": self.prefix_messages,
            "golden_system_response": self.golden_system_response,
            "tier": self.tier,
            "source_refs": [ref.__dict__ for ref in self.source_refs],
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_story(hint: str | None) -> tuple[str, str]:
    if hint and hint.upper() in _STORY_MAP:
        return _STORY_MAP[hint.upper()]
    return _FALLBACK_STORY


def _canonicalise_turn(turn: Turn) -> str:
    """Lower-case + whitespace-collapse content for hashing, so trivial
    formatting differences don't split two otherwise-identical prefixes."""
    return turn.role + ":" + " ".join(turn.content.lower().split())


def _hash_prefix(prefix: list[Turn]) -> str:
    canonical = "\n".join(_canonicalise_turn(t) for t in prefix)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _make_subexample_id(prefix_hash: str) -> str:
    return f"S-{prefix_hash[:10]}"


def _turns_to_messages(turns: list[Turn]) -> list[dict]:
    return [{"role": t.role, "content": t.content} for t in turns]


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------


def build_subexamples(
    eigenschaften: list[Eigenschaft],
) -> tuple[list[SubExample], list[str]]:
    """Produce deduplicated SubExamples from a parsed Eigenschaften tree.

    Returns ``(subexamples, skip_reasons)``. ``skip_reasons`` is a list of
    human-readable strings explaining each rejected turn pair (for the
    extraction log).
    """

    by_hash: dict[str, SubExample] = {}
    order: list[str] = []  # preserve first-seen order
    skip_reasons: list[str] = []

    for e in eigenschaften:
        for b in e.beispiele:
            _walk_beispiel(e, b, by_hash, order, skip_reasons)

    return [by_hash[h] for h in order], skip_reasons


def _walk_beispiel(
    eigenschaft: Eigenschaft,
    beispiel: Beispiel,
    by_hash: dict[str, SubExample],
    order: list[str],
    skip_reasons: list[str],
) -> None:
    story_id, chapter_id = _resolve_story(beispiel.story_hint)
    turns = beispiel.turns
    if not turns:
        return

    for k, turn in enumerate(turns):
        if turn.role != "system":
            continue
        prefix = turns[:k]
        # A usable prefix ends with a child turn. A system-turn-only prefix
        # or empty prefix would not correspond to anything our dialog
        # system would ever be asked to generate against.
        if not prefix or prefix[-1].role != "system" and prefix[-1].role != "child":
            skip_reasons.append(
                f"{eigenschaft.title_de!r} / {beispiel.label!r}: skipped turn {k} — prefix empty."
            )
            continue
        if prefix[-1].role != "child":
            skip_reasons.append(
                f"{eigenschaft.title_de!r} / {beispiel.label!r}: skipped turn {k} — prefix does not end with a child utterance."
            )
            continue

        prefix_hash = _hash_prefix(prefix)
        source_ref = SourceRef(
            eigenschaft_number=eigenschaft.number,
            eigenschaft_title_de=eigenschaft.title_de,
            beispiel_label=beispiel.label,
            target_turn_index=k,
        )

        if prefix_hash in by_hash:
            by_hash[prefix_hash].source_refs.append(source_ref)
            continue

        sub = SubExample(
            id=_make_subexample_id(prefix_hash),
            prefix_hash=prefix_hash,
            story_id=story_id,
            chapter_id=chapter_id,
            default_profile=dict(_FALLBACK_PROFILE),
            profile_variants=[dict(p) for p in _EXTENDED_PROFILES],
            prefix_messages=_turns_to_messages(prefix),
            golden_system_response=turn.content,
            tier="extended",  # curator promotes highlighted turns to "core" later
            source_refs=[source_ref],
        )

        # The first source-Beispiel whose highlighted turn matches this k
        # gets its tier auto-promoted to "core" — those are the PM-marked
        # "moment" turns.
        if beispiel.highlight_from_turn is not None and k >= beispiel.highlight_from_turn:
            sub.tier = "core"

        by_hash[prefix_hash] = sub
        order.append(prefix_hash)


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def write_examples_jsonl(subexamples: list[SubExample], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for sub in subexamples:
            f.write(json.dumps(sub.to_json(), ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Extract deduplicated SubExamples from Dialogbeispiele.md.")
    parser.add_argument(
        "--md",
        default="tests/feature-testing/Dialogbeispiele für die Eigenschaften.md",
        help="Path to Dialogbeispiele MD",
    )
    parser.add_argument(
        "--out",
        default="tests/feature-testing/_registry/examples.jsonl",
        help="Output JSONL path",
    )
    args = parser.parse_args()

    eigenschaften, parse_report = parse_markdown(Path(args.md))
    logger.info(
        "parsed %d Eigenschaften, %d Beispiele, %d turns",
        parse_report.eigenschaft_count,
        parse_report.beispiel_count,
        parse_report.turn_count,
    )

    subexamples, skip_reasons = build_subexamples(eigenschaften)
    logger.info(
        "produced %d SubExamples (dedup from %d candidate turns); %d skipped",
        len(subexamples),
        sum(len(b.turns) for e in eigenschaften for b in e.beispiele),
        len(skip_reasons),
    )

    write_examples_jsonl(subexamples, Path(args.out))
    logger.info("wrote %s", args.out)


if __name__ == "__main__":
    main()
