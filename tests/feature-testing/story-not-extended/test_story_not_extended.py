"""
Feature: Story Not Extended
Test file: Don't extend the story beyond the last scene.

When the last scene of the story has been discussed, the system should
gracefully wrap up rather than introduce new content.  A short child-related
question or a "how did you like the story?" is allowed, but the system must
NOT start new story topics or force the dialogue further.

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
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_CHAPTER_ID,
    FIXTURE_BOBO_STORY_ID,
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _script_to_messages(script: list[str]) -> list:
    """
    Convert a child-first conversation script to a LangChain message list.

    Even indices (0, 2, 4, ...) -> HumanMessage (child).
    Odd  indices (1, 3, 5, ...) -> AIMessage (system).
    """
    messages = []
    for i, text in enumerate(script):
        if i % 2 == 0:
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))
    return messages


# ---------------------------------------------------------------------------
# Conversation scripts — all reach the LAST scene of the Bobo story
# ---------------------------------------------------------------------------

# Example 1: Story ending reached, last scene discussed — system should wrap up
# Note: spec has no preceding dialog for this example, only the mögliche KI Antwort.
# The script below provides conversation context reaching the final scene.
SCRIPT_STORY_END_REACHED = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du, was Bobo und Papa als Erstes gemacht haben?',
    # child
    'n\u00f6',
    # system
    'Im Buch sind Bobo und Papa zuerst aus dem Fenster schauen gegangen.'
    ' Papa Siebenschl\u00e4fer geht zur Post, um ein Paket abzuholen.'
    ' Was war in dem Paket drin?',
    # child
    'kalender',
    # system
    'Ja, in dem Paket war ein Kalender.'
    ' Papa hat eine Idee: Sie wollen einen Adventskalender basteln.'
    ' Was brauchen sie zum Basteln?',
    # child
    'papier',
    # system
    'Ja, Papier brauchen sie.'
    ' Bobo und Papa holen eine Pappe.'
    ' Was macht Papa mit dem Messer?',
    # child
    'was',
    # system
    'Papa schneidet mit dem Messer die Pappe.'
    ' Was malt Bobo auf die Pappe? Malt er ein Auto oder ein Haus?',
    # child
    'haus',
    # system
    'Ja, Bobo malt ein Haus auf die Pappe.'
    ' Bobo malt auch B\u00e4ume und einen Mond.'
    ' Mama kommt nach Hause. Was fragt Mama?',
    # child
    'vergessen',
    # system
    'Du hast es vergessen. Das ist nicht schlimm!'
    ' Mama fragt: "Hast du das Bild gemalt, Bobo?"'
    ' Was macht Bobo, als Mama das fragt?',
    # child — TESTED: system response to this is judged
    'er sagt ja',
]

# Example 2: Last scene discussed with child answer — system should wrap up gently
SCRIPT_GENTLE_WRAP_UP = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Bobo und Papa Siebenschl\u00e4fer haben zusammen'
    ' einen Adventskalender gebastelt.'
    ' Wei\u00dft du noch, was in dem Paket war?',
    # child
    'kalender',
    # system
    'Ja, ein Kalender!'
    ' Bobo und Papa wollen einen Adventskalender basteln.'
    ' Zum Basteln brauchen sie Pappe.'
    ' Was schneiden sie in die Pappe?',
    # child
    'fenster',
    # system
    'Ja, sie schneiden Fenster in die Pappe.'
    ' Bobo malt ein Haus auf die Pappe.'
    ' Dann h\u00e4ngt Papa den Kalender ans Fenster.'
    ' Was macht jetzt Mama?',
    # child
    'einkaufen',
    # system
    'Mama kommt nach Hause und sieht den Adventskalender.'
    ' Sie findet ihn sehr sch\u00f6n.'
    ' Was ist denn mit Bobo los?',
    # child
    'er einschl\u00e4ft',
    # system
    'Ja, Bobo ist eingeschlafen.'
    ' Er schl\u00e4ft am Tisch zwischen den Bastelsachen.'
    ' Ist Bobo traurig oder m\u00fcde?',
    # child — TESTED
    'm\u00fcde',
]

# Example 3: Child repeatedly disengages near the end — system should stop forcing
SCRIPT_DISENGAGED_AT_END = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Ich habe die Geschichte von Bobos Adventskalender auch geh\u00f6rt.'
    ' Sprechen wir dar\u00fcber?'
    ' Wei\u00dft du noch, was Bobo und sein Papa am Anfang gemacht haben?',
    # child
    'nein',
    # system
    'Bobo und Papa Siebenschl\u00e4fer schauen aus dem Fenster.'
    ' Sollen wir dar\u00fcber sprechen, was die Postfrau gemacht hat,'
    ' oder was Bobo mit dem Paket macht?',
    # child
    'bobo mit Paket gemacht',
    # system
    'Bobo und Papa tragen das Paket zusammen in das Haus.'
    ' M\u00f6chtest du erz\u00e4hlen, was in dem Paket ist,'
    ' oder was sie danach machen?',
    # child
    'nee',
    # system
    'Bobo und Papa packen das Paket aus.'
    ' Sollen wir dar\u00fcber reden, was sie zum Basteln holen,'
    ' oder was Bobo auf die Pappe malt?',
    # child
    'wei\u00df nicht',
    # system
    'Bobo malt ein Haus auf die Pappe.'
    ' M\u00f6chtest du sagen, was Mama mitbringt,'
    ' oder was Bobo am Ende macht?',
    # child — TESTED: repeated disengagement, system should stop
    'nein',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_NO_STORY_EXTENSION = (
    "The conversation has reached the LAST scene of the story (Bobo falling "
    "asleep at the table). The child just answered a question about this "
    "final scene. Does the system response appropriately wrap up the "
    "conversation rather than introducing new story content? "
    "The response MUST make clear that the story is over. "
    "It is ACCEPTABLE to: ask how the child liked the story or what was "
    "special about it (max 2-3 closing exchanges) and say warmly goodbye. "
    "It is NOT acceptable to: ask new story-content questions, introduce "
    "new scenes, ask detail questions about the plot, or extend the dialogue "
    "with tasks like rhymes or riddles. "
    "Return PASS if the system clearly signals the story is over and wraps up "
    "(or begins wrapping up) without extending the story, "
    "FAIL if it introduces new content or forces the dialogue further."
)

CRITERION_GENTLE_WRAP_UP = (
    "The last scene of the story has been discussed (Bobo is asleep). "
    "The child answered the final question. Does the system gently wrap up "
    "the conversation? A short child-related question before saying goodbye "
    "is acceptable (e.g. 'Bist du auch müde?'). "
    "Return PASS if the system begins wrapping up the conversation "
    "(moving toward goodbye, no new story questions), "
    "FAIL if it continues with new story content or opens a new topic."
)

CRITERION_STOP_FORCING_DIALOGUE = (
    "The child has repeatedly disengaged in the last several turns "
    "(saying 'nein', 'nee', 'weiß nicht' multiple times). The system "
    "has now reached the end of the story. Does the system recognize "
    "the child's fatigue/disengagement and gracefully end the conversation "
    "instead of forcing more interaction? "
    "Return PASS if the system acknowledges the disengagement and moves "
    "toward saying goodbye (or offers a very gentle close), "
    "FAIL if it asks another question, proposes a new activity, or "
    "tries to force the dialogue to continue."
)

# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B
# ---------------------------------------------------------------------------

SIMULATED_CHILD_END_OF_STORY = [
    'hallo',
    'Hallo! Ich bin Thilio. Bobo und Papa haben einen Adventskalender gebastelt. '
    'Wei\u00dft du noch, was in dem Paket war?',
    'kalender',
    'Ja, ein Kalender! Bobo und Papa basteln zusammen. '
    'Was malt Bobo auf die Pappe?',
    'ein haus',
    'Ja, Bobo malt ein Haus! Dann kommt Mama nach Hause. '
    'Was ist mit Bobo passiert?',
    'er schl\u00e4ft',
    'Ja, Bobo ist eingeschlafen. Ist Bobo m\u00fcde oder traurig?',
    'm\u00fcde',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestStoryNotExtendedFixtureBased:
    """Strategy A: Verify the system wraps up after the last story scene."""

    def test_no_story_extension_after_last_scene(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: The final scene (Bobo falls asleep) has been discussed.
        Child answers 'er sagt ja'. System should correct gently and wrap up.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_STORY_END_REACHED),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NO_STORY_EXTENSION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NO_STORY_EXTENSION),
        )

    def test_gentle_wrap_up_after_final_answer(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: After child says 'müde' to the final question, system
        should gently wrap up. A child-related question is OK.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_GENTLE_WRAP_UP),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENTLE_WRAP_UP)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GENTLE_WRAP_UP),
        )

    def test_stop_forcing_when_child_disengages(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Child has said 'nein'/'nee'/'weiß nicht' repeatedly near
        the end. System should recognize fatigue and say goodbye.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DISENGAGED_AT_END),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_STOP_FORCING_DIALOGUE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_STOP_FORCING_DIALOGUE),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestStoryNotExtendedSimulated:
    """Strategy B: Full simulation reaching the end of the Bobo story."""

    def test_wrap_up_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Full simulation reaching the last scene. The final system response
        should wrap up rather than extend the story.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=5,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_END_OF_STORY,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_GENTLE_WRAP_UP
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System",
                 "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 5, "weiblich",
                SIMULATED_CHILD_END_OF_STORY,
                CRITERION_GENTLE_WRAP_UP,
            ),
        )
