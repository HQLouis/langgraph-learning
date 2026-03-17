"""
Feature: Child Prompts AI ("Kind fordert KI auf")
Test file: When a child asks the AI to do a task or help, the AI should
           engage helpfully — offer to do it together, ask what specifically
           the child needs help with, or recognize word-finding difficulty.

Three sub-behaviours are tested:
  1. Collaborative help: When the AI asks for a rhyme and the child deflects
     with "nein, und dir?", the AI should recognize the child wants help
     and offer to do it together.
  2. Give opinion / help when asked: When the child explicitly asks for help
     ("Kannst du mir helfen?"), the AI should respond helpfully and ask
     what specifically the child does not know.
  3. Word-finding support: When the child says "Ich weiss nicht wie das
     heisst..", the AI should recognize word-finding difficulty and offer
     to help explain the word.

Stories used:
  - "Bobos Adventskalender" (Example 1)
  - "Pia muss nicht perfekt sein" (Examples 2, 3)

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
# Bobo story fixture — "Bobos Adventskalender"
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
# Pia story fixture — "Pia muss nicht perfekt sein"
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
# Conversation scripts — child-first, odd-length
# ---------------------------------------------------------------------------

# Example 1 (BOBO): AI asks for a rhyme, child deflects with "nein, und dir?"
# The AI should recognize the child is asking the AI to do the task and
# offer to do it together or help.
SCRIPT_COLLABORATIVE_HELP = [
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
    'Ja, genau! Bobo und Papa haben aus dem K\u00fcchenfenster geschaut.'
    ' Dann kommt die Postbotin. Sie hat ein neues Fahrrad.'
    ' Bobo darf auf dem Fahrrad sitzen. Klingeling!'
    ' F\u00e4llt dir ein Reim zu "Klingeling" ein?',
    # child — TESTED: child deflects the rhyme task back to AI
    'nein, und dir?',
]

# Example 2 (PIA): Child explicitly asks for help
# AI should respond helpfully, ask what specifically the child does not know.
SCRIPT_GIVE_OPINION_WHEN_ASKED = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht.'
    ' Was hat Pia denn als Allererstes an diesem Freitag gemacht?',
    # child
    'socken angezogen',
    # system
    'Ja, Pia hat Socken angezogen, die zusammenpassen.'
    ' Pia hat auch ihrem Hamster Hubert Brokkoli gegeben.'
    ' Was denkst du, warum mag Hubert Brokkoli so gern?',
    # child — TESTED: child asks for help
    'Ich wei\u00df nicht. Kannst du mir helfen?',
]

# Example 3 (PIA): Child expresses word-finding difficulty
# AI should recognize word-finding difficulty and offer to help.
SCRIPT_WORD_FINDING_SUPPORT = [
    # child
    'hallo',
    # system
    'Hallo! Ich bin Thilio.'
    ' Wir haben gerade die Geschichte von Pia geh\u00f6rt.'
    ' Pia macht beim Talentwettbewerb mit.'
    ' Was jongliert Pia alles?',
    # child
    'hubert und den ballon',
    # system
    'Ja, Pia wirft Hubert und den Wasserballon in die Luft.'
    ' Und sie hat auch noch etwas anderes.'
    ' Wei\u00dft du, was das dritte Ding ist?',
    # child — TESTED: child has word-finding difficulty
    'Ich wei\u00df nicht wie das hei\u00dft..',
]


# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_COLLABORATIVE_HELP = (
    "The AI previously asked the child to come up with a rhyme for "
    "'Klingeling'. The child replied 'nein, und dir?' — meaning the child "
    "is asking the AI to do the task instead. Does the system response: "
    "(1) recognize that the child is asking the AI to help or do the task, AND "
    "(2) offer to do it together, help the child, or attempt the rhyme itself "
    "rather than ignoring the child's request or simply repeating the question? "
    "Return PASS if the system recognizes the child's request and engages "
    "helpfully (offers to try together, makes a rhyme, or asks if the child "
    "wants the AI to try), FAIL if it ignores the request, changes topic "
    "entirely, or just repeats the original question."
)

CRITERION_GIVE_OPINION_WHEN_ASKED = (
    "The child said 'Ich wei\u00df nicht. Kannst du mir helfen?' — explicitly "
    "asking the AI for help. Does the system response: "
    "(1) acknowledge the child's request for help, AND "
    "(2) respond helpfully — for example by giving a hint, asking what "
    "specifically the child does not know, offering an explanation, or "
    "providing a possible answer — RATHER than ignoring the request, "
    "just moving on, or repeating the same question? "
    "Return PASS if the system acknowledges the help request and responds "
    "helpfully, FAIL if it ignores the request or fails to offer assistance."
)

CRITERION_WORD_FINDING_SUPPORT = (
    "The child said 'Ich wei\u00df nicht wie das hei\u00dft..' — indicating "
    "word-finding difficulty. The child seems to know what the object is but "
    "cannot recall the word. Does the system response: "
    "(1) recognize the word-finding difficulty (the child knows the thing "
    "but not the word for it), AND "
    "(2) offer to help — for example by asking the child to describe it, "
    "giving a hint about the word, asking if the child means a specific "
    "object, or explaining what the word might be — RATHER than ignoring "
    "the difficulty or just telling the answer without acknowledgment? "
    "Return PASS if the system recognizes the word-finding struggle and "
    "offers supportive help, FAIL if it ignores the difficulty or simply "
    "moves on."
)


# ---------------------------------------------------------------------------
# Simulated child inputs for Strategy B — ODD length (ends with child)
# ---------------------------------------------------------------------------

SIMULATED_CHILD_ASKS_FOR_HELP = [
    'hallo',
    'Hallo! Ich bin Thilio. Wir haben die Geschichte von Pia geh\u00f6rt. '
    'Was hat Pia als Erstes am Freitag gemacht?',
    'socken',
    'Ja, Pia hat Socken angezogen. Pia hat auch Hubert gef\u00fcttert. '
    'Was denkst du, warum mag Hubert Brokkoli?',
    'Ich wei\u00df nicht. Kannst du mir helfen?',
]


# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestChildPromptsAIFixtureBased:
    """Strategy A: Verify AI responds helpfully when child asks for help."""

    def test_collaborative_help_on_request(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (BOBO): AI asks for a rhyme, child says 'nein, und dir?'
        AI should recognize the child is asking AI to do the task and offer
        to do it together or help.
        """
        state = build_state(
            child_name="Emma",
            child_age=4,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_COLLABORATIVE_HELP),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_COLLABORATIVE_HELP)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_COLLABORATIVE_HELP),
        )

    def test_give_opinion_when_asked(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (PIA): Child says 'Ich weiss nicht. Kannst du mir helfen?'
        AI should respond helpfully and ask what specifically the child
        does not know.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_GIVE_OPINION_WHEN_ASKED),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_GIVE_OPINION_WHEN_ASKED)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_GIVE_OPINION_WHEN_ASKED),
        )

    def test_word_finding_support(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (PIA): Child says 'Ich weiss nicht wie das heisst..'
        AI should recognize word-finding difficulty and offer to help
        explain the word.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WORD_FINDING_SUPPORT),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WORD_FINDING_SUPPORT)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WORD_FINDING_SUPPORT),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestChildPromptsAISimulated:
    """Strategy B: Full simulation where child asks AI for help."""

    def test_child_asks_for_help_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Full simulation: child explicitly asks for help mid-conversation.
        The final system response should acknowledge the request and
        offer assistance.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_ASKS_FOR_HELP,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_GIVE_OPINION_WHEN_ASKED,
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
                "Emma", 6, "weiblich",
                SIMULATED_CHILD_ASKS_FOR_HELP,
                CRITERION_GIVE_OPINION_WHEN_ASKED,
            ),
        )
