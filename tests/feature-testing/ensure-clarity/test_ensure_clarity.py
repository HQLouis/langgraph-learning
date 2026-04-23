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
  - "Pia muss nicht perfekt sein" (Examples 1, 2, 5, 7)
  - "Bobos Adventskalender" (Examples 3, 4, 6)

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
    FIXTURE_BOBO_AUDIO_BOOK,
    FIXTURE_BOBO_CHAPTER_ID,
    FIXTURE_BOBO_STORY_ID,
    FIXTURE_PIA_AUDIO_BOOK,
    FIXTURE_PIA_CHAPTER_ID,
    FIXTURE_PIA_STORY_ID,
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

# Example 1 (spec lines 56-67): Ambiguous single-word answer "Carl?"
# Context: conversation about Pia, ending with either/or question where
# the child echoes a single word from the question.
SCRIPT_AMBIGUOUS_CARL = [
    # child                                                                      # spec line
    'hallo',                                                                     # 56
    # system
    'Hallo! Ich bin Thilo.'
    ' Hast du auch die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht?',                                           # 57
    # child
    'ja',                                                                        # 58
    # system
    'Pia hat einen Hamster. Wie hei\u00dft der Hamster?',                       # 59
    # child
    'hubert',                                                                    # 60
    # system
    'Der Hamster mag es gern gr\u00fcn und es ist sein Lieblingsessen.'
    ' Was frisst Hubert am liebsten?',                                           # 61
    # child
    'brokkoli',                                                                  # 62
    # system
    'Ja, Hubert frisst Brokkoli.'
    ' Pia schmiert ihrem Bruder ein Pausenbrot.'
    ' Nimmt sie Nutella oder Erdnussbutter?',                                    # 63
    # child
    'erdnussbutter',                                                             # 64
    # system
    'Genau, Pia nimmt Erdnussbutter.'
    ' Und noch etwas S\u00fc\u00dfes kommt auf das Brot.'
    ' Was schmiert Pia noch auf das Brot?',                                      # 65
    # child
    'Marmelade',                                                                 # 66
    # system
    'Ja, Pia schmiert Marmelade auf das Brot.'
    ' Macht sie das, weil Carl das so mag'
    ' oder weil sie selbst Marmelade mag?',                                      # 67
    # child — TESTED: system response to this is judged
    'Carl?',
]

# Example 2 (spec lines 95-113): Child repeats unknown word "famos?"
# Context: conversation about Pia, system uses the word "famos" and the
# child echoes it as a question — likely doesn't know the meaning.
SCRIPT_UNKNOWN_WORD_FAMOS = [
    # child                                                                      # spec line
    'hallo',                                                                     # 95
    # system
    'Hallo! Hast du auch die Geschichte von Pia geh\u00f6rt,'
    ' die immer alles richtig macht?',                                           # 96
    # child
    'ja',                                                                        # 97
    # system
    'Pia hat immer alles richtig gemacht.'
    ' Was hat Pia ihrem Hamster Hubert zu fressen gegeben?',                     # 98
    # child
    'm\u00f6hren',                                                               # 99
    # system
    'Nein, Pia gab Hubert keinen M\u00f6hren.'
    ' Was frisst Hubert denn?',                                                  # 100
    # child
    'wei\u00df nicht',                                                           # 101
    # system
    'Ich helfe dir! Pia gab Hubert Brokkoli.'
    ' Hat Carl auch Brokkoli bekommen oder lieber Marmelade?',                   # 102
    # child
    'nee, er haben Marmelade bekommt',                                           # 103
    # system
    'Carl hat keine Marmelade bekommen.'
    ' Carl hat lieber Wachsmalkreide gegessen.'
    ' Was hat Pia denn f\u00fcr den Wettbewerb vorbereitet?',                   # 104
    # child
    'etwas, ich wei\u00dft nicht, hei\u00dft',                                 # 105
    # system
    'Pia \u00fcbt f\u00fcr einen Wettbewerb.'
    ' Hat Pia gesungen oder gezaubert?',                                         # 106
    # child
    'getanzen',                                                                  # 107
    # system
    'Pia hat nicht getanzt.'
    ' Pia wollte mit Sachen jonglieren.'
    ' Hat Pia mit B\u00e4llen oder mit T\u00fcchern jongliert?',               # 108
    # child
    'nein',                                                                      # 109
    # system
    'Pia wollte jonglieren.'
    ' Hat Pia mit Salzstreuer oder mit B\u00e4llen jongliert?',                 # 110
    # child
    'salz',                                                                      # 111
    # system
    'Pia jongliert mit dem Salz, das findet das Publikum ganz famos.'
    ' Was passiert denn mit Hubert, dem Hamsterheld?',                           # 112
    # child — TESTED: system response to this is judged
    'famos?',                                                                    # 113
]

# Example 5 (spec lines 193-263): "vergessen" — ambiguous meaning
# Context: very long conversation about Pia, ending with child saying
# "vergessen" which could mean "Pia forgot something" or "I forgot".
SCRIPT_VERGESSEN = [
    # child                                                                      # spec line
    'hallo',                                                                     # 193
    # system
    'Hallo! Ich bin Thilio.'
    ' Hast du die Geschichte von Pia geh\u00f6rt,'
    ' die eigentlich immer alles richtig macht?',                                # 194
    # child
    'ja',                                                                        # 195
    # system
    'Super! Pia ist wirklich besonders, oder?'
    ' Sie begr\u00fc\u00dft zum Beispiel jeden Morgen ihre Fans vor der T\u00fcr.'
    ' Hat sie ihnen "Guten Morgen" oder "Guten Abend" gesagt?',                  # 196
    # child
    'guten Morgen',                                                              # 197
    # system
    'Ja, genau, sie hat "Guten Morgen" gesagt.'
    ' Pia ist echt ordentlich, nicht wahr? Findest du das auch gut?',            # 198
    # child
    'ja gut',                                                                    # 199
    # system
    'Pia ist wirklich super organisiert.'
    ' Sie hat sogar darauf geachtet,'
    ' dass ihr Hamster Hubert sein Lieblingsessen bekommt.'
    ' Wei\u00dft du noch, was Hubert am liebsten gefuttert hat?'
    ' War es Marmelade oder Brokkoli?',                                          # 200
    # child
    'es ist Brokkolis',                                                          # 201
    # system
    'Ja, Brokkoli! Hubert mag Brokkoli.'
    ' Es ist gr\u00fcn und gesund, und Hubert knabbert es gern.'
    ' Was ist das?',                                                             # 202
    # child
    'Brokolis?',                                                                 # 203
    # system
    'Ja, stimmt genau! Der Brokkoli ist gr\u00fcn.'
    ' Und wer bekommt ihn? Der Brokkoli geh\u00f6rt ...?',                     # 204
    # child
    'Hubert?',                                                                   # 205
    # system
    'Ja, super! Der Brokkoli ist f\u00fcr Hubert.'
    ' Stell dir vor, du bist Hubert, der Hamster.'
    ' Was machst du jetzt mit dem Brokkoli?',                                    # 206
    # child
    'ich esse Brokkol',                                                          # 207
    # system
    'Mmmh, lecker! Hubert mag seinen Brokkoli.'
    ' Pia hat auch ihrem Bruder Carl ein Pausenbrot gemacht.'
    ' Sie hat Erdnussbutter und Marmelade drauf geschmiert.'
    ' Wei\u00dft du noch, wie viel von jedem?'
    ' War es gleich viel, oder mehr Erdnussbutter?',                             # 208
    # child
    'gleich viel',                                                               # 209
    # system
    'Ja, genau! Pia hat gleich viel Erdnussbutter und Marmelade genommen.'
    ' Pia hat ... geschmiert. Was passt da rein?',                               # 210
    # child
    'brot',                                                                      # 211
    # system
    'Ja, Pia hat das Brot geschmiert.'
    ' Pia ist echt genau, findest du nicht?',                                    # 212
    # child
    'ja, pia genau',                                                             # 213
    # system
    'Ja, Pia ist sehr genau.'
    ' Sie macht fast alles richtig.'
    ' Aber Carl, ihr Bruder, macht lieber Sachen falsch!'
    ' Er findet das toll. Carl macht Sachen...?',                                # 214
    # child
    'falsch?',                                                                   # 215
    # system
    'Ja, Carl macht Sachen falsch.'
    ' Er findet es lustig, Dinge anders zu machen.'
    ' Pia macht alles richtig, und Carl macht vieles falsch.'
    ' Was denkst du, macht mehr Spa\u00df?',                                    # 216
    # child
    'richtig machen?',                                                           # 217
    # system
    'Du findest, richtig machen macht mehr Spa\u00df?'
    ' Pia findet das bestimmt auch!'
    ' In der Schule wollte Pia mit ihren Freundinnen Muffins backen.'
    ' Was haben sie f\u00fcr den Teig gebraucht?',                             # 218
    # child
    'eier',                                                                      # 219
    # system
    'Ja, genau, sie brauchten Eier!'
    ' Pia wollte die Eier holen und dann ist ihr fast ein Fehler passiert!'
    ' Was ist denn da blo\u00df passiert?',                                     # 220
    # child
    'runter fallen alles fast',                                                  # 221
    # system
    'Ja, fast w\u00e4ren alle Eier runtergefallen!'
    ' Zum Gl\u00fcck hat Pia sie gefangen.'
    ' Pia wollte die ... holen. Was passt da rein?',                            # 222
    # child
    'eier',                                                                      # 223
    # system
    'Ja, Pia wollte die Eier holen.'
    ' Sie ist ganz sch\u00f6n geschickt, oder?',                               # 224
    # child
    'ja',                                                                        # 225
    # system
    'Findest du, Pia soll die Eier jetzt ganz vorsichtig'
    ' in eine Sch\u00fcssel legen oder schnell weiterlaufen?',                  # 226
    # child
    'vorsichtig',                                                                # 227
    # system
    'Ja, das finde ich auch.'
    ' Lieber vorsichtig sein, damit nichts mehr passiert.'
    ' Pia hat ja fast einen Fehler gemacht.'
    ' Aber sie hat ihn nicht gemacht.'
    ' Sie ist eben super vorsichtig. Pia ist fast ...?',                        # 228
    # child
    'gefallt',                                                                   # 229
    # system
    'Fast gefallen sind die Eier.'
    ' Aber Pia hat sie ja noch gefangen.'
    ' Sie hat fast einen ... gemacht. Was meinst du?',                          # 230
    # child
    'wei\u00df nicht',                                                           # 231
    # system
    'Das ist nicht schlimm.'
    ' Sie hat fast einen Fehler gemacht. Aber eben nur fast.',                  # 232
    # child
    'ach so',                                                                    # 233
    # system
    'Genau! Und dann wollte Pia eigentlich mit ihren Freundinnen'
    ' Schlittschuh laufen.'
    ' Aber sie hatte ein bisschen Angst.'
    ' Kannst du das verstehen?',                                                 # 234
    # child
    'ja',                                                                        # 235
    # system
    'Ja, ein bisschen Angst kann man da schon haben, oder?'
    ' War Pia mutig oder \u00e4ngstlich,'
    ' als sie Schlittschuh laufen sollte?',                                     # 236
    # child
    'mutig',                                                                     # 237
    # system
    'Pia war nicht so mutig. Sie hatte ja ein bisschen Angst.'
    ' Aber was meinst du:'
    ' H\u00e4tte sie es trotzdem mal probieren sollen'
    ' mit dem Schlittschuhlaufen?',                                              # 238
    # child
    'nein',                                                                      # 239
    # system
    'Du meinst, es ist besser, wenn Pia nicht Schlittschuh l\u00e4uft?'
    ' Vielleicht w\u00e4re es ihr ja doch zu gef\u00e4hrlich gewesen.'
    ' Pia hatte ja schon Angst, dass sie einen Fehler macht.'
    ' Sie sagte sogar: \u201eIch habe Angst, dass ich es heute ...\u201c'
    ' Was hat sie gesagt?',                                                      # 240
    # child
    'vermasele?',                                                                # 241
    # system
    'Ja, genau! Sie hatte Angst, dass sie es vermasselt.'
    ' Pia hatte Angst, dass sie einen ... macht.'
    ' Was passt da rein?',                                                       # 242
    # child
    'fehler',                                                                    # 243
    # system
    'Ja, Pia hatte Angst, einen Fehler zu machen.'
    ' Sie wollte ja alles richtig machen.',                                     # 244
    # child
    'ja',                                                                        # 245
    # system
    'Und dann kam der Abend des Talentwettbewerbs!'
    ' Pia hatte sich gut vorbereitet,'
    ' aber sie war trotzdem aufgeregt.'
    ' Was hat sie denn alles f\u00fcr ihren Auftritt eingepackt?',              # 246
    # child
    'hubert',                                                                    # 247
    # system
    'Ja, genau, ihren Hamster Hubert!'
    ' Und was noch?'
    ' Hatte sie einen Ball oder einen Salzstreuer dabei?',                       # 248
    # child
    'salz',                                                                      # 249
    # system
    'Ja, einen Salzstreuer! Und was noch?'
    ' War da noch ein Hut oder ein Wasserballon?',                               # 250
    # child
    'ballon wasser',                                                             # 251
    # system
    'Ja, ein Wasserballon!'
    ' Pia hatte ganz sch\u00f6n viel eingepackt f\u00fcr ihren Auftritt.'
    ' Sie hatte den Hamster ... dabei. Was passt da rein?',                     # 252
    # child
    'hubert',                                                                    # 253
    # system
    'Ja, genau! Sie hatte ihren Hamster Hubert dabei.'
    ' Ich denke an etwas, das Pia f\u00fcr ihren Auftritt eingepackt hat.'
    ' Es ist klein und rund,'
    ' und man kann es zum W\u00fcrzen von Essen benutzen. Was ist es?',         # 254
    # child
    'wei\u00df nicht wie hei\u00dft das',                                       # 255
    # system
    'Das ist nicht schlimm. Es ist ein Salzstreuer.'
    ' Da kommt Salz raus.'
    ' Pia hatte einen ... dabei. Was passt da rein?',                           # 256
    # child
    'satzstreuer',                                                               # 257
    # system
    'Fast richtig! Salzstreuer. Kannst du das auch sagen?',                     # 258
    # child
    'was',                                                                       # 259
    # system
    'Salzstreuer.',                                                              # 260
    # child
    'salzstreuer',                                                               # 261
    # system
    'Super! Pia hatte einen Salzstreuer dabei.'
    ' Und dann ist etwas ganz Unerwartetes passiert!'
    ' Was war denn das f\u00fcr eine \u00dcberraschung bei Pias Auftritt?',     # 262
    # child — TESTED: system response to this is judged
    'vergessen',                                                                 # 263
]

# Example 7 (spec lines 297-313): "weiß nicht" — should resolve
# Context: conversation about Pia, child says "weiß nicht" when asked
# a factual question.  The system should resolve rather than push harder.
SCRIPT_WEISS_NICHT_RESOLVE = [
    # child                                                                      # spec line
    'hallo',                                                                     # 297
    # system
    'Hallo! Du hast also auch die Geschichte von Pia geh\u00f6rt.'
    ' Pia ist ja ein M\u00e4dchen, dem nie Fehler passieren.'
    ' Was meinst du, wie findet sie das?',                                       # 298
    # child
    'toll',                                                                      # 299
    # system
    'Ja, Pia macht immer alles toll.'
    ' Meinst du, Pia ist traurig oder froh,'
    ' dass sie nie Fehler macht?',                                               # 300
    # child
    'sie ist froh',                                                              # 301
    # system
    'Pia ist froh. Ja, Pia ist eigentlich immer froh, weil alles klappt.'
    ' Aber sag mal, ist es denn auch sch\u00f6n,'
    ' wenn man immer alles richtig macht,'
    ' oder findet Carl es besser, Fehler zu machen?',                            # 302
    # child
    'carl mag besser Fehler',                                                    # 303
    # system
    'Carl mag lieber Fehler machen.'
    ' Stell dir vor, du bist Carl. Was machst du jetzt?',                        # 304
    # child
    'quatsch',                                                                   # 305
    # system
    'Du w\u00fcrdest Quatsch machen.'
    ' Carl findet es toll, wenn er Quatsch machen kann.'
    ' Meinst du, Carl w\u00fcrde lieber mit gr\u00fcnen Bohnen malen'
    ' oder lieber ein Bild mit Wachsmalstiften malen?',                          # 306
    # child
    'beides',                                                                    # 307
    # system
    'Carl mag beides. Pia geht in die Schule.'
    ' Pia ... mit ihren Freundinnen?'
    ' Mit wem ist Pia in der Schule?',                                           # 308
    # child
    'Freundinnen',                                                               # 309
    # system
    'Pia ist mit ihren Freundinnen in der Schule. Genau!'
    ' Wie hei\u00dfen denn Pias Freundinnen?',                                 # 310
    # child
    'lara?',                                                                     # 311
    # system
    'Du m\u00f6chtest wissen, wie Pias Freundinnen hei\u00dfen.'
    ' Eine Freundin hei\u00dft Millie.'
    ' Wie hei\u00dft die andere Freundin von Pia?',                            # 312
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                           # 313
]

# -- Bobo examples --

# Example 3 (spec lines 131-139): "ja" to either/or question
# Context: conversation about Bobo, child answers "ja" to an either/or
# question — ambiguous response that needs clarification.
SCRIPT_JA_TO_EITHER_OR = [
    # child                                                                      # spec line
    'hallo',                                                                     # 131
    # system
    'Hallo! Ich bin Thilio, dein Sprachf\u00f6rder-Spielzeug.'
    ' Wir haben eben die Geschichte von Bobo geh\u00f6rt,'
    ' der mit seinem Papa einen Adventskalender bastelt.'
    ' Wollen wir uns noch ein bisschen dar\u00fcber unterhalten?'
    ' Wei\u00dft du noch, was Bobo und Papa am Anfang'
    ' der Geschichte zusammen gemacht haben?',                                   # 132
    # child
    'ja',                                                                        # 133
    # system
    'Du wei\u00dft es noch!'
    ' Hat Bobo denn den Adventskalender ganz alleine gebastelt?',               # 134
    # child
    'ja',                                                                        # 135
    # system
    'Du denkst, Bobo hat den Kalender alleine gebastelt.'
    ' Wer hat denn mit Bobo zusammen den Kalender gebastelt?',                  # 136
    # child
    'papa',                                                                      # 137
    # system
    'Ja, Bobo hat mit Papa zusammen gebastelt.'
    ' Was haben Bobo und Papa denn alles zum Basteln benutzt?'
    ' Haben sie Farbe oder Papier genommen?',                                    # 138
    # child — TESTED: system response to this is judged
    'ja',                                                                        # 139
]

# Example 4 (spec lines 156-170): Child deflects task with "nein, und dir?"
# Context: conversation about Bobo, the child deflects a rhyming task
# back to the system.
SCRIPT_CHILD_DEFLECTS = [
    # child                                                                      # spec line
    'hallo',                                                                     # 156
    # system
    'Hallo! Ich bin Thilio, dein sprechendes Spielzeug.'
    ' Ich kenne mich gut mit Bobos Adventskalender aus.'
    ' Was haben Bobo und Papa Siebenschl\u00e4fer zuerst gemacht,'
    ' als sie aus dem Fenster geschaut haben?',                                  # 157
    # child
    'geguckt',                                                                   # 158
    # system
    'Ja, Bobo und Papa haben aus dem Fenster geguckt.'
    ' Hat die Postbotin ein Auto oder ein Fahrrad?',                             # 159
    # child
    'fahrrad',                                                                   # 160
    # system
    'Ja, die Postbotin hat ein Fahrrad.'
    ' Hat Bobo auf dem Fahrrad gesungen?',                                       # 161
    # child
    'was?',                                                                      # 162
    # system
    'Das bedeutet: Hat Bobo ein Lied gesungen,'
    ' als er auf dem Fahrrad sa\u00df?'
    ' Oder hat er das nicht? Ist es jetzt klar?',                               # 163
    # child
    'ja',                                                                        # 164
    # system
    'Aha, du hast also gefragt, ob Bobo auf dem Fahrrad gesungen hat.'
    ' Hat Bobo geklingelt oder gehupt?',                                         # 165
    # child
    'ja',                                                                        # 166
    # system
    'Hat Bobo geklingelt?'
    ' Hat Bobo mit dem Fu\u00df oder mit der Hand geklingelt?',                 # 167
    # child
    'mit hand',                                                                  # 168
    # system
    'Ja, Bobo hat mit der Hand geklingelt.'
    ' Die Postbotin ist nett.'
    ' F\u00e4llt dir ein Reim dazu ein?',                                      # 169
    # child — TESTED: system response to this is judged
    'nein, und dir?',                                                            # 170
]

# Example 6 (spec lines 277-281): "nein" then "weiß nicht" — should not misinterpret
# Context: conversation about Bobo, system misinterprets "nein" and "weiß nicht".
SCRIPT_WEISS_NICHT_NO_MISINTERPRET = [
    # child                                                                      # spec line
    'hallo',                                                                     # 277
    # system
    'Hallo! Ich bin Thilio, dein Sprachbegleiter.'
    ' Bobo und Papa Siebenschl\u00e4fer haben zusammen'
    ' einen Adventskalender gebastelt.'
    ' Wei\u00dft du, was sie als Erstes gemacht haben,'
    ' bevor sie mit dem Basteln angefangen haben?',                              # 278
    # child
    'nein',                                                                      # 279
    # system
    'Du bist gespannt, was zuerst passiert ist.'
    ' Fast richtig! Im Buch haben Bobo und Papa zuerst ein'
    ' gro\u00dfes Paket von der Post geholt.'
    ' Was war denn in dem Paket drin?',                                          # 280
    # child — TESTED: system response to this is judged
    'wei\u00df nicht',                                                           # 281
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
        state = build_state_with_beats(
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
        state = build_state_with_beats(
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
        state = build_state_with_beats(
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

    def test_weiss_nicht_resolve(
        self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder
    ):
        """
        Example 7 (weiß nicht): Child says 'weiß nicht' to a factual
        question.  The system should resolve rather than push harder.
        """
        state = build_state_with_beats(
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
        state = build_state_with_beats(
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
        state = build_state_with_beats(
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
        Example 6 (weiß nicht): Child says 'weiß nicht' to a factual
        question.  The system should not misinterpret it as curiosity.
        """
        state = build_state_with_beats(
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
