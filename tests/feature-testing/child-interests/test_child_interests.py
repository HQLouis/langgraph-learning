"""
Feature: Child Interests ("Auf Interessen des Kindes eingehen")
Test file: The system should briefly connect story content to the child's
           life, then return to the story. Max 2-3 sentences on the personal
           topic before steering back.

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

SCRIPT_BREAD_INTEREST = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia schmiert auf ein Brot Marmelade.'
    ' Was isst du gern auf deinem Brot?',
    'K\u00e4se',
]

SCRIPT_BAKING_INTEREST = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia backt mit ihren Freundinnen.'
    ' Magst du auch backen?',
    'Ja',
]

SCRIPT_SCHOOL_INTEREST = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia geht zur Schule.'
    ' Gehst du auch gern zur Schule?',
    'Nein',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_CONNECT_AND_RETURN = (
    "The child said 'K\u00e4se' when asked about bread toppings. "
    "Does the system response: "
    "(1) briefly acknowledge the child's answer (e.g. 'K\u00e4se ist lecker!'), AND "
    "(2) return to the story within the same response (e.g. ask about what "
    "Pia puts on her bread)? "
    "The personal comment should be short (1-2 sentences max). "
    "Return PASS if the system connects briefly to the child's interest "
    "and returns to the story, FAIL if it stays on the personal topic "
    "too long or ignores the child's answer."
)

CRITERION_INTEREST_THEN_STORY = (
    "The child said 'Ja' when asked about baking. Does the system response: "
    "(1) show interest in the child's answer (ask a brief follow-up about "
    "the child's baking experience or preference), AND "
    "(2) steer back to the story within 2-3 sentences? "
    "Return PASS if the system shows interest and returns to the story, "
    "FAIL if it abandons the story topic or ignores the child's interest."
)

CRITERION_TAKE_SERIOUSLY_AND_RETURN = (
    "The child said 'Nein' when asked if they like school. "
    "Does the system response: "
    "(1) take the child's answer seriously (not dismiss it), AND "
    "(2) briefly exchange about it, then return to the story? "
    "Return PASS if the system respects the 'Nein' and returns to the story, "
    "FAIL if it dismisses the answer or stays on the personal topic too long."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestChildInterestsFixtureBased:
    """Strategy A: Verify the system engages with child interests and returns to story."""

    def test_bread_interest(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child says 'Käse' for bread topping. System should
        acknowledge briefly and return to story.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BREAD_INTEREST),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CONNECT_AND_RETURN)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CONNECT_AND_RETURN),
        )

    def test_baking_interest(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child says 'Ja' to baking. System should show interest
        then return to story.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BAKING_INTEREST),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_INTEREST_THEN_STORY)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_INTEREST_THEN_STORY),
        )

    def test_school_negative_answer(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child says 'Nein' to school. System should take it
        seriously, briefly exchange, and return to story.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SCHOOL_INTEREST),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_TAKE_SERIOUSLY_AND_RETURN)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_TAKE_SERIOUSLY_AND_RETURN),
        )
