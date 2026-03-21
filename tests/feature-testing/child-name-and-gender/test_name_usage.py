"""
Feature: Child Name & Gender Consideration
Test file: Name Usage — does the system greet the child by name?

The system should use the child's name when greeting them at the start of
a conversation.  Mid-conversation it is natural to use "du"/"dein" instead
of repeating the name in every response, so only the greeting is tested.

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible):
      State and conversation history are hardcoded.
      The LLM is called only once per N-run iteration.

  Strategy B — fully simulated (realistic, end-to-end):
      No state is pre-set. The entire conversation is conducted using
      real LLMs from scratch with hardcoded child inputs.

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage

from feature_testing_utils import (
    build_state_with_beats,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NAME_IN_GREETING_EMMA = (
    "The child 'Emma' has just said hello. Does the system's greeting "
    "response address or mention the child by the name 'Emma'? "
    "Return PASS if the exact name 'Emma' appears anywhere in the response, "
    "FAIL otherwise."
)

CRITERION_NAME_IN_GREETING_LUCA = (
    "The child 'Luca' has just said hello. Does the system's greeting "
    "response address or mention the child by the name 'Luca'? "
    "Return PASS if the exact name 'Luca' appears anywhere in the response, "
    "FAIL otherwise."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_GREETING = [
    "Hallo!",
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestNameUsageFixtureBased:
    """Strategy A: Verify name usage in the greeting against hardcoded state fixtures."""

    def test_name_in_greeting_female(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        The system should greet the child 'Emma' (female, 6y) by name
        in its first response.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=[HumanMessage(content="Hallo!")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_GREETING_EMMA)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_IN_GREETING_EMMA))

    def test_name_in_greeting_male(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        The system should greet the child 'Luca' (male, 7y) by name
        in its first response.
        """
        state = build_state_with_beats(
            child_name="Luca",
            child_age=7,
            child_gender="männlich",
            messages=[HumanMessage(content="Hallo!")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_GREETING_LUCA)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_IN_GREETING_LUCA))


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestNameUsageSimulated:
    """
    Strategy B: Run the greeting from scratch using real LLMs.

    A single child input ("Hallo!") triggers the system's greeting.
    The greeting is then checked for the child's name.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves a
    real LLM call.
    """

    def test_name_in_greeting_simulated_female(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Emma' (female, 6y).
        The greeting response should address 'Emma' by name.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_GREETING,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_GREETING_EMMA)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Emma", 6, "weiblich",
                                                           SIMULATED_CHILD_GREETING,
                                                           CRITERION_NAME_IN_GREETING_EMMA))

    def test_name_in_greeting_simulated_male(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Luca' (male, 7y).
        The greeting response should address 'Luca' by name.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Luca",
                child_age=7,
                child_gender="männlich",
                child_inputs=SIMULATED_CHILD_GREETING,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_GREETING_LUCA)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Luca", 7, "männlich",
                                                           SIMULATED_CHILD_GREETING,
                                                           CRITERION_NAME_IN_GREETING_LUCA))
