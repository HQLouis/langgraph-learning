"""
Feature: Explanation-Correction-Verification
Test file: Transition from explanation/correction to next topic — does the
           system verify the child's understanding before continuing?

The feature requires that after the system:
  1. Explains a concept the child doesn't know (e.g. Rhabarber)
  2. Corrects a wrong answer (e.g. Lisa vs Millie)
...it must include a verification step (asking the child whether they
understood) before moving on to the regular conversation.

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
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
)

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Story fixture — "Pia muss nicht perfekt sein"
# ---------------------------------------------------------------------------

FIXTURE_PIA_AUDIO_BOOK: str = """\
Pia muss nicht perfekt sein. \
F\u00fcr Pia Piretti begann der Freitag wie jeder andere Tag. \
Sie suchte Socken aus, die zusammenpassten. \
Und nat\u00fcrlich zog sie jeden Schuh an den richtigen Fu\u00df. \
Sie verga\u00df nicht, ihrem Hamster Hubert sein Lieblingsessen zu f\u00fcttern: Brokkoli. \
Und als sie das Pausenbrot f\u00fcr ihren Bruder Carl schmierte, \
nahm sie daf\u00fcr haargenau so viel Erdnussbutter wie Marmelade. \
Als sie vor die T\u00fcr ging, um ihre Fans zu begr\u00fc\u00dfen, \
sagte sie 'Guten Morgen' und 'Dankesch\u00f6n'. \
Die Leute fragten, ob sie ihr Bett gemacht hatte. Hatte sie. \
Sie wollten wissen, ob sie vielleicht ihre Mathehausaufgaben vergessen hatte. N\u00f6. \
'Was ist mit dem Talentwettbewerb heute Abend?', wollten sie wissen. \
'Von mir aus kann's losgehen!', antwortete Pia l\u00e4chelnd. \
Schlie\u00dflich hatte sie mit ihrer Jongliernummer in den letzten drei Jahren immer gewonnen. \
Die meisten Menschen in der Stadt wussten nicht einmal, wie Pia wirklich hie\u00df. \
Sie nannten sie nur 'das M\u00e4dchen, das immer alles richtig macht', \
denn solange man denken konnte, war ihr noch nie ein Fehler passiert. \
Anders als Pia machte Carl jede Menge Fehler. \
Er a\u00df seine Wachsmalkreide und malte mit gr\u00fcnen Bohnen. \
Er tanzte mit den H\u00e4nden und spielte mit den F\u00fc\u00dfen Klavier. \
F\u00fcr Carl war es das Gr\u00f6\u00dfte, Dinge falsch zu machen! \
In der Schule war Pia mit ihren zwei besten Freundinnen, Millie und Sarah, in einem Kochteam. \
F\u00fcr ihren Riesenrhabarbermuffin brauchten sie Eier. \
Pia ging zum K\u00fchlschrank und w\u00e4hlte sorgf\u00e4ltig die gr\u00f6\u00dften und \
sch\u00f6nsten Eier aus, die sie finden konnte. \
Doch auf dem R\u00fcckweg rutschte sie aus. \
Die Eier flogen in hohem Bogen durch die Luft. \
Und Pia war kurz davor, ihren ersten Fehler zu machen! Tat sie aber nicht! \
'Das war knapp!', dachte Pia. \
'Tut mir leid, Pia... Ich habe ein St\u00fcck Rhabarber fallen lassen.' \
Auf dem Heimweg schaute Pia zu, wie Millie und Sarah im Park Schlittschuh liefen. \
'Komm doch zu uns!', rief Millie. 'Es macht Spa\u00df!', sagte Sarah. \
Pia beobachtete, wie sie \u00fcber den gefrorenen Teich rutschten und schlidderten. \
Millie und Sarah lachten, w\u00e4hrend sie \u00fcbers Eis stolperten. \
'Nein, danke', sagte Pia. \
Beim Abendessen r\u00fchrte Pia ihr Essen kaum an. \
'Ist alles in Ordnung, Sp\u00e4tzchen?', fragte ihr Vater. \
'Ich habe Angst, dass ich es heute verpatze', gestand Pia. 'Und alle werden es sehen.' \
'Angst? Aber du machst doch nie etwas falsch!', sagte ihr Vater mit einem L\u00e4cheln. \
Pia versuchte, auch zu l\u00e4cheln. \
Nach dem Essen machte sich Pia f\u00fcr den Talentwettbewerb bereit. \
Zuerst weckte sie Hubert, der ein Nickerchen gemacht hatte. \
Dann holte sie den Salzstreuer vom K\u00fcchentisch. \
Am Ende bef\u00fcllte sie einen Luftballon mit Wasser. \
Die Aula der Schule war gerammelt voll! In Pias Bauch ging es drunter und dr\u00fcber. \
Pia wartete darauf, dass ihre Jonglier-Musik einsetzte. \
'Da ist sie! Das ist das M\u00e4dchen, das immer alles richtig macht!', sagte eine Frau. \
'Oh! Bei ihr l\u00e4uft immer alles perfekt, immer!', rief ein Mann. \
Als die Musik einsetzte, warf Pia Hubert in die Luft. \
SUPER PIA! Als N\u00e4chstes kam der Salzstreuer. Und zum Schluss der Wasserballon. \
Pia war ganz bei der Sache! Die Zuschauer klatschten begeistert. \
Doch dann fiel Pia am Salzstreuer etwas Komisches auf... \
Die K\u00f6rner, die herausrieselten, waren nicht wei\u00df! \
HATSCHI! \
Hubert war von seinem eigenen Niesen so \u00fcberrascht, \
dass er sich mit seinen kleinen Krallen am Luftballon festklammerte. \
PENG! Hubert, kleine Ballonfetzen und Pfeffer: Alles regnete auf Pias Kopf. \
Zum ersten Mal, solange man denken konnte, hatte Pia einen Fehler gemacht. \
Und was f\u00fcr einen... \
Die Musik verstummte. Pia wusste nicht, was sie machen sollte. \
Weinen? Von der B\u00fchne rennen? \
Die Zuschauer hockten wie versteinert da. \
Sie konnten nicht glauben, dass dem M\u00e4dchen, das immer alles richtig macht, \
ein Fehler passiert war! \
Pia schaute zu Hubert. Der schaute zur\u00fcck. \
Sein Hamsterfell war pitschnass und voller kleiner Ballonreste. \
Pia musste kichern. Ihr Kichern wurde zu einem Glucksen. \
Und aus dem Glucksen wurde ein richtig lautes Lachen.\
"""

FIXTURE_PIA_STORY_ID: str = "pia_muss_nicht_perfekt_sein"
FIXTURE_PIA_CHAPTER_ID: str = "chapter_01"


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

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from feature-test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 40-66): Rhabarber explanation
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

# Example 2 (spec lines 85-109): Correction after wrong answer
# Context: long conversation about Pia's story, ending with the child giving
# the wrong friend name.  The system should correct AND verify.
SCRIPT_CORRECTION = [
    # child                                                                      # spec line
    'Start',                                                                     # 85
    # system
    'Hallo! Ich bin Thilio, dein sprechendes Spielzeug.'
    ' Wir haben eben die Geschichte von Pia geh\u00f6rt, oder?'
    ' Pia ist ja wirklich ein besonderes M\u00e4dchen!'
    ' Wei\u00dft du noch, wie der Freitag f\u00fcr Pia angefangen hat?',         # 86
    # child
    'nee',                                                                       # 87
    # system
    'Ach so, du wei\u00dft es nicht mehr. Pia hat Socken angezogen.'
    ' Waren die Socken bunt oder waren die Socken gleich?',                      # 88
    # child
    'gleich',                                                                    # 89
    # system
    'Ja, Pia hat gleiche Socken angezogen.'
    ' Pia hat viele Sachen am Morgen gemacht.'
    ' Hat Pia auch Hubert gef\u00fcttert oder hat Pia Carl gef\u00fcttert?',     # 90
    # child
    'hebert gef\u00fcttert',                                                     # 91
    # system
    'Ja, Pia hat Hubert gef\u00fcttert.'
    ' Pia hat Hubert Brokkoli gegeben.'
    ' Hat Hubert das gern gegessen oder nicht gern?',                            # 92
    # child
    'je',                                                                        # 93
    # system
    'Ja, Hubert hat das gern gegessen.'
    ' Soll Pia jetzt zur T\u00fcr gehen oder soll Pia noch bleiben?',           # 94
    # child
    't\u00fcr',                                                                  # 95
    # system
    'Ja, Pia geht zur T\u00fcr.'
    ' Hat Pia "Hallo" oder "Dankesch\u00f6n" gesagt?',                          # 96
    # child
    'warum',                                                                     # 97
    # system
    'Du fragst, warum Pia "Dankesch\u00f6n" gesagt hat.'
    ' Pia hat "Dankesch\u00f6n" gesagt,'
    ' weil Leute ihr etwas gesagt haben. Ist es jetzt klar?',                   # 98
    # child
    'ja',                                                                        # 99
    # system
    'Gut! Pia hat auch "Dankesch\u00f6n" gesagt.'
    ' Was haben die Leute Pia gefragt?'
    ' Haben die Leute nach dem Bett gefragt oder nach dem Hamster?',             # 100
    # child
    'warum fragst du nach dem bett?',                                            # 101
    # system
    'Du fragst, warum ich nach dem Bett frage.'
    ' Die Leute fragen Pia, ob sie ihr Bett gemacht hat.'
    ' Hat Pia das Bett gemacht oder nicht gemacht?',                             # 102
    # child
    'doch sie hat Bett gemacht',                                                 # 103
    # system
    'Ja, Pia hat das Bett gemacht.'
    ' Pia macht immer alles richtig. Stimmt das oder stimmt das nicht?',         # 104
    # child
    'stimmt',                                                                    # 105
    # system
    'Ja, das stimmt. Pia macht immer alles richtig.'
    ' Pia hat Freunde.'
    ' Hat Pia einen Freund oder hat Pia Freundinnen?',                           # 106
    # child
    'freundinnen',                                                               # 107
    # system
    'Ja, Pia hat Freundinnen.'
    ' Hei\u00dfen die Freundinnen Lisa und Sarah'
    ' oder Millie und Sarah?',                                                   # 108
    # child — TESTED: system response to this is judged
    'Lisa und sarah',                                                            # 109
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
        state = build_state(
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

    def test_correction_includes_verification(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (Lisa vs Millie): After a long conversation the child gives
        a wrong answer.  The system should correct gently AND verify
        acknowledgment before moving on.
        """
        state = build_state(
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

    def test_correction_verification_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (Lisa vs Millie): Full simulation over many turns.
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
