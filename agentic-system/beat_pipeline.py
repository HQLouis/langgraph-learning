"""
Beat Pipeline - Tools for generating beatpacks from chapter text.

This module provides semi-automated tools for creating beat packages:
1. Text normalization
2. Candidate segmentation (heuristic-based)
3. Entity extraction
4. Fact extraction (optional)
5. Index building
6. Versioning and hashing

For production use, you can enhance this with LLM-assisted refinement.
"""
import re
import logging
from typing import List, Tuple, Dict, Set, Optional
from pathlib import Path
from datetime import datetime
import unicodedata

from beats import (
    Beat, BeatPack, TextSpan, Fact, EntityInfo,
    compute_text_hash
)

logger = logging.getLogger(__name__)


class BeatPipeline:
    """Pipeline for generating beatpacks from raw chapter text."""

    def __init__(
        self,
        story_id: str,
        chapter_id: str,
        chapter_text: str,
        min_beat_length: int = 50,
        max_beat_length: int = 300
    ):
        """
        Initialize beat pipeline.

        :param story_id: Story identifier
        :param chapter_id: Chapter identifier
        :param chapter_text: Raw chapter text
        :param min_beat_length: Minimum characters per beat
        :param max_beat_length: Maximum characters per beat
        """
        self.story_id = story_id
        self.chapter_id = chapter_id
        self.raw_text = chapter_text
        self.min_beat_length = min_beat_length
        self.max_beat_length = max_beat_length

        # Normalized text
        self.chapter_text = self._normalize_text(chapter_text)

        # Entity dictionary (can be pre-populated)
        self.entity_dictionary: Set[str] = set()

        logger.info(f"Initialized BeatPipeline for {story_id}/{chapter_id}")

    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent processing.

        - Unicode normalization (NFC)
        - Consistent whitespace
        - Consistent quotes
        """
        # Unicode normalize
        text = unicodedata.normalize('NFC', text)

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Normalize quotes (optional - adapt to your needs)
        text = text.replace('„', '"').replace('"', '"')
        text = text.replace('\u201A', "'").replace('\u2018', "'")

        logger.debug(f"Normalized text: {len(text)} characters")
        return text

    def segment_into_candidates(self) -> List[Tuple[int, int, str]]:
        """
        Segment chapter into beat candidates using heuristics.

        Returns list of (start_char, end_char, text) tuples.

        Heuristics for children's stories:
        - Split on sentence boundaries
        - Split on dialogue changes
        - Split on transition words (dann, danach, plötzlich)
        - Split on scene changes (new paragraph + location/time indicator)
        """
        candidates: List[Tuple[int, int, str]] = []

        # Split into paragraphs first
        paragraphs = self._split_paragraphs()

        current_pos = 0
        for para_text in paragraphs:
            # Find paragraph position in normalized text
            para_start = self.chapter_text.find(para_text, current_pos)
            if para_start == -1:
                logger.warning(f"Could not find paragraph in text: {para_text[:50]}")
                continue

            para_end = para_start + len(para_text)
            current_pos = para_end

            # Split paragraph into sentences
            sentences = self._split_sentences(para_text)

            # Group sentences into beats
            current_beat_start = para_start
            current_beat_text = ""

            for sentence in sentences:
                sentence_len = len(sentence)

                # Check if adding this sentence would exceed max length
                if current_beat_text and len(current_beat_text) + sentence_len > self.max_beat_length:
                    # Save current beat
                    beat_end = current_beat_start + len(current_beat_text)
                    if len(current_beat_text) >= self.min_beat_length:
                        candidates.append((current_beat_start, beat_end, current_beat_text.strip()))

                    # Start new beat
                    current_beat_start = beat_end
                    current_beat_text = sentence
                else:
                    # Add to current beat
                    if current_beat_text:
                        current_beat_text += " " + sentence
                    else:
                        current_beat_text = sentence

                # Check for transition markers that might split beats
                if self._has_transition_marker(sentence):
                    beat_end = current_beat_start + len(current_beat_text)
                    if len(current_beat_text) >= self.min_beat_length:
                        candidates.append((current_beat_start, beat_end, current_beat_text.strip()))
                        current_beat_start = beat_end
                        current_beat_text = ""

            # Add remaining text as beat
            if current_beat_text and len(current_beat_text) >= self.min_beat_length:
                beat_end = current_beat_start + len(current_beat_text)
                candidates.append((current_beat_start, beat_end, current_beat_text.strip()))

        logger.info(f"Generated {len(candidates)} beat candidates")
        return candidates

    def _split_paragraphs(self) -> List[str]:
        """Split text into paragraphs."""
        # Split on double newlines or single newlines followed by significant content change
        paragraphs = [p.strip() for p in self.chapter_text.split('\n') if p.strip()]
        return paragraphs

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences (German-aware).

        Handles:
        - . ? ! as sentence terminators
        - Abbreviations (z.B., etc.)
        - Quotes
        """
        # Simple sentence splitting for German
        # This is basic - for production, consider spaCy or similar

        # Split on sentence terminators followed by space and capital letter
        sentences = re.split(r'([.!?]+)\s+(?=[A-ZÄÖÜ"])', text)

        # Rejoin sentences with their terminators
        result = []
        i = 0
        while i < len(sentences):
            if i + 1 < len(sentences) and sentences[i + 1] in ['.', '!', '?', '...', '!!', '??']:
                result.append(sentences[i] + sentences[i + 1])
                i += 2
            else:
                result.append(sentences[i])
                i += 1

        return [s.strip() for s in result if s.strip()]

    def _has_transition_marker(self, text: str) -> bool:
        """Check if text contains transition markers that suggest beat boundary."""
        transition_words = [
            r'\bdann\b', r'\bdanach\b', r'\bplötzlich\b',
            r'\bals nächstes\b', r'\bschließlich\b',
            r'\bdaraufhin\b', r'\bunmittelbar darauf\b'
        ]

        text_lower = text.lower()
        for pattern in transition_words:
            if re.search(pattern, text_lower):
                return True
        return False

    def extract_entities(self, text: str) -> List[str]:
        """
        Extract entities from text.

        Uses:
        1. Pre-defined entity dictionary
        2. Simple heuristics (capitalized words)

        For production: Use NER (spaCy, Flair) or LLM-assisted extraction.
        """
        entities = []

        # Check against dictionary
        for entity in self.entity_dictionary:
            if entity.lower() in text.lower():
                entities.append(entity)

        # Extract capitalized words (basic heuristic)
        # Exclude sentence-initial words
        words = re.findall(r'\b[A-ZÄÖÜ][a-zäöüß]+\b', text)

        # Filter out common non-entities
        stop_words = {'Der', 'Die', 'Das', 'Ein', 'Eine', 'Und', 'Aber', 'Oder'}

        for word in words:
            if word not in stop_words and word not in entities:
                entities.append(word)

        return list(set(entities))

    def extract_facts(self, text: str, entities: List[str]) -> List[Fact]:
        """
        Extract simple facts from text (optional).

        This is a placeholder for more sophisticated fact extraction.
        For production: Use dependency parsing or LLM-assisted extraction.
        """
        facts = []

        # Very simple pattern matching for common structures
        # Example: "X ging nach Y" -> Fact(s="X", p="ging nach", o="Y")

        # Pattern: Entity + Verb + Entity/Location
        for entity in entities:
            # Simple pattern: entity + verb phrase
            patterns = [
                rf'{entity}\s+(\w+)\s+nach\s+(\w+)',  # ging nach
                rf'{entity}\s+(\w+)\s+(\w+)',  # simple subject-verb-object
            ]

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for match in matches:
                    if len(match) >= 2:
                        facts.append(Fact(s=entity, p=match[0], o=match[1]))

        return facts[:5]  # Limit to avoid noise

    def set_entity_dictionary(self, entities: Dict[str, List[str]]) -> None:
        """
        Set predefined entity dictionary with aliases.

        :param entities: Dict mapping entity names to list of aliases
        """
        for entity, aliases in entities.items():
            self.entity_dictionary.add(entity)
            self.entity_dictionary.update(aliases)

        logger.info(f"Set entity dictionary with {len(entities)} entities")

    def create_beatpack(
        self,
        entity_registry: Optional[Dict[str, EntityInfo]] = None
    ) -> BeatPack:
        """
        Create complete beatpack from chapter text.

        :param entity_registry: Optional predefined entity registry
        :return: BeatPack
        """
        logger.info("Starting beatpack creation")

        # Generate beat candidates
        candidates = self.segment_into_candidates()

        # Create beats
        beats = []
        for i, (start, end, text) in enumerate(candidates):
            # Extract entities
            entities = self.extract_entities(text)

            # Extract facts (optional)
            facts = self.extract_facts(text, entities)

            # Determine tags (placeholder - can be enhanced)
            tags = []
            if any(word in text.lower() for word in ['sagte', 'fragte', 'antwortete']):
                tags.append('dialogue')
            if any(word in text.lower() for word in ['ging', 'lief', 'kam']):
                tags.append('action')

            beat = Beat(
                beat_id=i + 1,
                order=i + 1,
                span=TextSpan(start_char=start, end_char=end),
                text=text,
                entities=entities,
                facts=facts,
                tags=tags,
                safety_tags=[]
            )
            beats.append(beat)

        # Create entity registry if not provided
        if entity_registry is None:
            entity_registry = self._build_entity_registry(beats)

        # Compute hash
        chapter_hash = compute_text_hash(self.chapter_text)

        # Create beatpack
        beatpack = BeatPack(
            story_id=self.story_id,
            chapter_id=self.chapter_id,
            content_version=datetime.now().isoformat(),
            beatpack_version="v1",
            chapter_hash=chapter_hash,
            beats=beats,
            entity_registry=entity_registry,
            chapter_text=self.chapter_text
        )

        # Verify integrity
        is_valid, errors = beatpack.verify_integrity()
        if not is_valid:
            logger.warning(f"Beatpack integrity issues: {errors}")
        else:
            logger.info("Beatpack integrity verified")

        logger.info(f"Created beatpack with {len(beats)} beats")
        return beatpack

    def _build_entity_registry(self, beats: List[Beat]) -> Dict[str, EntityInfo]:
        """Build entity registry from extracted entities."""
        entity_counts: Dict[str, int] = {}

        # Count entity occurrences
        for beat in beats:
            for entity in beat.entities:
                entity_counts[entity] = entity_counts.get(entity, 0) + 1

        # Create registry for entities that appear multiple times
        registry = {}
        for entity, count in entity_counts.items():
            if count >= 2:  # Only include entities that appear at least twice
                registry[entity] = EntityInfo(
                    aliases=[],
                    entity_type="character" if entity[0].isupper() else "unknown"
                )

        return registry


def create_beatpack_from_file(
    story_id: str,
    chapter_id: str,
    chapter_file: Path,
    output_dir: Path,
    entity_registry: Optional[Dict[str, EntityInfo]] = None
) -> BeatPack:
    """
    Convenience function to create beatpack from a text file.

    :param story_id: Story identifier
    :param chapter_id: Chapter identifier
    :param chapter_file: Path to chapter text file
    :param output_dir: Directory to save beatpack
    :param entity_registry: Optional predefined entity registry
    :return: Created BeatPack
    """
    # Read chapter text
    with open(chapter_file, 'r', encoding='utf-8') as f:
        chapter_text = f.read()

    # Create pipeline
    pipeline = BeatPipeline(story_id, chapter_id, chapter_text)

    # Create beatpack
    beatpack = pipeline.create_beatpack(entity_registry)

    # Save beatpack
    output_path = output_dir / "stories" / story_id / chapter_id / "beatpack.v1.json"
    beatpack.save(output_path)

    return beatpack


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)

    # Example: Create a simple test beatpack
    example_text = """
    Es war einmal ein kleines Mädchen namens Mia. Mia lebte in einem kleinen Dorf am Waldrand.
    
    Eines Tages ging Mia in den Wald, um Beeren zu sammeln. Der Wald war dunkel und geheimnisvoll.
    Plötzlich hörte sie ein Rascheln im Gebüsch.
    
    "Wer ist da?", fragte Mia mutig. Ein kleiner Fuchs sprang hervor.
    "Keine Angst", sagte der Fuchs. "Ich bin nur auf der Suche nach meinem Abendessen."
    
    Mia lächelte und ging weiter. Sie fand viele leckere Beeren.
    Als es dunkel wurde, ging Mia nach Hause zurück.
    """

    pipeline = BeatPipeline("test_story", "chapter_01", example_text)

    # Add entity dictionary
    entity_dict = {
        "Mia": ["sie", "das Mädchen"],
        "Fuchs": ["er", "das Tier"],
        "Wald": ["im Wald"],
        "Dorf": ["das Dorf"]
    }

    entity_registry = {
        name: EntityInfo(aliases=aliases, entity_type="character" if name in ["Mia", "Fuchs"] else "location")
        for name, aliases in entity_dict.items()
    }

    beatpack = pipeline.create_beatpack(entity_registry)

    print(f"\nCreated beatpack with {len(beatpack.beats)} beats:")
    for beat in beatpack.beats:
        print(f"\nBeat {beat.beat_id} (order {beat.order}):")
        print(f"  Text: {beat.text[:80]}...")
        print(f"  Entities: {beat.entities}")
        print(f"  Tags: {beat.tags}")

