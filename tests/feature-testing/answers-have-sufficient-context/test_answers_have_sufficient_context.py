"""
Feature: Answers-Have-Sufficient-Context
Test file: Does the system provide enough context in its responses so the
           child understands WHY a question is asked and WHAT is being asked?

The feature requires that when the system asks questions or transitions to
new topics, it provides sufficient background and bridging information so
the child can follow along.  Three scenarios are tested:
  1. Topic transition: when moving from one story scene to the next, the
     system should explain the connection rather than jumping abruptly.
  2. Confusion recovery: when the child explicitly says they don't
     understand what's being asked, the system should re-establish context
     clearly.
  3. Character transition: when switching from one character to another,
     the system should provide enough context about the new character.

Story used: "Pia muss nicht perfekt sein"

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

CRITERION_TOPIC_TRANSITION_CONTEXT = (
    "After the child answers 'schule' (school), the system transitions to the "
    "next story scene. Does the system response provide sufficient context so "
    "the child understands what is being asked? Specifically: does it use "
    "concrete nouns instead of vague pronouns, add a mini-sentence about the "
    "content before asking the question, or pick up a key element from the "
    "child's answer to frame the next question? Sentences should be short "
    "and use concrete objects. "
    "Return PASS if the system provides enough context that the child can "
    "understand what is being discussed and why the question is being asked, "
    "FAIL if the question comes without clear context or uses vague references "
    "that a child could not follow."
)

CRITERION_CLARITY_AFTER_CONFUSION = (
    "The child explicitly said 'nein, ich weiß nicht, was du von mir willst' "
    "(no, I don't know what you want from me), indicating complete confusion "
    "about what is being discussed. Does the system response: "
    "(1) clearly re-establish context about what they are talking about "
    "(the story of Pia), AND "
    "(2) provide a clear, simple question or invitation that the child can "
    "understand and respond to, with enough context that the child knows "
    "what is expected? "
    "Return PASS if the system re-establishes context clearly and asks "
    "a well-framed question the child can follow, "
    "FAIL if the response remains vague or assumes the child can follow "
    "without additional context."
)

CRITERION_CHARACTER_TRANSITION_CONTEXT = (
    "After the child agrees 'ja, pia genau' (yes, Pia is exact), the system "
    "transitions to the next part of the story. Does the system response use "
    "concrete language with sufficient context? Specifically: pronouns like "
    "'das' or 'es' should be replaced or supplemented with concrete actions "
    "or descriptions. If the system mentions a new character or topic, it "
    "should name the concrete action or relationship, not just use vague "
    "references. Questions should have a clear connection to what was just "
    "discussed. "
    "Return PASS if the system uses concrete nouns/descriptions and provides "
    "enough context for the child to follow the conversation, "
    "FAIL if it uses vague pronouns (like 'das', 'es') without clarifying "
    "what they refer to, or asks questions without sufficient context."
)

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 40-52): Topic transition — school to cooking
SCRIPT_TOPIC_TRANSITION = [
    # child                                                                      # spec line
    'hallo',                                                                     # 40
    # system
    'Hallo! Ich bin Thilio.'
    ' Hast du die Geschichte von Pia geh\u00f6rt,'
    ' die eigentlich immer alles richtig macht?',                                # 41
    # child
    'ja',                                                                        # 42
    # system
    'Pia macht fast nie Fehler.'
    ' Sie begr\u00fc\u00dft ihre Fans und hat ihre Mathehausaufgaben gemacht.'
    ' Was macht Pia mit ihrem Hamster Hubert?',                                  # 43
    # child
    'gibt essn',                                                                 # 44
    # system
    'Ja, Pia gibt Hubert Essen.'
    ' Mag Hubert lieber Brokkoli oder lieber Nudeln?',                           # 45
    # child
    'Brokkoli mag',                                                              # 46
    # system
    'Ja, Hubert mag Brokkoli!'
    ' Pia hat auch einen Bruder.'
    ' Pia schmiert ein Pausenbrot. Was kommt auf das Brot?',                     # 47
    # child
    'Marmelade und erdnussbutter',                                               # 48
    # system
    'Genau, Pia nimmt Marmelade und Erdnussbutter.'
    ' Pia will gleichen Mengen nehmen. Was macht sie?',                          # 49
    # child
    'sie nimmt gleich viel Erdnussbutter und Marmelade',                         # 50
    # system
    'Ja, Pia nimmt gleich viel Erdnussbutter und Marmelade.'
    ' Pia ist gut vorbereitet. Sie macht alles richtig.'
    ' Pia geht jetzt ...?',                                                     # 51
    # child — TESTED: system response to this is judged
    'schule',                                                                    # 52
]

# Example 2 (spec lines 69-79): Confusion recovery — child doesn't understand
SCRIPT_CONFUSION_RECOVERY = [
    # child                                                                      # spec line
    'hallo',                                                                     # 69
    # system
    'Hallo! Ich bin Thilo, dein Sprachf\u00f6rder-Spielzeug.'
    ' Ich kenne die Geschichte von Pia,'
    ' die immer alles richtig macht.'
    ' Sprechen wir zusammen dar\u00fcber!'
    ' Was hat Pia als Erstes an diesem besonderen Freitag gemacht?',             # 70
    # child
    'gegessen',                                                                  # 71
    # system
    'Pia hat an diesem Morgen gegessen.'
    ' Hat Pia Socken angezogen oder Z\u00e4hne geputzt?',                       # 72
    # child
    'socken',                                                                    # 73
    # system
    'Ja, Pia hat Socken angezogen.'
    ' Hat Pia die Socken gefunden oder nicht gefunden?',                         # 74
    # child
    'gefunden',                                                                  # 75
    # system
    'Pia hat die Socken gefunden.'
    ' Pia sucht \u2026 Was sucht Pia?',                                         # 76
    # child
    'ich verstehe dich nicht',                                                   # 77
    # system
    'Ach so, du verstehst das Wort "suchen" nicht.'
    ' Suchen bedeutet, dass man etwas finden m\u00f6chte,'
    ' was man noch nicht sehen kann. Ist es jetzt klar?',                        # 78
    # child — TESTED: system response to this is judged
    'nein, ich wei\u00df nicht, was du von mir willst',                          # 79
]

# Example 3 (spec lines 90-110): Character transition — Pia to Carl
SCRIPT_CHARACTER_TRANSITION = [
    # child                                                                      # spec line
    'hallo',                                                                     # 90
    # system
    'Hallo! Ich bin Thilio.'
    ' Hast du die Geschichte von Pia geh\u00f6rt,'
    ' die eigentlich immer alles richtig macht?',                                # 91
    # child
    'ja',                                                                        # 92
    # system
    'Super! Pia ist wirklich besonders, oder?'
    ' Sie begr\u00fc\u00dft zum Beispiel jeden Morgen ihre Fans vor der T\u00fcr.'
    ' Hat sie ihnen "Guten Morgen" oder "Guten Abend" gesagt?',                  # 93
    # child
    'guten Morgen',                                                              # 94
    # system
    'Ja, genau, sie hat "Guten Morgen" gesagt.'
    ' Pia ist echt ordentlich, nicht wahr? Findest du das auch gut?',            # 95
    # child
    'ja gut',                                                                    # 96
    # system
    'Pia ist wirklich super organisiert.'
    ' Sie hat sogar darauf geachtet,'
    ' dass ihr Hamster Hubert sein Lieblingsessen bekommt.'
    ' Wei\u00dft du noch, was Hubert am liebsten gefuttert hat?'
    ' War es Marmelade oder Brokkoli?',                                          # 97
    # child
    'es ist Brokkolis',                                                          # 98
    # system
    'Ja, Brokkoli! Hubert mag Brokkoli.'
    ' Es ist gr\u00fcn und gesund, und Hubert knabbert es gern.'
    ' Was ist das?',                                                             # 99
    # child
    'Brokolis?',                                                                 # 100
    # system
    'Ja, stimmt genau! Der Brokkoli ist gr\u00fcn.'
    ' Und wer bekommt ihn? Der Brokkoli geh\u00f6rt ...?',                     # 101
    # child
    'Hubert?',                                                                   # 102
    # system
    'Ja, super! Der Brokkoli ist f\u00fcr Hubert.'
    ' Stell dir vor, du bist Hubert, der Hamster.'
    ' Was machst du jetzt mit dem Brokkoli?',                                    # 103
    # child
    'ich esse Brokkol',                                                          # 104
    # system
    'Mmmh, lecker! Hubert mag seinen Brokkoli.'
    ' Pia hat auch ihrem Bruder Carl ein Pausenbrot gemacht.'
    ' Sie hat Erdnussbutter und Marmelade drauf geschmiert.'
    ' Wei\u00dft du noch, wie viel von jedem?'
    ' War es gleich viel, oder mehr Erdnussbutter?',                             # 105
    # child
    'gleich viel',                                                               # 106
    # system
    'Ja, genau! Pia hat gleich viel Erdnussbutter und Marmelade genommen.'
    ' Pia hat ... geschmiert. Was passt da rein?',                               # 107
    # child
    'brot',                                                                      # 108
    # system
    'Ja, Pia hat das Brot geschmiert.'
    ' Pia ist echt genau, findest du nicht?',                                    # 109
    # child — TESTED: system response to this is judged
    'ja, pia genau',                                                             # 110
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
class TestSufficientContextFixtureBased:
    """Strategy A: Verify sufficient context in responses against hardcoded state fixtures."""

    def test_topic_transition_has_context(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (schule → cooking): The child says 'schule'.  The system
        should provide context connecting school to the cooking team before
        asking what they want to cook.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_TOPIC_TRANSITION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_TOPIC_TRANSITION_CONTEXT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_TOPIC_TRANSITION_CONTEXT),
        )

    def test_clarity_after_confusion(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (ich weiß nicht, was du von mir willst): The child is
        completely confused.  The system should re-establish context clearly
        and ask a well-framed question.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CONFUSION_RECOVERY),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CLARITY_AFTER_CONFUSION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CLARITY_AFTER_CONFUSION),
        )

    def test_character_transition_has_context(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Pia → Carl): The child agrees Pia is exact.  The system
        should introduce Carl with sufficient context (who he is, how he
        differs from Pia) before asking about him.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CHARACTER_TRANSITION),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CHARACTER_TRANSITION_CONTEXT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CHARACTER_TRANSITION_CONTEXT),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestSufficientContextSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_topic_transition_context_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (schule → cooking): Full simulation.
        Final response should connect school to cooking with context.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_TOPIC_TRANSITION,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_TOPIC_TRANSITION_CONTEXT,
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
                "Emma", 6, "weiblich", SCRIPT_TOPIC_TRANSITION,
                CRITERION_TOPIC_TRANSITION_CONTEXT,
            ),
        )

    def test_clarity_after_confusion_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (ich weiß nicht, was du von mir willst): Full simulation.
        Final response should re-establish context clearly.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_CONFUSION_RECOVERY,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_CLARITY_AFTER_CONFUSION,
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
                "Emma", 6, "weiblich", SCRIPT_CONFUSION_RECOVERY,
                CRITERION_CLARITY_AFTER_CONFUSION,
            ),
        )

    def test_character_transition_context_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (Pia → Carl): Full simulation.
        Final response should introduce Carl with sufficient context.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_CHARACTER_TRANSITION,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_CHARACTER_TRANSITION_CONTEXT,
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
                "Emma", 6, "weiblich", SCRIPT_CHARACTER_TRANSITION,
                CRITERION_CHARACTER_TRANSITION_CONTEXT,
            ),
        )
