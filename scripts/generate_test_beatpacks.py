"""
Script to generate beatpack fixtures for stories (Pia, Bobo).

Outputs to both test and production content directories to keep them in sync.

Usage:
    cd <project-root>
    python scripts/generate_test_beatpacks.py

Generates beatpacks at:
    tests/agentic_system/content/stories/<story_id>/<chapter_id>/beatpack.v1.json
    agentic-system/content/stories/<story_id>/<chapter_id>/beatpack.v1.json
"""
import sys
import logging
from pathlib import Path

# Ensure agentic-system and feature-testing are importable
_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root / "agentic-system"))
sys.path.insert(0, str(_project_root / "tests" / "feature-testing"))

from beat_pipeline import BeatPipeline
from beats import EntityInfo, BeatPack

# Single source of truth: story texts are defined in feature_testing_utils.py
from feature_testing_utils import (
    FIXTURE_PIA_AUDIO_BOOK as PIA_STORY_TEXT,
    FIXTURE_BOBO_AUDIO_BOOK as BOBO_STORY_TEXT,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

TEST_OUTPUT_DIR = _project_root / "tests" / "agentic_system" / "content"
PRODUCTION_OUTPUT_DIR = _project_root / "agentic-system" / "content"


# Story texts are imported from feature_testing_utils (single source of truth).
# PIA_STORY_TEXT and BOBO_STORY_TEXT are aliased at import time above.

# ---------------------------------------------------------------------------
# Entity registries
# ---------------------------------------------------------------------------

PIA_ENTITY_REGISTRY = {
    "Pia": EntityInfo(
        aliases=["Pia Piretti", "sie", "ihr", "das Mädchen, das immer alles richtig macht"],
        entity_type="character",
    ),
    "Carl": EntityInfo(
        aliases=["ihr Bruder", "ihren Bruder"],
        entity_type="character",
    ),
    "Hubert": EntityInfo(
        aliases=["der Hamster", "ihrem Hamster"],
        entity_type="character",
    ),
    "Millie": EntityInfo(aliases=[], entity_type="character"),
    "Sarah": EntityInfo(aliases=[], entity_type="character"),
    "Vater": EntityInfo(
        aliases=["ihr Vater", "Papa"],
        entity_type="character",
    ),
}

BOBO_ENTITY_REGISTRY = {
    "Bobo": EntityInfo(
        aliases=["er", "ihm"],
        entity_type="character",
    ),
    "Papa Siebenschläfer": EntityInfo(
        aliases=["Papa", "sein Papa"],
        entity_type="character",
    ),
    "Mama": EntityInfo(
        aliases=["sie"],
        entity_type="character",
    ),
    "Postbotin": EntityInfo(
        aliases=["die Postbotin", "ihr"],
        entity_type="character",
    ),
}


def generate_beatpack(
    story_id: str,
    chapter_id: str,
    story_text: str,
    entity_registry: dict[str, EntityInfo],
    min_beat_length: int = 40,
    max_beat_length: int = 250,
) -> BeatPack:
    """Generate and save a beatpack for a story."""
    pipeline = BeatPipeline(
        story_id=story_id,
        chapter_id=chapter_id,
        chapter_text=story_text,
        min_beat_length=min_beat_length,
        max_beat_length=max_beat_length,
    )

    # Pre-populate entity dictionary for better extraction
    entity_dict = {name: info.aliases for name, info in entity_registry.items()}
    pipeline.set_entity_dictionary(entity_dict)

    beatpack = pipeline.create_beatpack(entity_registry=entity_registry)

    # Save to both test and production content directories
    for output_dir in [TEST_OUTPUT_DIR, PRODUCTION_OUTPUT_DIR]:
        output_path = output_dir / "stories" / story_id / chapter_id / "beatpack.v1.json"
        beatpack.save(output_path)
        logger.info(f"  Saved to {output_path}")

    # Verify integrity
    is_valid, errors = beatpack.verify_integrity()
    if is_valid:
        logger.info(f"  Integrity check PASSED ({len(beatpack.beats)} beats)")
    else:
        logger.warning(f"  Integrity check FAILED: {errors}")

    return beatpack


def main():
    logger.info("Generating Pia beatpack...")
    pia = generate_beatpack(
        story_id="pia_muss_nicht_perfekt_sein",
        chapter_id="chapter_01",
        story_text=PIA_STORY_TEXT,
        entity_registry=PIA_ENTITY_REGISTRY,
    )
    logger.info(f"  Pia: {len(pia.beats)} beats")

    logger.info("Generating Bobo beatpack...")
    bobo = generate_beatpack(
        story_id="bobos_adventskalender",
        chapter_id="chapter_01",
        story_text=BOBO_STORY_TEXT,
        entity_registry=BOBO_ENTITY_REGISTRY,
    )
    logger.info(f"  Bobo: {len(bobo.beats)} beats")

    # Summary
    print(f"\nGenerated beatpacks:")
    print(f"  Pia:  {len(pia.beats)} beats")
    print(f"  Bobo: {len(bobo.beats)} beats")
    print(f"\nOutput directories:")
    print(f"  Test:       {TEST_OUTPUT_DIR / 'stories'}")
    print(f"  Production: {PRODUCTION_OUTPUT_DIR / 'stories'}")


if __name__ == "__main__":
    main()
