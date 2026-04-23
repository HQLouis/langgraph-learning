"""
Tests for output_contract_builder.detect_answer_type.

Coverage
--------
- German (currently supported): QUESTION, TASK_INSTRUCTION, ANSWER, STATEMENT
- English (partially supported via language-agnostic rules):
    • Question mark detection and STATEMENT fallback already work incidentally.
    • English-specific task/answer keywords are NOT implemented yet;
      those tests are marked @pytest.mark.xfail so they document the expected
      future behaviour without blocking the test suite.

Implementation priority (highest → lowest)
-------------------------------------------
1. QUESTION  — '?' anywhere, or response starts with a German question word
2. TASK_INSTRUCTION — response contains a German task keyword
3. ANSWER    — response contains a German answer/linking word
4. STATEMENT — fallback

Naming convention: test_<language>_<answer_type>_<scenario>
"""
import pytest

from output_contract_builder import detect_answer_type

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

QUESTION = "QUESTION"
TASK_INSTRUCTION = "TASK_INSTRUCTION"
ANSWER = "ANSWER"
STATEMENT = "STATEMENT"


# ===========================================================================
# German – QUESTION
# ===========================================================================


class TestGermanQuestion:
    """Responses that should be classified as QUESTION (German)."""

    def test_question_mark_at_end(self):
        assert detect_answer_type("Wo wohnt Mia?") == QUESTION

    def test_question_mark_in_middle(self):
        # A sentence containing '?' anywhere must be a QUESTION.
        assert detect_answer_type("Mia fragt: Wer bist du?") == QUESTION

    def test_starts_with_warum(self):
        assert detect_answer_type("Warum ist Mia in den Wald gegangen?") == QUESTION

    def test_starts_with_wie(self):
        assert detect_answer_type("Wie heißt der Fuchs?") == QUESTION

    def test_starts_with_was(self):
        assert detect_answer_type("Was hat Mia gefunden?") == QUESTION

    def test_starts_with_wer(self):
        assert detect_answer_type("Wer hat den Korb getragen?") == QUESTION

    def test_starts_with_wo(self):
        assert detect_answer_type("Wo liegt das Dorf?") == QUESTION

    def test_starts_with_wann(self):
        assert detect_answer_type("Wann ist Leo zurückgekehrt?") == QUESTION

    def test_starts_with_welche(self):
        assert detect_answer_type("Welche Beeren hat Mia gesammelt?") == QUESTION

    def test_starts_with_wie_with_surrounding_whitespace(self):
        # Leading/trailing whitespace must be stripped before matching.
        assert detect_answer_type("  Wie alt ist Mia?  ") == QUESTION

    def test_question_word_without_question_mark(self):
        # 'warum' at the start is sufficient – no '?' required.
        assert detect_answer_type("Warum ging Mia in den Wald") == QUESTION


# ===========================================================================
# German – TASK_INSTRUCTION
# ===========================================================================


class TestGermanTaskInstruction:
    """Responses that should be classified as TASK_INSTRUCTION (German)."""

    def test_erzaehl(self):
        assert detect_answer_type("Erzähl mir, was als nächstes passiert!") == TASK_INSTRUCTION

    def test_beschreib(self):
        assert detect_answer_type("Beschreib den Fuchs mit deinen eigenen Worten.") == TASK_INSTRUCTION

    def test_sag_mir(self):
        assert detect_answer_type("Sag mir, wie Mia sich gefühlt hat.") == TASK_INSTRUCTION

    def test_versuche(self):
        assert detect_answer_type("Versuche, die Geschichte weiterzuerzählen.") == TASK_INSTRUCTION

    def test_kannst_du_with_question_mark_returns_question(self):
        # "Kannst du" is a task keyword, but '?' is detected first because
        # QUESTION has higher priority than TASK_INSTRUCTION in the
        # implementation. This test documents that intentional priority.
        assert detect_answer_type("Kannst du die Szene beschreiben?") == QUESTION

    def test_kannst_du_without_question_mark_returns_task_instruction(self):
        # Without '?', the task keyword wins.
        assert detect_answer_type("Kannst du die Szene beschreiben") == TASK_INSTRUCTION


# ===========================================================================
# German – ANSWER
# ===========================================================================


class TestGermanAnswer:
    """Responses that should be classified as ANSWER (German)."""

    def test_weil(self):
        assert detect_answer_type("Mia ging nach Hause, weil es dunkel wurde.") == ANSWER

    def test_denn(self):
        assert detect_answer_type("Leo half Mia, denn er kannte den Wald gut.") == ANSWER

    def test_deshalb(self):
        assert detect_answer_type("Es war spät, deshalb beeilte sich Mia.") == ANSWER

    def test_darum(self):
        assert detect_answer_type("Leo war müde, darum legte er sich hin.") == ANSWER

    def test_ist(self):
        assert detect_answer_type("Mia ist ein mutiges Mädchen.") == ANSWER

    def test_war(self):
        assert detect_answer_type("Der Wald war dunkel und geheimnisvoll.") == ANSWER

    def test_hat(self):
        assert detect_answer_type("Leo hat die Beeren gefunden.") == ANSWER

    def test_ging(self):
        assert detect_answer_type("Mia ging tiefer in den Wald hinein.") == ANSWER

    def test_multiple_answer_indicators(self):
        assert detect_answer_type("Leo hat geholfen, weil er freundlich war.") == ANSWER


# ===========================================================================
# German – STATEMENT
# ===========================================================================


class TestGermanStatement:
    """Responses without any classifying markers → STATEMENT (German)."""

    def test_neutral_description(self):
        # No question mark, no task keyword, no answer indicator.
        assert detect_answer_type("Der Fuchs sprang aus dem Gebüsch.") == STATEMENT

    def test_empty_like_response(self):
        assert detect_answer_type("Okay.") == STATEMENT

    def test_single_word(self):
        assert detect_answer_type("Toll") == STATEMENT

    def test_exclamation_only(self):
        assert detect_answer_type("Super!") == STATEMENT

    def test_no_keyword_long_text(self):
        assert detect_answer_type("Mia lächelte und nahm den Korb mit nach Hause.") == STATEMENT


# ===========================================================================
# Edge cases (language-agnostic)
# ===========================================================================


class TestEdgeCases:
    """Edge cases that should behave deterministically regardless of language."""

    def test_empty_string_returns_statement(self):
        assert detect_answer_type("") == STATEMENT

    def test_whitespace_only_returns_statement(self):
        assert detect_answer_type("   ") == STATEMENT

    def test_task_indicators_parameter_accepted(self):
        # The second parameter is not yet used in the implementation but must
        # not cause an error when provided.
        result = detect_answer_type("Leo half Mia.", "some task context")
        assert result in {QUESTION, TASK_INSTRUCTION, ANSWER, STATEMENT}

    def test_return_value_is_string(self):
        assert isinstance(detect_answer_type("Mia ist glücklich."), str)

    def test_return_value_is_valid_answer_type(self):
        valid = {QUESTION, TASK_INSTRUCTION, ANSWER, STATEMENT}
        assert detect_answer_type("Mia ist glücklich.") in valid


# ===========================================================================
# English – language-agnostic rules already work
#
# The implementation uses two language-agnostic rules that happen to work
# correctly for English as well:
#   • Any '?' → QUESTION
#   • No matching keyword → STATEMENT (fallback)
# These are regular (non-xfail) tests because the behaviour is correct,
# even though it is a side-effect of the German implementation rather than
# deliberate English support.
# ===========================================================================


class TestEnglishQuestionMarkRule:
    """English questions detected via the language-agnostic '?' rule."""

    def test_question_mark_where_is(self):
        assert detect_answer_type("Where does Mia live?") == QUESTION

    def test_question_mark_why(self):
        assert detect_answer_type("Why did Mia go into the forest?") == QUESTION

    def test_question_mark_how(self):
        assert detect_answer_type("How did Leo find the berries?") == QUESTION

    def test_question_mark_what(self):
        assert detect_answer_type("What did Mia put in her basket?") == QUESTION

    def test_question_mark_who(self):
        assert detect_answer_type("Who helped Mia find the berries?") == QUESTION

    def test_question_mark_when(self):
        assert detect_answer_type("When did Mia return home?") == QUESTION

    def test_question_mark_which(self):
        assert detect_answer_type("Which berries did Leo recommend?") == QUESTION


class TestEnglishStatementFallback:
    """English plain statements fall through to STATEMENT (language-agnostic fallback)."""

    def test_neutral_description(self):
        assert detect_answer_type("The fox jumped out of the bushes.") == STATEMENT

    def test_no_keywords(self):
        assert detect_answer_type("Mia smiled and took the basket home.") == STATEMENT


# ===========================================================================
# English – xfail (English-specific keywords not yet implemented)
#
# These tests document the *expected* future behaviour for English keyword
# detection. They are marked xfail(strict=True) so that:
#   • A failure (current situation) does NOT break CI.
#   • An unexpected pass is reported as XPASS, signalling that the feature
#     was implemented without updating these tests.
# ===========================================================================

_ENGLISH_KEYWORDS_NOT_IMPLEMENTED = pytest.mark.xfail(
    reason="English keyword detection not yet implemented",
    strict=True,
)


@_ENGLISH_KEYWORDS_NOT_IMPLEMENTED
class TestEnglishTaskInstruction:
    """English responses that should eventually be classified as TASK_INSTRUCTION."""

    def test_tell_me(self):
        assert detect_answer_type("Tell me what happens next.") == TASK_INSTRUCTION

    def test_describe(self):
        assert detect_answer_type("Describe the fox in your own words.") == TASK_INSTRUCTION

    def test_try_to(self):
        assert detect_answer_type("Try to continue the story.") == TASK_INSTRUCTION

    def test_can_you_without_question_mark(self):
        assert detect_answer_type("Can you describe the scene") == TASK_INSTRUCTION

    def test_explain(self):
        assert detect_answer_type("Explain what Mia was feeling.") == TASK_INSTRUCTION


@_ENGLISH_KEYWORDS_NOT_IMPLEMENTED
class TestEnglishAnswer:
    """English responses that should eventually be classified as ANSWER."""

    def test_because(self):
        assert detect_answer_type("Mia went home because it was getting dark.") == ANSWER

    def test_therefore(self):
        assert detect_answer_type("It was late, therefore Mia hurried.") == ANSWER

    def test_so(self):
        assert detect_answer_type("Leo was tired, so he lay down.") == ANSWER

    def test_is(self):
        assert detect_answer_type("Mia is a brave girl.") == ANSWER

    def test_has(self):
        assert detect_answer_type("Leo has found the berries.") == ANSWER
