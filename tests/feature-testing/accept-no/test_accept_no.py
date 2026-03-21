"""
Feature: Accept No ("nicht auf eigenen Sachen beharren / 'Nein' akzeptieren")
Test file: When the child says "Nein" or declines, the system must accept it
           and continue the conversation — not insist or repeat the question.

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
    build_state,
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

SCRIPT_DECLINE_TO_ANSWER = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' M\u00f6chtest du sagen, was Pia macht?',
    'Nein',
]

SCRIPT_DECLINE_TO_ELABORATE = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia hat morgens viele Sachen gemacht.'
    ' M\u00f6chtest du dar\u00fcber mehr erz\u00e4hlen?',
    'Nein',
]

SCRIPT_DOESNT_KNOW = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia f\u00fcttert ihren Hamster Hubert.'
    ' Wei\u00dft du das noch?',
    'Nein',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_ACCEPT_AND_CONTINUE = (
    "The child said 'Nein' when asked if they want to say what Pia does. "
    "Does the system response: "
    "(1) accept the 'Nein' without insisting or repeating the question, AND "
    "(2) continue the conversation by providing the answer itself or "
    "offering a different question? "
    "Return PASS if the system accepts 'Nein' and moves forward, "
    "FAIL if it insists, repeats the question, or pressures the child."
)

CRITERION_ACCEPT_AND_OFFER_SOLUTION = (
    "The child said 'Nein' when asked to elaborate. Does the system response: "
    "(1) briefly confirm it accepts the child's decision, AND "
    "(2) offer its own suggestion or continue the story? "
    "Return PASS if the system accepts and offers an alternative, "
    "FAIL if it insists the child elaborate or repeats the question."
)

CRITERION_HELP_AFTER_NO = (
    "The child said 'Nein' when asked if they remember. Does the system "
    "response: "
    "(1) accept that the child doesn't know, AND "
    "(2) offer a short help (provide the answer or a hint)? "
    "Return PASS if the system helps after accepting, "
    "FAIL if it insists the child try harder or repeats the question."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestAcceptNoFixtureBased:
    """Strategy A: Verify the system accepts 'Nein' and continues."""

    def test_accept_decline_to_answer(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child declines to answer. System should accept and
        provide the answer itself.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DECLINE_TO_ANSWER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_ACCEPT_AND_CONTINUE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_ACCEPT_AND_CONTINUE),
        )

    def test_accept_decline_to_elaborate(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child declines to elaborate. System should accept
        and offer its own continuation.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DECLINE_TO_ELABORATE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_ACCEPT_AND_OFFER_SOLUTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_ACCEPT_AND_OFFER_SOLUTION),
        )

    def test_help_after_doesnt_know(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child doesn't remember. System should accept and
        offer a short help.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DOESNT_KNOW),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_HELP_AFTER_NO)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_HELP_AFTER_NO),
        )
