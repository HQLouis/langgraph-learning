"""
Feature: Child Name & Gender Consideration
Test file: Gender Usage — is the language gender-appropriate for the child?

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible)
  Strategy B — fully simulated (realistic, end-to-end)

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage

from feature_testing_utils import (
    build_state,
    llm_judge,
    simulate_conversation,
    MESSAGES_TURN_3_MID_STORY,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_GENDER_APPROPRIATE_FEMALE = (
    "Is the language in the response appropriate for a girl? "
    "Specifically: does the response use correct German grammatical gender "
    "agreement for a female child, and avoid masculine-specific phrasing or "
    "forms of address? "
    "Return PASS if the language is consistently appropriate for a girl, "
    "FAIL if there is any masculine-specific phrasing or gender error."
)

CRITERION_GENDER_APPROPRIATE_MALE = (
    "Is the language in the response appropriate for a boy named Jonas? "
    "Note: the story being discussed may feature female characters (like 'Mia') — "
    "that is expected and acceptable. "
    "Only evaluate how the system addresses or refers to the child Jonas himself. "
    "Specifically: does the system use correct German grammar when addressing Jonas "
    "(e.g. using his name, or gender-neutral 'du' forms), and avoid feminine-specific "
    "forms of address directed at the child? "
    "Return PASS if the language directed at the child is appropriate for a boy, "
    "FAIL only if there is a clear gender error in how the child himself is addressed."
)

CRITERION_GENDER_CONSISTENT_FEMALE = (
    "Is the language consistently gender-appropriate for a girl throughout "
    "the entire response, with no gender inconsistencies or switches? "
    "Return PASS if fully consistent for a girl, FAIL if any inconsistency is found."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_INPUTS_3_TURNS = [
    "Hallo!",
    "Ich höre gerne Geschichten.",
    "Was macht Mia im Wald?",
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestGenderUsageFixtureBased:
    """Strategy A: Verify gender-appropriate language against hardcoded state fixtures."""

    def test_gender_appropriate_female(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Response for 'Emma' (female, 6y) at first turn should use
        gender-appropriate language for a girl.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=[HumanMessage(content="Hallo!")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENDER_APPROPRIATE_FEMALE)

        run_details_recorder(_run, n_runs, pass_threshold)

    def test_gender_appropriate_male(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Response for 'Jonas' (male, 7y) at first turn should use
        gender-appropriate language for a boy.
        """
        state = build_state(
            child_name="Jonas",
            child_age=7,
            child_gender="männlich",
            messages=[HumanMessage(content="Hallo!")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENDER_APPROPRIATE_MALE)

        run_details_recorder(_run, n_runs, pass_threshold)

    def test_gender_consistent_mid_story(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Response for 'Emma' (female, 6y) mid-story (after 3 prior exchanges)
        should maintain consistent gender-appropriate language.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=list(MESSAGES_TURN_3_MID_STORY) + [
                HumanMessage(content="Warum geht Mia in den Wald?")
            ],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENDER_CONSISTENT_FEMALE)

        run_details_recorder(_run, n_runs, pass_threshold)


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestGenderUsageSimulated:
    """
    Strategy B: Run the full conversation from scratch to verify that
    gender-appropriate language is maintained throughout.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_gender_simulated_female(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Emma' (female, 6y) over 3 turns.
        The final response should use language appropriate for a girl.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple[bool, str, str]:
            _, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_INPUTS_3_TURNS,
            )
            return llm_judge(judge_llm, spoken_text, CRITERION_GENDER_APPROPRIATE_FEMALE)

        run_details_recorder(_run, n, pass_threshold)

    def test_gender_simulated_male(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Jonas' (male, 7y) over 3 turns.
        The final response should use language appropriate for a boy.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple[bool, str, str]:
            _, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Jonas",
                child_age=7,
                child_gender="männlich",
                child_inputs=SIMULATED_CHILD_INPUTS_3_TURNS,
            )
            return llm_judge(judge_llm, spoken_text, CRITERION_GENDER_APPROPRIATE_MALE)

        run_details_recorder(_run, n, pass_threshold)

