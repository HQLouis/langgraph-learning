"""
Feature: Different-Sentence-Starters
Test file: Does the system use varied sentence starters rather than
           repeating the same patterns (e.g. "Du sagst...", "Du hast
           gesagt...", "Ja, ...") throughout a conversation?

The feature requires that the system's responses use diverse sentence
openers.  When previous responses in the conversation already used certain
starters (e.g. "Du sagst", "Du hast gesagt", "Ja,"), the next response
should vary.  A starter may repeat once in a row but not more.

Story used: "Bobos Adventskalender"

Conversation scripts are taken verbatim from the spec file.  Each line in
the spec is one atomic message — never split or combined.  The conversations
are child-first and odd-length.  The last child message triggers a live
system response that is evaluated by the judge.

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

CRITERION_VARIED_STARTERS_SHORT = (
    "Look at the system responses in the conversation history. Several "
    "previous system responses start with 'Ja, ...' as their opening. "
    "Does the NEW system response (the last one) use a DIFFERENT sentence "
    "starter — i.e. NOT begin with the same word or phrase pattern as the "
    "majority of recent system responses? "
    "Acceptable variety includes starters like: 'Stimmt!', 'Genau!', "
    "'Weißt du...', 'Schau mal...', 'Und dann...', 'Oh!', 'Aha!', "
    "or any other opener that differs from the repetitive pattern. "
    "Return PASS if the new response uses a noticeably different starter "
    "than the dominant pattern in recent responses, "
    "FAIL if it repeats the same starter pattern yet again."
)

CRITERION_VARIED_STARTERS_MID = (
    "Look at the system responses in the conversation history. Multiple "
    "previous system responses start with 'Du hast gesagt' or 'Du sagst' "
    "as their opening pattern. Does the NEW system response (the last one) "
    "avoid repeating this 'Du hast gesagt'/'Du sagst'/'Du' pattern and "
    "instead use a different sentence starter? "
    "Return PASS if the new response begins differently from the dominant "
    "'Du...' pattern in recent responses, "
    "FAIL if it starts with 'Du hast gesagt', 'Du sagst', 'Du weißt', "
    "or another 'Du + verb' construction that matches the repetitive pattern."
)

CRITERION_VARIED_STARTERS_LONG = (
    "Look at the system responses in the conversation history. The vast "
    "majority start with 'Du sagst', 'Du fragst', 'Du weißt es nicht', "
    "or similar 'Du + verb' patterns — an extremely repetitive style. "
    "Does the NEW system response (the last one) break this pattern by "
    "using a genuinely different sentence opener? "
    "Return PASS if the new response does NOT start with 'Du' followed "
    "by a verb (i.e. uses a clearly different opening), "
    "FAIL if it continues the 'Du + verb' pattern."
)

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 27-33): Short conversation — "Ja, ..." repetition
SCRIPT_SHORT_CONVERSATION = [
    # child                                                                      # spec line
    'hallo',                                                                     # 27
    # system
    'Hallo, ich bin Thilio, dein sprechendes Spielzeug!'
    ' Ich habe die Geschichte von Bobos Adventskalender geh\u00f6rt.'
    ' Was haben Bobo und sein Papa denn zuerst zusammen gemacht?',               # 28
    # child
    'post gewartet',                                                             # 29
    # system
    'Ja, Bobo und Papa Siebenschl\u00e4fer warten auf die Post.'
    ' Wer kommt denn mit der Post?',                                             # 30
    # child
    'postfrau',                                                                  # 31
    # system
    'Ja, die Postfrau kommt.'
    ' Soll Bobo mit dem neuen Fahrrad fahren'
    ' oder lieber die Post tragen?',                                             # 32
    # child — TESTED: system response to this is judged
    'Fahrrad fahren',                                                            # 33
]

# Example 2 (spec lines 43-57): Mid-length — "Du hast gesagt"/"Du sagst" repetition
SCRIPT_MID_CONVERSATION = [
    # child                                                                      # spec line
    'hallo',                                                                     # 43
    # system
    'Hallo, ich bin Thilio, dein Sprachbegleiter.'
    ' Bobo und Papa Siebenschl\u00e4fer haben zusammen ein gro\u00dfes Paket'
    ' von der Post geholt.'
    ' Wei\u00dft du noch, was in dem Paket war?',                               # 44
    # child
    'kalender',                                                                  # 45
    # system
    'Du hast gesagt, es war ein Kalender.'
    ' Papa Siebenschl\u00e4fer hatte eine Idee mit dem Kalender.'
    ' Sollen sie den Kalender aufh\u00e4ngen'
    ' oder einen Adventskalender basteln?',                                      # 46
    # child
    'basteln',                                                                   # 47
    # system
    'Ja, Bobo und Papa wollen einen Adventskalender basteln.'
    ' Zum Basteln brauchen sie \u2026 Was brauchen sie?',                       # 48
    # child
    'pappe',                                                                     # 49
    # system
    'Du sagst, sie brauchen Pappe.'
    ' Sie schneiden in die Pappe \u2026 Was schneiden sie?',                    # 50
    # child
    'fenster',                                                                   # 51
    # system
    'Ja, sie schneiden Fenster in die Pappe.'
    ' Bobo malt danach noch etwas auf die Pappe.'
    ' Mal sehen \u2026'
    ' Malt Bobo ein Auto oder malt Bobo ein Haus?',                             # 52
    # child
    'ein haus',                                                                  # 53
    # system
    'Ja, Bobo malt ein Haus.'
    ' Bobo malt auch B\u00e4ume und einen Mond auf die Pappe.'
    ' Dann h\u00e4ngt Papa den Kalender ans Fenster.'
    ' Was macht jetzt Mama?',                                                    # 54
    # child
    'einkaufen',                                                                 # 55
    # system
    'Du hast gesagt, Mama geht einkaufen.'
    ' Mama kommt nach Hause und sieht den Adventskalender.'
    ' Sie findet ihn sehr sch\u00f6n. Was fragt Mama?',                        # 56
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                           # 57
]

# Example 3 (spec lines 67-108): Long conversation — heavy "Du sagst"/"Du"
# repetition throughout
SCRIPT_LONG_CONVERSATION = [
    # child                                                                      # spec line
    'hallo',                                                                     # 67
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben ja gerade zusammen die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du noch, wer Bobo und Papa Siebenschl\u00e4fer am Anfang'
    ' der Geschichte am K\u00fcchenfenster gesehen haben?',                     # 68
    # child
    'nein',                                                                      # 69
    # system
    'Ach so, du wei\u00dft es nicht mehr.'
    ' Bobo und Papa haben am Anfang die Postbotin gesehen.'
    ' Sie hatte ein neues Fahrrad.'
    ' Kannst du dich daran erinnern,'
    ' was die Postbotin Bobo gefragt hat?',                                     # 70
    # child
    'nein',                                                                      # 71
    # system
    'Du wei\u00dft es nicht?'
    ' Die Postbotin hat Bobo gefragt,'
    ' ob er mal auf ihrem neuen Fahrrad sitzen m\u00f6chte.'
    ' Was hat denn Bobos Papa gemacht,'
    ' damit Bobo auf dem Fahrrad sitzen kann?',                                 # 72
    # child
    'helm',                                                                      # 73
    # system
    'Du sagst Helm? Fast!'
    ' Im Buch hat Papa Bobo noch keinen Helm aufgesetzt.'
    ' Papa hat Bobo auf den Sattel gehoben.'
    ' Wei\u00dft du noch, was Bobo gemacht hat,'
    ' als er auf dem Fahrrad sa\u00df?',                                        # 74
    # child
    'sattel?',                                                                   # 75
    # system
    'Du fragst nach dem Sattel?'
    ' Der Sattel ist der Sitz auf dem Fahrrad.'
    ' Auf dem Sattel sitzt Bobo.'
    ' Kannst du dich erinnern, was Bobo gemacht hat,'
    ' als er auf dem Sattel sa\u00df?',                                         # 76
    # child
    'nein',                                                                      # 77
    # system
    'Du wei\u00dft es nicht mehr?'
    ' Bobo hat Klingeling mit der Fahrradklingel gemacht.'
    ' Was hat die Postbotin gemacht,'
    ' nachdem Bobo auf dem Fahrrad sa\u00df?',                                  # 78
    # child
    'wei\u00df nicht',                                                           # 79
    # system
    'Du wei\u00dft nicht, was die Postbotin gemacht hat.'
    ' Die Postbotin musste weiterfahren.'
    ' Sie hat Papa Siebenschl\u00e4fer noch die Post gegeben.'
    ' Was durfte Bobo mit der Post machen?',                                    # 80
    # child
    'wei\u00df nicht',                                                           # 81
    # system
    'Du wei\u00dft es nicht?'
    ' Bobo durfte die Werbeprospekte ins Haus tragen.'
    ' Was war denn noch in der Post?',                                           # 82
    # child
    'Werbeprospekte gab es in der geschichte?',                                  # 83
    # system
    'Du fragst, ob es Werbeprospekte in der Geschichte gab?'
    ' Ja, Bobo durfte die Werbeprospekte ins Haus tragen.'
    ' Was hat denn Papa Siebenschl\u00e4fer mit den Briefen gemacht?',          # 84
    # child
    'wei\u00df nicht',                                                           # 85
    # system
    'Du wei\u00dft es nicht?'
    ' Papa Siebenschl\u00e4fer hat die Stirn gerunzelt,'
    ' weil ein Zettel dabei war.'
    ' Was stand auf dem Zettel?',                                                # 86
    # child
    'post',                                                                      # 87
    # system
    'Du sagst Post. Ja, der Zettel hatte mit der Post zu tun.'
    ' Auf dem Zettel stand, dass Papa und Bobo ein Paket abholen m\u00fcssen.'
    ' Was hat Papa gesagt, wo sie das Paket abholen m\u00fcssen?',              # 88
    # child
    'bei post',                                                                  # 89
    # system
    'Du sagst, sie holen das Paket bei der Post ab. Stimmt!'
    ' Wie sind Bobo und Papa Siebenschl\u00e4fer zur Post gefahren?',           # 90
    # child
    'fahrraD',                                                                   # 91
    # system
    'Ja, Bobo und Papa sind mit dem Fahrrad zur Post gefahren.'
    ' Wo sa\u00df Bobo auf dem Fahrrad?',                                      # 92
    # child
    'hinten',                                                                    # 93
    # system
    'Ja, Bobo sa\u00df hinten auf dem Kindersitz.'
    ' Was musste Bobo aufsetzen, bevor die Fahrt losging?',                     # 94
    # child
    'helm',                                                                      # 95
    # system
    'Genau, Bobo musste seinen Helm aufsetzen.'
    ' Was hat Papa vor der Post gemacht?',                                       # 96
    # child
    'wei\u00df nicht',                                                           # 97
    # system
    'Du wei\u00dft es nicht?'
    ' Papa hat das Fahrrad vor der Post angeschlossen.'
    ' Was durfte Bobo am Postschalter machen?',                                 # 98
    # child
    'winken',                                                                    # 99
    # system
    'Winken? Im Buch hat Bobo am Postschalter nicht gewunken.'
    ' Bobo durfte den Zettel abgeben.'
    ' Wer hat das Paket geholt?',                                                # 100
    # child
    'bobo',                                                                      # 101
    # system
    'Bobo hat mitgeholfen, aber die Beamtin hat das Paket geholt'
    ' und um den Schalter herumgetragen.'
    ' Wie haben Bobo und Papa das Paket nach Hause bekommen?',                  # 102
    # child
    'mit fahrr',                                                                 # 103
    # system
    'Du sagst mit Fahrrad. Fast!'
    ' Sie sind mit dem Fahrrad gegangen und haben es geschoben,'
    ' weil das Paket so gro\u00df war.'
    ' Was war in dem Paket drin?',                                               # 104
    # child
    'dann haben sie Kalender gebastelt',                                         # 105
    # system
    'Ja, Bobo und Papa haben einen Kalender gebastelt.'
    ' Aber was war denn in dem Paket,'
    ' bevor sie angefangen haben zu basteln?',                                  # 106
    # child — TESTED: system response to this is judged
    'kalender',                                                                  # 107
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
class TestDifferentSentenceStartersFixtureBased:
    """Strategy A: Verify varied sentence starters against hardcoded state fixtures."""

    def test_varied_starters_short_conversation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Short conversation where system responses start with 'Ja, ...'.
        The next response should vary its opener.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_SHORT_CONVERSATION),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_VARIED_STARTERS_SHORT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_VARIED_STARTERS_SHORT),
        )

    def test_varied_starters_mid_conversation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Mid-length conversation with repetitive 'Du hast gesagt' /
        'Du sagst' starters.  The next response should vary.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_MID_CONVERSATION),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_VARIED_STARTERS_MID)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_VARIED_STARTERS_MID),
        )

    def test_varied_starters_long_conversation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Long conversation with extremely repetitive 'Du + verb'
        starters.  The next response must break this pattern.
        """
        state = build_state_with_beats(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_LONG_CONVERSATION),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_VARIED_STARTERS_LONG)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_VARIED_STARTERS_LONG),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestDifferentSentenceStartersSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_varied_starters_short_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Full simulation — short conversation.
        Final response should vary its sentence starter.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_SHORT_CONVERSATION,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_VARIED_STARTERS_SHORT,
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
                "Emma", 6, "weiblich", SCRIPT_SHORT_CONVERSATION,
                CRITERION_VARIED_STARTERS_SHORT,
            ),
        )

    def test_varied_starters_mid_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Full simulation — mid-length conversation.
        Final response should avoid repetitive 'Du' starters.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_MID_CONVERSATION,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_VARIED_STARTERS_MID,
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
                "Emma", 6, "weiblich", SCRIPT_MID_CONVERSATION,
                CRITERION_VARIED_STARTERS_MID,
            ),
        )

    def test_varied_starters_long_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Full simulation — long conversation.
        Final response must break 'Du + verb' pattern.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_LONG_CONVERSATION,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_VARIED_STARTERS_LONG,
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
                "Emma", 6, "weiblich", SCRIPT_LONG_CONVERSATION,
                CRITERION_VARIED_STARTERS_LONG,
            ),
        )
