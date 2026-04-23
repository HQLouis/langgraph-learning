"""
Combined applicability + verdict judge prompt (draft §2.6).

The judge receives:
  * the prior conversation,
  * the generated system response,
  * the German Anforderung text,
  * the German applicability rule,
  * the English judge criterion (extra spec from registry).

It emits exactly two lines:
  Line 1: "PASS" | "FAIL" | "N/A"
  Line 2: one short reason sentence

This module is deliberately pure: it builds a prompt string and parses a
response string. Any LLM transport (LangChain message, REST call, mock)
can be plugged in via :func:`invoke_judge`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


PROMPT_TEMPLATE = """\
You are evaluating a single system response from a German children's dialog
system against ONE requirement. The dialog system is designed for German-
speaking children ages 3–12.

--- Conversation history (up to and including the last child utterance) ---
{prefix_conversation}

--- System response being evaluated ---
{response_text}

--- Requirement (original German) ---
{anforderung_de}

--- Applicability rule (German) ---
{applicability_rule_de}

--- Extra judge specification (English, clarifies the requirement) ---
{judge_criterion_en}

--- Your task ---
Step 1. Decide whether the requirement is APPLICABLE to this response,
        according to the applicability rule. A requirement is APPLICABLE
        only when the situation it governs is actually present in the
        response. If the requirement does not touch the response at all,
        it is NOT applicable.
Step 2. Output exactly two lines:

    Line 1 — one of: PASS, FAIL, N/A
       PASS  = requirement applied and was satisfied
       FAIL  = requirement applied and was violated
       N/A   = requirement did not apply to this response

    Line 2 — one short sentence (max 25 words) explaining the verdict.

Do not output anything else. Do not compare against any reference or
"gold" response; judge only against the Anforderung.
"""


# ---------------------------------------------------------------------------
# Verdict parsing
# ---------------------------------------------------------------------------

_VALID_VERDICTS = {"PASS", "FAIL", "N/A"}


@dataclass(frozen=True)
class JudgeVerdict:
    """Structured verdict returned by the judge.

    ``verdict`` is always one of {"PASS", "FAIL", "N/A"}.
    ``is_non_failing`` is True for PASS or N/A (both count as pass for
    threshold math per draft §2.3).
    """

    verdict: str
    reason: str
    raw: str

    @property
    def is_non_failing(self) -> bool:
        return self.verdict in {"PASS", "N/A"}

    @property
    def is_not_applicable(self) -> bool:
        return self.verdict == "N/A"


def parse_verdict(raw: str) -> JudgeVerdict:
    """Parse the first non-empty line as the verdict; the next line as reason.

    Robust to leading whitespace, trailing punctuation, and models that
    emit "PASS:", "FAIL." etc. Falls back to FAIL with an explanatory
    reason when parsing fails — that way a mis-behaving judge can't
    accidentally score a cell as PASS.
    """

    lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
    if not lines:
        return JudgeVerdict(
            verdict="FAIL",
            reason="judge returned no output",
            raw=raw or "",
        )

    first_upper = lines[0].rstrip(":.!-").upper().replace(" ", "")
    # Normalise "N/A", "NA", "NOT_APPLICABLE", "NOT-APPLICABLE", ... by
    # dropping non-alphanumeric characters for the comparison.
    first_alnum = "".join(ch for ch in first_upper if ch.isalnum())
    if first_alnum in {"NA", "NOTAPPLICABLE"}:
        verdict = "N/A"
    elif first_alnum.startswith("PASS"):
        verdict = "PASS"
    elif first_alnum.startswith("FAIL"):
        verdict = "FAIL"
    else:
        return JudgeVerdict(
            verdict="FAIL",
            reason=f"unparseable verdict line: {lines[0]!r}",
            raw=raw,
        )

    reason = lines[1] if len(lines) > 1 else ""
    return JudgeVerdict(verdict=verdict, reason=reason, raw=raw)


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------


def build_prompt(
    *,
    prefix_messages: list[dict],
    response_text: str,
    anforderung_de: str,
    applicability_rule_de: str,
    judge_criterion_en: str,
) -> str:
    conversation = _render_conversation(prefix_messages)
    return PROMPT_TEMPLATE.format(
        prefix_conversation=conversation,
        response_text=response_text,
        anforderung_de=anforderung_de,
        applicability_rule_de=applicability_rule_de,
        judge_criterion_en=judge_criterion_en,
    )


def _render_conversation(messages: list[dict]) -> str:
    if not messages:
        return "(no prior conversation — this is the first turn)"
    parts = []
    for m in messages:
        role = "Child" if m["role"] == "child" else "System"
        parts.append(f"{role}: {m['content']}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Transport glue
# ---------------------------------------------------------------------------


class _Invocable(Protocol):
    """Minimal protocol the judge transport must satisfy.

    We accept either a LangChain chat model (``.invoke([HumanMessage(...)])``)
    or a plain callable ``str -> str`` so unit tests can stub easily.
    """

    def invoke(self, messages) -> object: ...  # pragma: no cover - structural only


def invoke_judge(
    judge_llm,
    prompt: str,
    *,
    invoke_fn: Callable[[object, str], str] | None = None,
) -> JudgeVerdict:
    """Run the judge prompt and return a parsed verdict.

    Pass ``invoke_fn`` when the caller already has a preferred transport
    (e.g. a LangSmith-wrapped invoke). By default we use
    ``HumanMessage(prompt)`` over LangChain's ``.invoke``, mirroring
    ``feature_testing_utils.llm_judge``.
    """

    if invoke_fn is not None:
        raw = invoke_fn(judge_llm, prompt)
    else:
        from langchain_core.messages import HumanMessage

        try:
            from langsmith import tracing_context  # type: ignore
            from ft_config import JUDGE_LANGSMITH_TRACING  # type: ignore
        except Exception:  # pragma: no cover — no langsmith in minimal envs
            tracing_context = None
            JUDGE_LANGSMITH_TRACING = False

        if tracing_context and not JUDGE_LANGSMITH_TRACING:
            with tracing_context(enabled=False):
                raw = judge_llm.invoke([HumanMessage(content=prompt)]).content.strip()
        else:
            raw = judge_llm.invoke([HumanMessage(content=prompt)]).content.strip()

    return parse_verdict(raw)
