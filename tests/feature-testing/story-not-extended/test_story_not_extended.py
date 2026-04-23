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
    build_state_with_beats,
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

# Example 3: Child repeatedly disengages AFTER story end was reached — system should say goodbye
# This conversation covers the full story arc up to Bobo falling asleep (beats 11-12),
# then the child disengages. The beat system will set story_near_end=True.
SCRIPT_DISENGAGED_AT_END = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du noch, was Bobo und Papa als Erstes gemacht haben?',
    # child
    'aus dem fenster geschaut',
    # system
    'Genau! Bobo und Papa schauen aus dem K\u00fcchenfenster.'
    ' Dann kommt die Postbotin mit einem neuen Fahrrad.'
    ' Bobo darf auf dem Fahrrad sitzen. Klingeling!'
    ' Danach gehen Papa und Bobo zur Post und holen ein gro\u00dfes Paket.',
    # child
    'was war drin',
    # system
    'In dem Paket war ein gro\u00dfer Fotokalender.'
    ' Papa hat eine Idee: Sie basteln zusammen einen Adventskalender!'
    ' Bobo und Papa holen Pappe, Stifte und einen Klebestift.'
    ' Papa schneidet 24 Fenster in die Pappe.',
    # child
    'und dann',
    # system
    'Bobo malt ein gro\u00dfes Haus auf die Pappe.'
    ' Mit B\u00e4umen und einem Mond. Das wird ein sch\u00f6nes Bild!'
    ' Dann h\u00e4ngen sie den Kalender am Fenster auf.'
    ' Da kommt Mama nach Hause. Sie hat eingekauft.',
    # child
    'was sagt mama',
    # system
    'Mama staunt: "Oh, das ist aber ein sch\u00f6ner Adventskalender!'
    ' Hast du das Bild gemalt, Bobo?"'
    ' Aber Bobo antwortet nicht.'
    ' Er ist zwischen all den Bastelsachen am Tisch eingeschlafen.',
    # child
    'nein',
    # system
    'Das war das Ende der Geschichte!'
    ' Bobo ist m\u00fcde eingeschlafen. Fandest du die Geschichte sch\u00f6n?',
    # child
    'wei\u00df nicht',
    # system
    'Kein Problem! Bobo hat ein tolles Bild gemalt.'
    ' M\u00f6chtest du noch etwas \u00fcber die Geschichte erz\u00e4hlen?',
    # child — TESTED: repeated disengagement at story end, system should say goodbye
    'nein',
]

# Example 4: Child disengages MID-STORY — system should offer different activity
# This is the mid-story disengagement scenario (beat system says story_near_end=False).
# AI messages ask questions without revealing new story content, avoiding
# an in-context pattern of "always continue the story after nein".
SCRIPT_DISENGAGED_MID_STORY = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben die Geschichte von Bobo geh\u00f6rt.'
    ' Wei\u00dft du noch, was Bobo und Papa am Anfang gemacht haben?',
    # child
    'nein',
    # system
    'Kein Problem! M\u00f6chtest du, dass ich es dir erz\u00e4hle?',
    # child
    'nee',
    # system
    'Okay! Sollen wir dann dar\u00fcber reden, was die Postbotin gemacht hat?',
    # child
    'wei\u00df nicht',
    # system
    'Hm, was m\u00f6chtest du gern machen?',
    # child — TESTED: repeated disengagement mid-story, system should offer activity
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
    "(saying 'nein', 'nee', 'wei\u00df nicht' multiple times). The story "
    "has already been fully discussed (Bobo fell asleep). Does the system "
    "recognize the child's fatigue/disengagement and gracefully end the "
    "conversation instead of forcing more interaction? "
    "Return PASS if the system acknowledges the disengagement and moves "
    "toward saying goodbye (or offers a very gentle close), "
    "FAIL if it asks another question, proposes a new activity, or "
    "tries to force the dialogue to continue."
)

CRITERION_OFFER_ACTIVITY_MID_STORY = (
    "The child has repeatedly disengaged (saying 'nein', 'nee', "
    "'wei\u00df nicht' multiple times), but the story has NOT been fully "
    "discussed yet — only the early scenes were covered. Does the system: "
    "(1) acknowledge the child's reluctance (e.g. 'Kein Problem!'), AND "
    "(2) offer a DIFFERENT type of activity (e.g. 'Sollen wir lieber "
    "ein Ratespiel machen?', 'M\u00f6chtest du lieber etwas malen?') "
    "RATHER than asking yet another story question or saying goodbye? "
    "Return PASS if the system acknowledges disengagement AND offers a "
    "different activity, FAIL if it asks another story question, ignores "
    "the disengagement pattern, or immediately says goodbye."
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
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_STORY_END_REACHED),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            story_near_end=True,
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
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_GENTLE_WRAP_UP),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            story_near_end=True,
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
        Example 3: Story has been fully discussed (Bobo fell asleep), child
        repeatedly disengages. System should say goodbye, not force more.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DISENGAGED_AT_END),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            story_near_end=True,
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

    def test_offer_activity_when_disengaged_mid_story(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 4: Child repeatedly disengages but story is only partially
        covered. System should offer a different activity, not say goodbye.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DISENGAGED_MID_STORY),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            story_near_end=False,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_OFFER_ACTIVITY_MID_STORY)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_OFFER_ACTIVITY_MID_STORY),
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
