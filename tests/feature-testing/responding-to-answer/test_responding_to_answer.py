"""
Feature: Responding-to-Answer
Test file: Does the system engage with the child's emotions and personal
           experiences when the story provides an opportunity, rather than
           immediately moving on?

The feature requires that the system engages meaningfully with the child's
answer rather than immediately moving on.  Three sub-behaviours are tested:
  1. Emotion engagement: when a story scene involves recognisable emotions
     (e.g. laughing, fear), the system explores the feeling and asks about
     the child's own experience (2-3 exchanges, then return to main topic).
  2. Memory hint: when the child says they forgot, the system gives a short
     memory prompt about the scene rather than just telling the answer.
  3. Disengage acknowledgment: when the child repeatedly disengages (says
     "nee", "nein", "weiß nicht"), the system first acknowledges, then
     gently transitions to a new activity.

Stories used: "Pia muss nicht perfekt sein", "Bobos Adventskalender"

Conversation scripts follow the same convention as all feature tests:
child-first, odd-length.  The last child message triggers a live system
response that is evaluated by the judge.  The last system response in
the spec is ignored (it represents the current, suboptimal behaviour).

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible):
      State and conversation history are hardcoded.
      The LLM is called only once per N-run iteration.

  Strategy B — fully simulated (realistic, end-to-end):
      No state is pre-set.  The entire conversation is conducted using
      real LLMs from scratch with hardcoded child inputs.

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from feature_testing_utils import (
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_CHAPTER_ID,
    FIXTURE_BOBO_STORY_ID,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_CHAPTER_ID,
    FIXTURE_PIA_STORY_ID,
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_EMOTION_ENGAGEMENT = (
    "After the child correctly answers 'Pia lacht' to the question about "
    "whether Pia is sad or laughs, does the system response: "
    "(1) acknowledge the child's correct answer, AND "
    "(2) explore the emotion further — for example by asking WHY Pia laughs, "
    "what the child finds funny about the situation, or whether the child "
    "has experienced something similar — RATHER than immediately ending the "
    "conversation or moving on to a completely new topic? "
    "Return PASS if the system engages with the emotion behind the answer "
    "(asks about the reason for laughing, relates to the child's experience, "
    "or discusses the feeling), FAIL if it merely confirms the answer and "
    "moves on without exploring the emotion."
)

CRITERION_MEMORY_HINT = (
    "The child said 'vergessen' (forgot) when asked what Pia did first on "
    "Friday morning. Does the system response: "
    "(1) acknowledge that the child forgot (not ignore or misinterpret it), AND "
    "(2) give a short memory prompt or hint about the scene to help the child "
    "remember (e.g. mentioning Pia's socks, referencing the morning routine) "
    "RATHER than simply telling the full answer without any bridging hint? "
    "Return PASS if the system acknowledges the forgetting AND provides a "
    "memory prompt or scene hint before or alongside a question, "
    "FAIL if it just states the answer directly without any recall aid."
)

CRITERION_REFLECT_AND_PERSONALIZE = (
    "The child answered 'richtig machen?' to a question about whether making "
    "things right or making mistakes is more fun. Does the system response: "
    "(1) name the action more precisely (e.g. 'Du findest, alles richtig "
    "machen macht mehr Spaß?'), AND "
    "(2) wait for or encourage the child's input (not rush past it), AND "
    "(3) mirror the child's thought or ask about the child's personal "
    "experience (e.g. 'Machst du auch alles richtig?') — RATHER than "
    "immediately jumping to a new story scene without engaging with "
    "the child's answer? "
    "Return PASS if the system engages with the child's answer by "
    "reflecting, personalizing, or asking about the child's own experience "
    "before transitioning to a new scene, "
    "FAIL if it immediately jumps to a new story topic without engaging."
)

CRITERION_DISENGAGE_ACKNOWLEDGE_TRANSITION = (
    "The child has repeatedly disengaged throughout the conversation (saying "
    "'nee', 'weiß nicht', 'nein' multiple times). Does the system response: "
    "(1) acknowledge or validate the child's reluctance (e.g. 'Kein Problem', "
    "'Das ist okay', or similar), AND "
    "(2) gently transition to a different type of activity or approach "
    "(e.g. suggesting a creative task, a game, or a different way to engage "
    "with the story) RATHER than asking yet another factual comprehension "
    "question in the same style? "
    "Return PASS if the system first acknowledges the child's disengagement "
    "AND then transitions to a new activity or approach, "
    "FAIL if it ignores the pattern and continues with the same question style."
)

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from responding-to-answer-test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 39-82): Emotion engagement after "Pia lacht"
# Context: full conversation about Pia's story, ending with the child saying
# Pia laughs.  The system should explore the emotion rather than move on.
SCRIPT_PIA_LACHT = [
    # child (prepended for child-first format)
    'Hallo!',
    # system                                                                     # spec line
    'Hallo! Ich bin Thilio, dein sprechendes Spielzeug.'
    ' Wir haben eben die Geschichte von Pia geh\u00f6rt, oder?'
    ' Pia ist ja wirklich ein besonderes M\u00e4dchen!'
    ' Wei\u00dft du noch, wie der Freitag f\u00fcr Pia angefangen hat?',         # 39
    # child
    'nee',                                                                       # 40
    # system
    'Ach so, du wei\u00dft es nicht mehr. Pia hat Socken angezogen.'
    ' Waren die Socken bunt oder waren die Socken gleich?',                      # 41
    # child
    'gleich',                                                                    # 42
    # system
    'Ja, Pia hat gleiche Socken angezogen.'
    ' Pia hat viele Sachen am Morgen gemacht.'
    ' Hat Pia auch Hubert gef\u00fcttert oder hat Pia Carl gef\u00fcttert?',     # 43
    # child
    'hebert gef\u00fcttert',                                                     # 44
    # system
    'Ja, Pia hat Hubert gef\u00fcttert.'
    ' Pia hat Hubert Brokkoli gegeben.'
    ' Hat Hubert das gern gegessen oder nicht gern?',                            # 45
    # child
    'je',                                                                        # 46
    # system
    'Ja, Hubert hat das gern gegessen.'
    ' Soll Pia jetzt zur T\u00fcr gehen oder soll Pia noch bleiben?',           # 47
    # child
    't\u00fcr',                                                                  # 48
    # system
    'Ja, Pia geht zur T\u00fcr.'
    ' Hat Pia "Hallo" oder "Dankesch\u00f6n" gesagt?',                          # 49
    # child
    'warum',                                                                     # 50
    # system
    'Du fragst, warum Pia "Dankesch\u00f6n" gesagt hat.'
    ' Pia hat "Dankesch\u00f6n" gesagt,'
    ' weil Leute ihr etwas gesagt haben. Ist es jetzt klar?',                   # 51
    # child
    'ja',                                                                        # 52
    # system
    'Gut! Pia hat auch "Dankesch\u00f6n" gesagt.'
    ' Was haben die Leute Pia gefragt?'
    ' Haben die Leute nach dem Bett gefragt oder nach dem Hamster?',             # 53
    # child
    'warum fragst du nach dem bett?',                                            # 54
    # system
    'Du fragst, warum ich nach dem Bett frage.'
    ' Die Leute fragen Pia, ob sie ihr Bett gemacht hat.'
    ' Hat Pia das Bett gemacht oder nicht gemacht?',                             # 55
    # child
    'doch sie hat Bett gemacht',                                                 # 56
    # system
    'Ja, Pia hat das Bett gemacht.'
    ' Pia macht immer alles richtig. Stimmt das oder stimmt das nicht?',         # 57
    # child
    'stimmt',                                                                    # 58
    # system
    'Ja, das stimmt. Pia macht immer alles richtig.'
    ' Pia hat Freunde.'
    ' Hat Pia einen Freund oder hat Pia Freundinnen?',                           # 59
    # child
    'freundinnen',                                                               # 60
    # system
    'Ja, Pia hat Freundinnen.'
    ' Hei\u00dfen die Freundinnen Lisa und Sarah'
    ' oder Millie und Sarah?',                                                   # 61
    # child
    'Lisa und sarah',                                                            # 62
    # system
    'Du sagst, Lisa und Sarah. Warte mal.'
    ' Ich glaube, die Freundinnen hei\u00dfen Millie und Sarah.'
    ' Pia braucht Eier.'
    ' Holt Pia die Eier aus dem Schrank oder aus dem K\u00fchlschrank?',         # 63
    # child
    'aus k\u00fchlschrank',                                                      # 64
    # system
    'Ja, Pia holt die Eier aus dem K\u00fchlschrank.'
    ' Was passiert mit den Eiern?'
    ' Fallen die Eier runter oder bleiben die heil?',                            # 65
    # child
    'heil',                                                                      # 66
    # system
    'Die Eier bleiben heil, sagst du.'
    ' Pia sagt: "Das war..."'
    ' Was sagt Pia? "Das war sch\u00f6n" oder "Das war knapp"?',                # 67
    # child
    'das war knapp',                                                             # 68
    # system
    'Ja, Pia sagt: "Das war knapp!"'
    ' Pia geht nach Hause. Was machen Millie und Sarah?'
    ' Gehen die mit oder fahren die Schlittschuh?',                              # 69
    # child
    'sie fahren schlittschuhe',                                                  # 70
    # system
    'Ja, Millie und Sarah fahren Schlittschuh.'
    ' Pia will nicht mitfahren.'
    ' Hat Pia Angst oder hat Pia keine Lust?',                                  # 71
    # child
    'angst?',                                                                    # 72
    # system
    'Du fragst, ob Pia Angst hat. Ja, Pia hat Angst.'
    ' Pia hat Angst, Fehler zu machen.'
    ' Was macht Pia am Abend?'
    ' Geht Pia ins Kino oder macht Pia beim Talentwettbewerb mit?',             # 73
    # child
    'nicht kino',                                                                # 74
    # system
    'Ja, Pia geht nicht ins Kino.'
    ' Pia macht beim Talentwettbewerb mit.'
    ' Was macht Pia mit Hubert?'
    ' Nimmt Pia Hubert mit oder l\u00e4sst Pia Hubert zu Hause?',              # 75
    # child
    'hubert kommt mit',                                                          # 76
    # system
    'Ja, Hubert kommt mit.'
    ' Pia nimmt auch einen Salzstreuer mit.'
    ' Was ist in dem Salzstreuer? Ist da Salz oder Pfeffer drin?',               # 77
    # child
    'salz',                                                                      # 78
    # system
    'Du denkst, da ist Salz drin. Aber warte mal!'
    ' Da ist Pfeffer drin!'
    ' Was passiert mit dem Ballon?'
    ' Platzt der Ballon oder bleibt der heil?',                                  # 79
    # child
    'er platzt',                                                                 # 80
    # system
    'Ja, der Ballon platzt!'
    ' Was passiert mit Pia? Ist Pia traurig oder lacht Pia?',                   # 81
    # child — TESTED: system response to this is judged
    'pia lacht',                                                                 # 82
]

# Example 2 (spec lines 101-103): Memory hint after "vergessen"
# Context: beginning of conversation, child says they forgot.
# The system should give a memory prompt/hint about the scene.
SCRIPT_VERGESSEN = [
    # child                                                                      # spec line
    'hallo',                                                                     # 101
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht.'
    ' Sprechen wir ein bisschen dar\u00fcber!'
    ' Was hat Pia denn als Allererstes an diesem besonderen Freitag gemacht?',   # 102
    # child — TESTED: system response to this is judged
    'vergessen',                                                                 # 103
]

# Example 3 (spec lines 118-128): Disengaged child (Bobo story)
# Context: the child repeatedly disengages ("nein", "nee", "weiß nicht").
# The system should acknowledge, gently transition, and offer a new activity.
SCRIPT_DISENGAGED = [
    # child                                                                      # spec line
    'hallo',                                                                     # 118
    # system
    'Hallo! Ich bin Thilo.'
    ' Ich habe die Geschichte von Bobos Adventskalender auch geh\u00f6rt.'
    ' Sprechen wir dar\u00fcber?'
    ' Wei\u00dft du noch, was Bobo und sein Papa am Anfang'
    ' der Geschichte gemacht haben?',                                            # 119
    # child
    'nein',                                                                      # 120
    # system
    'Ach so, du wei\u00dft es nicht mehr.'
    ' Bobo und Papa Siebenschl\u00e4fer schauen aus dem Fenster.'
    ' Sollen wir dar\u00fcber sprechen, was die Postfrau gemacht hat,'
    ' oder was Bobo mit dem Paket macht?',                                       # 121
    # child
    'bobo mit Paket gemacht',                                                    # 122
    # system
    'Aha, du willst wissen, was Bobo mit dem Paket macht.'
    ' Bobo und Papa tragen das Paket zusammen in das Haus.'
    ' M\u00f6chtest du erz\u00e4hlen, was in dem Paket ist,'
    ' oder was sie danach machen?',                                              # 123
    # child
    'nee',                                                                       # 124
    # system
    'Du m\u00f6chtest nicht erz\u00e4hlen, was in dem Paket ist.'
    ' Bobo und Papa packen das Paket aus.'
    ' Sollen wir dar\u00fcber reden, was sie zum Basteln holen,'
    ' oder was Bobo auf die Pappe malt?',                                        # 125
    # child
    'wei\u00df nicht',                                                           # 126
    # system
    'Du bist dir nicht sicher.'
    ' Bobo malt ein Haus auf die Pappe.'
    ' M\u00f6chtest du sagen, was Mama mitbringt,'
    ' oder was Bobo am Ende macht?',                                             # 127
    # child — TESTED: system response to this is judged
    'nein',                                                                      # 128
]

# Example 4: Child says "richtig machen?" — system should reflect, personalize,
# ask about child's own experience before transitioning to a new scene.
SCRIPT_RICHTIG_MACHEN = [
    # child
    'hallo',
    # system
    'Hallo! Du hast also auch die Geschichte von Pia geh\u00f6rt.'
    ' Pia ist ja ein M\u00e4dchen, dem nie Fehler passieren.'
    ' Was meinst du, wie findet sie das?',
    # child
    'toll',
    # system
    'Ja, Pia macht immer alles toll.'
    ' Meinst du, Pia ist traurig oder froh,'
    ' dass sie nie Fehler macht?',
    # child
    'sie ist froh',
    # system
    'Pia ist froh. Ja, Pia ist eigentlich immer froh, weil alles klappt.'
    ' Aber sag mal, ist es denn auch sch\u00f6n,'
    ' wenn man immer alles richtig macht,'
    ' oder findet Carl es besser, Fehler zu machen?',
    # child
    'carl mag besser Fehler',
    # system
    'Carl mag lieber Fehler machen.'
    ' Stell dir vor, du bist Carl. Was machst du jetzt?',
    # child
    'quatsch',
    # system
    'Du w\u00fcrdest Quatsch machen.'
    ' Carl findet es toll, wenn er Quatsch machen kann.'
    ' Meinst du, Carl w\u00fcrde lieber mit gr\u00fcnen Bohnen malen'
    ' oder lieber ein Bild mit Wachsmalstiften malen?',
    # child
    'beides',
    # system
    'Carl mag beides. Pia geht in die Schule.'
    ' Pia ist mit ihren Freundinnen in der Schule.'
    ' Wie hei\u00dfen denn Pias Freundinnen?',
    # child
    'lara?',
    # system
    'Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',
    # child
    'wei\u00df nicht',
    # system
    'Pia hat zwei Freundinnen: Millie und Sarah.'
    ' Pia und ihre Freundinnen brauchen Eier.'
    ' Holen sie die Eier aus dem Schrank oder aus dem K\u00fchlschrank?',
    # child
    'k\u00fchlschrank',
    # system
    'Ja, Pia holt die Eier aus dem K\u00fchlschrank.'
    ' Was passiert mit den Eiern?'
    ' Fallen sie runter oder bleiben sie heil?',
    # child
    'was ist heil',
    # system
    'Heil bedeutet, dass nichts kaputt ist.'
    ' Meinst du, die Eier bleiben heil, oder fallen sie runter?',
    # child
    'heil bleiben',
    # system
    'Die Eier bleiben heil.'
    ' Aber fallen die Eier wirklich nicht runter, oder purzeln sie doch?',
    # child
    'fast runter',
    # system
    'Sie fallen fast runter.'
    ' Pia sagt: "Das war knapp!"'
    ' Pia macht alles richtig, und Carl macht vieles falsch.'
    ' Was denkst du, macht mehr Spa\u00df?',
    # child — TESTED: system response to this is judged
    'richtig machen?',
]


# ---------------------------------------------------------------------------
# Helper — convert child-first script to LangChain message list
# ---------------------------------------------------------------------------


def _script_to_messages(script: list[str]) -> list:
    """
    Convert a child-first conversation script to a LangChain message list.

    Even indices (0, 2, 4, ...) → HumanMessage (child).
    Odd  indices (1, 3, 5, ...) → AIMessage (system).
    """
    messages = []
    for i, text in enumerate(script):
        if i % 2 == 0:
            messages.append(HumanMessage(content=text))
        else:
            messages.append(AIMessage(content=text))
    return messages


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestRespondingToAnswerFixtureBased:
    """Strategy A: Verify emotion engagement against hardcoded state fixtures."""

    def test_emotion_engagement_after_correct_answer(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Pia lacht): The child correctly answers that Pia laughs.
        The system should explore the emotion (ask WHY, relate to the child's
        own experience) rather than immediately moving on.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_PIA_LACHT),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_EMOTION_ENGAGEMENT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_EMOTION_ENGAGEMENT),
        )

    def test_memory_hint_after_forgetting(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (vergessen): The child says they forgot what Pia did.
        The system should give a memory prompt/hint about the scene rather
        than just telling the answer.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_VERGESSEN),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_MEMORY_HINT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_MEMORY_HINT),
        )

    def test_reflect_and_personalize(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (richtig machen?): The child says 'richtig machen?' when
        asked what is more fun.  The system should reflect the child's thought,
        ask about personal experience, and gently return to the story scene.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_RICHTIG_MACHEN),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_REFLECT_AND_PERSONALIZE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_REFLECT_AND_PERSONALIZE),
        )

    def test_disengage_acknowledge_transition(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Bobo — disengaged child): The child repeatedly says 'nein',
        'nee', 'weiß nicht'.  The system should acknowledge the reluctance
        and gently transition to a new activity.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_DISENGAGED),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_DISENGAGE_ACKNOWLEDGE_TRANSITION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_DISENGAGE_ACKNOWLEDGE_TRANSITION),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestRespondingToAnswerSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_emotion_engagement_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Pia lacht): Full simulation.
        Final response should explore the emotion rather than move on.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_PIA_LACHT,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_EMOTION_ENGAGEMENT,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich", SCRIPT_PIA_LACHT,
                CRITERION_EMOTION_ENGAGEMENT,
            ),
        )

    def test_memory_hint_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (vergessen): Full simulation.
        Final response should give a memory hint rather than just the answer.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_VERGESSEN,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_MEMORY_HINT,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich", SCRIPT_VERGESSEN,
                CRITERION_MEMORY_HINT,
            ),
        )

    def test_reflect_and_personalize_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (richtig machen?): Full simulation.
        Final response should reflect, personalize, and ask about experience.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_RICHTIG_MACHEN,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_REFLECT_AND_PERSONALIZE,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich", SCRIPT_RICHTIG_MACHEN,
                CRITERION_REFLECT_AND_PERSONALIZE,
            ),
        )

    def test_disengage_acknowledge_transition_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Bobo — disengaged child): Full simulation.
        Final response should acknowledge reluctance and transition to new activity.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_DISENGAGED,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_DISENGAGE_ACKNOWLEDGE_TRANSITION,
            )
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(
            _run, n, pass_threshold,
            setting=simulation_to_setting(
                "Emma", 6, "weiblich", SCRIPT_DISENGAGED,
                CRITERION_DISENGAGE_ACKNOWLEDGE_TRANSITION,
            ),
        )
