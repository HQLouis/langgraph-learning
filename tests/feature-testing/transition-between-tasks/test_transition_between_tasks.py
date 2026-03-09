"""
Feature: Transition-Between-Tasks
Test file: Does the system create smooth, well-linked transitions between
           story scenes/topics rather than jumping abruptly?

The feature requires that the system:
  1. Waits for the child's answer before moving on to a new topic/scene
     (unless the follow-up question restates/reinforces the first one).
  2. Links scenes together naturally — does not jump too fast to the next topic.
  3. Provides a short content recap when transitioning between scenes for
     better context.

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

CRITERION_WAIT_FOR_ANSWER = (
    "The system has just asked the child a question, and the child has "
    "answered it. Does the system's NEW response (the one being evaluated) "
    "acknowledge the child's answer FIRST before moving on to a new topic "
    "or scene? The system must NOT skip the child's answer and immediately "
    "jump to a completely new scene or question. It is acceptable for the "
    "system to ask a follow-up question that reinforces or restates the "
    "same topic, but it must NOT introduce a brand-new scene or topic "
    "without first reacting to what the child said. "
    "Return PASS if the system acknowledges the child's answer before "
    "transitioning (or stays on the same topic), "
    "FAIL if it ignores the child's answer and jumps to a new scene."
)

CRITERION_SMOOTH_SCENE_LINKING = (
    "The conversation is at a point where the system is transitioning from "
    "one story scene to another. Does the NEW system response create a "
    "smooth, natural bridge between the previous scene and the next one? "
    "A good transition might briefly reference what just happened before "
    "introducing the next topic. A bad transition jumps abruptly from one "
    "scene to a completely different one without any connecting language. "
    "Return PASS if the transition feels natural and connected (e.g. uses "
    "bridging language, a brief recap, or a logical link between scenes), "
    "FAIL if the response jumps abruptly to a new scene without any "
    "connecting context."
)

CRITERION_CONTENT_RECAP_TRANSITION = (
    "The system is moving from one story scene to the next. Does the NEW "
    "system response include a short content recap or contextual bridge "
    "that helps the child understand the transition? For example, briefly "
    "mentioning what just happened or where the characters are now before "
    "asking the next question. The recap does not need to be long — even "
    "a single clause is sufficient. "
    "Return PASS if the response includes some form of recap or contextual "
    "bridging when transitioning to the next scene, "
    "FAIL if it moves to the new scene with no recap or context at all."
)

# ---------------------------------------------------------------------------
# Conversation scripts — verbatim from test-specs.txt
#
# Child-first, odd-length.  Each element is one atomic message from the spec.
# The last element is always a child message whose system response is
# generated live and evaluated by the judge.
# ---------------------------------------------------------------------------

# Example 1 (spec lines 40-104): Long conversation — system should wait for
# the child's answer before moving on.
SCRIPT_WAIT_FOR_ANSWER = [
    # child                                                                      # spec line
    'hallo',                                                                     # 40
    # system
    'Hallo! Du hast also auch die Geschichte von Pia geh\u00f6rt.'
    ' Pia ist ja ein M\u00e4dchen, dem nie Fehler passieren.'
    ' Was meinst du, wie findet sie das?',                                       # 41
    # child
    'toll',                                                                      # 42
    # system
    'Ja, Pia macht immer alles toll.'
    ' Meinst du, Pia ist traurig oder froh,'
    ' dass sie nie Fehler macht?',                                               # 43
    # child
    'sie ist froh',                                                              # 44
    # system
    'Pia ist froh. Ja, Pia ist eigentlich immer froh, weil alles klappt.'
    ' Aber sag mal, ist es denn auch sch\u00f6n,'
    ' wenn man immer alles richtig macht,'
    ' oder findet Carl es besser, Fehler zu machen?',                            # 45
    # child
    'carl mag besser Fehler',                                                    # 46
    # system
    'Carl mag lieber Fehler machen.'
    ' Stell dir vor, du bist Carl. Was machst du jetzt?',                        # 47
    # child
    'quatsch',                                                                   # 48
    # system
    'Du w\u00fcrdest Quatsch machen.'
    ' Carl findet es toll, wenn er Quatsch machen kann.'
    ' Meinst du, Carl w\u00fcrde lieber mit gr\u00fcnen Bohnen malen'
    ' oder lieber ein Bild mit Wachsmalstiften malen?',                          # 49
    # child
    'beides',                                                                    # 50
    # system
    'Carl mag beides.'
    ' Pia geht in die Schule.'
    ' Pia ... mit ihren Freundinnen?'
    ' Mit wem ist Pia in der Schule?',                                           # 51
    # child
    'Freundinnen',                                                               # 52
    # system
    'Pia ist mit ihren Freundinnen in der Schule.'
    ' Genau! Wie hei\u00dfen denn Pias Freundinnen?',                           # 53
    # child
    'lara?',                                                                     # 54
    # system
    'Du m\u00f6chtest wissen, wie Pias Freundinnen hei\u00dfen.'
    ' Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',                             # 55
    # child
    'wei\u00df nicht',                                                           # 56
    # system
    'Du wei\u00dft es nicht?'
    ' Pia hat zwei Freundinnen. Ist es Sarah oder Paul?',                        # 57
    # child
    'sarah',                                                                     # 58
    # system
    'Sarah! Ja, genau!'
    ' Pia ist mit Sarah und Millie in der Schule.'
    ' Pia und ihre Freundinnen brauchen Eier.'
    ' Holen sie die Eier aus dem Schrank oder aus dem K\u00fchlschrank?',        # 59
    # child
    'k\u00fchlschrank',                                                          # 60
    # system
    'Du sagst, die Eier sind im K\u00fchlschrank.'
    ' Ja, Pia holt die Eier aus dem K\u00fchlschrank.'
    ' Was ist in dem Korb? Sind da \u00c4pfel oder Eier drin?',                 # 61
    # child
    '\u00c4pfel?',                                                               # 62
    # system
    'Du fragst, ob \u00c4pfel im Korb sind.'
    ' Nein, da sind keine \u00c4pfel.'
    ' Sind da die Eier drin oder nicht?',                                        # 63
    # child
    'ja, eier',                                                                  # 64
    # system
    'Ja, da sind Eier drin.'
    ' Was passiert mit den Eiern?'
    ' Fallen sie runter oder bleiben sie heil?',                                 # 65
    # child
    'was ist heil',                                                              # 66
    # system
    'Du fragst, was "heil" ist.'
    ' Heil bedeutet, dass nichts kaputt ist.'
    ' Meinst du, die Eier bleiben heil, oder fallen sie runter?',                # 67
    # child
    'heil bleiben',                                                              # 68
    # system
    'Die Eier bleiben heil.'
    ' Aber fallen die Eier wirklich nicht runter,'
    ' oder purzeln sie doch?',                                                   # 69
    # child
    'fast runter',                                                               # 70
    # system
    'Sie fallen fast runter.'
    ' Was sagt denn Pia, als die Eier fast runterfallen?'
    ' Sagt sie "Mist" oder "Das war knapp!"?',                                  # 71
    # child
    'das war knapp',                                                             # 72
    # system
    'Ja, Pia sagt: "Das war knapp!"'
    ' Was macht Pia mit ihren Freundinnen?'
    ' Gehen sie zusammen Schlittschuh laufen oder kochen?',                      # 73
    # child
    'Schlittschuhe',                                                             # 74
    # system
    'Du denkst, sie laufen Schlittschuh.'
    ' Pia schaut ihren Freundinnen beim Schlittschuhlaufen zu.'
    ' Macht Pia das auch, oder geht sie woanders hin?',                          # 75
    # child
    'sie geht in schule',                                                        # 76
    # system
    'Pia geht in die Schule. Das stimmt.'
    ' Aber jetzt gerade, wo ihre Freundinnen Schlittschuh laufen,'
    ' geht Pia da mit oder nicht?',                                              # 77
    # child
    'nein',                                                                      # 78
    # system
    'Nein, Pia geht nicht mit. Pia hat Angst.'
    ' Wovor hat Pia Angst?'
    ' Hat sie Angst vor dem Talentwettbewerb oder vor dem Hamster?',             # 79
    # child
    'talentwettberb',                                                            # 80
    # system
    'Pia hat Angst vor dem Talentwettbewerb.'
    ' Was macht Pia beim Talentwettbewerb?'
    ' Spielt sie Klavier oder jongliert sie?',                                   # 81
    # child
    'sie macht jonglieren',                                                      # 82
    # system
    'Ja, Pia jongliert.'
    ' Was nimmt Pia zum Jonglieren?'
    ' Nimmt sie B\u00e4lle oder einen Salzstreuer?',                            # 83
    # child
    'salzstreer',                                                                # 84
    # system
    'Du sagst, sie nimmt einen Salzstreuer.'
    ' Was passiert mit dem Salzstreuer?'
    ' Ist da Salz drin oder Pfeffer?',                                           # 85
    # child
    'salz',                                                                      # 86
    # system
    'Da ist Salz drin.'
    ' Aber ist es wirklich Salz oder doch Pfeffer? Was meinst du?',             # 87
    # child
    'Pfeffer doch',                                                              # 88
    # system
    'Ja, da ist Pfeffer drin.'
    ' Und was passiert dann mit dem Pfeffer?'
    ' Muss Pia niesen oder husten?',                                             # 89
    # child
    'niesen',                                                                    # 90
    # system
    'Ja, Pia muss niesen.'
    ' Und was passiert noch?'
    ' Was macht Hubert, der Hamster?',                                           # 91
    # child
    'er laufen',                                                                 # 92
    # system
    'Du sagst, er l\u00e4uft.'
    ' Pia jongliert mit Hubert, dem Salzstreuer und noch etwas.'
    ' Ist das ein Ball oder ein Wasserballon?',                                  # 93
    # child
    'Wasserballon',                                                              # 94
    # system
    'Ja, ein Wasserballon.'
    ' Und was passiert mit dem Wasserballon, wenn Hubert niest?'
    ' Platzt er oder bleibt er ganz?',                                           # 95
    # child
    'er platzen',                                                                # 96
    # system
    'Der Ballon platzt! Genau!'
    ' Was passiert dann?'
    ' Lachen die Leute oder sind sie still?',                                    # 97
    # child
    'zuerst still',                                                              # 98
    # system
    'Ja, zuerst sind alle still.'
    ' Und dann? Lachen sie oder weinen sie?',                                    # 99
    # child
    'warum sind sie still?',                                                     # 100
    # system
    'Du fragst, warum sie still sind.'
    ' Die Leute sind still, weil so etwas noch nie passiert ist.'
    ' Pia macht sonst nie Fehler.'
    ' Was passiert dann?'
    ' Fangen sie an zu lachen oder bleiben sie still?',                          # 101
    # child
    'dann lachen',                                                               # 102
    # system
    'Ja, dann fangen sie an zu lachen.'
    ' Und was macht Pia? Lacht sie mit oder weint sie?',                         # 103
    # child — TESTED: system response to this is judged
    'sie lacht auch',                                                            # 104
]

# Example 2 (spec lines 121-145): Mid-length conversation — scenes should
# be better linked, not jump too fast.
SCRIPT_SMOOTH_LINKING = [
    # child                                                                      # spec line
    'hallo',                                                                     # 121
    # system
    'Hallo! Ich bin Thilio.'
    ' Hast du die Geschichte von Pia geh\u00f6rt,'
    ' die eigentlich immer alles richtig macht?',                                # 122
    # child
    'ja',                                                                        # 123
    # system
    'Super! Pia ist wirklich besonders, oder?'
    ' Sie begr\u00fc\u00dft zum Beispiel jeden Morgen ihre Fans vor der T\u00fcr.'
    ' Hat sie ihnen "Guten Morgen" oder "Guten Abend" gesagt?',                  # 124
    # child
    'guten Morgen',                                                              # 125
    # system
    'Ja, genau, sie hat "Guten Morgen" gesagt.'
    ' Pia ist echt ordentlich, nicht wahr? Findest du das auch gut?',            # 126
    # child
    'ja gut',                                                                    # 127
    # system
    'Pia ist wirklich super organisiert.'
    ' Sie hat sogar darauf geachtet, dass ihr Hamster Hubert'
    ' sein Lieblingsessen bekommt.'
    ' Wei\u00dft du noch, was Hubert am liebsten gefuttert hat?'
    ' War es Marmelade oder Brokkoli?',                                          # 128
    # child
    'es ist Brokkolis',                                                          # 129
    # system
    'Ja, Brokkoli! Hubert mag Brokkoli.'
    ' Es ist gr\u00fcn und gesund, und Hubert knabbert es gern.'
    ' Was ist das?',                                                             # 130
    # child
    'Brokolis?',                                                                 # 131
    # system
    'Ja, stimmt genau! Der Brokkoli ist gr\u00fcn.'
    ' Und wer bekommt ihn? Der Brokkoli geh\u00f6rt ...?',                     # 132
    # child
    'Hubert?',                                                                   # 133
    # system
    'Ja, super! Der Brokkoli ist f\u00fcr Hubert.'
    ' Stell dir vor, du bist Hubert, der Hamster.'
    ' Was machst du jetzt mit dem Brokkoli?',                                    # 134
    # child
    'ich esse Brokkoli',                                                         # 135
    # system
    'Mmmh, lecker! Hubert mag seinen Brokkoli.'
    ' Pia hat auch ihrem Bruder Carl ein Pausenbrot gemacht.'
    ' Sie hat Erdnussbutter und Marmelade drauf geschmiert.'
    ' Wei\u00dft du noch, wie viel von jedem?'
    ' War es gleich viel, oder mehr Erdnussbutter?',                             # 136
    # child
    'gleich viel',                                                               # 137
    # system
    'Ja, genau! Pia hat gleich viel Erdnussbutter und Marmelade genommen.'
    ' Pia hat ... geschmiert. Was passt da rein?',                               # 138
    # child
    'brot',                                                                      # 139
    # system
    'Ja, Pia hat das Brot geschmiert.'
    ' Pia ist echt genau, findest du nicht?',                                    # 140
    # child
    'ja, pia genau',                                                             # 141
    # system
    'Ja, Pia ist sehr genau.'
    ' Sie macht fast alles richtig.'
    ' Aber Carl, ihr Bruder, macht lieber Sachen falsch!'
    ' Er findet das toll. Carl macht Sachen...?',                                # 142
    # child
    'falsch?',                                                                   # 143
    # system
    'Ja, Carl macht Sachen falsch.'
    ' Er findet es lustig, Dinge anders zu machen.'
    ' Pia macht alles richtig, und Carl macht vieles falsch.'
    ' Was denkst du, macht mehr Spa\u00df?',                                    # 144
    # child — TESTED: system response to this is judged
    'richtig machen?',                                                           # 145
]

# Example 3 (spec lines 157-189): Mid-length conversation — short content
# recap needed for better transitions between scenes.
SCRIPT_CONTENT_RECAP = [
    # child                                                                      # spec line
    'hallo',                                                                     # 157
    # system
    'Hallo! Du hast also auch die Geschichte von Pia geh\u00f6rt.'
    ' Pia ist ja ein M\u00e4dchen, dem nie Fehler passieren.'
    ' Was meinst du, wie findet sie das?',                                       # 158
    # child
    'toll',                                                                      # 159
    # system
    'Ja, Pia macht immer alles toll.'
    ' Meinst du, Pia ist traurig oder froh,'
    ' dass sie nie Fehler macht?',                                               # 160
    # child
    'sie ist froh',                                                              # 161
    # system
    'Pia ist froh. Ja, Pia ist eigentlich immer froh, weil alles klappt.'
    ' Aber sag mal, ist es denn auch sch\u00f6n,'
    ' wenn man immer alles richtig macht,'
    ' oder findet Carl es besser, Fehler zu machen?',                            # 162
    # child
    'carl mag besser Fehler',                                                    # 163
    # system
    'Carl mag lieber Fehler machen.'
    ' Stell dir vor, du bist Carl. Was machst du jetzt?',                        # 164
    # child
    'quatsch',                                                                   # 165
    # system
    'Du w\u00fcrdest Quatsch machen.'
    ' Carl findet es toll, wenn er Quatsch machen kann.'
    ' Meinst du, Carl w\u00fcrde lieber mit gr\u00fcnen Bohnen malen'
    ' oder lieber ein Bild mit Wachsmalstiften malen?',                          # 166
    # child
    'beides',                                                                    # 167
    # system
    'Carl mag beides.'
    ' Pia geht in die Schule.'
    ' Pia ... mit ihren Freundinnen?'
    ' Mit wem ist Pia in der Schule?',                                           # 168
    # child
    'Freundinnen',                                                               # 169
    # system
    'Pia ist mit ihren Freundinnen in der Schule.'
    ' Genau! Wie hei\u00dfen denn Pias Freundinnen?',                           # 170
    # child
    'lara?',                                                                     # 171
    # system
    'Du m\u00f6chtest wissen, wie Pias Freundinnen hei\u00dfen.'
    ' Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',                             # 172
    # child
    'wei\u00df nicht',                                                           # 173
    # system
    'Du wei\u00dft es nicht?'
    ' Pia hat zwei Freundinnen. Ist es Sarah oder Paul?',                        # 174
    # child
    'sarah',                                                                     # 175
    # system
    'Sarah! Ja, genau!'
    ' Pia ist mit Sarah und Millie in der Schule.'
    ' Pia und ihre Freundinnen brauchen Eier.'
    ' Holen sie die Eier aus dem Schrank oder aus dem K\u00fchlschrank?',        # 176
    # child
    'k\u00fchlschrank',                                                          # 177
    # system
    'Du sagst, die Eier sind im K\u00fchlschrank.'
    ' Ja, Pia holt die Eier aus dem K\u00fchlschrank.'
    ' Was ist in dem Korb? Sind da \u00c4pfel oder Eier drin?',                 # 178
    # child
    '\u00c4pfel?',                                                               # 179
    # system
    'Du fragst, ob \u00c4pfel im Korb sind.'
    ' Nein, da sind keine \u00c4pfel.'
    ' Sind da die Eier drin oder nicht?',                                        # 180
    # child
    'ja, eier',                                                                  # 181
    # system
    'Ja, da sind Eier drin.'
    ' Was passiert mit den Eiern?'
    ' Fallen sie runter oder bleiben sie heil?',                                 # 182
    # child
    'was ist heil',                                                              # 183
    # system
    'Du fragst, was "heil" ist.'
    ' Heil bedeutet, dass nichts kaputt ist.'
    ' Meinst du, die Eier bleiben heil, oder fallen sie runter?',                # 184
    # child
    'heil bleiben',                                                              # 185
    # system
    'Die Eier bleiben heil.'
    ' Aber fallen die Eier wirklich nicht runter,'
    ' oder purzeln sie doch?',                                                   # 186
    # child
    'fast runter',                                                               # 187
    # system
    'Sie fallen fast runter.'
    ' Was sagt denn Pia, als die Eier fast runterfallen?'
    ' Sagt sie "Mist" oder "Das war knapp!"?',                                  # 188
    # child — TESTED: system response to this is judged
    'das war knapp',                                                             # 189
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
class TestTransitionBetweenTasksFixtureBased:
    """Strategy A: Verify smooth scene transitions against hardcoded state fixtures."""

    def test_wait_for_answer_before_transition(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Long conversation ending with 'sie lacht auch'.
        System should acknowledge the child's answer before moving on.
        """
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_WAIT_FOR_ANSWER),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_WAIT_FOR_ANSWER)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_WAIT_FOR_ANSWER),
        )

    def test_smooth_scene_linking(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Mid-length conversation ending with 'richtig machen?'.
        System should link scenes smoothly, not jump too fast.
        """
        state = build_state(
            child_name="Luca",
            child_age=5,
            child_gender="m\u00e4nnlich",
            messages=_script_to_messages(SCRIPT_SMOOTH_LINKING),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_SMOOTH_SCENE_LINKING)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_SMOOTH_SCENE_LINKING),
        )

    def test_content_recap_on_transition(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Mid-length conversation ending with 'das war knapp'.
        System should provide a short content recap when transitioning.
        """
        state = build_state(
            child_name="Mia",
            child_age=7,
            child_gender="weiblich",
            messages=_script_to_messages(SCRIPT_CONTENT_RECAP),
            audio_book=FIXTURE_PIA_AUDIO_BOOK,
            story_id=FIXTURE_PIA_STORY_ID,
            chapter_id=FIXTURE_PIA_CHAPTER_ID,
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_CONTENT_RECAP_TRANSITION)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, CRITERION_CONTENT_RECAP_TRANSITION),
        )


# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------


@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestTransitionBetweenTasksSimulated:
    """
    Strategy B: Run the full conversation from scratch using real LLMs.

    Uses SIMULATED_N_RUNS (default: 3) because each run involves multiple
    real LLM calls.
    """

    def test_wait_for_answer_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 1: Full simulation — long conversation.
        System should wait for the child's answer before transitioning.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SCRIPT_WAIT_FOR_ANSWER,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_WAIT_FOR_ANSWER,
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
                "Emma", 6, "weiblich", SCRIPT_WAIT_FOR_ANSWER,
                CRITERION_WAIT_FOR_ANSWER,
            ),
        )

    def test_smooth_scene_linking_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 2: Full simulation — mid-length conversation.
        System should link scenes smoothly.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Luca",
                child_age=5,
                child_gender="m\u00e4nnlich",
                child_inputs=SCRIPT_SMOOTH_LINKING,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_SMOOTH_SCENE_LINKING,
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
                "Luca", 5, "m\u00e4nnlich", SCRIPT_SMOOTH_LINKING,
                CRITERION_SMOOTH_SCENE_LINKING,
            ),
        )

    def test_content_recap_transition_simulated(
        self, system_llm, judge_llm, pass_threshold, run_details_recorder
    ):
        """
        Example 3: Full simulation — mid-length conversation.
        System should include a content recap when transitioning.
        """
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Mia",
                child_age=7,
                child_gender="weiblich",
                child_inputs=SCRIPT_CONTENT_RECAP,
                audio_book=FIXTURE_PIA_AUDIO_BOOK,
                story_id=FIXTURE_PIA_STORY_ID,
                chapter_id=FIXTURE_PIA_CHAPTER_ID,
            )
            passed, resp, reason = llm_judge(
                judge_llm, spoken_text, CRITERION_CONTENT_RECAP_TRANSITION,
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
                "Mia", 7, "weiblich", SCRIPT_CONTENT_RECAP,
                CRITERION_CONTENT_RECAP_TRANSITION,
            ),
        )
