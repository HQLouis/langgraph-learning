"""
Feature: Clear References ("Referenzen klar halten")
Test file: The system should always use names and concrete objects instead of
           ambiguous pronouns. Every sentence must be understandable on its own.

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

SCRIPT_HUBERT_FOOD = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia f\u00fcttert ihren Hamster Hubert mit Brokkoli.'
    ' Was frisst Hubert gern \u2013 Brokkoli oder Marmelade?',
    'Brokkoli',
]

SCRIPT_BREAD_TOPPING = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia schmiert ein Pausenbrot f\u00fcr ihren Bruder Carl.'
    ' Was streicht Pia auf das Brot \u2013 Marmelade oder Erdnussbutter?',
    'Marmelade',
]

SCRIPT_EGGS_CAUGHT = [
    'hallo',
    'Hallo! Ich bin Thilio. Pia stolpert mit den Eiern, aber sie f\u00e4ngt'
    ' die Eier wieder auf. Was f\u00e4ngt Pia auf \u2013 die Eier oder den Ball?',
    'die Eier',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NAME_NOT_PRONOUN = (
    "The child said 'Brokkoli' when asked what Hubert eats. Does the system "
    "response use the name 'Hubert' (or 'der Hamster') and the word 'Brokkoli' "
    "explicitly, rather than vague pronouns like 'er', 'es', or 'das'? "
    "Return PASS if the system uses clear names/nouns, "
    "FAIL if it relies on ambiguous pronouns."
)

CRITERION_REPEAT_KEY_TERMS = (
    "The child said 'Marmelade'. Does the system response repeat the key "
    "term 'Marmelade' (and ideally mention 'Brot' or 'Pausenbrot') rather "
    "than using vague words like 'das', 'es', or 'darauf'? "
    "Return PASS if the system repeats the important terms clearly, "
    "FAIL if it uses ambiguous references."
)

CRITERION_STANDALONE_SENTENCES = (
    "The child said 'die Eier'. Does the system response repeat 'Eier' "
    "(or 'die Eier') so that the sentence is understandable on its own, "
    "rather than using unclear references like 'sie' or 'das'? "
    "Return PASS if the response is self-contained and clear, "
    "FAIL if it uses pronouns that could be ambiguous."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestClearReferencesFixtureBased:
    """Strategy A: Verify the system uses clear references, not ambiguous pronouns."""

    def test_name_not_pronoun(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Child says 'Brokkoli'. System should use 'Hubert' and
        'Brokkoli' explicitly, not vague pronouns.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_HUBERT_FOOD),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NAME_NOT_PRONOUN)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NAME_NOT_PRONOUN),
        )

    def test_repeat_key_terms(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Child says 'Marmelade'. System should repeat
        'Marmelade' and 'Brot' clearly.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BREAD_TOPPING),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_REPEAT_KEY_TERMS)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_REPEAT_KEY_TERMS),
        )

    def test_standalone_sentences(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child says 'die Eier'. System should repeat 'Eier'
        so the sentence is self-contained.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_EGGS_CAUGHT),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_STANDALONE_SENTENCES)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_STANDALONE_SENTENCES),
        )
