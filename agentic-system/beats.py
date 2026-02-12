"""
Beat system for closed-world story content management.

Beats are the smallest stable content units within a chapter that ensure:
- Closed-world: Only discuss content that actually exists in the chapter
- Scene-integrity: Don't mix scenes
- No-new-facts: Don't invent details
- Evidence: Machine-verifiable references

This module provides data models and runtime retrieval for the beat-based content system.
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime
import hashlib
import re

logger = logging.getLogger(__name__)


@dataclass
class TextSpan:
    """Represents a span of text within the chapter."""
    start_char: int
    end_char: int

    def to_dict(self) -> Dict[str, int]:
        return {"start_char": self.start_char, "end_char": self.end_char}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'TextSpan':
        return cls(start_char=data["start_char"], end_char=data["end_char"])


@dataclass
class Fact:
    """Structured fact extracted from a beat (subject-predicate-object)."""
    s: str  # subject
    p: str  # predicate
    o: str  # object

    def to_dict(self) -> Dict[str, str]:
        return {"s": self.s, "p": self.p, "o": self.o}

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> 'Fact':
        return cls(s=data["s"], p=data["p"], o=data["o"])


@dataclass
class Beat:
    """A single beat - the smallest stable content unit in a chapter."""
    beat_id: int
    order: int
    span: TextSpan
    text: str
    entities: List[str] = field(default_factory=list)
    facts: List[Fact] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    safety_tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "beat_id": self.beat_id,
            "order": self.order,
            "span": self.span.to_dict(),
            "text": self.text,
            "entities": self.entities,
            "facts": [f.to_dict() for f in self.facts],
            "tags": self.tags,
            "safety_tags": self.safety_tags
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Beat':
        return cls(
            beat_id=data["beat_id"],
            order=data["order"],
            span=TextSpan.from_dict(data["span"]),
            text=data["text"],
            entities=data.get("entities", []),
            facts=[Fact.from_dict(f) for f in data.get("facts", [])],
            tags=data.get("tags", []),
            safety_tags=data.get("safety_tags", [])
        )


@dataclass
class EntityInfo:
    """Entity registry entry with aliases and type."""
    aliases: List[str] = field(default_factory=list)
    entity_type: str = "unknown"  # character, location, object, etc.

    def to_dict(self) -> Dict[str, Any]:
        return {"aliases": self.aliases, "type": self.entity_type}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EntityInfo':
        return cls(aliases=data.get("aliases", []), entity_type=data.get("type", "unknown"))


@dataclass
class BeatPack:
    """Complete beat package for a chapter - versioned content artifact."""
    story_id: str
    chapter_id: str
    content_version: str
    beatpack_version: str
    chapter_hash: str
    beats: List[Beat]
    entity_registry: Dict[str, EntityInfo] = field(default_factory=dict)
    chapter_text: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "story_id": self.story_id,
            "chapter_id": self.chapter_id,
            "content_version": self.content_version,
            "beatpack_version": self.beatpack_version,
            "chapter_hash": self.chapter_hash,
            "beats": [b.to_dict() for b in self.beats],
            "entity_registry": {k: v.to_dict() for k, v in self.entity_registry.items()},
            "chapter_text": self.chapter_text
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BeatPack':
        return cls(
            story_id=data["story_id"],
            chapter_id=data["chapter_id"],
            content_version=data["content_version"],
            beatpack_version=data["beatpack_version"],
            chapter_hash=data["chapter_hash"],
            beats=[Beat.from_dict(b) for b in data["beats"]],
            entity_registry={k: EntityInfo.from_dict(v) for k, v in data.get("entity_registry", {}).items()},
            chapter_text=data.get("chapter_text")
        )

    def save(self, output_path: Path) -> None:
        """Save beatpack to JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info(f"Saved beatpack to {output_path}")

    @classmethod
    def load(cls, path: Path) -> 'BeatPack':
        """Load beatpack from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        logger.info(f"Loaded beatpack from {path}")
        return cls.from_dict(data)

    def get_beat_by_id(self, beat_id: int) -> Optional[Beat]:
        """Get a specific beat by ID."""
        for beat in self.beats:
            if beat.beat_id == beat_id:
                return beat
        return None

    def get_beats_by_order(self, start: int, end: int) -> List[Beat]:
        """Get beats in a specific order range [start, end) (inclusive start, exclusive end)."""
        return [b for b in self.beats if start <= b.order < end]

    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """Verify that all beats match the chapter text using spans and hash."""
        errors = []

        if not self.chapter_text:
            errors.append("No chapter_text available for verification")
            return False, errors

        # Verify hash
        computed_hash = compute_text_hash(self.chapter_text)
        if computed_hash != self.chapter_hash:
            errors.append(f"Chapter hash mismatch: expected {self.chapter_hash}, got {computed_hash}")

        # Verify each beat's span matches its text
        for beat in self.beats:
            try:
                extracted_text = self.chapter_text[beat.span.start_char:beat.span.end_char]
                if extracted_text != beat.text:
                    errors.append(f"Beat {beat.beat_id} text mismatch at span {beat.span}")
            except IndexError:
                errors.append(f"Beat {beat.beat_id} has invalid span {beat.span}")

        return len(errors) == 0, errors


def compute_text_hash(text: str) -> str:
    """Compute SHA256 hash of normalized text."""
    normalized = text.strip()
    return f"sha256:{hashlib.sha256(normalized.encode('utf-8')).hexdigest()}"


class BeatRetriever:
    """Runtime retrieval of beats for dialogue system integration."""

    def __init__(self, beatpack: BeatPack):
        self.beatpack = beatpack
        self._build_search_index()
        logger.info(f"Initialized BeatRetriever for {beatpack.story_id}/{beatpack.chapter_id} with {len(beatpack.beats)} beats")

    def _build_search_index(self) -> None:
        """Build simple keyword index for BM25-style retrieval."""
        self._inverted_index: Dict[str, List[int]] = {}

        for beat in self.beatpack.beats:
            # Tokenize beat text
            tokens = self._tokenize(beat.text)
            for token in tokens:
                if token not in self._inverted_index:
                    self._inverted_index[token] = []
                self._inverted_index[token].append(beat.beat_id)

            # Also index entities
            for entity in beat.entities:
                entity_lower = entity.lower()
                if entity_lower not in self._inverted_index:
                    self._inverted_index[entity_lower] = []
                self._inverted_index[entity_lower].append(beat.beat_id)

        logger.debug(f"Built search index with {len(self._inverted_index)} terms")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for German text."""
        # Lowercase and extract words (alphanumeric + umlauts)
        tokens = re.findall(r'[a-zäöüß0-9]+', text.lower())
        return tokens

    def retrieve_beats(self, query: str, top_k: int = 5) -> List[Beat]:
        """
        Retrieve top-k most relevant beats for a query using BM25-style scoring.

        :param query: Search query (typically the child's last message)
        :param top_k: Number of beats to return
        :return: List of beats sorted by relevance
        """
        if not query:
            # Return first k beats if no query
            return self.beatpack.beats[:top_k]

        query_tokens = self._tokenize(query)
        beat_scores: Dict[int, float] = {}

        # Simple term frequency scoring
        for token in query_tokens:
            if token in self._inverted_index:
                for beat_id in self._inverted_index[token]:
                    beat_scores[beat_id] = beat_scores.get(beat_id, 0) + 1

        # Sort beats by score
        sorted_beat_ids = sorted(beat_scores.keys(), key=lambda x: beat_scores[x], reverse=True)
        top_beat_ids = sorted_beat_ids[:top_k]

        # If we don't have enough scored beats, add some in order
        if len(top_beat_ids) < top_k:
            for beat in self.beatpack.beats:
                if beat.beat_id not in top_beat_ids:
                    top_beat_ids.append(beat.beat_id)
                    if len(top_beat_ids) >= top_k:
                        break

        # Retrieve beats and sort by order for narrative consistency
        beats = [self.beatpack.get_beat_by_id(bid) for bid in top_beat_ids]
        beats = [b for b in beats if b is not None]
        beats.sort(key=lambda x: x.order)

        logger.debug(f"Retrieved {len(beats)} beats for query: {query[:50]}...")
        return beats

    def get_beats_for_tasks(self, num_tasks: int = 5) -> List[Beat]:
        """
        Get chronologically distributed beats for task assignment.

        When planning N tasks, select N beats distributed evenly across the chapter.

        :param num_tasks: Number of tasks planned (default 5)
        :return: List of beats distributed across the chapter
        """
        total_beats = len(self.beatpack.beats)

        if total_beats == 0:
            return []

        if num_tasks >= total_beats:
            # Return all beats if we have fewer beats than tasks
            return self.beatpack.beats

        # Calculate step size for even distribution
        step = total_beats / num_tasks
        selected_indices = [int(i * step) for i in range(num_tasks)]

        # Get beats at selected positions
        selected_beats = [self.beatpack.beats[i] for i in selected_indices]

        logger.info(f"Selected {len(selected_beats)} beats for {num_tasks} tasks: {selected_indices}")
        return selected_beats

    def format_beats_for_context(self, beats: List[Beat], include_entities: bool = True) -> str:
        """
        Format beats as context string for the LLM.

        :param beats: List of beats to format
        :param include_entities: Whether to include entity information
        :return: Formatted context string
        """
        if not beats:
            return "Kein spezifischer Kontext verfügbar."

        context_parts = ["[GESCHICHTSKONTEXT - NUR DIESE INHALTE VERWENDEN]"]

        for beat in beats:
            context_parts.append(f"\n[Beat {beat.beat_id}]: {beat.text}")

            if include_entities and beat.entities:
                entities_str = ", ".join(beat.entities)
                context_parts.append(f"  → Figuren/Orte: {entities_str}")

        # Add entity registry for reference
        if include_entities and self.beatpack.entity_registry:
            context_parts.append("\n[BEKANNTE FIGUREN/ORTE]")
            for entity, info in self.beatpack.entity_registry.items():
                if info.aliases:
                    aliases_str = ", ".join(info.aliases)
                    context_parts.append(f"  • {entity} (auch: {aliases_str})")
                else:
                    context_parts.append(f"  • {entity}")

        return "\n".join(context_parts)


class BeatPackManager:
    """Manager for loading and caching beat packs."""

    def __init__(self, content_dir: Path):
        self.content_dir = content_dir
        self._cache: Dict[Tuple[str, str], BeatPack] = {}
        logger.info(f"Initialized BeatPackManager with content_dir: {content_dir}")

    def get_beatpack(self, story_id: str, chapter_id: str, force_reload: bool = False) -> Optional[BeatPack]:
        """
        Load beatpack for a specific story/chapter.

        :param story_id: Story identifier
        :param chapter_id: Chapter identifier
        :param force_reload: Force reload from disk (bypass cache)
        :return: BeatPack or None if not found
        """
        cache_key = (story_id, chapter_id)

        if not force_reload and cache_key in self._cache:
            logger.debug(f"BeatPack cache hit for {story_id}/{chapter_id}")
            return self._cache[cache_key]

        # Try to load from disk
        beatpack_path = self.content_dir / "stories" / story_id / chapter_id / "beatpack.v1.json"

        if not beatpack_path.exists():
            logger.warning(f"BeatPack not found at {beatpack_path}")
            return None

        try:
            beatpack = BeatPack.load(beatpack_path)

            # Verify integrity if chapter text is available
            if beatpack.chapter_text:
                is_valid, errors = beatpack.verify_integrity()
                if not is_valid:
                    logger.error(f"BeatPack integrity check failed: {errors}")
                    # Still return it, but log the issue

            self._cache[cache_key] = beatpack
            return beatpack

        except Exception as e:
            logger.error(f"Failed to load beatpack from {beatpack_path}: {e}")
            return None

    def get_retriever(self, story_id: str, chapter_id: str) -> Optional[BeatRetriever]:
        """Get a beat retriever for a specific story/chapter."""
        beatpack = self.get_beatpack(story_id, chapter_id)
        if beatpack:
            return BeatRetriever(beatpack)
        return None

    def clear_cache(self) -> None:
        """Clear the beatpack cache."""
        self._cache.clear()
        logger.info("Cleared BeatPack cache")

