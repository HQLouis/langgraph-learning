"""
Feature: Ensure-Clarity
Test file: Does the system properly handle ambiguous, unclear, or uncertain
           child answers by asking clarifying questions?

The feature requires that when a child gives an ambiguous answer (single
word from the question, "ja"/"nein" to an either/or, "wei\u00df nicht",
"vergessen", or an unclear one-word response), the system:
  - Does NOT assume the meaning
  - Asks a clarifying question to confirm what the child meant
  - Shows empathy when the child expresses uncertainty
  - Resolves the question when the child clearly cannot answer

Stories used:
  - "Pia muss nicht perfekt sein" (Examples 1, 2, 5, 7, 10)
  - "Bobos Adventskalender" (Examples 3, 4, 9)

Conversation scripts follow the same convention as all feature tests:
child-first, odd-length.  The system message from the spec is preceded by
a child "Hallo!" greeting.  The last child message triggers a live system
response that is evaluated by the judge.  The last system response in the
spec is ignored (it represents the current, suboptimal behaviour).

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
# Judge criteria (English)
# ---------------------------------------------------------------------------

# -- Pia examples --

CRITERION_AMBIGUOUS_SINGLE_WORD = (
    "After the system asks an either/or question ('weil Carl das so mag "
    "oder weil sie selbst Marmelade mag?') and the child responds with "
    "just 'Carl?' (a single word from the question, with question "
    "intonation), does the system response ask a clarifying question to "
    "determine what the child means — e.g. 'Meinst du, sie macht es "
    "f\u00fcr Carl?' or 'Willst du sagen: f\u00fcr Carl?' — rather than "
    "assuming the child's intent and moving on? "
    "Return PASS if the system asks a clarifying question about the "
    "child's ambiguous answer, FAIL if it assumes the meaning and "
    "continues without clarification."
)

CRITERION_UNKNOWN_WORD = (
    "After the system uses the word 'famos' in its message and the child "
    "repeats 'famos?' as a single-word question, does the system response "
    "recognize that the child likely does not know the word and either "
    "(a) ask whether the child knows what 'famos' means, or "
    "(b) directly explain the meaning of 'famos'? "
    "Return PASS if the system addresses the child's apparent unfamiliarity "
    "with the word (asks or explains), FAIL if it ignores the question "
    "and continues with the story."
)

CRITERION_VERGESSEN_DISAMBIGUATION = (
    "After the system asks 'Was war denn das f\u00fcr eine \u00dcberraschung "
    "bei Pias Auftritt?' and the child responds with just 'vergessen', "
    "does the system response disambiguate between the two possible "
    "meanings: (a) the child means 'Pia hat etwas vergessen' (a story "
    "answer), or (b) the child means 'ich habe es vergessen' (the child "
    "doesn't remember)? "
    "Return PASS if the system asks a clarifying question to determine "
    "which meaning the child intended, FAIL if it assumes one meaning "
    "without checking."
)

CRITERION_WEISS_NICHT_EMPATHY = (
    "After the system asks 'Was machen Pia und ihr Bruder Carl denn so "
    "am liebsten?' and the child says 'wei\u00df nicht', does the system "
    "response show empathy or provide a supportive bridge before helping "
    "— e.g. 'Das ist okay', 'Kein Problem', 'Ich helfe dir gerne', or "
    "similar acknowledgment of the child's difficulty — rather than "
    "immediately giving the answer or moving on without recognizing "
    "the child's uncertainty? "
    "Return PASS if the system shows empathy or understanding before "
    "providing help, FAIL if it jumps straight to the answer or a new "
    "question without any supportive transition."
)

CRITERION_WEISS_NICHT_RESOLVE = (
    "After the system asks 'Wie hei\u00dft die andere Freundin von Pia?' "
    "and the child says 'wei\u00df nicht', does the system response resolve "
    "the question — e.g. by revealing the answer ('Sie hei\u00dft Sarah') "
    "or offering to tell the child ('Soll ich es dir verraten?') — "
    "rather than insisting the child keep trying or pushing further "
    "without resolution? "
    "Return PASS if the system resolves or offers to resolve the question, "
    "FAIL if it insists the child try harder without providing help."
)

# -- Bobo examples --

CRITERION_JA_TO_EITHER_OR = (
    "After the system asks an either/or question ('Haben sie Farbe oder "
    "Papier genommen?') and the child responds with just 'ja', does the "
    "system response clarify what the child means by 'ja' — e.g. asking "
    "'Was meinst du mit ja?' and repeating the last option from the "
    "question — rather than assuming the child's intent and continuing? "
    "Return PASS if the system asks a clarifying question about the "
    "ambiguous 'ja', FAIL if it assumes the meaning and moves on."
)

CRITERION_CHILD_DEFLECTS_TASK = (
    "After the system asks the child to come up with a rhyme "
    "('F\u00e4llt dir ein Reim dazu ein?') and the child deflects by "
    "saying 'nein, und dir?', does the system acknowledge the child's "
    "request or deflection — e.g. by asking 'M\u00f6chtest du, dass ich "
    "es mache?', 'Ist es zu schwer?', or showing that it would also "
    "enjoy doing the task — rather than ignoring 'und dir?' and just "
    "proceeding with the task? "
    "Return PASS if the system acknowledges the child's deflection and "
    "engages with it, FAIL if it ignores the child's question and "
    "continues as if the child said nothing."
)

CRITERION_WEISS_NICHT_NO_MISINTERPRET = (
    "After the child says 'wei\u00df nicht' when asked 'Was war denn in "
    "dem Paket drin?', does the system handle it naturally — e.g. by "
    "acknowledging the child doesn't know and offering to help "
    "('Du wei\u00dft es nicht? Ich helfe dir gerne') — rather than "
    "misinterpreting the child's answer by attributing emotions like "
    "curiosity or excitement ('Du bist neugierig')? "
    "Return PASS if the system responds naturally to the child not "
    "knowing the answer, FAIL if it misinterprets 'wei\u00df nicht' as "
    "something other than uncertainty."
)


# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from ensure-clarity-test-specs.txt
#
# Child-first, odd-length.  Each system message from the spec is preceded
# by a child "Hallo!" greeting.  The last child message triggers a live
# system response that is evaluated by the judge.  The last system
# response in the spec is ignored.
# ---------------------------------------------------------------------------

# -- Pia examples --

# Example 1 (spec lines 59-60): Ambiguous single-word answer "Carl?"
SCRIPT_AMBIGUOUS_CARL = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Ja, Pia schmiert Marmelade auf das Brot.'
    ' Macht sie das, weil Carl das so mag'
    ' oder weil sie selbst Marmelade mag?',                                     # 59
    # child — TESTED: system response to this is judged
    'Carl?',                                                                    # 60
]

# Example 2 (spec lines 90-91): Child repeats unknown word "famos?"
SCRIPT_UNKNOWN_WORD_FAMOS = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Pia jongliert mit dem Salz, das findet das Publikum ganz famos.'
    ' Was passiert denn mit Hubert, dem Hamsterheld?',                           # 90
    # child — TESTED: system response to this is judged
    'famos?',                                                                   # 91
]

# Example 5 (spec lines 148-149): "vergessen" — ambiguous meaning
SCRIPT_VERGESSEN = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Pia hatte einen Salzstreuer dabei.'
    ' Und dann ist etwas ganz Unerwartetes passiert!'
    ' Was war denn das f\u00fcr eine \u00dcberraschung bei Pias Auftritt?',     # 148
    # child — TESTED: system response to this is judged
    'vergessen',                                                                # 149
]

# Example 7 (spec lines 162-163): "weiß nicht" — needs empathetic bridge
SCRIPT_WEISS_NICHT_BRIDGE = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Hallo! Wir h\u00f6ren uns gerade die Geschichte von Pia an, oder?'
    ' Was machen Pia und ihr Bruder Carl denn so am liebsten?',                  # 162
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                          # 163
]

# Example 10 (spec lines 194-195): "weiß nicht" — should resolve
SCRIPT_WEISS_NICHT_RESOLVE = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Du m\u00f6chtest wissen, wie Pias Freundinnen hei\u00dfen.'
    ' Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',                            # 194
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                          # 195
]

# -- Bobo examples --

# Example 3 (spec lines 110-111): "ja" to either/or question
SCRIPT_JA_TO_EITHER_OR = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Was haben sie zum Basteln benutzt?'
    ' Haben sie Farbe oder Papier genommen?',                                   # 110
    # child — TESTED: system response to this is judged
    'ja',                                                                       # 111
]

# Example 4 (spec lines 126-127): Child deflects task with "nein, und dir?"
SCRIPT_CHILD_DEFLECTS = [
    # child
    'Hallo!',
    # system                                                                    # spec line
    'Ja, Bobo hat mit der Hand geklingelt.'
    ' Die Postbotin ist nett.'
    ' F\u00e4llt dir ein Reim dazu ein?',                                      # 126
    # child — TESTED: system response to this is judged
    'nein, und dir?',                                                           # 127
]

# Example 9 (spec lines 174-176): "nein" then "weiß nicht" — should not misinterpret
# This example is already child-first (child → system → child), 3 elements.
SCRIPT_WEISS_NICHT_NO_MISINTERPRET = [
    # child                                                                     # spec line
    'nein',                                                                     # 174
    # system
    'Du bist gespannt, was zuerst passiert ist.'
    ' Fast richtig! Im Buch haben Bobo und Papa zuerst ein'
    ' gro\u00dfes Paket von der Post geholt.'
    ' Was war denn in dem Paket drin?',                                         # 175
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                          # 176
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
class TestEnsureClarityFixtureBased:
    """Strategy A: Verify clarity-seeking behaviour against hardcoded state fixtures."""

    # -- Pia examples --

    def test_ambiguous_single_word_carl(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Carl?): Child answers either/or question with a single
        ambiguous word.  The system should ask a clarifying question.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_AMBIGUOUS_CARL),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_AMBIGUOUS_SINGLE_WORD)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_AMBIGUOUS_SINGLE_WORD),
        )

    def test_unknown_word_famos(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (famos?): Child repeats an unknown word from the system's
        message.  The system should address the word's meaning.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_UNKNOWN_WORD_FAMOS),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_UNKNOWN_WORD)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_UNKNOWN_WORD),
        )

    def test_vergessen_disambiguation(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 5 (vergessen): Child says 'vergessen' which could mean
        the story answer or 'I forgot'.  The system should disambiguate.
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
            return llm_judge(judge_llm, spoken_text, CRITERION_VERGESSEN_DISAMBIGUATION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_VERGESSEN_DISAMBIGUATION),
        )

    def test_weiss_nicht_empathy(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 7 (weiß nicht): Child says 'weiß nicht'.  The system should
        show empathy before helping, not jump straight to the answer.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WEISS_NICHT_BRIDGE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WEISS_NICHT_EMPATHY)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WEISS_NICHT_EMPATHY),
        )

    def test_weiss_nicht_resolve(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 10 (weiß nicht): Child says 'weiß nicht' to a factual
        question.  The system should resolve rather than push harder.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WEISS_NICHT_RESOLVE),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WEISS_NICHT_RESOLVE)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WEISS_NICHT_RESOLVE),
        )

    # -- Bobo examples --

    def test_ja_to_either_or(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (ja): Child answers 'ja' to an either/or question.
        The system should clarify which option the child means.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_JA_TO_EITHER_OR),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_JA_TO_EITHER_OR)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_JA_TO_EITHER_OR),
        )

    def test_child_deflects_task(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (nein, und dir?): Child deflects a task back to the
        system.  The system should acknowledge the deflection.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CHILD_DEFLECTS),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CHILD_DEFLECTS_TASK)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CHILD_DEFLECTS_TASK),
        )

    def test_weiss_nicht_no_misinterpret(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 9 (weiß nicht): Child says 'weiß nicht' to a factual
        question.  The system should not misinterpret it as curiosity.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WEISS_NICHT_NO_MISINTERPRET),
            audio_book=FIXTURE_BOBO_AUDIO_BOOK,
            story_id=FIXTURE_BOBO_STORY_ID,
            chapter_id=FIXTURE_BOBO_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WEISS_NICHT_NO_MISINTERPRET)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WEISS_NICHT_NO_MISINTERPRET),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestEnsureClaritySimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    # -- Pia examples --

    def test_ambiguous_single_word_carl_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1 (Carl?): Full simulation.
        System should clarify the child's ambiguous single-word answer.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_AMBIGUOUS_CARL,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_AMBIGUOUS_SINGLE_WORD,
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
                "Emma", 6, "weiblich", SCRIPT_AMBIGUOUS_CARL,
                CRITERION_AMBIGUOUS_SINGLE_WORD,
            ),
        )

    def test_unknown_word_famos_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2 (famos?): Full simulation.
        System should address the child's unfamiliarity with the word.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_UNKNOWN_WORD_FAMOS,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_UNKNOWN_WORD,
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
                "Emma", 6, "weiblich", SCRIPT_UNKNOWN_WORD_FAMOS,
                CRITERION_UNKNOWN_WORD,
            ),
        )

    def test_vergessen_disambiguation_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 5 (vergessen): Full simulation.
        System should disambiguate whether child means the story or forgot.
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
                judge_llm, spoken_text, CRITERION_VERGESSEN_DISAMBIGUATION,
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
                CRITERION_VERGESSEN_DISAMBIGUATION,
            ),
        )

    def test_weiss_nicht_empathy_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 7 (wei\u00df nicht): Full simulation.
        System should show empathy before helping.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_WEISS_NICHT_BRIDGE,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_WEISS_NICHT_EMPATHY,
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
                "Emma", 6, "weiblich", SCRIPT_WEISS_NICHT_BRIDGE,
                CRITERION_WEISS_NICHT_EMPATHY,
            ),
        )

    def test_weiss_nicht_resolve_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 10 (wei\u00df nicht): Full simulation.
        System should resolve the question rather than push harder.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_WEISS_NICHT_RESOLVE,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_WEISS_NICHT_RESOLVE,
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
                "Emma", 6, "weiblich", SCRIPT_WEISS_NICHT_RESOLVE,
                CRITERION_WEISS_NICHT_RESOLVE,
            ),
        )

    # -- Bobo examples --

    def test_ja_to_either_or_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3 (ja): Full simulation.
        System should clarify which option the child means.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_JA_TO_EITHER_OR,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_JA_TO_EITHER_OR,
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
                "Emma", 6, "weiblich", SCRIPT_JA_TO_EITHER_OR,
                CRITERION_JA_TO_EITHER_OR,
            ),
        )

    def test_child_deflects_task_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 4 (nein, und dir?): Full simulation.
        System should acknowledge the child's deflection.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_CHILD_DEFLECTS,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_CHILD_DEFLECTS_TASK,
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
                "Emma", 6, "weiblich", SCRIPT_CHILD_DEFLECTS,
                CRITERION_CHILD_DEFLECTS_TASK,
            ),
        )

    def test_weiss_nicht_no_misinterpret_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 9 (wei\u00df nicht): Full simulation.
        System should not misinterpret the child's uncertainty.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_WEISS_NICHT_NO_MISINTERPRET,
                audio_book=FIXTURE_BOBO_AUDIO_BOOK,
                story_id=FIXTURE_BOBO_STORY_ID,
                chapter_id=FIXTURE_BOBO_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_WEISS_NICHT_NO_MISINTERPRET,
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
                "Emma", 6, "weiblich", SCRIPT_WEISS_NICHT_NO_MISINTERPRET,
                CRITERION_WEISS_NICHT_NO_MISINTERPRET,
            ),
        )
