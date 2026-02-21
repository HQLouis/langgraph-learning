"""
Tests for output_contract_builder.build_output_contract

These tests verify that evidence and claims are correctly built from
real response text and active beats, covering the live scenario where
the spoken text contains referential sentences (not verbatim quotes).

Regression cases
----------------
- "No evidence for first-turn Thilio greeting" (GitHub issue / user report
  2026-02-21): build_output_contract returned empty evidence/claims for a
  response that referenced beat 1 content such as "Waldrand" and "Fenster".
  Root cause: min_overlap guard was 0.50 but referential sentences only share
  ~17-33 % of content words with the beat they reference.
  Fix: build_output_contract now passes min_overlap=0.20 to
  fuzzy_match_quote_to_beat.
"""
import pytest
from output_contract_builder import build_output_contract


# ---------------------------------------------------------------------------
# 1. Referential first-turn greeting (regression test)
#    Reproduces the exact response from the live failure report.
# ---------------------------------------------------------------------------

class TestBuildOutputContractFirstTurn:
    """build_output_contract must produce evidence for the first-turn greeting."""

    SPOKEN_TEXT = (
        "Hallo! Ich bin Thilio, dein Sprachbegleiter. "
        "Wir haben ja gerade erst von Mia gehört, die am Waldrand wohnt.\n\n"
        "Weißt du noch, was Mia jeden Tag gemacht hat, "
        "wenn sie aus dem Fenster geschaut hat?"
    )

    def test_evidence_not_empty_with_beat_1_active(self, beat_1):
        """
        The greeting references 'Waldrand' and 'Fenster' from beat 1.
        build_output_contract must produce at least one evidence entry
        pointing to beat 1.
        """
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        grounding = contract.grounding
        assert grounding.evidence, (
            "Expected at least one evidence entry but got an empty list. "
            "The response references beat 1 content (Waldrand, Fenster)."
        )

    def test_evidence_points_to_beat_1(self, beat_1):
        """Evidence entries must reference beat_id 1."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        beat_ids = {ev.beat_id for ev in contract.grounding.evidence}
        assert 1 in beat_ids, (
            f"Expected beat_id=1 in evidence but got beat_ids={beat_ids}"
        )

    def test_claims_not_empty(self, beat_1):
        """At least one sentence from the response must be backed by a claim."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.claims, "Expected at least one claim."

    def test_confidence_above_base_when_evidence_found(self, beat_1):
        """Confidence should exceed the base 0.5 when evidence is found."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.confidence > 0.5, (
            f"Confidence should be > 0.5 when evidence is found, got {contract.confidence}"
        )

    def test_story_and_chapter_id_propagated(self, beat_1):
        """story_id and chapter_id must be preserved in grounding."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.story_id == "mia_und_leo"
        assert contract.grounding.chapter_id == "chapter_01"

    def test_no_evidence_without_active_beats(self):
        """When no beats are provided, evidence must remain empty."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=None,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == []
        assert contract.grounding.claims == []

    def test_thilio_sentence_does_not_produce_hallucinated_evidence(self, all_beats):
        """
        "Ich bin Thilio, dein Sprachbegleiter" must NOT be grounded to any
        beat because 'Thilio' and 'Sprachbegleiter' do not exist in the story.
        The evidence entries that DO exist must only reference sentences that
        contain actual story content.
        """
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        # All claim texts must NOT be the Thilio sentence alone
        thilio_claim = "Ich bin Thilio, dein Sprachbegleiter"
        claim_texts = [c.claim for c in contract.grounding.claims]
        assert thilio_claim not in claim_texts, (
            "The invented 'Thilio' sentence should not be grounded to any beat."
        )


# ---------------------------------------------------------------------------
# 2. Planned-tasks scenario (num_planned_tasks=3 → beats 1, 4, 7 selected)
#    This mirrors exactly the failing live request.
# ---------------------------------------------------------------------------

class TestBuildOutputContractPlannedTasksScenario:
    """
    With num_planned_tasks=3 the beat loader selects beats 1, 4, 7.
    The first-turn greeting references beat 1 content and must be grounded.
    """

    SPOKEN_TEXT = (
        "Hallo! Ich bin Thilio, dein Sprachbegleiter. "
        "Wir haben ja gerade erst von Mia gehört, die am Waldrand wohnt.\n\n"
        "Weißt du noch, was Mia jeden Tag gemacht hat, "
        "wenn sie aus dem Fenster geschaut hat?"
    )

    def test_evidence_found_with_beats_1_4_7(self, beat_1, beat_4, beat_7):
        """
        Active beats 1, 4, 7 (the distribution for num_planned_tasks=3).
        Evidence should be found because the response references beat 1.
        """
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1, beat_4, beat_7],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence, (
            "Evidence must not be empty when beat 1 is active and the response "
            "references Waldrand and Fenster from beat 1."
        )

    def test_correct_beat_selected_among_1_4_7(self, beat_1, beat_4, beat_7):
        """The evidence must point to beat 1, not beat 4 or 7."""
        contract = build_output_contract(
            response=self.SPOKEN_TEXT,
            active_beats=[beat_1, beat_4, beat_7],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        beat_ids = {ev.beat_id for ev in contract.grounding.evidence}
        assert 1 in beat_ids, (
            f"Expected beat 1 in evidence (Waldrand/Fenster references), got {beat_ids}"
        )
        assert 4 not in beat_ids or 7 not in beat_ids, (
            "Beat 4 or 7 should not be the primary evidence for a beat-1 reference"
        )


# ---------------------------------------------------------------------------
# 3. Paraphrase question sentence grounding
# ---------------------------------------------------------------------------

class TestBuildOutputContractParaphraseQuestion:
    """
    A question that paraphrases beat content must produce evidence.
    """

    def test_fenster_question_grounded_to_beat_1(self, beat_1):
        """
        "Weißt du noch, was Mia jeden Tag gemacht hat, wenn sie aus dem
        Fenster geschaut hat?" is a paraphrase-question of beat 1.
        It must produce evidence pointing to beat 1.
        """
        question = (
            "Weißt du noch, was Mia jeden Tag gemacht hat, "
            "wenn sie aus dem Fenster geschaut hat?"
        )
        contract = build_output_contract(
            response=question,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence, "Paraphrase question must produce evidence."
        assert contract.grounding.evidence[0].beat_id == 1

    def test_waldrand_sentence_grounded_via_entity_anchor(self, beat_1):
        """
        "Wir haben ja gerade erst von Mia gehört, die am Waldrand wohnt"
        contains 'Waldrand' which is a unique beat-1 entity (≥5 chars, only
        in beat 1).  The entity-anchor guard therefore allows this sentence
        to be grounded to beat 1 even though plain word-overlap is low.
        """
        sentence = "Wir haben ja gerade erst von Mia gehört, die am Waldrand wohnt"
        contract = build_output_contract(
            response=sentence,
            active_beats=[beat_1],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        # With only beat 1 available, 'Waldrand' anchors this sentence there.
        assert contract.grounding.evidence, (
            "Sentence containing unique entity 'Waldrand' must be grounded to beat 1."
        )
        assert contract.grounding.evidence[0].beat_id == 1


# ---------------------------------------------------------------------------
# 4. Negative tests – responses with NO evidence in any beat
#    The grounding must stay empty for all of these.
# ---------------------------------------------------------------------------

class TestNoEvidenceHallucinatedContent:
    """
    Responses that invent facts, characters, or places not present in any
    beat of mia_und_leo / chapter_01.  Evidence and claims must be empty.
    """

    def test_invented_character_emma(self, all_beats):
        """
        'Emma' does not exist in the story.  A response that only talks about
        Emma must produce no evidence.
        """
        response = (
            "Emma fand einen großen Drachen tief im Wald. "
            "Der Drachen sprach mit ihr auf Englisch."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Invented character 'Emma' must not produce any evidence."
        )
        assert contract.grounding.claims == []

    def test_invented_location_schloss(self, all_beats):
        """
        'Schloss Mondstein' never appears in the chapter.
        """
        response = (
            "Hinter dem Wald lag das Schloss Mondstein. "
            "Mia wollte unbedingt dorthin reisen und die Prinzessin besuchen."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Invented location 'Schloss Mondstein' must not produce evidence."
        )

    def test_invented_event_leo_flies(self, all_beats):
        """
        Leo never flies in the story.  Fabricated events must not be grounded.
        """
        response = (
            "Leo breitete seine Flügel aus und flog hoch in den Himmel. "
            "Von dort oben sah er das ganze Königreich."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Leo has no wings in the story; fabricated event must not be grounded."
        )

    def test_completely_unrelated_topic_weather(self, all_beats):
        """
        A response about meteorology has nothing to do with the story.
        """
        response = (
            "Morgen wird es regnen und die Temperatur fällt auf fünf Grad. "
            "Vergiss nicht, einen Regenschirm mitzunehmen."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Off-topic weather forecast must not produce any story evidence."
        )

    def test_completely_unrelated_topic_cooking(self, all_beats):
        """
        A cooking recipe has no overlap with any beat.
        """
        response = (
            "Zuerst schneidest du die Zwiebeln klein und brätst sie in der Pfanne an. "
            "Dann gibst du die Tomaten dazu und lässt alles köcheln."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Cooking instructions must not produce any story evidence."
        )

    def test_english_response_unrelated(self, all_beats):
        """
        An English response about a completely different topic must not match.
        """
        response = (
            "The astronaut floated through the space station corridor. "
            "She looked out the window and saw the blue earth below."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "English off-topic response must not produce evidence."
        )

    def test_thilio_self_introduction_alone(self, all_beats):
        """
        'Ich bin Thilio, dein Sprachbegleiter' is pure meta-speech from the
        AI persona – it references nothing from the story.
        Alone it must produce no evidence.
        """
        response = "Ich bin Thilio, dein Sprachbegleiter."
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "AI persona self-introduction must not be grounded to any beat."
        )

    def test_generic_encouragement_produces_no_evidence(self, all_beats):
        """
        Generic encouragement phrases contain no story content.
        """
        response = (
            "Super gemacht! Du hast das wirklich toll erklärt. "
            "Ich bin sehr stolz auf dich!"
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Generic praise/encouragement has no story content and must not be grounded."
        )

    def test_no_beats_always_empty(self):
        """
        Even a verbatim quote from beat 1 must produce no evidence when
        active_beats is an empty list (no context available).
        """
        response = "Jeden Tag schaute sie aus ihrem Fenster und träumte davon, den Wald zu erkunden."
        contract = build_output_contract(
            response=response,
            active_beats=[],
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "No beats available → evidence must always be empty."
        )
        assert contract.grounding.claims == []

    def test_confidence_is_base_when_no_evidence(self, all_beats):
        """
        When no evidence is found the confidence must stay at the base value
        of 0.5 (not inflated as if evidence had been found).
        """
        response = (
            "Emma und die Drachen-Prinzessin tanzten auf dem Mondschloss. "
            "Niemand aus dem Dorf kannte ihr Geheimnis."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == []
        assert contract.confidence == 0.5, (
            f"Confidence must be 0.5 when no evidence found, got {contract.confidence}"
        )


class TestNoEvidencePartialOverlapResponses:
    """
    Responses that mention story characters by name but state facts that
    are not in any beat.  The hallucinated predicate must not be grounded.
    """

    def test_mia_rides_a_horse_not_in_story(self, all_beats):
        """
        Mia is a real story character but she never rides a horse.
        The fabricated predicate must not produce evidence.
        """
        response = (
            "Mia sattelte ihr weißes Pferd und ritt durch das Dorf. "
            "Das Pferd hieß Schneeflocke und war sehr schnell."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Mia riding a horse is not in the story; must produce no evidence."
        )

    def test_leo_has_a_sister_not_in_story(self, all_beats):
        """
        Leo never mentions a sister in any beat.
        """
        response = (
            "Leo hatte eine kleine Schwester namens Luna. "
            "Luna war noch kleiner als Leo und lebte am anderen Ende des Waldes."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Leo's invented sister 'Luna' must not be grounded to any beat."
        )

    def test_mia_builds_a_treehouse_not_in_story(self, all_beats):
        """
        Mia never builds anything in the chapter.
        """
        response = (
            "Mia baute ein Baumhaus im höchsten Eichenbaum des Waldes. "
            "Von dort oben konnte sie das ganze Dorf sehen."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Mia building a treehouse is not in the story; must produce no evidence."
        )

    def test_wrong_chapter_content_no_evidence(self, all_beats):
        """
        A plausible-sounding continuation that invents new chapter events
        must not be grounded to existing beats.
        """
        response = (
            "Am nächsten Tag brachte Leo Mia zu einem geheimen See im Wald. "
            "Der See glitzerte silbern in der Morgensonne."
        )
        contract = build_output_contract(
            response=response,
            active_beats=all_beats,
            story_id="mia_und_leo",
            chapter_id="chapter_01",
        )
        assert contract.grounding.evidence == [], (
            "Invented 'secret lake' scene must not be grounded to chapter_01 beats."
        )

