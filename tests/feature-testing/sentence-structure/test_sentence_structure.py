"""
Feature: Sentence Structure ("Satzbau berücksichtigen")
Test file: The system should adapt its sentence structure to match the child's
           language level. Use simple sentences, model correct grammar, and
           only extend complexity when the child shows readiness.

Story used:
  - "Pia muss nicht perfekt sein"

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from feature_testing_utils import (
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_CHAPTER_ID,
    FIXTURE_PIA_STORY_ID,
    build_state_with_beats,
    llm_judge,
    state_to_setting,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _script_to_messages(script: list[str]) -> list:
    messages = []
    for i, text in enumerate(script):
        if i % 2 == 0:
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))
    return messages


# ---------------------------------------------------------------------------
# Conversation scripts
# ---------------------------------------------------------------------------

# Example 1: Child uses very simple language ("Marmelade drauf").
# System should model correct grammar simply.
SCRIPT_SIMPLE_CHILD = [
    'hallo',
    'Hallo! Ich bin Thilio. Was macht Pia mit dem Brot?',
    'Marmelade drauf',
]

# Example 2: Child uses simple structure ("Pia geht Schule").
# System should model correct form and add small extension.
SCRIPT_MISSING_PREPOSITION = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia geht jetzt los. Wohin geht Pia?',
    'Pia geht Schule',
]

# Example 3: Child uses "und" connective ("Pia macht Brot und geht Schule").
# System should mirror the connective level, not introduce complex ones.
SCRIPT_SIMPLE_CONNECTIVE = [
    'hallo',
    'Hallo! Ich bin Thilio. Was macht Pia am Morgen?',
    'Pia macht Brot und geht Schule',
]

# Example 4: Child uses Perfekt with errors ("Pia hat Eier fallen").
# System should model correct Perfekt without over-complicating.
SCRIPT_PERFEKT_ERROR = [
    'hallo',
    'Hallo! Ich bin Thilio. Was ist beim Backen passiert?',
    'Pia hat Eier fallen',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_SIMPLE_MODELLING = (
    "The child said 'Marmelade drauf' — a very simple, incomplete sentence. "
    "Does the system response: "
    "(1) model the correct sentence form (e.g. 'Pia macht Marmelade auf "
    "das Brot'), AND "
    "(2) keep its own sentences short and simple, matching the child's "
    "level — no complex subordinate clauses or abstract language? "
    "Return PASS if the system models correct grammar in simple sentences, "
    "FAIL if it uses complex structures that exceed the child's level."
)

CRITERION_GENTLE_CORRECTION_SIMPLE = (
    "The child said 'Pia geht Schule' — missing the preposition 'in die'. "
    "Does the system response: "
    "(1) model the correct form naturally (e.g. 'Pia geht in die Schule'), AND "
    "(2) optionally add a small content extension (e.g. 'Dort trifft sie "
    "ihre Freundinnen'), AND "
    "(3) NOT use complex sentence structures or introduce too many new "
    "details at once? "
    "Return PASS if the system models correct grammar simply and doesn't "
    "overwhelm, FAIL if it uses overly complex language."
)

CRITERION_MATCH_CONNECTIVE_LEVEL = (
    "The child said 'Pia macht Brot und geht Schule' — using 'und' as a "
    "connector. Does the system response: "
    "(1) use simple connectives like 'und' or 'dann' if connecting ideas, AND "
    "(2) NOT use complex connectives like 'weil', 'obwohl', 'damit' that "
    "exceed the child's demonstrated language level? "
    "Return PASS if the system matches the child's connective level, "
    "FAIL if it introduces complex connectives the child hasn't used."
)

CRITERION_CORRECT_PERFEKT = (
    "The child said 'Pia hat Eier fallen' — attempting Perfekt tense with "
    "errors. Does the system response: "
    "(1) model the correct Perfekt form naturally (e.g. 'Pia hat die Eier "
    "fast fallen lassen'), AND "
    "(2) NOT use complex tenses or nested clauses beyond the child's level? "
    "Return PASS if the system models correct Perfekt simply, "
    "FAIL if it uses overly complex grammar."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestSentenceStructureFixtureBased:
    """Strategy A: Verify the system adapts sentence structure to child's level."""

    def test_simple_modelling(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child says 'Marmelade drauf'. System should model
        correct grammar in simple sentences.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SIMPLE_CHILD),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SIMPLE_MODELLING)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SIMPLE_MODELLING),
        )

    def test_missing_preposition(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child says 'Pia geht Schule'. System should model
        correct form with preposition and add small extension.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_MISSING_PREPOSITION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENTLE_CORRECTION_SIMPLE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GENTLE_CORRECTION_SIMPLE),
        )

    def test_match_connective_level(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child uses 'und' connector. System should match
        connective level, not use 'weil'/'obwohl'.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SIMPLE_CONNECTIVE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_MATCH_CONNECTIVE_LEVEL)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_MATCH_CONNECTIVE_LEVEL),
        )

    def test_correct_perfekt(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 4: Child uses broken Perfekt ('Pia hat Eier fallen').
        System should model correct Perfekt simply.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_PERFEKT_ERROR),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CORRECT_PERFEKT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CORRECT_PERFEKT),
        )
