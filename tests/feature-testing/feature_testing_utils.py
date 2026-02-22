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

from states import State

logger = logging.getLogger(__name__)

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
        satzbaubegrenzung: Sentence structure constraints (empty = none active).
        story_id: Story identifier for the beat system.
        chapter_id: Chapter identifier for the beat system.
        active_beat_ids: Beat IDs currently in scope (None = empty list).

    Returns:
        A fully-populated State TypedDict ready for use with masterChatbot().
    """
    gender_word = "ein Mädchen" if child_gender == "weiblich" else "ein Junge"
    child_profile = (
        f"Das Kind heißt {child_name}, ist {child_age} Jahre alt und ist {gender_word}."
    )

    return State(
        child_id="fixture_child",
        audio_book_id="fixture_audio_book",
        child_profile=child_profile,
        audio_book=audio_book,
        messages=messages,
        grammar_analysis="",
        speech_comprehension_analysis="",
        sprachhandlung_analysis="",
        vocabulary_analysis="",
        boredom_analysis="",
        foerderfokus="",
        aufgaben=aufgaben,
        satzbaubegrenzung=satzbaubegrenzung,
        story_id=story_id,
        chapter_id=chapter_id,
        beat_context=None,
        active_beat_ids=active_beat_ids or [],
        num_planned_tasks=5,
        response_contract=None,
    )


# ---------------------------------------------------------------------------
# N-run helper
# ---------------------------------------------------------------------------


def run_n_times(
    test_fn: Callable[[], tuple[bool, str]],
    n: int,
    threshold: float,
) -> None:
    """
    Execute test_fn n times and assert that at least (threshold * n) runs pass.

    test_fn must return a (passed: bool, reason: str) tuple so that failure
    details can be included in the assertion message.

    Args:
        test_fn: Zero-argument callable returning (passed, reason).
        n: Total number of executions.
        threshold: Required pass rate as a fraction (e.g. 0.80 for 80 %).

    Raises:
        AssertionError: When fewer than (threshold * n) runs pass, including
                        per-run PASS/FAIL verdicts and reasons.
    """
    results: list[tuple[bool, str]] = [test_fn() for _ in range(n)]
    passes = sum(1 for passed, _ in results if passed)

    if passes / n < threshold:
        details = "\n".join(
            f"  Run {i + 1}: {'PASS' if passed else 'FAIL'} — {reason}"
            for i, (passed, reason) in enumerate(results)
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


def llm_judge(judge_llm_instance, response_text: str, criterion: str) -> tuple[bool, str]:
    """
    Evaluate response_text against a natural-language criterion using the judge LLM.

    The judge prompt is always in English for maximum model consistency.

    Args:
        judge_llm_instance: Initialised judge LLM (from the judge_llm fixture).
        response_text: The spoken_text produced by the dialog system.
        criterion: English-language criterion the response must satisfy.

    Returns:
        (passed, reason) where passed is True iff the first line is "PASS".
    """
    prompt = _JUDGE_PROMPT_TEMPLATE.format(
        response_text=response_text,
        criterion=criterion,
    )
    verdict_raw = judge_llm_instance.invoke([HumanMessage(content=prompt)]).content.strip()

    lines = verdict_raw.splitlines()
    verdict_line = lines[0].strip().upper() if lines else ""
    reason = lines[1].strip() if len(lines) > 1 else verdict_raw

    passed = verdict_line.startswith("PASS")
    return passed, reason


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
) -> tuple[State, str]:
    """
    Run a full conversation from scratch using real LLMs (Strategy B).

    The human side of the conversation is driven by the hardcoded child_inputs
    list to keep simulations as reproducible as possible despite the LLM's
    non-determinism on the system side.

    Args:
        system_llm_instance: Real LLM for the dialog system under test.
        child_name: The child's first name.
        child_age: The child's age in years.
        child_gender: "weiblich" or "männlich".
        child_inputs: Hardcoded child utterances, one per turn.
                      The last entry is the input for the turn being tested.
        audio_book: Story content (defaults to the Mia und Leo fixture).
        story_id: Story identifier.
        chapter_id: Chapter identifier.

    Returns:
        (final_state, spoken_text) where final_state is the State after the
        last turn and spoken_text is the system's response to the last input.
    """
    from nodes import masterChatbot

    accumulated_messages: list = []
    result: dict = {}
    spoken_text: str = ""

    for turn_index, child_input in enumerate(child_inputs):
        accumulated_messages = list(accumulated_messages) + [HumanMessage(content=child_input)]

        turn_state = build_state(
            child_name=child_name,
            child_age=child_age,
            child_gender=child_gender,
            messages=accumulated_messages,
            audio_book=audio_book,
            story_id=story_id,
            chapter_id=chapter_id,
        )

        result = masterChatbot(turn_state, system_llm_instance)
        ai_messages = result.get("messages", [])

        if ai_messages:
            ai_message = ai_messages[-1]
            spoken_text = ai_message.content
            accumulated_messages = accumulated_messages + [ai_message]

        logger.info(
            "simulate_conversation: turn %d/%d completed",
            turn_index + 1,
            len(child_inputs),
        )

    final_state = build_state(
        child_name=child_name,
        child_age=child_age,
        child_gender=child_gender,
        messages=accumulated_messages,
        audio_book=audio_book,
        story_id=story_id,
        chapter_id=chapter_id,
    )
    if result.get("response_contract"):
        final_state["response_contract"] = result["response_contract"]  # type: ignore[index]

    return final_state, spoken_text

