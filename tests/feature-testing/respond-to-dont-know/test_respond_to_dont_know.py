"""
Feature: Reagieren auf "weiß nicht" (Respond to "I don't know")
Test file: When the child says "weiß nicht", the system should clarify what
the child doesn't know, offer a brief hint, optionally connect to the child's
life, then return to the story. Must NOT respond with "bist du gespannt" or
"bist du neugierig". Must NOT use abstract/complex explanations.

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible)
  Strategy B — fully simulated (realistic, end-to-end)

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage, AIMessage

from feature_testing_utils import (
    build_state_with_beats,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_STORY_ID,
    FIXTURE_PIA_CHAPTER_ID,
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_STORY_ID,
    FIXTURE_BOBO_CHAPTER_ID,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_DONT_KNOW_HELP = (
    "The child said 'weiß nicht' (I don't know). "
    "Does the system: (1) briefly clarify what the child doesn't know, "
    "(2) offer a short hint or give the answer, and "
    "(3) continue the conversation naturally (e.g. connect to the child's experience or move to the next story point)? "
    "The system must NOT say 'bist du gespannt' or 'bist du neugierig'. "
    "The system must NOT use complex or abstract explanations. "
    "Return PASS if the system helps with a brief hint and moves on naturally, "
    "FAIL if it ignores the 'weiß nicht', uses forbidden phrases, or gives an overly complex explanation."
)

CRITERION_DONT_KNOW_SIMPLE_EXPLANATION = (
    "The child said 'weiß nicht' in response to a word meaning question. "
    "Does the system explain the word in simple, concrete language that a young child can understand? "
    "The explanation should be short (1-2 sentences max) and use everyday comparisons or examples. "
    "Return PASS if the explanation is simple and child-friendly, "
    "FAIL if it uses abstract language or is overly complex."
)

CRITERION_DONT_KNOW_NO_FORBIDDEN_PHRASES = (
    "The child said 'weiß nicht'. "
    "Does the system's response avoid the phrases 'bist du gespannt' and 'bist du neugierig'? "
    "These phrases incorrectly attribute excitement/curiosity to a child who expressed not knowing. "
    "Return PASS if neither phrase appears, "
    "FAIL if either 'bist du gespannt' or 'bist du neugierig' is present in the response."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_INPUTS_PIA_DONT_KNOW = [
    "Hallo!",
    "Hallo Lena! Pia ist ein besonderes Mädchen. Weißt du noch, was Pia morgens als Erstes macht?",
    "weiß nicht",
]

SIMULATED_CHILD_INPUTS_BOBO_DONT_KNOW = [
    "Hallo!",
    "Hallo! Bobo und Papa Siebenschläfer haben zusammen ein Paket von der Post geholt. Was war in dem Paket drin?",
    "weiß nicht",
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestRespondToDontKnowFixtureBased:
    """Strategy A: Verify system handles 'weiß nicht' correctly."""

    def test_dont_know_offers_help_pia(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'weiß nicht' to a story question (Pia).
        System should help with a brief hint and continue naturally.
        """
        state = build_state_with_beats(
            child_name="Lena",
            child_age=5,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Lena! Pia macht morgens viele Sachen. Was gibt Pia ihrem Hamster Hubert zu fressen?"),
                HumanMessage(content="weiß nicht"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_DONT_KNOW_HELP)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_DONT_KNOW_HELP))

    def test_dont_know_no_forbidden_phrases(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'weiß nicht' to a story content question (Bobo).
        System must NOT use 'bist du gespannt' or 'bist du neugierig'.
        """
        state = build_state_with_beats(
            child_name="Finn",
            child_age=8,
            child_gender="männlich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Finn! Bobo und Papa haben ein Paket bekommen. Was war in dem Paket?"),
                HumanMessage(content="weiß nicht"),
            ],
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_DONT_KNOW_NO_FORBIDDEN_PHRASES)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_DONT_KNOW_NO_FORBIDDEN_PHRASES))

    def test_dont_know_simple_word_explanation(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Child says 'weiß nicht' when asked about a word meaning ('knapp').
        System should explain in simple, concrete language.
        """
        state = build_state_with_beats(
            child_name="Lena",
            child_age=5,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Lena! Pia sagt: 'Das war knapp!' Weißt du, was das bedeutet?"),
                HumanMessage(content="weiß nicht"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_DONT_KNOW_SIMPLE_EXPLANATION)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_DONT_KNOW_SIMPLE_EXPLANATION))


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestRespondToDontKnowSimulated:
    """Strategy B: Full simulation where child says 'weiß nicht'."""

    def test_dont_know_simulated_pia(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation (Pia story): child says 'weiß nicht' on turn 2.
        System should offer help naturally.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Lena",
                child_age=5,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_INPUTS_PIA_DONT_KNOW,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_DONT_KNOW_HELP)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Lena", 5, "weiblich",
                                                           SIMULATED_CHILD_INPUTS_PIA_DONT_KNOW,
                                                           CRITERION_DONT_KNOW_HELP))