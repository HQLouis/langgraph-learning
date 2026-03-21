"""
Feature: Stick to Story Content ("sich an Szenen, Orte oder Figuren im Buch halten")
Test file: The system must stick to scenes, locations and characters from the
           book. It may briefly ask about the child's feelings or personal
           experiences, but must return to the story and never invent new plot.

Story used:
  - "Pia muss nicht perfekt sein"

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible)

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


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

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

# Example 1: After a near-accident with eggs, system may ask about child's
# feelings but must return to the story and not invent new scenes.
SCRIPT_FEELINGS_DETOUR = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Pia stolpert fast mit den Eiern, aber sie f\u00e4ngt sie wieder auf.'
    ' Das war knapp! Hattest du auch schon mal so einen Moment,'
    ' wo etwas fast schiefgegangen ist?',
    'Ja',
]

# Example 2: System asks a personal question about bread toppings,
# then must return to the story content (not invent new scenes).
SCRIPT_PERSONAL_QUESTION_RETURN = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Pia schmiert ein Brot mit Marmelade und Erdnussbutter.'
    ' Was isst du am liebsten auf deinem Brot?',
    'Nutella',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_FEELINGS_THEN_RETURN = (
    "The child confirmed having had a near-accident moment. The system is "
    "now expected to briefly engage with the child's feelings (e.g. ask "
    "'Wie hast du dich da gef\u00fchlt?') and then return to the story. "
    "Does the system response: "
    "(1) take the child's feelings seriously (ask about them or acknowledge), AND "
    "(2) NOT invent new story scenes, characters, or locations that are not "
    "in the original book? "
    "Return PASS if the system engages with the child's feelings and stays "
    "grounded in the book content, FAIL if it invents new plot or ignores "
    "the child's answer."
)

CRITERION_RETURN_TO_STORY = (
    "The child answered a personal question about bread toppings ('Nutella'). "
    "The system should briefly acknowledge the child's answer and then "
    "return to the story content (Pia's bread with Marmelade and "
    "Erdnussbutter). Does the system response: "
    "(1) acknowledge the child's personal answer, AND "
    "(2) return to the book's content with a story-related question, AND "
    "(3) NOT invent new scenes, locations, or characters beyond the book? "
    "Return PASS if the system returns to the story without inventing "
    "new content, FAIL if it continues the personal tangent or invents "
    "new story elements."
)


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestStickToStoryContentFixtureBased:
    """Strategy A: Verify the system sticks to book content."""

    def test_feelings_detour_then_return(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: System asked about child's near-accident experience.
        Child said 'Ja'. System should ask about feelings then return to story.
        Must not invent new story content.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_FEELINGS_DETOUR),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_FEELINGS_THEN_RETURN)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_FEELINGS_THEN_RETURN),
        )

    def test_personal_question_return_to_story(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: System asked personal bread question, child said 'Nutella'.
        System should acknowledge and return to story. Must not invent new content.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_PERSONAL_QUESTION_RETURN),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_RETURN_TO_STORY)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_RETURN_TO_STORY),
        )
