"""
Feature: No Repeat Prompts ("keine Aufforderung zum Wiederholen geben")
Test file: The system must not ask the child to repeat words or sentences.
           It should confirm answers and move on, not do mechanical drills.

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

SCRIPT_BROKKOLI_ANSWER = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia gibt ihrem Hamster Hubert Brokkoli.'
    ' Was frisst Hubert gern?',
    'Brokkoli',
]

SCRIPT_MARMELADE_ANSWER = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia schmiert ein Brot mit Marmelade und'
    ' Erdnussbutter. Was kommt auf das Brot?',
    'Marmelade',
]

SCRIPT_SCHULE_ANSWER = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia geht zur Schule. Wohin geht Pia?',
    'Schule',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NO_REPEAT_REQUEST = (
    "The child correctly answered the question. Does the system response "
    "confirm the answer and continue the conversation WITHOUT asking the "
    "child to repeat the word (e.g. 'Sag das nochmal', 'Kannst du das "
    "wiederholen?', 'Sag mal: ...')? "
    "Return PASS if the system confirms and moves on without any repeat "
    "request, FAIL if it asks the child to say the word again."
)

CRITERION_NO_DRILL = (
    "The child answered correctly. Does the system response confirm and "
    "move forward WITHOUT turning the exchange into a mechanical drill "
    "(e.g. 'Sag den ganzen Satz', 'Wiederhole: ...', or asking the child "
    "to say back what was just said)? "
    "Return PASS if the system confirms naturally and continues, "
    "FAIL if it creates a repetition exercise."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestNoRepeatPromptsFixtureBased:
    """Strategy A: Verify the system does not ask the child to repeat words."""

    def test_no_repeat_brokkoli(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child says 'Brokkoli'. System should confirm and
        continue, not ask child to repeat.
        """
        state = build_state(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BROKKOLI_ANSWER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_REPEAT_REQUEST)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_REPEAT_REQUEST),
        )

    def test_no_drill_marmelade(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child says 'Marmelade'. System should confirm and
        continue, not create a repetition exercise.
        """
        state = build_state(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_MARMELADE_ANSWER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_DRILL)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_DRILL),
        )

    def test_no_drill_schule(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child says 'Schule'. System should confirm and
        continue, no mechanical repetition.
        """
        state = build_state(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SCHULE_ANSWER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_DRILL)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_DRILL),
        )
