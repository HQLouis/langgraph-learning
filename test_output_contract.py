#!/usr/bin/env python3
"""
Test script for Output Contract functionality.

This script tests the automatic generation of output contracts from responses.
"""
import sys
from pathlib import Path

# Add agentic-system to path
agentic_path = Path(__file__).parent / "agentic-system"
sys.path.insert(0, str(agentic_path))

from output_contract_builder import build_output_contract
from beats import Beat

def test_basic_contract():
    """Test basic contract building without beats."""
    print("=" * 60)
    print("Test 1: Basic contract without beats")
    print("=" * 60)

    response = "Mia ist nach Hause gegangen, weil es schon dunkel wurde."

    contract = build_output_contract(
        response=response,
        story_id="mia_und_leo",
        chapter_id="chapter_01"
    )

    print(f"Answer Type: {contract['answer_type']}")
    print(f"Spoken Text: {contract['spoken_text']}")
    print(f"Confidence: {contract['confidence']}")
    print(f"Evidence Count: {len(contract['grounding']['evidence'])}")
    print(f"Claims Count: {len(contract['grounding']['claims'])}")
    print()


def test_contract_with_beats():
    """Test contract building with beat context."""
    print("=" * 60)
    print("Test 2: Contract with beat evidence")
    print("=" * 60)
    
    # Create mock beats (Beat is a dataclass with: beat_id, order, span, text, entities, facts, tags, safety_tags)
    from beats import TextSpan
    
    beats = [
        Beat(
            beat_id=1,
            order=0,
            span=TextSpan(start_char=0, end_char=100),
            text="Mia spielte im Park mit ihrem Ball."
        ),
        Beat(
            beat_id=2,
            order=1,
            span=TextSpan(start_char=100, end_char=200),
            text="Es wurde schon dunkel, also ging Mia nach Hause."
        ),
        Beat(
            beat_id=3,
            order=2,
            span=TextSpan(start_char=200, end_char=300),
            text="Ihre Mutter wartete schon auf sie."
        )
    ]

    response = "Mia ist nach Hause gegangen, weil es schon dunkel wurde."

    contract = build_output_contract(
        response=response,
        active_beats=beats,
        story_id="mia_und_leo",
        chapter_id="chapter_01"
    )

    print(f"Answer Type: {contract['answer_type']}")
    print(f"Spoken Text: {contract['spoken_text']}")
    print(f"Confidence: {contract['confidence']}")
    print(f"\nEvidence ({len(contract['grounding']['evidence'])} items):")
    for i, evidence in enumerate(contract['grounding']['evidence']):
        print(f"  [{i}] Beat {evidence['beat_id']}: '{evidence['quote'][:50]}...'")

    print(f"\nClaims ({len(contract['grounding']['claims'])} items):")
    for i, claim in enumerate(contract['grounding']['claims']):
        print(f"  [{i}] '{claim['claim'][:50]}...' (supported by: {claim['supported_by']})")
    print()


def test_question_detection():
    """Test question detection in contract."""
    print("=" * 60)
    print("Test 3: Question detection")
    print("=" * 60)

    response = "Warum ist Mia nach Hause gegangen?"
    aufgaben = "Stelle dem Kind Verständnisfragen zur Geschichte."

    contract = build_output_contract(
        response=response,
        story_id="mia_und_leo",
        chapter_id="chapter_01",
        aufgaben=aufgaben
    )

    print(f"Answer Type: {contract['answer_type']}")
    print(f"Task Type: {contract['task']['task_type'] if contract['task'] else 'None'}")
    print(f"Learning Goal: {contract['task']['learning_goal'] if contract['task'] else 'None'}")
    print()


def test_fuzzy_matching():
    """Test fuzzy matching of evidence."""
    print("=" * 60)
    print("Test 4: Fuzzy matching with slight variations")
    print("=" * 60)
    
    from beats import TextSpan
    
    beats = [
        Beat(
            beat_id=1,
            order=0,
            span=TextSpan(start_char=0, end_char=100),
            text="Es wurde schon dunkel, also ging Mia nach Hause."
        )
    ]

    # Response with slight variation
    response = "Mia ging nach Hause, weil es dunkel wurde."

    contract = build_output_contract(
        response=response,
        active_beats=beats,
        story_id="mia_und_leo",
        chapter_id="chapter_01"
    )

    print(f"Response: {response}")
    print(f"Evidence found: {len(contract['grounding']['evidence']) > 0}")
    if contract['grounding']['evidence']:
        print(f"Matched to beat {contract['grounding']['evidence'][0]['beat_id']}")
        print(f"Quote: {contract['grounding']['evidence'][0]['quote']}")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("OUTPUT CONTRACT BUILDER TESTS")
    print("=" * 60 + "\n")

    test_basic_contract()
    test_contract_with_beats()
    test_question_detection()
    test_fuzzy_matching()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)

