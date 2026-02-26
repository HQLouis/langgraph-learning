"""
Feature: Child Name & Gender Consideration
Test file: Name Usage — does the system address the child by name?

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
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
    MESSAGES_TURN_3_MID_STORY,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NAME_USED_EMMA = (
    "Does the response address or mention the child by the name 'Emma'? "
    "Return PASS if the exact name 'Emma' appears anywhere in the response, "
    "FAIL otherwise."
)

CRITERION_NAME_USED_EMMA_MID_CONVERSATION = (
    "The response is part of an ongoing conversation where the child 'Emma' has already been greeted by name. "
    "Does the response feel personally directed at a specific child named 'Emma', "
    "either by using her name, or by using direct personal address (e.g. 'du', 'dein', 'deine') "
    "rather than a generic or impersonal tone? "
    "Return PASS if the response is personal and child-directed, FAIL if it feels generic or impersonal."
)

CRITERION_NAME_USED_LUCA = (
    "Does the response address or mention the child by the name 'Luca'? "
    "Return PASS if the exact name 'Luca' appears anywhere in the response, "
    "FAIL otherwise."
)

CRITERION_NAME_USED_JONAS = (
    "Does the response address or mention the child by the name 'Jonas'? "
    "Return PASS if the exact name 'Jonas' appears anywhere in the response, "
    "FAIL otherwise."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_INPUTS_3_TURNS = [
    "Hallo!",
    "Hallo Emma! Ich freue mich, dass du heute mit mir lernst. Heute lesen wir eine Geschichte über ein Mädchen namens Mia.",
    "Cool, ich mag Geschichten!",
    "Das ist toll! Mia lebt in einem kleinen Dorf am Waldrand. Eines Tages geht sie in den Wald, um Beeren zu sammeln.",
    "Wer ist Mia?",
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestNameUsageFixtureBased:
    """Strategy A: Verify name usage against hardcoded state fixtures."""

    def test_name_used_female_child(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        The system should address or mention the child 'Emma' (female, 6y)
        in a first-turn response.
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
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_USED_EMMA)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_USED_EMMA))

    def test_name_used_male_child(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        The system should address or mention the child 'Luca' (male, 7y)
        in a first-turn response.
        """
        state = build_state(
            child_name="Luca",
            child_age=7,
            child_gender="männlich",
            messages=[HumanMessage(content="Hallo!")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_USED_LUCA)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_USED_LUCA))

    def test_name_used_mid_conversation(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        The system should produce a personally-directed response mid-story
        (after 3 prior exchanges).

        Mid-conversation, the system does not need to repeat the name in every
        response — using direct address ('du', 'dein') is also acceptable.
        Uses a fixed n=5 to give enough statistical headroom at the 80% threshold.
        """
        n = 5
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=list(MESSAGES_TURN_3_MID_STORY) + [
                HumanMessage(content="Was passiert als nächstes?")
            ],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_USED_EMMA_MID_CONVERSATION)

        run_details_recorder(_run, n, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_USED_EMMA_MID_CONVERSATION))


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestNameUsageSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    child_inputs are hardcoded so that the human side of the conversation is
    reproducible. The system's earlier responses will vary, but the fixture
    child inputs provide a stable anchor.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_name_used_simulated_female(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Emma' (female, 6y) over 3 turns.
        The final response should address or mention 'Emma'.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_INPUTS_3_TURNS,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_NAME_USED_EMMA)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Emma", 6, "weiblich",
                                                           SIMULATED_CHILD_INPUTS_3_TURNS,
                                                           CRITERION_NAME_USED_EMMA))

    def test_name_used_simulated_male(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full simulation for 'Jonas' (male, 8y) over 3 turns.
        The final response should address or mention 'Jonas'.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Jonas",
                child_age=8,
                child_gender="männlich",
                child_inputs=SIMULATED_CHILD_INPUTS_3_TURNS,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_NAME_USED_JONAS)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Jonas", 8, "männlich",
                                                           SIMULATED_CHILD_INPUTS_3_TURNS,
                                                           CRITERION_NAME_USED_JONAS))
