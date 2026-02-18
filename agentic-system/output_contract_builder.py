"""
Output Contract Builder - Automatically constructs output contracts from responses.

This module builds the output contract structure programmatically rather than asking
the LLM to generate it. It uses the available context (beats, state) to construct
evidence and claims automatically.
"""
import logging
import re
from typing import Optional, List, Dict, Tuple
from difflib import SequenceMatcher
from beats import Beat

logger = logging.getLogger(__name__)


def fuzzy_match_quote_to_beat(quote: str, beats: List[Beat], threshold: float = 0.6) -> Optional[Tuple[Beat, str]]:
    """
    Find which beat contains a quote using fuzzy matching.

    Args:
        quote: The quote to search for
        beats: List of beats to search in
        threshold: Similarity threshold (0.0 to 1.0)

    Returns:
        Tuple of (matching_beat, exact_quote_found) or None if no match
    """
    quote_normalized = " ".join(quote.lower().split())
    best_match = None
    best_score = 0.0
    best_quote = None

    for beat in beats:
        content_normalized = " ".join(beat.text.lower().split())

        # Try exact match first
        if quote_normalized in content_normalized:
            # Find the exact quote in the original text
            pattern = re.compile(re.escape(quote), re.IGNORECASE)
            match = pattern.search(beat.text)
            if match:
                return beat, match.group(0)

        # Try fuzzy matching
        matcher = SequenceMatcher(None, quote_normalized, content_normalized)
        score = matcher.ratio()

        if score > best_score:
            best_score = score
            best_match = beat
            # Find the best matching substring
            matching_blocks = matcher.get_matching_blocks()
            if matching_blocks:
                # Get the longest matching block
                longest_block = max(matching_blocks, key=lambda b: b.size)
                if longest_block.size > 0:
                    start = longest_block.b
                    end = start + longest_block.size
                    best_quote = beat.text[start:end]

    if best_score >= threshold and best_match:
        return best_match, best_quote or best_match.text[:100]

    return None


def extract_sentences(text: str) -> List[str]:
    """
    Extract sentences from text for claim analysis.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Simple sentence splitting (can be improved with NLP)
    sentences = re.split(r'[.!?]+', text)
    return [s.strip() for s in sentences if s.strip()]


def detect_answer_type(response: str, task_indicators: Optional[str] = None) -> str:
    """
    Detect the type of answer from the response text.

    Args:
        response: The response text
        task_indicators: Optional task indicators from aufgaben

    Returns:
        Answer type (ANSWER, QUESTION, STATEMENT, TASK_INSTRUCTION)
    """
    response_lower = response.lower().strip()

    # Check for questions
    if '?' in response or response_lower.startswith(('warum', 'wie', 'was', 'wer', 'wo', 'wann', 'welche')):
        return "QUESTION"

    # Check for task instructions
    task_keywords = ['erzähl', 'beschreib', 'sag mir', 'versuche', 'kannst du']
    if any(keyword in response_lower for keyword in task_keywords):
        return "TASK_INSTRUCTION"

    # Check if it's answering something
    answer_indicators = ['weil', 'denn', 'deshalb', 'darum', 'ist', 'war', 'hat', 'ging']
    if any(indicator in response_lower for indicator in answer_indicators):
        return "ANSWER"

    return "STATEMENT"


def detect_task_type(aufgaben: Optional[str], response: str) -> Tuple[str, Optional[str]]:
    """
    Detect task type from aufgaben and response.

    Args:
        aufgaben: Task information from state
        response: The response text

    Returns:
        Tuple of (task_type, learning_goal)
    """
    if not aufgaben:
        return "NONE", None

    aufgaben_lower = aufgaben.lower()

    # Map keywords to task types
    # TODO LNG: Adjust this! Wir haben andere Aufgaben. Entweder  wir setzen die Keywords hier passend zu unseren Aufgaben oder diese Methode wird nicht verwendet!
    if any(word in aufgaben_lower for word in ['verständnis', 'comprehension', 'verstehen']):
        return "COMPREHENSION_QUESTION", "Leseverständnis und Textverständnis"
    elif any(word in aufgaben_lower for word in ['grammatik', 'grammar', 'satzbau']):
        return "GRAMMAR_EXERCISE", "Grammatik und Satzbau"
    elif any(word in aufgaben_lower for word in ['vokabular', 'vocabulary', 'wörter', 'wort']):
        return "VOCABULARY_TASK", "Wortschatz und Sprachentwicklung"
    elif any(word in aufgaben_lower for word in ['kreativ', 'creative', 'erfinde', 'gestalte']):
        return "CREATIVE_TASK", "Kreatives Denken und Ausdruck"

    return "NONE", None


def build_output_contract(
    response: str,
    active_beats: Optional[List[Beat]] = None,
    story_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    aufgaben: Optional[str] = None,
    last_user_message: Optional[str] = None
) -> dict:
    """
    Build an output contract from the response and available context.

    This function constructs the entire output contract programmatically
    without relying on the LLM to format JSON.

    Args:
        response: The spoken text generated by the LLM
        active_beats: List of beats that were used as context
        story_id: Story identifier
        chapter_id: Chapter identifier
        aufgaben: Task information from state
        last_user_message: The user's last message

    Returns:
        Complete output contract dictionary
    """
    logger.info("Building output contract from response and context")

    # Detect answer type
    answer_type = detect_answer_type(response, aufgaben)
    logger.info(f"Detected answer_type: {answer_type}")

    # Build task information
    task_type, learning_goal = detect_task_type(aufgaben, response)
    task = None

    if answer_type == "QUESTION" or task_type != "NONE":
        task = {
            "task_type": task_type if task_type != "NONE" else "COMPREHENSION_QUESTION",
            "prompt_spoken": response if answer_type == "QUESTION" else None,
            "expected_child_response_type": "FREE_TEXT",
            "learning_goal": learning_goal
        }

    # Build grounding with evidence
    evidence_list = []
    claims_list = []

    if active_beats:
        logger.info(f"Processing {len(active_beats)} active beats for evidence extraction")

        # Extract sentences from response as potential claims
        sentences = extract_sentences(response)

        for idx, sentence in enumerate(sentences):
            # Skip very short sentences
            if len(sentence.split()) < 3:
                continue

            # Try to find this sentence or parts of it in the beats
            match_result = fuzzy_match_quote_to_beat(sentence, active_beats, threshold=0.5)

            if match_result:
                beat, quote = match_result

                # Check if we already have this evidence
                evidence_idx = None
                for i, ev in enumerate(evidence_list):
                    if ev.get("beat_id") == beat.beat_id:
                        evidence_idx = i
                        break

                if evidence_idx is None:
                    # Add new evidence
                    evidence_idx = len(evidence_list)
                    evidence_list.append({
                        "beat_id": beat.beat_id,
                        "quote": quote,
                        "source": chapter_id
                    })
                    logger.info(f"Added evidence from beat {beat.beat_id}: '{quote[:50]}...'")

                # Add claim
                claims_list.append({
                    "claim": sentence,
                    "supported_by": [evidence_idx]
                })
                logger.info(f"Added claim: '{sentence[:50]}...' supported by evidence {evidence_idx}")

        # If no claims were found from sentences, try to match the whole response
        if not claims_list and active_beats:
            match_result = fuzzy_match_quote_to_beat(response, active_beats, threshold=0.4)
            if match_result:
                beat, quote = match_result
                evidence_list.append({
                    "beat_id": beat.beat_id,
                    "quote": quote,
                    "source": chapter_id
                })
                claims_list.append({
                    "claim": response,
                    "supported_by": [0]
                })
                logger.info(f"Added whole response as single claim from beat {beat.beat_id}")

    grounding = {
        "story_id": story_id,
        "chapter_id": chapter_id,
        "evidence": evidence_list,
        "claims": claims_list
    }

    # Calculate confidence based on evidence quality
    confidence = 0.5  # Base confidence
    if evidence_list:
        # Higher confidence if we found evidence
        confidence = 0.8 + (min(len(evidence_list), 3) * 0.05)
    if not active_beats:
        # Lower confidence if no beats available
        confidence = 0.6

    contract = {
        "answer_type": answer_type,
        "spoken_text": response,
        "task": task, # TODO LNG: Entfernen des tasks wenn aufgaben hier nicht richtig benutzt werden kann. Dann auch entsprechend in nodes.py anpassen
        "grounding": grounding,
        "confidence": round(confidence, 2)
    }

    logger.info(f"Built output contract: {len(evidence_list)} evidence items, {len(claims_list)} claims, confidence={confidence:.2f}")

    return contract

