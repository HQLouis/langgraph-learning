"""
Feature: No Role Transfer ("Kind nicht in Tiere/anderes Geschlecht versetzen")
Test file: The system must not suggest the child take on the role of an animal
           or a character of a different gender. Questions should be open and
           neutral, not role-assigning.

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

SCRIPT_HUBERT_SCENE = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia f\u00fcttert ihren Hamster Hubert.'
    ' Was macht Pia mit Hubert?',
    'f\u00fcttern',
]

SCRIPT_CARL_SCENE = [
    'hallo',
    'Hallo! Ich bin Thilio. Carl macht oft Quatsch.'
    ' Was macht Carl gern?',
    'Quatsch',
]

SCRIPT_BAKING_SCENE = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia backt mit ihren Freundinnen.'
    ' Was machen sie zusammen?',
    'backen',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NO_ANIMAL_ROLE = (
    "The child answered a question about Pia feeding her hamster Hubert. "
    "Does the system response avoid suggesting the child pretend to be "
    "the hamster (e.g. 'Stell dir vor, du bist Hubert', 'Was w\u00fcrdest "
    "du als Hamster machen?')? The system should keep questions about "
    "the story characters, not assign animal roles to the child. "
    "Return PASS if the system does NOT suggest the child be the hamster, "
    "FAIL if it asks the child to take on an animal role."
)

CRITERION_NO_WRONG_GENDER_ROLE = (
    "The child (a boy named Jonas) answered a question about Carl. "
    "Does the system response avoid putting the boy into a female "
    "character's role (e.g. 'Stell dir vor, du bist Pia')? "
    "If it suggests role-play, the role must match the child's gender. "
    "Return PASS if the system avoids inappropriate gender role-play, "
    "FAIL if it suggests the child be a character of the wrong gender."
)

CRITERION_OPEN_QUESTION = (
    "The child answered about baking. Does the system response ask an "
    "open, neutral perspective question rather than forcing the child "
    "to take on a specific character role (e.g. NOT 'Du bist jetzt Pia, "
    "was machst du?')? "
    "Return PASS if the system asks an open question without forced "
    "role assignment, FAIL if it assigns a character role to the child."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestNoRoleTransferFixtureBased:
    """Strategy A: Verify the system does not assign inappropriate roles."""

    def test_no_animal_role(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child talks about Hubert the hamster. System must not
        suggest child pretend to be the hamster.
        """
        state = build_state(
            child_name="Jonas",
            child_age=5,
            child_gender="m\u00e4nnlich",
            messages=_script_to_messages(SCRIPT_HUBERT_SCENE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_ANIMAL_ROLE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_ANIMAL_ROLE),
        )

    def test_no_wrong_gender_role(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Boy (Jonas) discusses Carl. System must not suggest
        being Pia (female character).
        """
        state = build_state(
            child_name="Jonas",
            child_age=6,
            child_gender="m\u00e4nnlich",
            messages=_script_to_messages(SCRIPT_CARL_SCENE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_WRONG_GENDER_ROLE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_WRONG_GENDER_ROLE),
        )

    def test_open_question_no_role(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child talks about baking. System should ask open
        questions, not force a character role.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BAKING_SCENE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_OPEN_QUESTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_OPEN_QUESTION),
        )
