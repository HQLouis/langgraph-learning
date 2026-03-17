"""
Post-processing module for correcting common German grammar errors in LLM output.

Phase 1 of the grammar correction pipeline: regex-based corrections for known
error patterns. Designed to be incrementally extended as new patterns are discovered.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Each pattern is a tuple of (name, compiled_regex, replacement_function_or_string)
# The replacement function receives a match object and returns the corrected string.

def _fix_verb_conjugation_2nd_to_3rd(match: re.Match) -> str:
    """Fix 2nd person singular verb used before 3rd person pronoun.

    E.g., 'suchst er' → 'sucht er', 'spielst sie' → 'spielt sie'
    The pattern captures a verb stem ending in 'st' before er/sie/es/man.
    We remove the 's' to get the 3rd person singular form (stem + t).
    """
    verb_2nd = match.group(1)  # e.g., "suchst"
    pronoun = match.group(2)   # e.g., "er"
    # Remove the 's' before the final 't' → "sucht"
    verb_3rd = verb_2nd[:-2] + "t"
    return f"{verb_3rd} {pronoun}"


PATTERNS: list[tuple[str, re.Pattern, callable]] = [
    (
        "verb_conjugation_2nd_to_3rd_person",
        # Matches verbs ending in 'st' followed by 3rd person pronouns.
        # Negative lookbehind for 'du ' to avoid correcting valid 2nd person usage.
        # Word boundary ensures we match complete words.
        # Requires at least 3 chars in the verb (stem + st) to avoid matching
        # words like "ist", "bist", etc.
        re.compile(
            r"(?<!du )(?<!Du )\b(\w{2,}st)\s+(er|sie|es|man)\b",
            re.UNICODE,
        ),
        _fix_verb_conjugation_2nd_to_3rd,
    ),
]


def correct_common_german_errors(text: str) -> tuple[str, list[str]]:
    """Apply known German grammar corrections to the given text.

    Args:
        text: The input text to correct.

    Returns:
        A tuple of (corrected_text, list_of_corrections).
        Each correction is a descriptive string like
        "verb_conjugation_2nd_to_3rd_person: 'suchst er' → 'sucht er'".
    """
    corrections: list[str] = []

    for name, pattern, replacement_fn in PATTERNS:
        def _make_replacer(rule_name: str, repl_fn: callable):
            def replacer(m: re.Match) -> str:
                original = m.group(0)
                corrected = repl_fn(m)
                if original != corrected:
                    corrections.append(f"{rule_name}: '{original}' → '{corrected}'")
                return corrected
            return replacer

        text = pattern.sub(_make_replacer(name, replacement_fn), text)

    return text, corrections
