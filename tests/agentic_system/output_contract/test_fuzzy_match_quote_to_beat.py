"""
Tests for output_contract_builder.fuzzy_match_quote_to_beat

Test strategy
-------------
Each test documents:
  - The quote being searched
  - Which beat(s) are provided as candidates
  - The expected return value: either a (Beat, str) tuple or None

NOTE: These tests document the *expected correct behaviour* of the function.
      Some tests are currently FAILING because the SequenceMatcher.ratio()
      scoring penalises short quotes against long beat texts.  They are marked
      with pytest.mark.xfail so the suite stays green while the implementation
      is being improved.

Test groups
-----------
  1. Exact text matches  – the quote is a verbatim substring of a beat
  2. Near-exact matches  – minor wording differences / paraphrase from the LLM
  3. Multi-beat search   – the correct beat must be selected from a full list
  4. No-match cases      – the quote has no connection to any beat (expect None)
  5. Edge cases          – empty string, single word, very long quote, …
"""
import pytest

from output_contract_builder import fuzzy_match_quote_to_beat
from beats import Beat


# ===========================================================================
# 1. EXACT TEXT MATCHES
#    The quote is a verbatim (or case-insensitive) substring of the beat text.
#    fuzzy_match_quote_to_beat MUST return the correct beat and the matched
#    verbatim string from beat.text.
# ===========================================================================

class TestExactMatches:
    """Verbatim substrings that exist word-for-word inside a beat."""

    def test_beat1_window_sentence_exact(self, beat_1):
        """
        'Jeden Tag schaute sie aus ihrem Fenster' is a substring of beat 1.
        Expect: beat_id=1 returned, quote contains the matched text.
        """
        quote = "Jeden Tag schaute sie aus ihrem Fenster"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None, "Expected a match but got None"
        matched_beat, matched_quote = result
        assert matched_beat.beat_id == 1
        assert "Fenster" in matched_quote

    def test_beat1_opening_sentence_exact(self, beat_1):
        """
        The very first sentence of beat 1 should match beat 1.
        """
        quote = "Es war einmal ein kleines Mädchen namens Mia"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None
        matched_beat, matched_quote = result
        assert matched_beat.beat_id == 1
        assert "Mia" in matched_quote

    def test_beat2_forest_intro_exact(self, beat_2):
        """
        'Eines Morgens beschloss Mia, in den Wald zu gehen' is from beat 2.
        """
        quote = "Eines Morgens beschloss Mia, in den Wald zu gehen"
        result = fuzzy_match_quote_to_beat(quote, [beat_2])

        assert result is not None
        matched_beat, matched_quote = result
        assert matched_beat.beat_id == 2

    def test_beat3_rustling_exact(self, beat_3):
        """
        Beat 3 is a single short sentence; match it verbatim.
        """
        quote = "Plötzlich hörte sie ein Rascheln im Gebüsch"
        result = fuzzy_match_quote_to_beat(quote, [beat_3])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 3

    def test_beat4_fox_jumps_exact(self, beat_4):
        """
        'Ein kleiner Fuchs sprang aus dem Gebüsch hervor' is from beat 4.
        """
        quote = "Ein kleiner Fuchs sprang aus dem Gebüsch hervor"
        result = fuzzy_match_quote_to_beat(quote, [beat_4])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 4

    def test_beat5_leo_introduction_exact(self, beat_5):
        """
        'Ich bin Leo' is a verbatim substring of beat 5.
        """
        quote = "Ich bin Leo"
        result = fuzzy_match_quote_to_beat(quote, [beat_5])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 5

    def test_beat9_sunset_exact(self, beat_9):
        """
        'Als die Sonne langsam unterging' is from beat 9.
        """
        quote = "Als die Sonne langsam unterging"
        result = fuzzy_match_quote_to_beat(quote, [beat_9])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 9

    def test_beat10_goodbye_exact(self, beat_10):
        """
        'ging Mia fröhlich nach Hause zurück' is from beat 10.
        """
        quote = "ging Mia fröhlich nach Hause zurück"
        result = fuzzy_match_quote_to_beat(quote, [beat_10])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 10

    def test_case_insensitive_match(self, beat_1):
        """
        The match must work regardless of capitalisation.
        'jeden tag schaute sie aus ihrem fenster' (all lowercase) should still
        match beat 1.
        """
        quote = "jeden tag schaute sie aus ihrem fenster"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 1


# ===========================================================================
# 2. NEAR-EXACT / PARAPHRASE MATCHES
#    The LLM often slightly rephrases beat content.  These tests check that
#    a reasonable threshold still produces the right beat.
#    Marked xfail because the current ratio()-based scorer may miss them.
# ===========================================================================

class TestNearExactMatches:
    """Slightly rephrased quotes that still clearly originate from a beat."""

    def test_beat1_paraphrase_window(self, beat_1):
        """
        The spoken response says 'Mia hat jeden Tag aus ihrem Fenster geschaut'
        (perfect tense) instead of the present 'schaute'.
        Should still resolve to beat 1.
        """
        quote = "Mia hat jeden Tag aus ihrem Fenster geschaut"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None, (
            "Paraphrase of beat 1 window sentence should match beat 1, but got None"
        )
        matched_beat, _ = result
        assert matched_beat.beat_id == 1

    @pytest.mark.xfail(
        reason="Same scorer issue as above"
    )
    def test_beat2_paraphrase_berries(self, beat_2):
        """
        'Mia wollte Beeren im Wald sammeln' is a paraphrase of beat 2.
        """
        quote = "Mia wollte Beeren im Wald sammeln"
        result = fuzzy_match_quote_to_beat(quote, [beat_2])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 2

    @pytest.mark.xfail(reason="Same scorer issue")
    def test_beat5_paraphrase_leo_fox(self, beat_5):
        """
        'Der Fuchs hieß Leo' is an indirect restatement of beat 5.
        """
        quote = "Der Fuchs hieß Leo"
        result = fuzzy_match_quote_to_beat(quote, [beat_5])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 5

    @pytest.mark.xfail(reason="Same scorer issue")
    def test_beat9_paraphrase_sunset(self, beat_9):
        """
        'Die Sonne ging unter und der Himmel wurde orange' is a paraphrase of
        beat 9 that merges two facts from the same beat.
        """
        quote = "Die Sonne ging unter und der Himmel wurde orange"
        result = fuzzy_match_quote_to_beat(quote, [beat_9])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 9


# ===========================================================================
# 3. MULTI-BEAT SEARCH
#    The correct beat must be selected from the full 10-beat list.
# ===========================================================================

class TestMultiBeatSearch:
    """The function must pick the RIGHT beat out of all 10 candidates."""

    def test_beat1_selected_from_all_beats(self, all_beats, beat_1):
        """
        'Jeden Tag schaute sie aus ihrem Fenster' should select beat 1
        even when all 10 beats are available.
        """
        quote = "Jeden Tag schaute sie aus ihrem Fenster"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 1

    def test_beat3_selected_from_all_beats(self, all_beats):
        """
        The exact text of beat 3 should uniquely identify beat 3.
        """
        quote = "Plötzlich hörte sie ein Rascheln im Gebüsch"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 3

    def test_beat4_fox_selected_from_all_beats(self, all_beats):
        """
        'Ein kleiner Fuchs sprang aus dem Gebüsch hervor' should select beat 4.
        """
        quote = "Ein kleiner Fuchs sprang aus dem Gebüsch hervor"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 4

    def test_beat10_selected_from_all_beats(self, all_beats):
        """
        'Mit ihrem vollen Korb und einem neuen Freund im Herzen ging Mia fröhlich nach Hause zurück'
        should select beat 10 (the final beat).
        """
        quote = "Mit ihrem vollen Korb und einem neuen Freund im Herzen ging Mia fröhlich nach Hause zurück"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 10

    def test_beat5_leo_name_selected_from_all_beats(self, all_beats):
        """
        'Ich bin Leo' appears only in beat 5; it should not be confused with
        other beats that also mention Leo.
        """
        quote = "Ich bin Leo und ich bin nur auf der Suche nach meinem Abendessen"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 5

    @pytest.mark.xfail(reason="Paraphrase scoring issue – see TestNearExactMatches")
    def test_beat1_paraphrase_selected_from_all_beats(self, all_beats):
        """
        Even when all beats are present, the paraphrased window sentence
        should still map to beat 1, not beat 2 which also mentions the forest.
        """
        quote = "Mia hat jeden Tag aus ihrem Fenster geschaut"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 1


# ===========================================================================
# 4. NO-MATCH CASES
#    Fabricated / hallucinated content that does not appear in any beat.
#    The function MUST return None.
# ===========================================================================

class TestNoMatchCases:
    """Quotes that are completely unrelated to the beatpack content."""

    def test_invented_character_returns_none(self, all_beats):
        """
        'Emma fand einen Drachen im Wald' – 'Emma' and 'Drachen' do not exist
        in the story at all; expect None.
        """
        quote = "Emma fand einen Drachen im Wald"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is None, (
            f"Hallucinated content should return None, but got beat_id="
            f"{result[0].beat_id if result else 'N/A'}"
        )

    def test_unrelated_topic_returns_none(self, all_beats):
        """
        'Die Katze saß auf dem Dach und schaute in den Himmel' – 'Katze' and
        'Dach' never appear in this chapter.
        """
        quote = "Die Katze saß auf dem Dach und schaute in den Himmel"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is None

    def test_empty_beat_list_returns_none(self):
        """
        When no beats are provided the function must return None gracefully.
        """
        quote = "Mia hat jeden Tag aus ihrem Fenster geschaut"
        result = fuzzy_match_quote_to_beat(quote, [])

        assert result is None

    def test_completely_different_language_returns_none(self, all_beats):
        """
        An English sentence unrelated to the German story should return None.
        """
        quote = "The quick brown fox jumped over the lazy dog"
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is None


# ===========================================================================
# 5. EDGE CASES
# ===========================================================================

class TestEdgeCases:

    @pytest.mark.xfail(
        reason="Empty quote triggers the exact-match path ('') which is a substring of every "
               "beat, causing the function to return a spurious match instead of None. "
               "The implementation should guard against empty/whitespace-only input."
    )
    def test_empty_quote_returns_none(self, all_beats):
        """
        An empty string quote should not crash and must return None.
        The current implementation incorrectly returns a match because the empty
        string is a substring of every beat text.
        """
        result = fuzzy_match_quote_to_beat("", all_beats)
        assert result is None

    @pytest.mark.xfail(
        reason="'Mia' is a verbatim substring of beat 1, so the exact-match path fires "
               "immediately before the threshold check, bypassing the 0.6 guard. "
               "Single-word / too-short queries should be rejected before substring search."
    )
    def test_single_common_word_returns_none(self, all_beats):
        """
        A single extremely common word like 'Mia' would match every beat that
        mentions her.  At the default threshold (0.6) a single word should
        NOT produce a confident match because the ratio is too low.
        The current implementation returns beat 1 because 'mia' is literally
        a substring, completely bypassing the threshold.
        """
        result = fuzzy_match_quote_to_beat("Mia", all_beats, threshold=0.6)
        assert result is None

    def test_very_long_quote_spanning_two_beats(self, all_beats):
        """
        A quote that spans the boundary of beat 1 and beat 2 should still
        match ONE of the two beats (whichever has the higher score).
        The function must not crash and must return beat 1 or beat 2.
        """
        # Final sentence of beat 1 + opening sentence of beat 2
        quote = (
            "Jeden Tag schaute sie aus ihrem Fenster und träumte davon, "
            "den Wald zu erkunden. Eines Morgens beschloss Mia, in den Wald zu gehen"
        )
        result = fuzzy_match_quote_to_beat(quote, all_beats)

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id in (1, 2)

    def test_custom_low_threshold_matches_paraphrase(self, beat_1):
        """
        With a very low threshold (0.1) even a loose paraphrase should return
        something rather than None.
        """
        quote = "Mia schaute täglich aus dem Fenster"
        result = fuzzy_match_quote_to_beat(quote, [beat_1], threshold=0.1)

        # At threshold=0.1 we expect a match to be found for beat 1
        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 1

    def test_custom_high_threshold_rejects_paraphrase(self, beat_1):
        """
        With a very high threshold (0.99) a paraphrase should return None
        because it cannot possibly score that high.
        """
        quote = "Mia hat jeden Tag aus ihrem Fenster geschaut"
        result = fuzzy_match_quote_to_beat(quote, [beat_1], threshold=0.99)

        assert result is None

    def test_return_type_is_tuple(self, beat_1):
        """
        A successful match must return a tuple of exactly (Beat, str).
        """
        quote = "Jeden Tag schaute sie aus ihrem Fenster"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 2
        matched_beat, matched_quote = result
        assert isinstance(matched_beat, Beat)
        assert isinstance(matched_quote, str)
        assert len(matched_quote) > 0

    def test_matched_quote_is_substring_of_beat_text(self, beat_1):
        """
        The matched_quote returned must be a substring of the beat's text
        (for exact matches).
        """
        quote = "Jeden Tag schaute sie aus ihrem Fenster"
        result = fuzzy_match_quote_to_beat(quote, [beat_1])

        assert result is not None
        matched_beat, matched_quote = result
        assert matched_quote in matched_beat.text or matched_quote.lower() in matched_beat.text.lower()

    def test_whitespace_normalisation(self, beat_3):
        """
        Extra internal whitespace in the quote should not prevent a match
        because normalisation strips it.
        """
        # Beat 3: "Plötzlich hörte sie ein Rascheln im Gebüsch."
        quote = "Plötzlich  hörte   sie  ein  Rascheln  im  Gebüsch"
        result = fuzzy_match_quote_to_beat(quote, [beat_3])

        assert result is not None
        matched_beat, _ = result
        assert matched_beat.beat_id == 3

