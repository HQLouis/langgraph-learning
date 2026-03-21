"""
Feature: Explanation-Correction-Verification
Test file: Transition from explanation/correction to next topic — does the
           system verify the child's understanding before continuing?

The feature requires that after the system:
  1. Explains a concept the child doesn't know (e.g. Rhabarber, "heil")
  2. Corrects a wrong answer (e.g. Lisa vs Millie)
...it must include a verification step (asking the child whether they
understood) before moving on to the regular conversation.

Additionally, when a child is lost or helpless in the conversation,
the system should express empathy and provide a bridge/transition
before offering help.

Story used: "Pia muss nicht perfekt sein"

Conversation scripts are taken verbatim from the spec file.  Each line in
the spec is one atomic message — never split or combined.  The conversations
are child-first and odd-length.  The last child message triggers a live
system response that is evaluated by the judge.  The last system response
and any trailing child message in the spec are ignored (they represent the
current, suboptimal behaviour).

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
    build_state_with_beats,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_STORY_ID,
    FIXTURE_PIA_CHAPTER_ID,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_EXPLANATION_VERIFICATION = (
    "After the child indicated they don't know a concept (said 'nee' when asked "
    "'Kennst du Rhabarber?'), does the system response: "
    "(1) explain what Rhabarber is in child-friendly terms, AND "
    "(2) ask the child whether they understood the explanation (e.g. "
    "'Verstehst du das?', 'Weisst du jetzt was das ist?', or similar)? "
    "Return PASS if BOTH an explanation AND a verification question are present, "
    "FAIL otherwise."
)

CRITERION_CORRECTION_VERIFICATION = (
    "After the child gave a wrong answer ('Lisa und Sarah' instead of the correct "
    "'Millie und Sarah'), does the system response: "
    "(1) gently correct the child's mistake (mentioning the correct answer "
    "'Millie und Sarah'), AND "
    "(2) verify the child acknowledges or understands the correction "
    "(e.g. 'Erinnerst du dich?', 'Verstehst du?', or a similar confirmation "
    "question) BEFORE moving on to a completely new topic? "
    "Return PASS if BOTH a correction AND a verification step are present, "
    "FAIL otherwise."
)

CRITERION_WORD_EXPLANATION_VERIFICATION = (
    "The child asked 'was ist heil' — they don't know the meaning of the word "
    "'heil'. Does the system response: "
    "(1) explain what 'heil' means in simple, child-friendly terms "
    "(e.g. 'nicht kaputt', 'ganz', 'in Ordnung'), AND "
    "(2) ask the child whether they now understand the meaning "
    "(e.g. 'Verstehst du jetzt?', 'Weißt du jetzt, was das heißt?', or similar)? "
    "Return PASS if BOTH an explanation of 'heil' AND a verification question "
    "are present, FAIL otherwise."
)

CRITERION_EMPATHY_BRIDGE = (
    "The child said 'weiß nicht' when asked about what Pia and Carl like to do, "
    "indicating they feel lost or helpless in the conversation. "
    "Does the system response: "
    "(1) acknowledge the child's feeling of not knowing — expressing empathy or "
    "understanding (e.g. 'Das ist nicht schlimm', 'Kein Problem', "
    "'Ich kann dir helfen'), AND "
    "(2) provide a bridge or helpful transition before jumping into content "
    "(e.g. offering a hint, recapping something from the story, or gently "
    "guiding the child back) rather than immediately asking a new factual question? "
    "Return PASS if BOTH empathy/acknowledgment AND a supportive bridge are "
    "present, FAIL otherwise."
)

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from feature-test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 39-66): Rhabarber explanation
# Context: long conversation about Pia's story, ending with the child not
# knowing what Rhabarber is.  The system should explain AND verify.
SCRIPT_RHABARBER = [
    # child                                                                      # spec line
    'hallo',                                                                     # 40
    # system
    'Hallo! Hast du die Geschichte von Pia geh\u00f6rt, die eigentlich immer'
    ' alles richtig macht?',                                                     # 41
    # child
    'ja',                                                                        # 42
    # system
    'Super! Pia ist schon ein besonderes M\u00e4dchen, oder?'
    ' Was findest du denn besonders an ihr?',                                    # 43
    # child
    'sie macht richtig alles',                                                   # 44
    # system
    'Ja, Pia macht fast immer alles richtig. Sie sucht zum Beispiel Socken,'
    ' die zusammen passen. Findest du das auch gut,'
    ' wenn Socken zusammen passen?',                                             # 45
    # child
    'ja',                                                                        # 46
    # system
    'Ich auch! Ich mag es auch, wenn alles zusammenpasst.'
    ' Pia macht noch etwas ganz genau richtig:'
    ' Sie gibt ihrem Hamster Hubert sein Lieblingsessen,'
    ' n\u00e4mlich ...?',                                                        # 47
    # child
    'M\u00f6hren',                                                               # 48
    # system
    'Fast! Pia gibt ihrem Hamster Hubert etwas Gr\u00fcnes. Es ist ...?',        # 49
    # child
    'salat',                                                                     # 50
    # system
    'Nein, Salat ist es auch nicht. Aber Hubert bekommt etwas zu essen,'
    ' das auch gesund ist. Wei\u00dft du es jetzt?',                             # 51
    # child
    'nein',                                                                      # 52
    # system
    'Pia gibt Hubert Brokkoli. Das ist ein gr\u00fcnes Gem\u00fcse.'
    ' Magst du auch Brokkoli?',                                                  # 53
    # child
    'nein',                                                                      # 54
    # system
    'Brokkoli ist nicht jedermanns Sache, das stimmt.'
    ' Pia macht noch etwas sehr ordentlich:'
    ' Wenn sie ein Pausenbrot f\u00fcr ihren Bruder Carl macht,'
    ' dann nimmt sie genauso viel Erdnussbutter wie ...?',                       # 55
    # child
    'marmelade?',                                                                # 56
    # system
    'Genau, Pia nimmt genauso viel Erdnussbutter wie Marmelade.'
    ' Pia ist wirklich ordentlich.'
    ' Pia r\u00e4umt ihr Spielzeug in eine ...?',                               # 57
    # child
    'schublade',                                                                 # 58
    # system
    'Ja, Pia r\u00e4umt ihr Spielzeug bestimmt in eine Schublade.'
    ' Oder vielleicht in eine Kiste?',                                           # 59
    # child
    'vielleicht',                                                                # 60
    # system
    'Ja, vielleicht! Pia macht so viel richtig, da fragen sich die Leute,'
    ' ob sie auch ihr Bett gemacht hat. Und Pia hat ihr Bett gemacht.'
    ' Pia geht in den Garten und pfl\u00fcckt einen sch\u00f6nen,'
    ' gro\u00dfen, roten ...?',                                                 # 61
    # child
    'm\u00f6hren',                                                               # 62
    # system
    'Fast richtig! Pia pfl\u00fcckt etwas im Garten, aber es sind keine'
    ' M\u00f6hren. Es ist eine gro\u00dfe, rote ...?',                          # 63
    # child
    'was',                                                                       # 64
    # system
    'Pia pfl\u00fcckt einen Rhabarber. Kennst du Rhabarber?',                   # 65
    # child — TESTED: system response to this is judged
    'nee',                                                                       # 66
]

# Example 2 (spec lines 85-112): Word explanation ("heil")
# Context: long conversation about Pia's story, ending with the child asking
# what "heil" means.  The system should explain AND verify understanding.
SCRIPT_HEIL = [
    # child                                                                      # spec line
    'hallo',                                                                     # 85
    # system
    'Hallo! Du hast also auch die Geschichte von Pia geh\u00f6rt.'
    ' Pia ist ja ein M\u00e4dchen, dem nie Fehler passieren.'
    ' Was meinst du, wie findet sie das?',                                       # 86
    # child
    'toll',                                                                      # 87
    # system
    'Ja, Pia macht immer alles toll. Meinst du,'
    ' Pia ist traurig oder froh, dass sie nie Fehler macht?',                    # 88
    # child
    'sie ist froh',                                                              # 89
    # system
    'Pia ist froh. Ja, Pia ist eigentlich immer froh, weil alles klappt.'
    ' Aber sag mal, ist es denn auch sch\u00f6n, wenn man immer alles'
    ' richtig macht, oder findet Carl es besser, Fehler zu machen?',             # 90
    # child
    'carl mag besser Fehler',                                                    # 91
    # system
    'Carl mag lieber Fehler machen.'
    ' Stell dir vor, du bist Carl. Was machst du jetzt?',                        # 92
    # child
    'quatsch',                                                                   # 93
    # system
    'Du w\u00fcrdest Quatsch machen.'
    ' Carl findet es toll, wenn er Quatsch machen kann.'
    ' Meinst du, Carl w\u00fcrde lieber mit gr\u00fcnen Bohnen malen'
    ' oder lieber ein Bild mit Wachsmalstiften malen?',                          # 94
    # child
    'beides',                                                                    # 95
    # system
    'Carl mag beides. Pia geht in die Schule.'
    ' Pia ... mit ihren Freundinnen?'
    ' Mit wem ist Pia in der Schule?',                                           # 96
    # child
    'Freundinnen',                                                               # 97
    # system
    'Pia ist mit ihren Freundinnen in der Schule. Genau!'
    ' Wie hei\u00dfen denn Pias Freundinnen?',                                  # 98
    # child
    'lara?',                                                                     # 99
    # system
    'Du m\u00f6chtest wissen, wie Pias Freundinnen hei\u00dfen.'
    ' Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',                             # 100
    # child
    'wei\u00df nicht',                                                           # 101
    # system
    'Du wei\u00dft es nicht? Pia hat zwei Freundinnen.'
    ' Ist es Sarah oder Paul?',                                                  # 102
    # child
    'sarah',                                                                     # 103
    # system
    'Sarah! Ja, genau! Pia ist mit Sarah und Millie in der Schule.'
    ' Pia und ihre Freundinnen brauchen Eier.'
    ' Holen sie die Eier aus dem Schrank oder aus dem K\u00fchlschrank?',        # 104
    # child
    'k\u00fchlschrank',                                                          # 105
    # system
    'Du sagst, die Eier sind im K\u00fchlschrank.'
    ' Ja, Pia holt die Eier aus dem K\u00fchlschrank.'
    ' Was ist in dem Korb? Sind da \u00c4pfel oder Eier drin?',                 # 106
    # child
    '\u00c4pfel?',                                                               # 107
    # system
    'Du fragst, ob \u00c4pfel im Korb sind.'
    ' Nein, da sind keine \u00c4pfel.'
    ' Sind da die Eier drin oder nicht?',                                        # 108
    # child
    'ja, eier',                                                                  # 109
    # system
    'Ja, da sind Eier drin. Was passiert mit den Eiern?'
    ' Fallen sie runter oder bleiben sie heil?',                                 # 110
    # child — TESTED: system response to this is judged
    'was ist heil',                                                              # 111
]

# Example 3 (spec lines 131-155): Correction after wrong answer
# Context: long conversation about Pia's story, ending with the child giving
# the wrong friend name.  The system should correct AND verify.
SCRIPT_CORRECTION = [
    # child                                                                      # spec line
    'Start',                                                                     # 131
    # system
    'Hallo! Ich bin Thilio, dein sprechendes Spielzeug.'
    ' Wir haben eben die Geschichte von Pia geh\u00f6rt, oder?'
    ' Pia ist ja wirklich ein besonderes M\u00e4dchen!'
    ' Wei\u00dft du noch, wie der Freitag f\u00fcr Pia angefangen hat?',         # 132
    # child
    'nee',                                                                       # 133
    # system
    'Ach so, du wei\u00dft es nicht mehr. Pia hat Socken angezogen.'
    ' Waren die Socken bunt oder waren die Socken gleich?',                      # 134
    # child
    'gleich',                                                                    # 135
    # system
    'Ja, Pia hat gleiche Socken angezogen.'
    ' Pia hat viele Sachen am Morgen gemacht.'
    ' Hat Pia auch Hubert gef\u00fcttert oder hat Pia Carl gef\u00fcttert?',     # 136
    # child
    'hebert gef\u00fcttert',                                                     # 137
    # system
    'Ja, Pia hat Hubert gef\u00fcttert.'
    ' Pia hat Hubert Brokkoli gegeben.'
    ' Hat Hubert das gern gegessen oder nicht gern?',                            # 138
    # child
    'je',                                                                        # 139
    # system
    'Ja, Hubert hat das gern gegessen.'
    ' Soll Pia jetzt zur T\u00fcr gehen oder soll Pia noch bleiben?',           # 140
    # child
    't\u00fcr',                                                                  # 141
    # system
    'Ja, Pia geht zur T\u00fcr.'
    ' Hat Pia "Hallo" oder "Dankesch\u00f6n" gesagt?',                          # 142
    # child
    'warum',                                                                     # 143
    # system
    'Du fragst, warum Pia "Dankesch\u00f6n" gesagt hat.'
    ' Pia hat "Dankesch\u00f6n" gesagt,'
    ' weil Leute ihr etwas gesagt haben. Ist es jetzt klar?',                   # 144
    # child
    'ja',                                                                        # 145
    # system
    'Gut! Pia hat auch "Dankesch\u00f6n" gesagt.'
    ' Was haben die Leute Pia gefragt?'
    ' Haben die Leute nach dem Bett gefragt oder nach dem Hamster?',             # 146
    # child
    'warum fragst du nach dem bett?',                                            # 147
    # system
    'Du fragst, warum ich nach dem Bett frage.'
    ' Die Leute fragen Pia, ob sie ihr Bett gemacht hat.'
    ' Hat Pia das Bett gemacht oder nicht gemacht?',                             # 148
    # child
    'doch sie hat Bett gemacht',                                                 # 149
    # system
    'Ja, Pia hat das Bett gemacht.'
    ' Pia macht immer alles richtig. Stimmt das oder stimmt das nicht?',         # 150
    # child
    'stimmt',                                                                    # 151
    # system
    'Ja, das stimmt. Pia macht immer alles richtig.'
    ' Pia hat Freunde.'
    ' Hat Pia einen Freund oder hat Pia Freundinnen?',                           # 152
    # child
    'freundinnen',                                                               # 153
    # system
    'Ja, Pia hat Freundinnen.'
    ' Hei\u00dfen die Freundinnen Lisa und Sarah'
    ' oder Millie und Sarah?',                                                   # 154
    # child — TESTED: system response to this is judged
    'Lisa und sarah',                                                            # 155
]

# Example 4 (spec lines 171-173): Child feels lost
# Context: short conversation start, child says "weiß nicht" immediately.
# The system should express empathy AND provide a bridge/transition before helping.
SCRIPT_LOST_CHILD = [
    # child                                                                      # spec line
    'hallo',                                                                     # 171
    # system
    'Hallo! Wir h\u00f6ren uns gerade die Geschichte von Pia an, oder?'
    ' Was machen Pia und ihr Bruder Carl denn so am liebsten?',                  # 172
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                           # 173
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
class TestExplanationVerificationFixtureBased:
    """Strategy A: Verify explanation/correction verification against hardcoded state fixtures."""

    def test_concept_explanation_includes_verification(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Rhabarber): After a long conversation the child says 'nee'
        when asked if they know Rhabarber.  The system should explain it AND
        ask a verification question before continuing.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_RHABARBER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_EXPLANATION_VERIFICATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_EXPLANATION_VERIFICATION),
        )

    def test_word_explanation_includes_verification(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (heil): After a long conversation the child asks 'was ist
        heil'.  The system should explain the word AND ask a verification
        question before continuing.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_HEIL),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WORD_EXPLANATION_VERIFICATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WORD_EXPLANATION_VERIFICATION),
        )

    def test_correction_includes_verification(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Lisa vs Millie): After a long conversation the child gives
        a wrong answer.  The system should correct gently AND verify
        acknowledgment before moving on.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CORRECTION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CORRECTION_VERIFICATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CORRECTION_VERIFICATION),
        )

    def test_lost_child_empathy_bridge(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (weiß nicht): Early in the conversation the child says they
        don't know.  The system should express empathy AND provide a
        bridge/transition before offering help.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_LOST_CHILD),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_EMPATHY_BRIDGE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_EMPATHY_BRIDGE),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestExplanationVerificationSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    The scripts are child-first and used directly as child_inputs for
    simulate_conversation.  Pre-defined system responses keep the
    conversation deterministic up to the final turn, which is generated
    live and judged.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_concept_explanation_verification_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Rhabarber): Full simulation over many turns.
        Final response should explain Rhabarber AND verify understanding.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_RHABARBER,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_EXPLANATION_VERIFICATION,
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
                "Emma", 6, "weiblich", SCRIPT_RHABARBER,
                CRITERION_EXPLANATION_VERIFICATION,
            ),
        )

    def test_word_explanation_verification_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (heil): Full simulation over many turns.
        Final response should explain 'heil' AND verify understanding.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_HEIL,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_WORD_EXPLANATION_VERIFICATION,
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
                "Emma", 6, "weiblich", SCRIPT_HEIL,
                CRITERION_WORD_EXPLANATION_VERIFICATION,
            ),
        )

    def test_correction_verification_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Lisa vs Millie): Full simulation over many turns.
        Final response should correct AND verify acknowledgment.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_CORRECTION,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_CORRECTION_VERIFICATION,
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
                "Emma", 6, "weiblich", SCRIPT_CORRECTION,
                CRITERION_CORRECTION_VERIFICATION,
            ),
        )

    def test_lost_child_empathy_bridge_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (weiß nicht): Full simulation over a few turns.
        Final response should show empathy AND bridge before helping.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_LOST_CHILD,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_EMPATHY_BRIDGE,
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
                "Emma", 6, "weiblich", SCRIPT_LOST_CHILD,
                CRITERION_EMPATHY_BRIDGE,
            ),
        )
