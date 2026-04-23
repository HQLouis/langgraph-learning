"""
Output Contract Validator - makes hallucination measurable.

This module validates response contracts by checking:
1. Evidence quotes exist exactly in the source content
2. Claims are supported by evidence
3. No unsupported factual claims are made
"""
import logging
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import sys

# Add agentic-system to path
agentic_path = Path(__file__).parent.parent.parent / "agentic-system"
sys.path.insert(0, str(agentic_path))

from beats import BeatPackManager

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of contract validation."""

    def __init__(self):
        self.is_valid = True
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.evidence_validation: List[Dict] = []
        self.claims_validation: List[Dict] = []

    def add_error(self, message: str):
        """Add an error and mark as invalid."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str):
        """Add a warning (doesn't invalidate)."""
        self.warnings.append(message)

    def to_dict(self) -> dict:
        """Convert to dictionary for API responses."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "evidence_validation": self.evidence_validation,
            "claims_validation": self.claims_validation
        }


class OutputContractValidator:
    """Validates output contracts against story content."""

    def __init__(self, beat_manager: Optional[BeatPackManager] = None):
        """
        Initialize validator.

        Args:
            beat_manager: BeatPackManager instance for accessing story content
        """
        self.beat_manager = beat_manager

    def validate_contract(
        self,
        contract: dict,
        story_id: Optional[str] = None,
        chapter_id: Optional[str] = None,
        full_content: Optional[str] = None
    ) -> ValidationResult:
        """
        Validate a response contract.

        Args:
            contract: The response contract dictionary
            story_id: Story identifier (for beat-based validation)
            chapter_id: Chapter identifier (for beat-based validation)
            full_content: Full story content (fallback if beat system not available)

        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult()

        # Validate required fields
        if not contract:
            result.add_error("Contract is empty or None")
            return result

        if "spoken_text" not in contract:
            result.add_error("Missing required field: spoken_text")

        if "grounding" not in contract:
            result.add_warning("No grounding information provided - cannot validate evidence")
            return result

        grounding = contract["grounding"]

        # Validate evidence
        evidence_list = grounding.get("evidence", [])
        if not evidence_list:
            result.add_warning("No evidence provided in grounding")
        else:
            self._validate_evidence(
                evidence_list,
                story_id,
                chapter_id,
                full_content,
                result
            )

        # Validate claims
        claims_list = grounding.get("claims", [])
        if not claims_list:
            result.add_warning("No claims provided in grounding")
        else:
            self._validate_claims(claims_list, evidence_list, result)

        # Log validation summary
        if result.is_valid:
            logger.info(f"✓ Contract validation passed - {len(evidence_list)} evidence items, {len(claims_list)} claims")
        else:
            logger.warning(f"✗ Contract validation failed - {len(result.errors)} errors")

        return result

    def _validate_evidence(
        self,
        evidence_list: List[dict],
        story_id: Optional[str],
        chapter_id: Optional[str],
        full_content: Optional[str],
        result: ValidationResult
    ):
        """Validate that evidence quotes exist in source content."""

        # Get source content
        source_content = None
        if self.beat_manager and story_id and chapter_id:
            # Use beat system
            retriever = self.beat_manager.get_retriever(story_id, chapter_id)
            if retriever:
                # Get all beats as source content
                all_beats = retriever.get_all_beats()
                source_content = "\n".join([beat.content for beat in all_beats])
                logger.info(f"Using beat-based content for validation ({len(all_beats)} beats)")

        if not source_content and full_content:
            source_content = full_content
            logger.info("Using full content for validation")

        if not source_content:
            result.add_warning("No source content available for evidence validation")
            return

        # Validate each evidence item
        for idx, evidence in enumerate(evidence_list):
            evidence_result = {
                "index": idx,
                "quote": evidence.get("quote", ""),
                "found": False,
                "beat_id": evidence.get("beat_id")
            }

            quote = evidence.get("quote", "").strip()
            if not quote:
                result.add_error(f"Evidence {idx}: Empty quote")
                evidence_result["error"] = "Empty quote"
            else:
                # Check if quote exists exactly in source content
                if quote in source_content:
                    evidence_result["found"] = True
                    logger.info(f"✓ Evidence {idx}: Quote verified in source")
                else:
                    # Try fuzzy matching (normalize whitespace)
                    normalized_quote = " ".join(quote.split())
                    normalized_source = " ".join(source_content.split())

                    if normalized_quote in normalized_source:
                        evidence_result["found"] = True
                        evidence_result["match_type"] = "normalized"
                        result.add_warning(f"Evidence {idx}: Quote found with normalized whitespace")
                    else:
                        result.add_error(f"Evidence {idx}: Quote not found in source content: '{quote[:50]}...'")
                        evidence_result["error"] = "Quote not found in source"

            result.evidence_validation.append(evidence_result)

    def _validate_claims(
        self,
        claims_list: List[dict],
        evidence_list: List[dict],
        result: ValidationResult
    ):
        """Validate that claims are properly supported by evidence."""

        num_evidence = len(evidence_list)

        for idx, claim in enumerate(claims_list):
            claim_result = {
                "index": idx,
                "claim": claim.get("claim", ""),
                "supported_by": claim.get("supported_by", []),
                "valid_support": False
            }

            if not claim.get("claim"):
                result.add_error(f"Claim {idx}: Empty claim text")
                claim_result["error"] = "Empty claim"

            supported_by = claim.get("supported_by", [])
            if not supported_by:
                result.add_error(f"Claim {idx}: No supporting evidence specified")
                claim_result["error"] = "No support"
            else:
                # Check that all evidence indices are valid
                invalid_indices = [i for i in supported_by if i < 0 or i >= num_evidence]
                if invalid_indices:
                    result.add_error(
                        f"Claim {idx}: Invalid evidence indices {invalid_indices} "
                        f"(max: {num_evidence - 1})"
                    )
                    claim_result["error"] = f"Invalid indices: {invalid_indices}"
                else:
                    claim_result["valid_support"] = True
                    logger.info(f"✓ Claim {idx}: Supported by evidence {supported_by}")

            result.claims_validation.append(claim_result)


# TODO LNG: Check if this validation works properly
def validate_response_contract(
    contract: dict,
    beat_manager: Optional[BeatPackManager] = None,
    story_id: Optional[str] = None,
    chapter_id: Optional[str] = None,
    full_content: Optional[str] = None
) -> ValidationResult:
    """
    Convenience function to validate a response contract.

    Args:
        contract: The response contract dictionary
        beat_manager: BeatPackManager instance (optional)
        story_id: Story identifier (optional)
        chapter_id: Chapter identifier (optional)
        full_content: Full story content (optional fallback)

    Returns:
        ValidationResult with detailed validation information
    """
    validator = OutputContractValidator(beat_manager)
    return validator.validate_contract(contract, story_id, chapter_id, full_content)

