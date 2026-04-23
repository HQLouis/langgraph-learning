"""
Feature: Das Kind mit dem Namen nicht zu oft ansprechen (Don't overuse child's name)
Test file: The system should use the child's name sparingly — only at greeting,
farewell, when the child doesn't respond, or occasionally when praising.
The name should NOT appear in every response during mid-dialog exchanges.

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
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NAME_IN_GREETING = (
    "The system is greeting the child for the first time. "
    "Does the response include the child's name (e.g. 'Hallo Mila')? "
    "The name should appear naturally in the greeting. "
    "Return PASS if the child's name is used in the greeting, "
    "FAIL if the name is absent from the greeting."
)

CRITERION_NAME_IN_FAREWELL = (
    "The child is saying goodbye at the end of the conversation "
    "(e.g. 'tschüss', 'mach's gut'). "
    "Does the system's farewell response include the child's name "
    "(e.g. 'Tschüss Mila, bis zum nächsten Mal!')? "
    "The name should appear naturally in the farewell, as explicitly "
    "allowed by the style guideline. "
    "Return PASS if the child's name is used in the farewell, "
    "FAIL if the name is absent from the farewell."
)

CRITERION_NO_NAME_MID_DIALOG = (
    "The system is responding to a simple factual answer from the child during "
    "the middle of a conversation about a story. This is a routine mid-dialog exchange. "
    "The child's name is '{child_name}'. "
    "Does the response avoid using the child's name? "
    "Mid-dialog confirmations like 'Ja, genau' or 'Stimmt' should NOT include the name. "
    "Return PASS if the child's name does NOT appear in the response, "
    "FAIL if the child's name appears in the response."
)

CRITERION_NAME_FREQUENCY_FULL_CONVERSATION = (
    "Review the entire conversation. The child's name is '{child_name}'. "
    "The system should use the child's name sparingly: primarily at greeting, "
    "farewell, when praising something special, or when the child doesn't respond. "
    "The name should NOT appear in every system response. "
    "Count how many system responses contain the child's name vs total system responses. "
    "Return PASS if the name appears in fewer than half of the system responses, "
    "FAIL if the name appears in most or all system responses."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_INPUTS_5_TURNS = [
    "Hallo!",
    "Hallo Mila! Wir haben die Geschichte von Pia gehört. Pia macht immer alles richtig. Was hat Pia ihrem Hamster Hubert zu fressen gegeben?",
    "Brokkoli",
    "Ja, Hubert frisst gern Brokkoli. Pia macht auch ein Pausenbrot für Carl. Was kommt auf das Brot?",
    "Marmelade",
    "Genau, Marmelade und Erdnussbutter. Pia geht dann in die Schule. Mit wem ist Pia in der Schule?",
    "Freundinnen",
    "Ja, mit Millie und Sarah. Was backen sie zusammen?",
    "Muffins",
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestNameUsageFrequencyFixtureBased:
    """Strategy A: Verify name usage frequency in different dialog contexts."""

    def test_name_used_in_greeting(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        At first turn (greeting), the system should include the child's name.
        """
        state = build_state_with_beats(
            child_name="Mila",
            child_age=7,
            child_gender="weiblich",
            messages=[HumanMessage(content="Hallo!")],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_GREETING)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_IN_GREETING))

    def test_no_name_mid_dialog_confirmation(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Mid-dialog: child gives a simple correct answer ('Brokkoli').
        System should confirm without using the child's name.
        """
        state = build_state_with_beats(
            child_name="Mila",
            child_age=7,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Mila! Pia gibt ihrem Hamster Hubert etwas zu essen. Was frisst Hubert gern?"),
                HumanMessage(content="Brokkoli"),
                AIMessage(content="Ja, Hubert frisst gern Brokkoli. Pia macht ein Pausenbrot für Carl. Was kommt auf das Brot?"),
                HumanMessage(content="Marmelade"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_NO_NAME_MID_DIALOG.format(child_name="Mila")

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))

    def test_name_used_in_farewell(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        At farewell, the system should include the child's name (e.g.
        'Tschüss Mila, bis zum nächsten Mal!'). This is one of the explicitly
        allowed contexts for using the child's name per the style guideline.
        """
        state = build_state_with_beats(
            child_name="Mila",
            child_age=7,
            child_gender="weiblich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Mila! Wir haben die Geschichte von Pia gehört. Pia macht alles richtig. Was frisst Hubert gern?"),
                HumanMessage(content="Brokkoli"),
                AIMessage(content="Ja, Hubert frisst gern Brokkoli. Pia geht dann in die Schule. Mit wem ist Pia in der Schule?"),
                HumanMessage(content="mit Millie und Sarah"),
                AIMessage(content="Genau, mit Millie und Sarah. Das hast du gut erklärt. Möchtest du noch weiter über die Geschichte sprechen?"),
                HumanMessage(content="nein, tschüss"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_IN_FAREWELL)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_NAME_IN_FAREWELL))

    def test_no_name_simple_story_answer(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """
        Mid-dialog: child gives another routine story answer.
        System should not use the name in a routine confirmation.
        """
        state = build_state_with_beats(
            child_name="Leon",
            child_age=6,
            child_gender="männlich",
            messages=[
                HumanMessage(content="Hallo!"),
                AIMessage(content="Hallo Leon! Pia geht in die Schule. Mit wem ist Pia in der Schule?"),
                HumanMessage(content="Freundinnen"),
                AIMessage(content="Ja, mit Millie und Sarah. Was backen sie zusammen in der Schule?"),
                HumanMessage(content="Muffins"),
            ],
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        criterion = CRITERION_NO_NAME_MID_DIALOG.format(child_name="Leon")

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, criterion))


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestNameUsageFrequencySimulated:
    """Strategy B: Full simulation to check name frequency across a conversation."""

    def test_name_frequency_full_conversation(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """
        Full 5-turn conversation. The child's name should appear sparingly —
        in fewer than half of the system responses.
        """
        n = _cfg.SIMULATED_N_RUNS
        criterion = CRITERION_NAME_FREQUENCY_FULL_CONVERSATION.format(child_name="Mila")

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Mila",
                child_age=7,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_INPUTS_5_TURNS,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            # Judge the FULL conversation, not just last response
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            full_text = "\n".join(
                f"[{c['role']}]: {c['content']}" for c in conversation
            )
            passed, resp, reason = llm_judge(judge_llm, full_text, criterion)
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Mila", 7, "weiblich",
                                                           SIMULATED_CHILD_INPUTS_5_TURNS,
                                                           criterion))