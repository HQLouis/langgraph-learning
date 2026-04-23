"""
Feature: Child Name & Gender Consideration
Test file: Output Contract — structural field-presence assertions

These tests verify that every response from the dialog system produces a
ResponseContract with all required fields populated and of the correct type.
They do NOT assert content quality (that is the job of the LLM-as-judge tests).

Strategy: A (fixture-based) — single run, no N-run loop required.
Marker:   contract
"""

import sys
from pathlib import Path
# Ensure feature-testing/ is on sys.path for feature_testing_utils and ft_config
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from langchain_core.messages import HumanMessage

from feature_testing_utils import build_state_with_beats, MESSAGES_TURN_0
from backend.models.output_contract import AnswerType, ResponseContract

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CHILD_NAME = "Emma"
CHILD_AGE = 6
CHILD_GENDER = "weiblich"
CHILD_INPUT = "Hallo!"


@pytest.fixture(scope="module")
def contract_response(system_llm):
    """
    Run the dialog system once with a fixed first-turn state and return the
    full result dict (containing 'messages' and 'response_contract').

    Scoped to module so the LLM is called only once for all contract tests.
    """
    from nodes import masterChatbot

    state = build_state_with_beats(
        child_name=CHILD_NAME,
        child_age=CHILD_AGE,
        child_gender=CHILD_GENDER,
        messages=[HumanMessage(content=CHILD_INPUT)],
    )
    return masterChatbot(state, system_llm)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.contract
class TestOutputContractFieldPresence:
    """Verify that all required ResponseContract fields are present and valid."""

    def test_response_contract_is_present(self, contract_response):
        """The result must include a response_contract key."""
        assert "response_contract" in contract_response, (
            "masterChatbot() did not return a 'response_contract' key in its result."
        )

    def test_response_contract_is_correct_type(self, contract_response):
        """response_contract must be a ResponseContract instance."""
        contract = contract_response["response_contract"]
        assert isinstance(contract, ResponseContract), (
            f"Expected ResponseContract, got {type(contract).__name__}."
        )

    def test_answer_type_is_valid(self, contract_response):
        """answer_type must be a recognised AnswerType value, not None."""
        contract: ResponseContract = contract_response["response_contract"]
        assert contract.answer_type is not None, "answer_type must not be None."
        valid_values = {e.value for e in AnswerType}
        assert contract.answer_type in valid_values, (
            f"answer_type '{contract.answer_type}' is not a valid AnswerType. "
            f"Expected one of: {valid_values}"
        )

    def test_spoken_text_is_non_empty(self, contract_response):
        """spoken_text must be a non-empty string."""
        contract: ResponseContract = contract_response["response_contract"]
        assert isinstance(contract.spoken_text, str), (
            f"spoken_text must be a string, got {type(contract.spoken_text).__name__}."
        )
        assert contract.spoken_text.strip(), "spoken_text must not be empty or whitespace-only."

    def test_grounding_object_is_present(self, contract_response):
        """grounding must be present (not None)."""
        contract: ResponseContract = contract_response["response_contract"]
        assert contract.grounding is not None, "grounding must not be None."

    def test_no_required_fields_are_none(self, contract_response):
        """Both answer_type and spoken_text must be set (not None)."""
        contract: ResponseContract = contract_response["response_contract"]
        assert contract.answer_type is not None, "answer_type is None — required field missing."
        assert contract.spoken_text is not None, "spoken_text is None — required field missing."

    def test_messages_returned(self, contract_response):
        """masterChatbot must also return at least one AIMessage."""
        from langchain_core.messages import AIMessage
        messages = contract_response.get("messages", [])
        assert messages, "No messages returned by masterChatbot()."
        assert any(isinstance(m, AIMessage) for m in messages), (
            "No AIMessage found in the returned messages list."
        )

