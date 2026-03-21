"""
Feature: Make Suggestions ("eigenen Vorschlag machen")
Test file: The system should make clear suggestions to support the child's
           thinking, and then follow through by working on it together.

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

# Example 1: System suggests thinking about baking ingredients together.
SCRIPT_BAKING_SUGGESTION = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia backt Muffins.'
    ' Was braucht man zum Backen?',
    'wei\u00df nicht',
]

# Example 2: System offers part of the solution and involves the child.
SCRIPT_HAMSTER_FOOD_SUGGESTION = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia f\u00fcttert Hubert.'
    ' Frisst Hubert Brokkoli oder Marmelade?',
    'Brokkoli',
    'Ja, Hubert frisst gern Brokkoli.'
    ' M\u00f6chtest du mit mir \u00fcberlegen, was Hamster noch gerne essen?',
    'Ja',
]

# Example 3: System suggests thinking together about what happens next.
SCRIPT_EGGS_SUGGESTION = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia stolpert mit den Eiern.'
    ' Sollen wir zusammen \u00fcberlegen:'
    ' Was kann passieren \u2013 fallen die Eier auf den Boden'
    ' oder f\u00e4ngt Pia die Eier noch?',
    'f\u00e4ngt',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_CLEAR_SUGGESTION = (
    "The child said 'wei\u00df nicht' when asked about baking ingredients. "
    "Does the system response: "
    "(1) make a clear suggestion to help the child think (e.g. propose "
    "thinking together, give a concrete hint like 'Eier oder Schuhe?'), AND "
    "(2) keep the suggestion simple and concrete so the child can engage? "
    "Return PASS if the system makes a helpful, concrete suggestion, "
    "FAIL if it just repeats the question, gives the answer without "
    "involving the child, or provides no support."
)

CRITERION_OFFER_PART_AND_INVOLVE = (
    "The child agreed to think together about what hamsters eat. "
    "Does the system response: "
    "(1) offer part of the answer itself (e.g. 'Hamster essen gerne "
    "Karotten'), AND "
    "(2) actively involve the child by asking what else hamsters might eat? "
    "Return PASS if the system shares knowledge AND asks the child to "
    "contribute, FAIL if it just gives a complete answer or asks without "
    "offering its own input first."
)

CRITERION_COLLABORATIVE_THINKING = (
    "The child answered 'f\u00e4ngt' to the suggestion about the eggs. "
    "Does the system response: "
    "(1) confirm the child's answer positively, AND "
    "(2) continue in a collaborative, encouraging tone? "
    "Return PASS if the system confirms and stays encouraging, "
    "FAIL if it is dismissive or overly didactic."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestMakeSuggestionsFixtureBased:
    """Strategy A: Verify the system makes helpful suggestions."""

    def test_clear_suggestion_on_uncertainty(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child says 'weiß nicht' about baking. System should
        make a clear, concrete suggestion to support thinking.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BAKING_SUGGESTION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CLEAR_SUGGESTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CLEAR_SUGGESTION),
        )

    def test_offer_part_and_involve(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child agrees to think together. System should share
        part of the answer and ask child to contribute.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_HAMSTER_FOOD_SUGGESTION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_OFFER_PART_AND_INVOLVE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_OFFER_PART_AND_INVOLVE),
        )

    def test_collaborative_thinking(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child answers the collaborative question. System should
        confirm positively and stay encouraging.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_EGGS_SUGGESTION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_COLLABORATIVE_THINKING)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_COLLABORATIVE_THINKING),
        )
