"""
Feature: Korrektives Feedback (Corrective Feedback)
Test file: When the child makes a grammatical error, the system should
repeat the sentence correctly in its next response (modeling correct form)
without explicitly correcting the child. If the child's sentence is correct,
no repetition is needed.

Strategy A only — fixture-based (fast, reproducible).
Corrective feedback is observable from a single system response.

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from feature_testing_utils import (
    build_state_with_beats,
    llm_judge,
    state_to_setting,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_STORY_ID,
    FIXTURE_PIA_CHAPTER_ID,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_CORRECTIVE_MODELING = (
    "The child made a grammatical error in German: '{child_utterance}'. "
    "The correct form would be something like: '{correct_form}'. "
    "Does the system's response naturally include the correct form of what the child said? "
    "The correction should be implicit — the system repeats the child's idea in correct German "
    "as part of its natural response (corrective modeling), without saying 'that's wrong' or "
    "'you should say...'. "
    "Return PASS if the system naturally models the correct form in its response, "
    "FAIL if the system ignores the error entirely or corrects it explicitly/critically."
)

CRITERION_NO_CORRECTION_WHEN_CORRECT = (
    "The child said a grammatically correct sentence: '{child_utterance}'. "
    "Does the system respond naturally without unnecessarily repeating or correcting the child's sentence? "
    "The system should confirm and continue, not echo the sentence back as if modeling. "
    "Return PASS if the system responds naturally, "
    "FAIL if the system unnecessarily repeats the child's correct sentence as if correcting it."
)

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestCorrectiveFeedbackFixtureBased:
    """Strategy A: Verify corrective feedback modeling behavior."""

    def test_models_correct_form_missing_verb(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'sie froh' (missing verb 'ist').
        System should model correct form: 'Pia ist froh'.
        """
        state = build_state_with_beats(
            child_name="Lena",
            child_age=5,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Lena! Pia macht immer alles richtig. Meinst du, Pia ist traurig oder froh?"),
                HumanMessage(content="sie froh"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_CORRECTIVE_MODELING.format(
            child_utterance="sie froh",
            correct_form="Pia ist froh",
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))

    def test_models_correct_form_missing_preposition(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'Pia geht Schule' (missing preposition 'in die').
        System should model: 'Pia geht in die Schule'.
        """
        state = build_state_with_beats(
            child_name="Finn",
            child_age=8,
            child_gender="männlich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Finn! Pia geht jetzt los. Wohin geht Pia?"),
                HumanMessage(content="Pia geht Schule"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_CORRECTIVE_MODELING.format(
            child_utterance="Pia geht Schule",
            correct_form="Pia geht in die Schule",
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))

    def test_models_correct_form_perfekt_error(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'Pia hat Eier fallen' (incorrect Perfekt form).
        System should model: 'Pia hat die Eier fast fallen lassen'.
        """
        state = build_state_with_beats(
            child_name="Lena",
            child_age=5,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Lena! Was ist beim Backen passiert?"),
                HumanMessage(content="Pia hat Eier fallen"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_CORRECTIVE_MODELING.format(
            child_utterance="Pia hat Eier fallen",
            correct_form="Pia hat die Eier fast fallen lassen",
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))

    def test_no_correction_when_correct(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says a correct sentence 'Pia ist froh'.
        System should NOT echo/repeat it as if correcting.
        """
        state = build_state_with_beats(
            child_name="Mila",
            child_age=7,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Mila! Meinst du, Pia ist traurig oder froh?"),
                HumanMessage(content="Pia ist froh"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_NO_CORRECTION_WHEN_CORRECT.format(
            child_utterance="Pia ist froh",
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))