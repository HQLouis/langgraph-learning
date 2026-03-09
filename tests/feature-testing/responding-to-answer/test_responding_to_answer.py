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
# Bobo story fixture — "Bobos Adventskalender" (used by Example 3)
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
