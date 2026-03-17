"""
Feature: Incorrect Story Facts
Test file: When child gives wrong story information, system should correct
           gently and without judgment.

The feature requires that when a child provides incorrect facts about the
story, the system:
  - Corrects the information gently (not critically or judgmentally)
  - May ask a small confirmation to check the child remembers
  - For short/simple corrections, gives the correct answer directly
  - Incorporates correct information neutrally

Stories used:
  - "Pia muss nicht perfekt sein" (Examples 1, 3)
  - "Bobos Adventskalender" (Example 2)

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
# Story fixture — "Bobos Adventskalender"
# ---------------------------------------------------------------------------

FIXTURE_BOBO_AUDIO_BOOK: str = """\
Bobos Adventskalender. \
Was machen Bobo und Papa Siebenschl\u00e4fer denn da? \
Sie schauen aus dem K\u00fcchenfenster. Die B\u00e4ume sind kahl. \
Es ist Ende November. Da kommt die Postbotin angefahren. \
Bobo und Papa gehen zu ihr nach drau\u00dfen. \
Die Postbotin hat ein neues Fahrrad. \
M\u00f6chtest du mal darauf sitzen? fragt die Postbotin Bobo. \
Das m\u00f6chte Bobo gern! Papa hilft ihm auf den Sattel. \
Klingeling!, macht die Fahrradklingel. \
Jetzt muss die Postbotin aber weiter. \
Vorher gibt sie Papa Siebenschl\u00e4fer noch die Post. \
Bobo darf die Werbeprospekte ins Haus tragen. \
Zwischen den Briefen liegt ein Zettel. Papa runzelt die Stirn. \
Wir m\u00fcssen zur Post gehen, Bobo. Da liegt ein Paket f\u00fcr uns, sagt er. \
Papa holt sein Fahrrad. Bobo freut sich: \
Er liebt es hinten auf dem Kindersitz mitzufahren. \
Nur noch den Helm aufsetzen - und fertig! \
Hui! Papa und Bobo sausen den H\u00fcgel hinunter! \
Vor der Post schlie\u00dft Papa das Fahrrad an. Dann gehen sie hinein. \
Am Postschalter darf Bobo den Zettel abgeben. \
Die Beamtin holt ein gro\u00dfes Paket. \
Sie muss um den Schalter herumgehen, \
damit Papa und Bobo es nehmen k\u00f6nnen. \
Bobo und Papa tragen das Paket zusammen. \
Aber wie sollen sie mit dem gro\u00dfen Paket Fahrrad fahren? \
Wir m\u00fcssen schieben, sagt Papa. \
Papa und Bobo gehen zu Fu\u00df nach Hause. \
Das Paket darf auf Bobos Kindersitz mitfahren. \
Zu Hause packen Bobo und Papa das Paket aus. \
Darin ist ein gro\u00dfer Fotokalender f\u00fcr das n\u00e4chste Jahr. \
Papa hat eine Idee: Wollen wir zusammen einen Adventskalender basteln?, \
fragt er Bobo. Oh ja! ruft Bobo. Er liebt basteln. \
Papa und Bobo holen alle Sachen, die sie zum Basteln brauchen: \
eine gro\u00dfe Pappe, Transparentpapier, ein scharfes Messer, \
Filzstifte und einen Klebestift. \
Papa schneidet mit dem scharfen Messer 24 \u00d6ffnungen in die Pappe. \
Dann klebt er das Transparentpapier auf die Pappe. \
Jetzt darf Bobo ein gro\u00dfes Haus auf die Pappe malen. \
Die \u00d6ffnungen sind die Fenster. Bobo malt auch B\u00e4ume. \
Und einen Mond. Das wird ein sch\u00f6nes Bild! \
Nun wird der Kalender noch am Fenster aufgeh\u00e4ngt. Fertig! \
Da kommt Mama nach Hause. Sie hat eingekauft. \
Dann darf Bobo alle T\u00fcrchen schlie\u00dfen. \
Papa malt 24 Zahlen darauf. \
Oh, das ist aber ein sch\u00f6ner Adventskalender!, staunt sie. \
Hast du das Bild gemalt, Bobo? \
Aber Bobo antwortet nicht. \
Er ist zwischen all den Bastelsachen am Tisch eingeschlafen.\
"""

FIXTURE_BOBO_STORY_ID: str = "bobos_adventskalender"
FIXTURE_BOBO_CHAPTER_ID: str = "chapter_01"


# ---------------------------------------------------------------------------
# Helper — convert child-first script to LangChain message list
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
# Conversation scripts
# ---------------------------------------------------------------------------

# Example 1 (PIA): Child says "Lisa und sarah" for Pia's friends.
# Correct answer: Millie und Sarah.
# System should correct AND ask a small confirmation.
SCRIPT_WRONG_FRIEND_NAMES = [
    # child
    'Hallo!',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt.'
    ' Pia macht immer alles richtig!'
    ' Wei\u00dft du noch, was Pia morgens als Erstes gemacht hat?',
    # child
    'socken',
    # system
    'Ja, Pia hat Socken angezogen, die zusammenpassen.'
    ' Pia hat auch ihren Hamster Hubert gef\u00fcttert.'
    ' In der Schule war Pia mit ihren Freundinnen in einem Kochteam.'
    ' Wei\u00dft du, wie die Freundinnen hei\u00dfen?',
    # child — TESTED: wrong answer, system should correct gently + confirm
    'Lisa und sarah',
]

# Example 2 (BOBO): Child says "er sagt ja" when asked what Bobo does
# when Mama asks if he painted the picture.
# Correct: Bobo says nothing, he fell asleep.
# System should give correct answer directly, short, not critical.
SCRIPT_BOBO_WRONG_ANSWER = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben gerade die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wei\u00dft du, was Bobo und Papa als Erstes gemacht haben?',
    # child
    'aus dem fenster geschaut',
    # system
    'Ja, genau! Bobo und Papa schauen aus dem K\u00fcchenfenster.'
    ' Dann kommt die Postbotin. Sie bringt einen Zettel.'
    ' Papa und Bobo gehen zur Post und holen ein Paket.'
    ' Zu Hause basteln sie einen Adventskalender.'
    ' Bobo malt ein Haus auf die Pappe.'
    ' Dann kommt Mama nach Hause.'
    ' Mama fragt: "Hast du das Bild gemalt, Bobo?"'
    ' Was macht Bobo, als Mama das fragt?',
    # child — TESTED: wrong answer, system should correct directly + short
    'er sagt ja',
]

# Example 3 (PIA): Child says wrong food for Hubert.
# Correct: Brokkoli.
# System should incorporate correct info neutrally, not judgmentally.
SCRIPT_WRONG_HUBERT_FOOD = [
    # child
    'Hallo!',
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Wir haben die Geschichte von Pia geh\u00f6rt.'
    ' Pia hat morgens viel gemacht.'
    ' Was hat Pia ihrem Hamster Hubert gegeben?',
    # child — TESTED: wrong answer, system should correct neutrally
    'Marmelade',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION = (
    "The child said 'Lisa und Sarah' when asked about Pia's friends. "
    "The correct answer is 'Millie und Sarah'. Does the system response: "
    "(1) correct the wrong name gently (mention that the friends are called "
    "Millie und Sarah, not Lisa und Sarah), AND "
    "(2) include a small confirmation check — ask whether the child now "
    "remembers or understands (e.g. 'Erinnerst du dich?' or similar)? "
    "The system must NOT just move on immediately without checking. "
    "The correction must sound friendly and non-judgmental. "
    "Return PASS if the system corrects the name AND checks for confirmation, "
    "FAIL if it skips the correction, sounds critical, or moves on without "
    "any confirmation check."
)

CRITERION_SHORT_DIRECT_CORRECTION = (
    "The child said 'er sagt ja' when asked what Bobo does when Mama asks "
    "if he painted the picture. The correct answer is that Bobo does not "
    "answer because he fell asleep. Does the system response: "
    "(1) provide the correct answer (Bobo says nothing / Bobo fell asleep), AND "
    "(2) keep the correction short and direct — no lengthy commentary "
    "about the child's mistake? "
    "The response must NOT sound critical or judgmental toward the child. "
    "Return PASS if the system gives the correct answer directly without "
    "sounding critical, FAIL if it is overly long, critical, or fails to "
    "provide the correct information."
)

CRITERION_NEUTRAL_FACT_CORRECTION = (
    "The child said 'Marmelade' when asked what Pia gave her hamster Hubert. "
    "The correct answer is Brokkoli. Does the system response: "
    "(1) incorporate the correct information (Brokkoli) into the reply, AND "
    "(2) do so neutrally — without reacting correctively, judgmentally, "
    "or making the child feel bad about the wrong answer? "
    "The tone should be warm and matter-of-fact, as if simply sharing "
    "the story fact. "
    "Return PASS if the system mentions Brokkoli in a neutral, "
    "non-judgmental way, FAIL if it sounds corrective, critical, "
    "or fails to mention the correct food."
)


# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B
# ---------------------------------------------------------------------------

# Child gives a wrong answer about Hubert's food during normal conversation.
# ODD length (5 elements) — ends with child utterance.
SIMULATED_WRONG_STORY_FACT = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt. '
    'Pia macht morgens ganz viel. Was hat Pia ihrem Hamster Hubert gegeben?',
    'Marmelade',
    'Hubert bekommt in der Geschichte Brokkoli. '
    'Pia hat auch ein Pausenbrot f\u00fcr ihren Bruder Carl geschmiert. '
    'Was hat Pia auf das Brot getan?',
    'k\u00e4se',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestIncorrectStoryFactsFixtureBased:
    """Strategy A: Verify gentle correction of wrong story facts."""

    def test_gentle_correction_with_confirmation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (PIA): Child says 'Lisa und sarah' for friends' names.
        System should correct ('Millie und Sarah') AND check if child
        now remembers (small confirmation). Should NOT just move on.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WRONG_FRIEND_NAMES),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GENTLE_CORRECTION_WITH_CONFIRMATION),
        )

    def test_short_direct_correction(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (BOBO): Child says 'er sagt ja' about what Bobo does
        when Mama asks. System should give correct answer directly
        ('Bobo sagt nichts, er ist eingeschlafen') without lengthy
        commentary. Must not sound critical.
        """
        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_BOBO_WRONG_ANSWER),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SHORT_DIRECT_CORRECTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SHORT_DIRECT_CORRECTION),
        )

    def test_neutral_fact_correction(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Child says wrong food for Hubert.
        System should incorporate correct information neutrally,
        not react correctively or judgmentally.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WRONG_HUBERT_FOOD),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_NEUTRAL_FACT_CORRECTION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_NEUTRAL_FACT_CORRECTION),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestIncorrectStoryFactsSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_neutral_fact_correction_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Full simulation where the child gives a wrong
        answer about Hubert's food. The final system response should
        correct neutrally without judgment.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_WRONG_STORY_FACT,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_NEUTRAL_FACT_CORRECTION,
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
                "Emma", 6, "weiblich",
                SIMULATED_WRONG_STORY_FACT,
                CRITERION_NEUTRAL_FACT_CORRECTION,
            ),
        )
