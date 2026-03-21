"""
Feature: Concrete Language ("Konkrete Sprache statt abstrakter Formulierungen")
Test file: The system should use concrete, simple language instead of abstract
           phrasing. Idioms should be immediately translated into plain words.

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

# Example 1: System should explain "Das war knapp!" in concrete terms.
SCRIPT_IDIOM_EXPLANATION = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Pia stolpert mit den Eiern, aber sie f\u00e4ngt die Eier wieder auf.'
    ' Pia sagt: "Das war knapp!" Wei\u00dft du, was das bedeutet?',
    'nein',
]

# Example 2: System should name concrete objects rather than use vague terms.
SCRIPT_CONCRETE_OBJECTS = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia macht ihrem Bruder ein Pausenbrot.'
    ' Was schmiert Pia auf das Brot \u2013 Marmelade oder Erdnussbutter?',
    'beides',
]

# Example 3: System should explain abstract concepts with simple comparisons.
SCRIPT_ABSTRACT_CONCEPT = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia nimmt von Marmelade und Erdnussbutter'
    ' gleich viel. Ist auf einer Seite mehr oder ist es gleich viel?',
    'gleich viel',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_IDIOM_EXPLAINED = (
    "The child does not know what 'Das war knapp!' means. Does the system "
    "response explain the idiom in simple, concrete language — e.g. 'Die "
    "Eier w\u00e4ren fast auf den Boden gefallen' — directly connected to "
    "the story action? The explanation must be short and concrete, not "
    "abstract or overly complex. "
    "Return PASS if the system explains the idiom in simple, child-friendly "
    "concrete terms, FAIL if it uses abstract language or fails to explain."
)

CRITERION_CONCRETE_NAMING = (
    "The child said 'beides' when asked about Pia's bread toppings. "
    "Does the system response name the concrete objects explicitly "
    "(Marmelade, Erdnussbutter) rather than using vague references like "
    "'das', 'es', or 'die Sachen'? "
    "Return PASS if the system names the specific items clearly, "
    "FAIL if it uses vague or abstract references."
)

CRITERION_SIMPLE_EXPLANATION = (
    "The child correctly said 'gleich viel'. Does the system response "
    "confirm the answer using concrete, simple language? The system should "
    "NOT use unnecessarily abstract or complex phrasing. "
    "Return PASS if the system confirms clearly and concretely, "
    "FAIL if it introduces abstract or overly complex language."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestConcreteLanguageFixtureBased:
    """Strategy A: Verify the system uses concrete, simple language."""

    def test_idiom_explained_concretely(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child doesn't know 'Das war knapp!'. System should
        explain in concrete, simple terms connected to the story action.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_IDIOM_EXPLANATION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_IDIOM_EXPLAINED)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_IDIOM_EXPLAINED),
        )

    def test_concrete_object_naming(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child says 'beides'. System should name Marmelade and
        Erdnussbutter explicitly, not use vague references.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CONCRETE_OBJECTS),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CONCRETE_NAMING)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CONCRETE_NAMING),
        )

    def test_simple_confirmation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child says 'gleich viel'. System should confirm
        using concrete, simple language.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_ABSTRACT_CONCEPT),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SIMPLE_EXPLANATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SIMPLE_EXPLANATION),
        )
