"""
LLM-based enrichment for draft requirements.

For each requirement whose fields still hold ``[DRAFT]`` placeholders,
this pipeline calls an LLM once to produce:

  * a short ``title_de`` (one line, no DRAFT prefix)
  * a structured German ``applicability_rule_de`` describing when the
    requirement applies to a response
  * an English ``judge_criterion_en`` emitting PASS / FAIL / N/A

The original Anforderung text, the Eigenschaft title, the linked
Beispiele dialogues, and (when present) the "mögliche KI Antwort"
reference are passed as context. The "mögliche KI Antwort" is used
only to disambiguate terse Anforderungen during enrichment authoring
per draft §6.2 — it is never stored in the registry, never shown to
the runtime judge.

The pipeline is idempotent: re-running over a partially-enriched YAML
skips entries whose fields no longer start with ``[DRAFT]``.

Run with::

    PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements \
        --only R-19-02,R-19-03

or omit ``--only`` to enrich every DRAFT entry.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import yaml

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


ENRICHMENT_PROMPT = """\
You are enriching a single requirement entry in a German children's
dialog-system test registry. You must output a short JSON object (no
markdown fences, no commentary) with exactly three keys:

  {{
    "title_de": "one short line summarising the requirement in German",
    "applicability_rule_de": "…",
    "judge_criterion_en": "…"
  }}

### The requirement

Eigenschaft (category): {eigenschaft_title_de}

Original Anforderung (German, verbatim):
{anforderung_de}

### Context from the linked Beispiel(e)
(Treat these as illustrative dialogue examples. Do NOT store them
verbatim. Use them only to infer WHEN the requirement applies.)

{beispiel_context}

### Authoring rules

1. title_de — One line, 8–14 German words, capturing the rule.
   Do NOT start with "[DRAFT]".

2. applicability_rule_de — 2–4 German sentences describing precisely
   WHEN this requirement applies to a generated system response. Focus
   on surface conditions the judge can check from the conversation
   prefix + the generated response. When the requirement applies only
   in specific conversation states, say so explicitly ("Gilt nur, wenn
   …", "Gilt nicht, wenn …"). Do NOT say "applies to every response"
   unless it really does.

3. judge_criterion_en — 4–7 English sentences. Must end with three
   explicit return conditions:
     Return PASS if …
     Return FAIL if …
     Return N/A if …
   N/A is the correct verdict when the requirement's applicability
   rule is not met by the response. Never reference or compare against
   any "gold" or reference response.

Output ONLY the JSON object. No preamble, no code fences.
"""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class EnrichmentResult:
    title_de: str
    applicability_rule_de: str
    judge_criterion_en: str


class EnrichmentError(Exception):
    """Raised when the LLM output cannot be parsed into an EnrichmentResult."""


# ---------------------------------------------------------------------------
# Core API — pure
# ---------------------------------------------------------------------------


def is_draft(requirement: dict) -> bool:
    """True when any of the three enrichable fields still holds [DRAFT]."""
    for key in ("title_de", "applicability_rule_de", "judge_criterion_en"):
        if (requirement.get(key) or "").strip().startswith("[DRAFT"):
            return True
    return False


def build_prompt(
    requirement: dict,
    beispiel_context: str,
) -> str:
    return ENRICHMENT_PROMPT.format(
        eigenschaft_title_de=requirement.get("eigenschaft_title_de", ""),
        anforderung_de=requirement.get("anforderung_de", ""),
        beispiel_context=beispiel_context.strip() or "(no Beispiel context available)",
    )


def parse_enrichment(raw: str) -> EnrichmentResult:
    """Parse the LLM output into an EnrichmentResult.

    Tolerates surrounding whitespace and the occasional markdown fence
    some models emit despite our instructions. Raises
    :class:`EnrichmentError` if the result cannot be parsed.
    """

    text = raw.strip()
    # Strip a "```json ... ```" fence if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1)

    try:
        obj = json.loads(text)
    except json.JSONDecodeError as exc:
        raise EnrichmentError(f"LLM did not return valid JSON: {exc}") from exc

    required = {"title_de", "applicability_rule_de", "judge_criterion_en"}
    missing = required - obj.keys()
    if missing:
        raise EnrichmentError(f"Enrichment missing keys: {sorted(missing)}")

    for key in required:
        if not isinstance(obj[key], str) or not obj[key].strip():
            raise EnrichmentError(f"Enrichment field {key!r} is empty or not a string")
        if obj[key].strip().startswith("[DRAFT"):
            raise EnrichmentError(f"Enrichment field {key!r} still carries a DRAFT marker")

    # Final sanity check: judge_criterion_en must carry all three return lines.
    crit_lower = obj["judge_criterion_en"].lower()
    for fragment in ("pass", "fail", "n/a"):
        if fragment not in crit_lower:
            raise EnrichmentError(
                f"judge_criterion_en is missing the {fragment.upper()} return clause"
            )

    return EnrichmentResult(
        title_de=obj["title_de"].strip(),
        applicability_rule_de=obj["applicability_rule_de"].strip(),
        judge_criterion_en=obj["judge_criterion_en"].strip(),
    )


# ---------------------------------------------------------------------------
# Beispiel context resolution
# ---------------------------------------------------------------------------


def build_beispiel_context(
    requirement: dict,
    eigenschaften: list,
) -> str:
    """Gather up to two Beispiele (and any suggested KI Antwort) from the
    MD parse that this requirement references.

    ``eigenschaften`` is the output of ``parse_dialogbeispiele.parse_markdown``
    — the same objects the extractor used, so labels line up.
    """

    if not requirement.get("example_refs"):
        return ""

    matched: list[str] = []
    wanted = {lbl for lbl in requirement["example_refs"] if lbl}
    eig_num = requirement.get("eigenschaft")
    for e in eigenschaften:
        if e.number != eig_num:
            continue
        for b in e.beispiele:
            if b.label not in wanted:
                continue
            turns = "\n".join(
                f"  {'Kind' if t.role == 'child' else 'KI'}: {t.content}"
                for t in b.turns
            ) or "  (no dialogue)"
            suggested = ""
            if b.suggested_ki_turns:
                suggested_lines = "\n".join(
                    f"  {'Kind' if t.role == 'child' else 'KI'}: {t.content}"
                    for t in b.suggested_ki_turns
                )
                suggested = f"\n  [mögliche KI Antwort]\n{suggested_lines}"
            matched.append(f"[{b.label}]\n{turns}{suggested}")
            if len(matched) >= 2:
                return "\n\n".join(matched)
    return "\n\n".join(matched)


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def enrich_requirements(
    registry_path: Path,
    md_path: Path,
    llm_call: Callable[[str], str],
    *,
    only_ids: Iterable[str] | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Enrich every draft requirement in-place via ``llm_call``.

    ``llm_call`` is a function ``str -> str`` that takes a prompt and
    returns the model's raw text output. Unit tests pass a stub; the
    CLI below binds a LangChain chat model.

    Returns the list of Requirement IDs that were enriched.
    """

    from _pipelines.parse_dialogbeispiele import parse_markdown

    doc = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    requirements = doc.get("requirements", [])
    eigenschaften, _report = parse_markdown(md_path)

    want_ids: set[str] | None = set(only_ids) if only_ids else None
    enriched_ids: list[str] = []
    errors: list[tuple[str, str]] = []

    for req in requirements:
        if want_ids is not None and req.get("id") not in want_ids:
            continue
        if not is_draft(req):
            continue

        context = build_beispiel_context(req, eigenschaften)
        prompt = build_prompt(req, context)
        logger.info("enriching %s (%s)", req.get("id"), req.get("eigenschaft_title_de"))
        try:
            raw = llm_call(prompt)
            result = parse_enrichment(raw)
        except EnrichmentError as exc:
            errors.append((req.get("id", "?"), str(exc)))
            logger.warning("  skipped: %s", exc)
            continue

        req["title_de"] = result.title_de
        req["applicability_rule_de"] = result.applicability_rule_de
        req["judge_criterion_en"] = result.judge_criterion_en
        # Status remains "draft"; a human still flips to "active" after review.
        enriched_ids.append(req["id"])

    if not dry_run and enriched_ids:
        doc["requirements"] = requirements
        registry_path.write_text(
            yaml.safe_dump(doc, allow_unicode=True, sort_keys=False, width=100),
            encoding="utf-8",
        )

    if errors:
        logger.warning(
            "%d enrichment failures — review and retry: %s",
            len(errors),
            ", ".join(f"{rid} ({err[:60]})" for rid, err in errors),
        )
    return enriched_ids


# ---------------------------------------------------------------------------
# Default LangChain transport
# ---------------------------------------------------------------------------


def _default_llm_call(model_name: str, temperature: float) -> Callable[[str], str]:
    """Return a callable that invokes a LangChain chat model with a HumanMessage."""
    from langchain.chat_models import init_chat_model  # type: ignore
    from langchain_core.messages import HumanMessage  # type: ignore

    model = init_chat_model(model_name, temperature=temperature)

    def _call(prompt: str) -> str:
        resp = model.invoke([HumanMessage(content=prompt)])
        return getattr(resp, "content", "") or ""

    return _call


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Enrich draft requirements via LLM.")
    parser.add_argument(
        "--md",
        default="tests/feature-testing/Dialogbeispiele für die Eigenschaften.md",
    )
    parser.add_argument(
        "--registry",
        default="tests/feature-testing/_registry/requirements.yaml",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated requirement IDs to enrich (default: all DRAFT entries).",
    )
    # Model default is centralised in ``agentic_system.model_config``
    # (``agentic-system`` is already on pythonpath via pyproject.toml).
    # Override with ``--model`` on the CLI or the ``LINGOLINO_LLM_MODEL``
    # env var.
    from model_config import resolve_model as _resolve_model  # type: ignore[import-not-found]

    parser.add_argument("--model", default=_resolve_model())
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    only = [s.strip() for s in args.only.split(",")] if args.only else None
    llm_call = _default_llm_call(args.model, args.temperature)

    changed = enrich_requirements(
        Path(args.registry),
        Path(args.md),
        llm_call,
        only_ids=only,
        dry_run=args.dry_run,
    )
    logger.info("enriched %d requirements: %s", len(changed), ", ".join(changed))


if __name__ == "__main__":
    main()
