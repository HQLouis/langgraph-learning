"""
Tests for output_contract_builder.detect_task_type.

Coverage
--------
- German (currently supported):
    COMPREHENSION_QUESTION, GRAMMAR_EXERCISE, VOCABULARY_TASK, CREATIVE_TASK, NONE
- English (not yet implemented):
    marked with @pytest.mark.xfail – documents expected future behaviour
    without blocking the test suite.

Function signature
------------------
    detect_task_type(aufgaben: Optional[str], response: str)
        -> Tuple[str, Optional[str]]

    aufgaben  – task instruction text (the signal that drives classification)
    response  – the AI response text (currently unused by the implementation,
                but accepted so callers can pass it for future use)

Return contract
---------------
    (task_type: str, learning_goal: Optional[str])

    | task_type               | learning_goal                            |
    |-------------------------|------------------------------------------|
    | COMPREHENSION_QUESTION  | "Leseverständnis und Textverständnis"    |
    | GRAMMAR_EXERCISE        | "Grammatik und Satzbau"                  |
    | VOCABULARY_TASK         | "Wortschatz und Sprachentwicklung"       |
    | CREATIVE_TASK           | "Kreatives Denken und Ausdruck"          |
    | NONE                    | None                                     |

German detection keywords (per category)
-----------------------------------------
    COMPREHENSION_QUESTION : 'verständnis', 'comprehension', 'verstehen'
    GRAMMAR_EXERCISE       : 'grammatik', 'grammar', 'satzbau'
    VOCABULARY_TASK        : 'vokabular', 'vocabulary', 'wörter', 'wort'
    CREATIVE_TASK          : 'kreativ', 'creative', 'erfinde', 'gestalte'

Naming convention: test_<language>_<task_type>_<scenario>
"""
import pytest

from output_contract_builder import detect_task_type

# ---------------------------------------------------------------------------
# Constants – task types and their expected learning goals
# ---------------------------------------------------------------------------

NONE_TYPE = "NONE"
COMPREHENSION = "COMPREHENSION_QUESTION"
GRAMMAR = "GRAMMAR_EXERCISE"
VOCABULARY = "VOCABULARY_TASK"
CREATIVE = "CREATIVE_TASK"

LEARNING_GOAL_COMPREHENSION = "Leseverständnis und Textverständnis"
LEARNING_GOAL_GRAMMAR = "Grammatik und Satzbau"
LEARNING_GOAL_VOCABULARY = "Wortschatz und Sprachentwicklung"
LEARNING_GOAL_CREATIVE = "Kreatives Denken und Ausdruck"

# Placeholder response – the implementation does not use it yet, but it is
# required by the function signature.
ANY_RESPONSE = "Mia ging in den Wald."


# ===========================================================================
# No aufgaben → always NONE
# ===========================================================================


class TestNoAufgaben:
    """When aufgaben is absent the function must always return (NONE, None)."""

    def test_none_aufgaben_returns_none_type(self):
        task_type, learning_goal = detect_task_type(None, ANY_RESPONSE)
        assert task_type == NONE_TYPE

    def test_none_aufgaben_returns_none_learning_goal(self):
        _, learning_goal = detect_task_type(None, ANY_RESPONSE)
        assert learning_goal is None

    def test_empty_string_aufgaben_returns_none_type(self):
        task_type, _ = detect_task_type("", ANY_RESPONSE)
        assert task_type == NONE_TYPE

    def test_empty_string_aufgaben_returns_none_learning_goal(self):
        _, learning_goal = detect_task_type("", ANY_RESPONSE)
        assert learning_goal is None

    def test_whitespace_only_aufgaben_returns_none_type(self):
        task_type, _ = detect_task_type("   ", ANY_RESPONSE)
        assert task_type == NONE_TYPE

    def test_whitespace_only_aufgaben_returns_none_learning_goal(self):
        _, learning_goal = detect_task_type("   ", ANY_RESPONSE)
        assert learning_goal is None


# ===========================================================================
# German – COMPREHENSION_QUESTION
# ===========================================================================


class TestGermanComprehensionQuestion:
    """Aufgaben that should be classified as COMPREHENSION_QUESTION (German)."""

    def test_keyword_verstaendnis(self):
        task_type, _ = detect_task_type("Zeige dein Verständnis des Textes.", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_keyword_verstehen(self):
        task_type, _ = detect_task_type("Kannst du die Geschichte verstehen?", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_keyword_verstaendnis_lowercase(self):
        task_type, _ = detect_task_type("zeige dein verständnis", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_keyword_verstaendnis_in_compound_word(self):
        # 'verständnis' must be found even when embedded in a compound noun.
        task_type, _ = detect_task_type("Textverständnisaufgabe", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_learning_goal_is_correct(self):
        _, learning_goal = detect_task_type("Zeige dein Verständnis.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_COMPREHENSION

    def test_response_argument_does_not_affect_result(self):
        # The response text must be irrelevant to the classification.
        result_a = detect_task_type("verstehen", "Mia lief nach Hause.")
        result_b = detect_task_type("verstehen", "Leo fand die Beeren.")
        assert result_a == result_b


# ===========================================================================
# German – GRAMMAR_EXERCISE
# ===========================================================================


class TestGermanGrammarExercise:
    """Aufgaben that should be classified as GRAMMAR_EXERCISE (German)."""

    def test_keyword_grammatik(self):
        task_type, _ = detect_task_type("Erkläre die Grammatik des Satzes.", ANY_RESPONSE)
        assert task_type == GRAMMAR

    def test_keyword_satzbau(self):
        task_type, _ = detect_task_type("Analysiere den Satzbau.", ANY_RESPONSE)
        assert task_type == GRAMMAR

    def test_keyword_grammatik_lowercase(self):
        task_type, _ = detect_task_type("grammatik üben", ANY_RESPONSE)
        assert task_type == GRAMMAR

    def test_learning_goal_is_correct(self):
        _, learning_goal = detect_task_type("Erkläre die Grammatik.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_GRAMMAR


# ===========================================================================
# German – VOCABULARY_TASK
# ===========================================================================


class TestGermanVocabularyTask:
    """Aufgaben that should be classified as VOCABULARY_TASK (German)."""

    def test_keyword_vokabular(self):
        task_type, _ = detect_task_type("Erweitere dein Vokabular.", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_keyword_woerter(self):
        task_type, _ = detect_task_type("Welche neuen Wörter kennst du?", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_keyword_wort(self):
        task_type, _ = detect_task_type("Erkläre das Wort 'geheimnisvoll'.", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_keyword_vokabular_lowercase(self):
        task_type, _ = detect_task_type("vokabular lernen", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_learning_goal_is_correct(self):
        _, learning_goal = detect_task_type("Erweitere dein Vokabular.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_VOCABULARY


# ===========================================================================
# German – CREATIVE_TASK
# ===========================================================================


class TestGermanCreativeTask:
    """Aufgaben that should be classified as CREATIVE_TASK (German)."""

    def test_keyword_kreativ(self):
        task_type, _ = detect_task_type("Schreibe eine kreativ Geschichte weiter.", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_keyword_erfinde(self):
        task_type, _ = detect_task_type("Erfinde ein neues Ende für die Geschichte.", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_keyword_gestalte(self):
        task_type, _ = detect_task_type("Gestalte eine neue Szene.", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_keyword_kreativ_lowercase(self):
        task_type, _ = detect_task_type("eine kreativ aufgabe", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_learning_goal_is_correct(self):
        _, learning_goal = detect_task_type("Erfinde ein neues Ende.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_CREATIVE


# ===========================================================================
# German – NONE (no matching keyword)
# ===========================================================================


class TestGermanNone:
    """Aufgaben with no recognisable keyword → (NONE, None)."""

    def test_unrelated_aufgaben_returns_none_type(self):
        task_type, _ = detect_task_type("Höre der Geschichte aufmerksam zu.", ANY_RESPONSE)
        assert task_type == NONE_TYPE

    def test_unrelated_aufgaben_returns_none_learning_goal(self):
        _, learning_goal = detect_task_type("Höre der Geschichte aufmerksam zu.", ANY_RESPONSE)
        assert learning_goal is None

    def test_gibberish_returns_none(self):
        task_type, learning_goal = detect_task_type("xyzxyz", ANY_RESPONSE)
        assert task_type == NONE_TYPE
        assert learning_goal is None


# ===========================================================================
# Edge cases (language-agnostic)
# ===========================================================================


class TestEdgeCases:
    """Structural / contract guarantees independent of language."""

    def test_return_value_is_tuple_of_length_two(self):
        result = detect_task_type("Grammatik üben", ANY_RESPONSE)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_task_type_is_always_string(self):
        task_type, _ = detect_task_type("Grammatik üben", ANY_RESPONSE)
        assert isinstance(task_type, str)

    def test_learning_goal_is_string_or_none(self):
        _, learning_goal = detect_task_type("Grammatik üben", ANY_RESPONSE)
        assert learning_goal is None or isinstance(learning_goal, str)

    def test_known_task_type_values(self):
        """task_type must always be one of the five documented values."""
        valid_types = {NONE_TYPE, COMPREHENSION, GRAMMAR, VOCABULARY, CREATIVE}
        for aufgaben in [
            None, "", "unbekannt",
            "verständnis", "grammatik", "vokabular", "kreativ",
        ]:
            task_type, _ = detect_task_type(aufgaben, ANY_RESPONSE)
            assert task_type in valid_types, f"Unexpected task_type {task_type!r} for aufgaben={aufgaben!r}"

    def test_first_matching_category_wins(self):
        # 'verständnis' is checked before 'grammatik', so only COMPREHENSION
        # should be returned when both keywords are present.
        task_type, _ = detect_task_type("verständnis grammatik", ANY_RESPONSE)
        assert task_type == COMPREHENSION


# ===========================================================================
# English – language-agnostic keywords already work
#
# Two keywords in the German lists are English loanwords/shared spellings
# that happen to match English aufgaben text:
#   • 'comprehension'  → COMPREHENSION_QUESTION
#   • 'vocabulary'     → VOCABULARY_TASK
# These produce the correct result today (as a side-effect of the German
# implementation), so they are regular – not xfail – tests.
# ===========================================================================


class TestEnglishLoanwordKeywords:
    """
    English loanwords already present in the German keyword lists.

    These four keywords appear verbatim in the German detection lists and
    therefore work correctly today, even without dedicated English support:
      'comprehension' → COMPREHENSION_QUESTION
      'vocabulary'    → VOCABULARY_TASK
      'grammar'       → GRAMMAR_EXERCISE
      'creative'      → CREATIVE_TASK

    The learning_goal returned is always the German label, because the
    full English implementation (localised learning goals, etc.) is still
    pending.
    """

    def test_comprehension_keyword_works_for_english_aufgaben(self):
        task_type, _ = detect_task_type("Test reading comprehension.", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_comprehension_learning_goal_is_german_string(self):
        _, learning_goal = detect_task_type("Test reading comprehension.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_COMPREHENSION

    def test_vocabulary_keyword_works_for_english_aufgaben(self):
        task_type, _ = detect_task_type("Expand your vocabulary.", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_vocabulary_learning_goal_is_german_string(self):
        _, learning_goal = detect_task_type("Expand your vocabulary.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_VOCABULARY

    def test_grammar_keyword_works_for_english_aufgaben(self):
        task_type, _ = detect_task_type("Practise the grammar rule.", ANY_RESPONSE)
        assert task_type == GRAMMAR

    def test_grammar_learning_goal_is_german_string(self):
        _, learning_goal = detect_task_type("Practise the grammar rule.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_GRAMMAR

    def test_creative_keyword_works_for_english_aufgaben(self):
        task_type, _ = detect_task_type("Write a creative ending.", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_creative_learning_goal_is_german_string(self):
        _, learning_goal = detect_task_type("Write a creative ending.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_CREATIVE


# ===========================================================================
# English – xfail (English-specific keywords not yet implemented)
#
# These tests document the *expected* future behaviour for English keyword
# detection. Marked xfail(strict=True) so that:
#   • A failure (current situation) does NOT break CI.
#   • An unexpected pass surfaces as XPASS, signalling the feature was
#     implemented without updating these tests.
# ===========================================================================

_ENGLISH_NOT_IMPLEMENTED = pytest.mark.xfail(
    reason="English keyword detection not yet implemented",
    strict=True,
)


@_ENGLISH_NOT_IMPLEMENTED
class TestEnglishComprehensionQuestion:
    """English aufgaben that should eventually map to COMPREHENSION_QUESTION."""

    def test_keyword_understanding(self):
        task_type, _ = detect_task_type("Show your understanding of the text.", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_keyword_reading(self):
        task_type, _ = detect_task_type("Answer the reading questions.", ANY_RESPONSE)
        assert task_type == COMPREHENSION

    def test_learning_goal_when_english_aufgaben(self):
        _, learning_goal = detect_task_type("Show your understanding.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_COMPREHENSION


@_ENGLISH_NOT_IMPLEMENTED
class TestEnglishGrammarExercise:
    """English aufgaben that should eventually map to GRAMMAR_EXERCISE."""

    def test_keyword_sentence_structure(self):
        # 'grammar' already works via the loanword list; this covers a
        # purely English synonym that is not yet in the keyword lists.
        task_type, _ = detect_task_type("Analyse the sentence structure.", ANY_RESPONSE)
        assert task_type == GRAMMAR


@_ENGLISH_NOT_IMPLEMENTED
class TestEnglishVocabularyTask:
    """English aufgaben that should eventually map to VOCABULARY_TASK."""

    def test_keyword_words(self):
        task_type, _ = detect_task_type("Find the new words in the story.", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_keyword_word(self):
        task_type, _ = detect_task_type("Explain the word 'mysterious'.", ANY_RESPONSE)
        assert task_type == VOCABULARY

    def test_learning_goal_when_english_aufgaben(self):
        _, learning_goal = detect_task_type("Find the new words.", ANY_RESPONSE)
        assert learning_goal == LEARNING_GOAL_VOCABULARY


@_ENGLISH_NOT_IMPLEMENTED
class TestEnglishCreativeTask:
    """English aufgaben that should eventually map to CREATIVE_TASK."""

    def test_keyword_invent(self):
        # 'creative' already works via the loanword list; these cover purely
        # English synonyms that are not yet in the keyword lists.
        task_type, _ = detect_task_type("Invent a new character.", ANY_RESPONSE)
        assert task_type == CREATIVE

    def test_keyword_design(self):
        task_type, _ = detect_task_type("Design a new scene.", ANY_RESPONSE)
        assert task_type == CREATIVE

