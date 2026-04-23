"""
Pipeline B — seed ``requirements.yaml`` from the Anforderung blocks in the
Dialogbeispiele MD.

The seeded entries start with ``status: draft`` and clearly-marked
placeholder fields where an LLM enrichment pass (or a human) must
provide final wording:

* ``title_de``: short one-line summary — seeded with a truncated version
  of ``anforderung_de`` and marked ``[DRAFT]``.
* ``applicability_rule_de``: when does this requirement apply to a
  response? — seeded with a ``[DRAFT]`` placeholder.
* ``judge_criterion_en``: the PASS|FAIL|N/A judge prompt — seeded with a
  ``[DRAFT]`` placeholder that references the anforderung_de.

All other fields are computed from the MD and the heuristics below.

**Phase 0 intentionally does not call an LLM.** The pipeline is
deterministic; LLM enrichment is a separate pass we layer on top once we
have confidence in the structural extraction.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import yaml

from _pipelines.parse_dialogbeispiele import Beispiel, Eigenschaft, parse_markdown

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Heuristics for tier / profile_sensitivity / needs_background_analysis
# ---------------------------------------------------------------------------

# Lowercase German keyword markers that, if any match the anforderung
# text, promote the requirement to ``tier: core``.
_CORE_KEYWORDS = (
    "sofort", "muss", "nicht verwenden", "akzeptieren", "keine ",
    "darf nicht", "immer", "kein ", "nein", "weiß nicht",
    "aufforderung zum wiederholen",
)

# When the anforderung mentions these, the requirement depends on the
# system addressing the child with gendered language.
_GENDER_KEYWORDS = (
    "geschlecht", "mädchen", "jungen", "junge ", "weiblich", "männlich", "rolle",
)

# When the anforderung references the child's age or developmental
# stage, mark ``profile_sensitivity: age``.
_AGE_KEYWORDS = (
    "alter", "kleinkind", "altersgemäß", "altersstufe",
)


def _infer_tier(anforderung_de: str) -> str:
    lower = anforderung_de.lower()
    if any(kw in lower for kw in _CORE_KEYWORDS):
        return "core"
    return "extended"


def _infer_profile_sensitivity(anforderung_de: str, eigenschaft_title: str) -> str:
    text = (anforderung_de + " " + eigenschaft_title).lower()
    if any(kw in text for kw in _GENDER_KEYWORDS):
        return "gender"
    if any(kw in text for kw in _AGE_KEYWORDS):
        return "age"
    return "none"


def _infer_needs_background_analysis(_anforderung_de: str) -> bool:
    # Per draft §2.5b (v1): the current dialog-system topology routes every
    # background worker output into the next master turn. Default to True
    # for every requirement; curator / future optimisation pass may flip
    # individual entries to False when a worker is confirmed isolated.
    return True


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Requirement:
    id: str
    eigenschaft: int | None
    eigenschaft_title_de: str
    title_de: str
    anforderung_de: str
    example_refs: list[str]
    applicability_rule_de: str
    judge_criterion_en: str
    tier: str
    profile_sensitivity: str
    needs_background_analysis: bool
    status: str = "draft"


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def build_requirements(eigenschaften: list[Eigenschaft]) -> list[Requirement]:
    out: list[Requirement] = []
    for e in eigenschaften:
        counter = 0
        # Section-level Anforderungen (present before the first Beispiel)
        # count as Requirements for the whole section. We attach them to
        # every Beispiel in example_refs so reports can still trace them.
        for anforderung in e.section_anforderungen:
            counter += 1
            out.append(_make_section_requirement(e, anforderung, counter))
        for b in e.beispiele:
            for anforderung in b.anforderungen:
                counter += 1
                req = _make_requirement(e, b, anforderung, counter)
                out.append(req)
    return out


_DRAFT_TITLE_LIMIT = 90


def _make_requirement(
    eigenschaft: Eigenschaft,
    beispiel: Beispiel,
    anforderung_de: str,
    seq: int,
) -> Requirement:
    number = eigenschaft.number if eigenschaft.number is not None else 0
    req_id = f"R-{number:02d}-{seq:02d}"
    title_de = anforderung_de.strip()
    if len(title_de) > _DRAFT_TITLE_LIMIT:
        title_de = title_de[:_DRAFT_TITLE_LIMIT - 1].rstrip() + "…"
    title_de = f"[DRAFT] {title_de}"

    applicability = (
        "[DRAFT] Applies to every system response. A curator must restrict "
        "this to the specific situations described in anforderung_de before "
        "flipping status to active."
    )
    judge_en = (
        "[DRAFT — review before activation]\n"
        "Evaluate whether the system response complies with this German "
        "requirement:\n\n"
        f"  {anforderung_de}\n\n"
        "If the situation described by the requirement does not apply to "
        "the response, answer N/A with a one-line reason. Otherwise answer "
        "PASS or FAIL with a one-line reason."
    )

    return Requirement(
        id=req_id,
        eigenschaft=eigenschaft.number,
        eigenschaft_title_de=eigenschaft.title_de,
        title_de=title_de,
        anforderung_de=anforderung_de,
        example_refs=[beispiel.label] if beispiel.label else [],
        applicability_rule_de=applicability,
        judge_criterion_en=judge_en,
        tier=_infer_tier(anforderung_de),
        profile_sensitivity=_infer_profile_sensitivity(anforderung_de, eigenschaft.title_de),
        needs_background_analysis=_infer_needs_background_analysis(anforderung_de),
        status="draft",
    )


def _make_section_requirement(
    eigenschaft: Eigenschaft,
    anforderung_de: str,
    seq: int,
) -> Requirement:
    """Create a Requirement for a section-level Anforderung (no
    example_refs — it applies to the whole Eigenschaft)."""
    req = _make_requirement(eigenschaft, _PSEUDO_BEISPIEL, anforderung_de, seq)
    # Attach all Beispiel labels as refs so reports can trace context.
    req.example_refs = [b.label for b in eigenschaft.beispiele if b.label]
    return req


# Module-level sentinel — the section-level path doesn't correspond to
# any single Beispiel.
class _PseudoBeispiel:
    label = ""


_PSEUDO_BEISPIEL = _PseudoBeispiel()


# ---------------------------------------------------------------------------
# Curator-state preservation
# ---------------------------------------------------------------------------


def _load_existing(path: Path) -> dict[str, dict]:
    """Index existing requirements by id; empty dict on any I/O issue."""
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return {r["id"]: r for r in doc.get("requirements", []) if isinstance(r, dict) and "id" in r}


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------


def write_requirements_yaml(
    requirements: list[Requirement],
    out_path: Path,
    *,
    preserve_curator_state: bool = True,
    existing_source_path: Path | None = None,
) -> None:
    """Write the YAML registry with ordered keys for reviewable diffs.

    When ``preserve_curator_state`` is True (default) curator-edited
    fields are carried over from an existing YAML for any Requirement
    whose ``anforderung_de`` is unchanged. By default we look at
    ``out_path`` for the old file, but callers that stage writes through
    a temp directory (see ``_pipelines.run``) should pass the committed
    path via ``existing_source_path``.

    Fields preserved: ``applicability_rule_de``, ``judge_criterion_en``,
    ``title_de``, ``status``, ``tier``, ``profile_sensitivity``,
    ``needs_background_analysis``. When ``anforderung_de`` changes the
    entry is re-seeded from scratch with ``status: draft``.
    """

    existing: dict[str, dict] = {}
    if preserve_curator_state:
        source = existing_source_path if existing_source_path is not None else out_path
        if source.exists():
            existing = _load_existing(source)

    def _as_dict(r: Requirement) -> dict:
        old = existing.get(r.id)
        if old and old.get("anforderung_de") == r.anforderung_de:
            # Unchanged source → carry the curator's edits over.
            return {
                "id": r.id,
                "eigenschaft": r.eigenschaft,
                "eigenschaft_title_de": r.eigenschaft_title_de,
                "title_de": old.get("title_de", r.title_de),
                "anforderung_de": r.anforderung_de,
                "example_refs": r.example_refs,
                "applicability_rule_de": old.get("applicability_rule_de", r.applicability_rule_de),
                "judge_criterion_en": old.get("judge_criterion_en", r.judge_criterion_en),
                "tier": old.get("tier", r.tier),
                "profile_sensitivity": old.get("profile_sensitivity", r.profile_sensitivity),
                "needs_background_analysis": old.get("needs_background_analysis", r.needs_background_analysis),
                "status": old.get("status", r.status),
            }
        # New entry or source text changed → emit fresh draft.
        return {
            "id": r.id,
            "eigenschaft": r.eigenschaft,
            "eigenschaft_title_de": r.eigenschaft_title_de,
            "title_de": r.title_de,
            "anforderung_de": r.anforderung_de,
            "example_refs": r.example_refs,
            "applicability_rule_de": r.applicability_rule_de,
            "judge_criterion_en": r.judge_criterion_en,
            "tier": r.tier,
            "profile_sensitivity": r.profile_sensitivity,
            "needs_background_analysis": r.needs_background_analysis,
            "status": r.status,
        }

    doc = {
        "version": 1,
        "metadata": {
            "source": "Dialogbeispiele für die Eigenschaften.md",
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator": "_pipelines.extract_requirements",
            "count": len(requirements),
        },
        "requirements": [_as_dict(r) for r in requirements],
    }

    # Disable the PyYAML aliasing so repeated strings aren't anchor-referenced —
    # that makes the YAML hard for non-YAML readers (our PM reviews this file).
    class _NoAliasDumper(yaml.SafeDumper):
        def ignore_aliases(self, _data):  # noqa: ANN001
            return True

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.dump(doc, f, Dumper=_NoAliasDumper, sort_keys=False, allow_unicode=True, width=100)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Seed requirements.yaml from Dialogbeispiele.md.")
    parser.add_argument(
        "--md",
        default="tests/feature-testing/Dialogbeispiele für die Eigenschaften.md",
    )
    parser.add_argument(
        "--out",
        default="tests/feature-testing/_registry/requirements.yaml",
    )
    args = parser.parse_args()

    eigenschaften, report = parse_markdown(Path(args.md))
    logger.info(
        "parsed %d Eigenschaften, %d Beispiele",
        report.eigenschaft_count,
        report.beispiel_count,
    )

    requirements = build_requirements(eigenschaften)
    logger.info("built %d requirements", len(requirements))

    write_requirements_yaml(requirements, Path(args.out))
    logger.info("wrote %s", args.out)


if __name__ == "__main__":
    main()
