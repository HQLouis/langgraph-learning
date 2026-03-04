"""
Feature Testing Framework — Shared Utilities

This module contains pure helper functions that test files import directly.
Pytest fixtures (which wrap these helpers) are defined in conftest.py.

Importable from any feature test file:
    from feature_testing_utils import build_state, run_n_times, llm_judge, simulate_conversation
    from feature_testing_utils import MESSAGES_TURN_0, MESSAGES_TURN_1_GREETING, MESSAGES_TURN_3_MID_STORY
    from feature_testing_utils import FIXTURE_AUDIO_BOOK, FIXTURE_STORY_ID, FIXTURE_CHAPTER_ID
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Callable

from langchain_core.messages import AIMessage, HumanMessage

# ---------------------------------------------------------------------------
# Path setup — allow importing from agentic-system without installation
# Location: tests/feature-testing/
#   _FEATURE_TESTING_DIR  →  <root>/tests/feature-testing
#   _PROJECT_ROOT         →  <root>               (two levels up)
#   _AGENTIC_SYSTEM       →  <root>/agentic-system
# ---------------------------------------------------------------------------
_FEATURE_TESTING_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _FEATURE_TESTING_DIR.parent.parent.resolve()
_AGENTIC_SYSTEM = _PROJECT_ROOT / "agentic-system"

for _p in [str(_AGENTIC_SYSTEM), str(_PROJECT_ROOT), str(_FEATURE_TESTING_DIR)]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from states import State, BackgroundState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Background analysis field list — derived from BackgroundState so it stays
# in sync with states.py without any duplication here.
# Only fields that also exist on State (i.e. the analysis outputs) are relevant;
# infrastructure fields like child_id, audio_book, story_id, … are excluded.
# ---------------------------------------------------------------------------
_STATE_FIELDS: frozenset[str] = frozenset(State.__annotations__)
_BG_ANALYSIS_FIELDS: tuple[str, ...] = tuple(
    field for field in BackgroundState.__annotations__
    if field in _STATE_FIELDS
    and field not in {
        "child_id", "audio_book_id", "child_profile", "audio_book",
        "story_id", "chapter_id", "beat_context", "active_beat_ids", "num_planned_tasks",
    }
)

# ---------------------------------------------------------------------------
# Story fixture constants
# ---------------------------------------------------------------------------

FIXTURE_AUDIO_BOOK: str = (
    "Es war einmal ein kleines Mädchen namens Mia. Mia lebte in einem kleinen Dorf am Waldrand. "
    "Jeden Tag schaute sie aus ihrem Fenster und träumte davon, den Wald zu erkunden. "
    "Eines Morgens beschloss Mia, in den Wald zu gehen, um Beeren zu sammeln. Sie nahm einen kleinen Korb mit. "
    "Der Wald war dunkel und geheimnisvoll. Hohe Bäume ragten in den Himmel. "
    "Plötzlich hörte sie ein Rascheln im Gebüsch. Mia blieb stehen und lauschte aufmerksam. "
    "'Wer ist da?', fragte Mia mutig. Ihre Stimme klang fest, aber ihr Herz klopfte schnell. "
    "Ein kleiner Fuchs sprang aus dem Gebüsch hervor. Seine Augen funkelten neugierig. "
    "'Keine Angst', sagte der Fuchs freundlich. 'Ich bin Leo und ich bin nur auf der Suche nach meinem Abendessen.' "
    "Mia lächelte erleichtert. 'Ich heiße Mia', antwortete sie. 'Ich sammle Beeren. Möchtest du mir helfen?' "
    "Der Fuchs nickte eifrig. 'Gerne! Ich kenne die besten Stellen im Wald.' "
    "Gemeinsam gingen Mia und Leo tiefer in den Wald hinein. Leo zeigte ihr einen versteckten Platz voller Himbeeren. "
    "Die Beeren waren rot und saftig. Mia füllte ihren Korb bis zum Rand. "
    "'Danke für deine Hilfe, Leo', sagte Mia glücklich. Sie gab dem Fuchs ein paar Beeren. "
    "'Gern geschehen', antwortete Leo und knabberte genüsslich an den Beeren. "
    "Als die Sonne langsam unterging, färbte sich der Himmel orange und rosa. Es wurde Zeit, nach Hause zu gehen. "
    "'Wir sehen uns morgen wieder?', fragte Leo hoffnungsvoll. "
    "'Auf jeden Fall!', versprach Mia. Sie winkte zum Abschied und machte sich auf den Heimweg. "
    "Mit ihrem vollen Korb und einem neuen Freund im Herzen ging Mia fröhlich nach Hause zurück."
)

FIXTURE_STORY_ID: str = "mia_und_leo"
FIXTURE_CHAPTER_ID: str = "chapter_01"

# ---------------------------------------------------------------------------
# Conversation history fixtures
# ---------------------------------------------------------------------------

MESSAGES_TURN_0: list = []
"""First ever turn — no prior conversation."""

MESSAGES_TURN_1_GREETING: list = [
    AIMessage(content="Hallo Emma! Ich freue mich, dass du heute mit mir lernst."),
    HumanMessage(content="Hallo!"),
]
"""One complete exchange: system greeted, child responded."""

MESSAGES_TURN_3_MID_STORY: list = [
    AIMessage(content="Hallo Emma! Schön, dass du heute dabei bist."),
    HumanMessage(content="Hallo!"),
    AIMessage(content="Heute lesen wir eine Geschichte über ein Mädchen namens Mia und einen Fuchs namens Leo."),
    HumanMessage(content="Cool!"),
    AIMessage(content="Was denkst du, warum Mia in den Wald geht?"),
    HumanMessage(content="Sie will Beeren sammeln."),
]
"""Three complete exchanges — child is mid-story."""


# ---------------------------------------------------------------------------
# State builder
# ---------------------------------------------------------------------------


def build_state(
        child_name: str,
        child_age: int,
        child_gender: str,
        messages: list,
        audio_book: str = FIXTURE_AUDIO_BOOK,
        aufgaben: str = "",
        satzbaubegrenzung: str = "",
        story_id: str = FIXTURE_STORY_ID,
        chapter_id: str = FIXTURE_CHAPTER_ID,
        active_beat_ids: list | None = None,
        background_state: dict | None = None,
        num_planned_tasks: int = 5,
) -> State:
    """
    Build a fully-populated State for Strategy A (fixture-based) tests.

    All values are hardcoded — nothing is loaded from S3, DynamoDB, or any
    external service. The child_profile string is constructed from the
    provided parameters in the same free-form format used in production.

    Args:
        child_name: The child's first name (e.g. "Emma").
        child_age: The child's age in years.
        child_gender: "weiblich" or "männlich".
        messages: Pre-built conversation history (use MESSAGES_TURN_* constants).
        audio_book: Story content (defaults to the Mia und Leo fixture).
        aufgaben: Analysis result from the aufgaben worker (empty = not yet analysed).
                  Ignored when background_state is provided.
        satzbaubegrenzung: Sentence structure constraints (empty = none active).
                           Ignored when background_state is provided.
        story_id: Story identifier for the beat system.
        chapter_id: Chapter identifier for the beat system.
        active_beat_ids: Beat IDs currently in scope (None = empty list).
        background_state: Optional dict (BackgroundState-shaped) produced by
                          :func:`run_background_analysis`.  When provided, ALL
                          analysis fields are copied from it so that the
                          immediate graph sees the full background output — not
                          only ``aufgaben`` and ``satzbaubegrenzung``.  The
                          individual keyword arguments above act as fallbacks
                          when this is None.
        num_planned_tasks: Number of story tasks planned for this chapter.
                           Passed through to the beat system (default: 5).

    Returns:
        A fully-populated State TypedDict ready for use with masterChatbot().
    """
    gender_word = "ein Mädchen" if child_gender == "weiblich" else "ein Junge"
    child_profile = (
        f"Das Kind heißt {child_name}, ist {child_age} Jahre alt und ist {gender_word}."
    )

    # Resolve analysis values: background_state wins over individual kwargs.
    # _BG_ANALYSIS_FIELDS is derived from BackgroundState.__annotations__ at
    # module level — no duplication needed here.
    if background_state is not None:
        analysis = {field: background_state.get(field, "") for field in _BG_ANALYSIS_FIELDS}
    else:
        analysis = {field: "" for field in _BG_ANALYSIS_FIELDS}
        analysis["aufgaben"] = aufgaben
        analysis["satzbaubegrenzung"] = satzbaubegrenzung

    return State(
        child_id="fixture_child",
        audio_book_id="fixture_audio_book",
        child_profile=child_profile,
        audio_book=audio_book,
        messages=messages,
        grammar_analysis=analysis["grammar_analysis"],
        speech_comprehension_analysis=analysis["speech_comprehension_analysis"],
        sprachhandlung_analysis=analysis["sprachhandlung_analysis"],
        vocabulary_analysis=analysis["vocabulary_analysis"],
        boredom_analysis=analysis["boredom_analysis"],
        foerderfokus=analysis["foerderfokus"],
        aufgaben=analysis["aufgaben"],
        satzbaubegrenzung=analysis["satzbaubegrenzung"],
        story_id=story_id,
        chapter_id=chapter_id,
        beat_context=None,
        active_beat_ids=active_beat_ids or [],
        num_planned_tasks=num_planned_tasks,
        response_contract=None,
    )


# ---------------------------------------------------------------------------
# Setting extractors — derive report metadata from test inputs, not strings
# ---------------------------------------------------------------------------


def state_to_setting(state: State, criterion: str, strategy: str = "Fixture-based (Strategy A)") -> dict:
    """
    Derive a human-readable test-setting dict from a State object.

    Reads child_profile, messages, story_id and chapter_id directly from the
    state so there is no manual string duplication in the test file.

    Args:
        state:     The State produced by build_state().
        criterion: The judge criterion string used in this test.
        strategy:  Short label for the test strategy (default: Strategy A).

    Returns:
        A dict ready to be passed as ``setting=`` to run_details_recorder.
    """
    import re as _re
    from langchain_core.messages import HumanMessage as _HM

    # ── Parse child_profile free-form string ────────────────────────────────
    # Format: "Das Kind heißt {name}, ist {age} Jahre alt und ist {gender_word}."
    profile = state.get("child_profile", "")
    name_match = _re.search(r"heißt\s+(\S+),", profile)
    age_match  = _re.search(r"ist\s+(\d+)\s+Jahre", profile)
    gender_match = _re.search(r"und ist\s+(.+?)\.", profile)
    child_name   = name_match.group(1)  if name_match   else "?"
    child_age    = age_match.group(1)   if age_match    else "?"
    gender_word  = gender_match.group(1) if gender_match else "?"

    # ── Structured conversation history ─────────────────────────────────────
    # Store as a list of {role, content} dicts so the report renderer can
    # display each turn as its own labelled bubble rather than a flat string.
    messages = state.get("messages", [])
    conversation: list[dict] = [
        {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
        for m in messages
    ]

    return {
        "Child":        f"{child_name}, {child_age} years old, {gender_word}",
        "Strategy":     strategy,
        "Story":        f"{state.get('story_id', '?')} / {state.get('chapter_id', '?')}",
        "Criterion":    criterion,
        # Special key — rendered as a chat transcript by _build_setting_dropdown
        "__messages__": conversation,
    }


def simulation_to_setting(
        child_name: str,
        child_age: int,
        child_gender: str,
        child_inputs: list[str],
        criterion: str,
) -> dict:
    """
    Derive a human-readable test-setting dict for Strategy B (simulated) tests.

    ``child_inputs`` uses the interleaved format expected by
    :func:`simulate_conversation`: alternating child and pre-defined system
    utterances, ending with a child utterance (odd length).  All but the last
    system response are pre-defined in the list; the last system response is
    generated live by the dialog system and captured in the sidecar.

    Args:
        child_name:   Child's first name.
        child_age:    Child's age in years.
        child_gender: "weiblich" or "männlich".
        child_inputs: Conversation script in interleaved format:
                      ``[child_1, system_1, child_2, system_2, …, child_N]``.
        criterion:    The judge criterion string used in this test.

    Returns:
        A dict ready to be passed as ``setting=`` to run_details_recorder.
    """
    gender_label = "female" if child_gender == "weiblich" else "male"
    num_child_turns = (len(child_inputs) + 1) // 2

    # Reconstruct the scripted conversation for display.
    # Elements at even indices are child turns; odd indices are pre-defined
    # system responses.  The final system response is generated live.
    messages: list[dict] = []
    for i, text in enumerate(child_inputs):
        role = "Child" if i % 2 == 0 else "System"
        messages.append({"role": role, "content": text})
    # Indicate that the last system response is generated live.
    messages.append({"role": "System", "content": "(generated live — evaluated by judge)"})

    return {
        "Child":        f"{child_name}, {child_age} years old, {gender_label}",
        "Strategy":     f"Fully simulated (Strategy B) — {num_child_turns} child turns from scratch",
        "Criterion":    criterion,
        "__messages__": messages,
    }


# ---------------------------------------------------------------------------
# N-run helper
# ---------------------------------------------------------------------------


def run_n_times(
        test_fn: Callable[[], tuple[bool, str, str]],
        n: int,
        threshold: float,
        _node_id: str | None = None,
        _sidecar_path: "Path | None" = None,
        _setting: dict | None = None,
) -> None:
    """
    Execute test_fn n times and assert that at least (threshold * n) runs pass.

    test_fn must return either:
      (passed: bool, response_text: str, reason: str)          — Strategy A
      (passed: bool, response_text: str, reason: str,
       conversation: list[dict])                               — Strategy B

    The optional 4th element is a list of ``{role, content}`` dicts
    representing the full conversation that occurred during that run.  When
    present it is stored in the sidecar so the HTML report can show the actual
    turn-by-turn exchange inside each run card.

    When _node_id and _sidecar_path are provided the per-run results are also
    written to a sidecar JSON file so that the HTML report generator can show
    run details for *passing* tests (where pytest stores no longrepr).

    Args:
        test_fn:        Zero-argument callable returning a 3- or 4-tuple.
        n:              Total number of executions.
        threshold:      Required pass rate as a fraction (e.g. 0.80 for 80 %).
        _node_id:       pytest node ID — used as key in the sidecar file.
        _sidecar_path:  Path to the sidecar JSON file that accumulates run details.
        _setting:       Optional dict describing the test setup shown in the HTML report.

    Raises:
        AssertionError: When fewer than (threshold * n) runs pass, including
                        per-run PASS/FAIL verdicts and reasons.
    """
    import json as _json

    raw_results: list[tuple] = [test_fn() for _ in range(n)]
    passes = sum(1 for r in raw_results if r[0])

    # ── Persist run details to sidecar ───────────────────────────────────────
    if _node_id and _sidecar_path:
        try:
            sidecar: dict = {}
            if _sidecar_path.exists():
                sidecar = _json.loads(_sidecar_path.read_text(encoding="utf-8"))

            runs_out = []
            for r in raw_results:
                passed, response_text, reason = r[0], r[1], r[2]
                conversation = list(r[3]) if len(r) >= 4 else []
                runs_out.append({
                    "passed": passed,
                    "response_text": response_text,
                    "reason": reason,
                    "conversation": conversation,
                })

            sidecar[_node_id] = {
                "setting": _setting or {},
                "runs": runs_out,
            }
            _sidecar_path.write_text(
                _json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:  # noqa: BLE001 — never let sidecar I/O break the test
            pass

    if passes / n < threshold:
        details = "\n".join(
            f"  Run {i + 1}: {'PASS' if r[0] else 'FAIL'} — {r[1]} — {r[2]}"
            for i, r in enumerate(raw_results)
        )
        raise AssertionError(
            f"Only {passes}/{n} runs passed "
            f"(required: {threshold * 100:.0f}%)\n{details}"
        )


# ---------------------------------------------------------------------------
# LLM judge helper
# ---------------------------------------------------------------------------

_JUDGE_PROMPT_TEMPLATE = """\
You are a quality judge for a children's dialog system.

Evaluate the following system response against the given criterion.
Reply with ONLY "PASS" or "FAIL" on the first line, followed by a brief reason on the second line.
Do not add any other text.

--- System Response ---
{response_text}

--- Criterion ---
{criterion}

--- Your Verdict (PASS or FAIL + reason) ---"""


def llm_judge(judge_llm_instance, response_text: str, criterion: str) -> tuple[bool, str, str]:
    """
    Evaluate response_text against a natural-language criterion using the judge LLM.

    The judge prompt is always in English for maximum model consistency.
    LangSmith tracing is disabled by default for judge calls to avoid polluting
    traces. Set JUDGE_LANGSMITH_TRACING=true to enable.

    Args:
        judge_llm_instance: Initialised judge LLM (from the judge_llm fixture).
        response_text: The spoken_text produced by the dialog system.
        criterion: English-language criterion the response must satisfy.

    Returns:
        (passed, response_text, reason) where passed is True iff the first line is "PASS".
    """
    from ft_config import JUDGE_LANGSMITH_TRACING

    prompt = _JUDGE_PROMPT_TEMPLATE.format(
        response_text=response_text,
        criterion=criterion,
    )

    if JUDGE_LANGSMITH_TRACING:
        verdict_raw = judge_llm_instance.invoke([HumanMessage(content=prompt)]).content.strip()
    else:
        from langsmith import tracing_context
        with tracing_context(enabled=False):
            verdict_raw = judge_llm_instance.invoke([HumanMessage(content=prompt)]).content.strip()

    lines = verdict_raw.splitlines()
    verdict_line = lines[0].strip().upper() if lines else ""
    reason = lines[1].strip() if len(lines) > 1 else verdict_raw

    passed = verdict_line.startswith("PASS")
    return passed, response_text, reason


# ---------------------------------------------------------------------------
# Strategy B — background graph runner
# ---------------------------------------------------------------------------


def run_background_analysis(
        background_llm_instance,
        child_name: str,
        child_age: int,
        child_gender: str,
        messages: list,
        audio_book: str = FIXTURE_AUDIO_BOOK,
        story_id: str = FIXTURE_STORY_ID,
        chapter_id: str = FIXTURE_CHAPTER_ID,
        num_planned_tasks: int = 5,
) -> dict:
    """
    Run the real ``background_graph`` against a completed conversation turn.

    This mirrors the production flow where the background_graph is triggered
    asynchronously after each immediate_graph turn.  The workers analyse the
    conversation and produce analysis fields (``aufgaben``, ``satzbaubegrenzung``,
    and all intermediate analyses) that are consumed by the *next*
    immediate_graph turn via ``load_analysis``.

    Uses ``create_background_analysis_graph`` directly so the graph topology,
    node order, and LLM bindings are always in sync with the real implementation
    — no manual duplication of the DAG here.

    The background workers call ``get_messages_history_from_immediate_graph_state``
    to fetch the conversation from the immediate graph's LangGraph checkpoint.
    In the test context there is no LangGraph runtime, so we monkey-patch that
    helper to return our in-memory message list instead.

    The ``initialStateLoader`` node would normally load ``audio_book`` and
    ``child_profile`` from DynamoDB/S3.  We bypass it by pre-seeding those
    values directly into the input state, relying on the
    ``background_graph_needs_initial_state`` conditional edge that skips
    ``initialStateLoader`` when both fields are already present.

    Args:
        background_llm_instance: LLM used by the background analysis workers.
        child_name: The child's first name.
        child_age: The child's age in years.
        child_gender: "weiblich" or "männlich".
        messages: Full conversation history *after* the most recent turn
                  (i.e. including the AI reply for that turn).
        audio_book: Story content.
        story_id: Story identifier.
        chapter_id: Chapter identifier.
        num_planned_tasks: Number of story tasks planned for this chapter,
                           forwarded to the beat system (default: 5).

    Returns:
        A dict (BackgroundState-shaped) containing all analysis fields produced
        by the background graph, including ``aufgaben`` and ``satzbaubegrenzung``.
        Pass it directly to :func:`build_state` via the ``background_state``
        parameter.
    """
    from langgraph.checkpoint.memory import MemorySaver
    from background_graph import create_background_analysis_graph
    import nodes as _nodes_module

    # Build child_profile in the same format used by data_loaders.py.
    gender_word = "ein Mädchen" if child_gender == "weiblich" else "ein Junge"
    child_profile = (
        f"Das Kind heißt {child_name}, ist {child_age} Jahre alt und ist {gender_word}."
    )

    # Pre-seed the state so background_graph_needs_initial_state skips
    # initialStateLoader (which would try to hit DynamoDB/S3).
    initial_input = {
        "child_id": "fixture_child",
        "audio_book_id": "fixture_audio_book",
        "child_profile": child_profile,
        "audio_book": audio_book,
        "story_id": story_id,
        "chapter_id": chapter_id,
        "num_planned_tasks": num_planned_tasks,
        # None of the background graph workers read beat_context or active_beat_ids from the state.
        # So seeding them as None / [] is not just acceptable — it 's semantically correct: the background graph genuinely has no use for beat context, and pre-seeding them simply satisfies the TypedDict without influencing any behaviour.
        "beat_context": None,
        "active_beat_ids": [],
    }

    # Patch the helper that workers use to read the conversation history so it
    # returns our in-memory message list rather than a LangGraph checkpoint.
    _original_get_messages = _nodes_module.get_messages_history_from_immediate_graph_state

    def _patched_get_messages(_config):  # noqa: ANN001
        return messages

    _nodes_module.get_messages_history_from_immediate_graph_state = _patched_get_messages

    # Each test run gets its own in-memory checkpointer so state never leaks
    # between invocations.
    _memory = MemorySaver()
    _graph = create_background_analysis_graph(background_llm_instance, _memory)
    _config = {"configurable": {"thread_id": "fixture_bg_thread"}}

    try:
        _graph.invoke(initial_input, _config)
        snapshot = _graph.get_state(_config)
        bg_state: dict = dict(snapshot.values)
    finally:
        # Always restore the original helper to avoid side-effects on other tests.
        _nodes_module.get_messages_history_from_immediate_graph_state = _original_get_messages

    logger.info(
        "run_background_analysis: completed — aufgaben length=%d, satzbaubegrenzung length=%d",
        len(bg_state.get("aufgaben", "")),
        len(bg_state.get("satzbaubegrenzung", "")),
    )

    return bg_state


# ---------------------------------------------------------------------------
# Strategy B — full conversation simulator
# ---------------------------------------------------------------------------


def simulate_conversation(
        system_llm_instance,
        child_name: str,
        child_age: int,
        child_gender: str,
        child_inputs: list[str],
        audio_book: str = FIXTURE_AUDIO_BOOK,
        story_id: str = FIXTURE_STORY_ID,
        chapter_id: str = FIXTURE_CHAPTER_ID,
        run_background: bool = True,
        run_background_only_before_last: bool = True,
        background_llm_instance=None,
        num_planned_tasks: int = 5,
) -> tuple[State, str]:
    """
    Run a full conversation from scratch using real LLMs (Strategy B).

    **Conversation format (``child_inputs``):**

    The list defines the *full* conversation script — alternating child and
    system turns — with the system responses pre-fixed for every turn except
    the last.  The last element is **always a child utterance**; the system's
    response to it is what gets produced live and evaluated by the judge.

    Expected structure::

        [
            child_turn_1,   # str  — child utterance
            system_turn_1,  # str  — pre-defined system response
            child_turn_2,   # str  — child utterance
            system_turn_2,  # str  — pre-defined system response
            ...
            child_turn_N,   # str  — last child utterance  ← tested turn
        ]

    So an odd-length list means N child turns and N-1 pre-defined system
    turns.  The list must have an odd length (at least 1).

    This guarantees:

    * The conversation history fed into the final turn is fully deterministic
      and always makes sense — earlier system responses are authored, not
      randomly generated.
    * Only ``masterChatbot`` (immediate_graph) is called on the **last** child
      turn, making evaluation stable.

    **Background analysis (``run_background`` / ``run_background_only_before_last``):**

    * ``run_background=False`` — background analysis is never run (fast, less realistic).
    * ``run_background=True, run_background_only_before_last=True`` (default) —
      background analysis is run **only after the second-to-last child turn**
      (i.e. once, to populate the analysis fields used by the final turn).
    * ``run_background=True, run_background_only_before_last=False`` —
      background analysis is run after **every** child turn, mirroring full
      production behaviour.

    Args:
        system_llm_instance: Real LLM for the dialog system under test.
        child_name: The child's first name.
        child_age: The child's age in years.
        child_gender: "weiblich" or "männlich".
        child_inputs: Conversation script as described above.  Odd-length list
                      of alternating child and system utterances, ending with a
                      child utterance.  Minimum length: 1.
        audio_book: Story content (defaults to the Mia und Leo fixture).
        story_id: Story identifier.
        chapter_id: Chapter identifier.
        run_background: When True (default) the real background graph is run
                        to produce analysis fields.  Controlled further by
                        ``run_background_only_before_last``.
        run_background_only_before_last: When True (default) background analysis
                        is run only after the second-to-last child turn — the
                        one whose analysis actually influences the final system
                        response.  Set to False together with ``run_background``
                        to run background analysis after *every* turn.
        background_llm_instance: LLM used for the background workers.  Falls
                                  back to ``system_llm_instance`` when None.
        num_planned_tasks: Number of story tasks planned for this chapter,
                           forwarded to the beat system in both the immediate
                           and background graphs (default: 5).

    Returns:
        (final_state, spoken_text) where final_state is the State after the
        last turn and spoken_text is the system's response to the last child
        input.

    Raises:
        ValueError: If ``child_inputs`` has an even length (meaning it would
                    end on a system turn rather than a child turn).
    """
    from nodes import masterChatbot

    if len(child_inputs) % 2 == 0:
        raise ValueError(
            "child_inputs must have an odd length: alternating child/system utterances "
            "ending with a child utterance.  "
            f"Got {len(child_inputs)} elements (even)."
        )

    _bg_llm = background_llm_instance if background_llm_instance is not None else system_llm_instance

    # ---------------------------------------------------------------------------
    # Parse child_inputs into structured turns.
    #
    # child_inputs layout (0-based indices):
    #   0        → child turn 1
    #   1        → system turn 1  (pre-defined)
    #   2        → child turn 2
    #   3        → system turn 2  (pre-defined)
    #   ...
    #   N-1      → last child turn  (tested — system response generated live)
    #
    # child_turns  = elements at even indices: child_inputs[0], [2], [4], …
    # system_turns = elements at odd  indices: child_inputs[1], [3], [5], …
    #                (one fewer than child_turns)
    # ---------------------------------------------------------------------------
    child_turns: list[str] = child_inputs[0::2]
    system_turns: list[str] = child_inputs[1::2]  # pre-defined system responses

    total_child_turns = len(child_turns)
    # Index (0-based) of the second-to-last child turn, i.e. the last turn
    # after which background analysis is relevant.  -1 means there is only one
    # child turn and no background is needed.
    before_last_child_index = total_child_turns - 2

    accumulated_messages: list = []
    result: dict = {}
    spoken_text: str = ""

    # Full BackgroundState snapshot from the previous background run.
    # None on the first turn — build_state will default all analysis fields to "".
    current_background_state: dict | None = None

    for turn_index, child_input in enumerate(child_turns):
        is_last_turn = turn_index == total_child_turns - 1

        # Append the child's utterance.
        accumulated_messages = list(accumulated_messages) + [HumanMessage(content=child_input)]

        if is_last_turn:
            # ── Final turn: run the immediate_graph (masterChatbot) live ────
            turn_state = build_state(
                child_name=child_name,
                child_age=child_age,
                child_gender=child_gender,
                messages=accumulated_messages,
                audio_book=audio_book,
                story_id=story_id,
                chapter_id=chapter_id,
                background_state=current_background_state,
                num_planned_tasks=num_planned_tasks,
            )

            result = masterChatbot(turn_state, system_llm_instance)
            ai_messages = result.get("messages", [])

            if ai_messages:
                ai_message = ai_messages[-1]
                spoken_text = ai_message.content
                accumulated_messages = accumulated_messages + [ai_message]

            logger.info(
                "simulate_conversation: final turn %d/%d completed (immediate_graph)",
                turn_index + 1,
                total_child_turns,
            )
        else:
            # ── Intermediate turn: use the pre-defined system response ───────
            system_response = system_turns[turn_index]
            ai_message = AIMessage(content=system_response)
            accumulated_messages = accumulated_messages + [ai_message]
            spoken_text = system_response

            logger.info(
                "simulate_conversation: turn %d/%d — using pre-defined system response",
                turn_index + 1,
                total_child_turns,
            )

            # ── Background analysis after this intermediate turn ─────────────
            # Determine whether to run background for this turn:
            #   • run_background must be True
            #   • Either run_background_only_before_last is False (run every turn),
            #     or this is the second-to-last child turn (before_last_child_index).
            should_run_bg = run_background and (
                not run_background_only_before_last
                or turn_index == before_last_child_index
            )

            if should_run_bg:
                logger.info(
                    "simulate_conversation: running background analysis after turn %d/%d",
                    turn_index + 1,
                    total_child_turns,
                )
                current_background_state = run_background_analysis(
                    background_llm_instance=_bg_llm,
                    child_name=child_name,
                    child_age=child_age,
                    child_gender=child_gender,
                    messages=accumulated_messages,
                    audio_book=audio_book,
                    story_id=story_id,
                    chapter_id=chapter_id,
                    num_planned_tasks=num_planned_tasks,
                )

    final_state = build_state(
        child_name=child_name,
        child_age=child_age,
        child_gender=child_gender,
        messages=accumulated_messages,
        audio_book=audio_book,
        story_id=story_id,
        chapter_id=chapter_id,
        background_state=current_background_state,
        num_planned_tasks=num_planned_tasks,
    )
    if result.get("response_contract"):
        final_state["response_contract"] = result["response_contract"]  # type: ignore[index]

    return final_state, spoken_text
