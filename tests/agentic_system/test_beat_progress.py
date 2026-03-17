"""
Unit tests for beat progress tracking and story-end detection.

Tests:
- _check_story_near_end() with various coverage scenarios
- Beatpack loading from generated fixtures (Pia, Bobo)
- BeatRetriever.get_all_beats() returns correct count
"""
import sys
from pathlib import Path

import pytest

# Ensure agentic-system is importable
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root / "agentic-system"))

from beats import Beat, BeatPack, BeatPackManager, TextSpan
from nodes import _check_story_near_end


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_beats(n: int) -> list[Beat]:
    """Create n simple beats with order 1..n and beat_id 1..n."""
    return [
        Beat(
            beat_id=i,
            order=i,
            span=TextSpan(start_char=0, end_char=10),
            text=f"Beat {i} text.",
        )
        for i in range(1, n + 1)
    ]


# ---------------------------------------------------------------------------
# _check_story_near_end tests
# ---------------------------------------------------------------------------

class TestCheckStoryNearEnd:
    """Unit tests for _check_story_near_end()."""

    def test_near_end_with_final_beats_covered(self):
        """Covering beats 9-10 of a 10-beat story → True."""
        all_beats = _make_beats(10)
        assert _check_story_near_end(
            covered_beat_ids=[9, 10],
            active_beat_ids=[],
            all_beats=all_beats,
        ) is True

    def test_not_near_end_with_early_beats(self):
        """Covering only beats 1-5 of a 10-beat story → False."""
        all_beats = _make_beats(10)
        assert _check_story_near_end(
            covered_beat_ids=[1, 2, 3, 4, 5],
            active_beat_ids=[],
            all_beats=all_beats,
        ) is False

    def test_near_end_via_active_beats(self):
        """Active beat in final range triggers detection."""
        all_beats = _make_beats(10)
        assert _check_story_near_end(
            covered_beat_ids=[1, 2],
            active_beat_ids=[10],
            all_beats=all_beats,
        ) is True

    def test_empty_beats(self):
        """No beats at all → False."""
        assert _check_story_near_end([], [], []) is False

    def test_single_beat(self):
        """Single beat → always near end when covered."""
        all_beats = _make_beats(1)
        assert _check_story_near_end([1], [], all_beats) is True

    def test_single_beat_not_covered(self):
        """Single beat not covered → False."""
        all_beats = _make_beats(1)
        assert _check_story_near_end([], [], all_beats) is False

    def test_all_beats_covered(self):
        """All beats covered → True."""
        all_beats = _make_beats(5)
        assert _check_story_near_end(
            covered_beat_ids=[1, 2, 3, 4, 5],
            active_beat_ids=[],
            all_beats=all_beats,
        ) is True

    def test_none_values(self):
        """None for covered/active IDs should be handled gracefully."""
        all_beats = _make_beats(10)
        assert _check_story_near_end(None, None, all_beats) is False

    def test_threshold_boundary(self):
        """Beat at exact threshold boundary (order == total - threshold)."""
        all_beats = _make_beats(10)
        # final_threshold = max(1, int(10 * 0.2)) = 2
        # final_beat_ids = beats where order > 10 - 2 = 8, so beats 9 and 10
        # Beat 8 should NOT trigger near-end
        assert _check_story_near_end([8], [], all_beats) is False
        # Beat 9 should trigger
        assert _check_story_near_end([9], [], all_beats) is True


# ---------------------------------------------------------------------------
# Beatpack fixture loading tests
# ---------------------------------------------------------------------------

CONTENT_DIR = Path(__file__).parent / "content"


class TestBeatpackFixtures:
    """Test that generated beatpack fixtures load correctly."""

    @pytest.fixture(scope="class")
    def manager(self):
        return BeatPackManager(CONTENT_DIR)

    def test_mia_beatpack_loads(self, manager):
        bp = manager.get_beatpack("mia_und_leo", "chapter_01")
        assert bp is not None
        assert len(bp.beats) == 10

    def test_pia_beatpack_loads(self, manager):
        bp = manager.get_beatpack("pia_muss_nicht_perfekt_sein", "chapter_01")
        assert bp is not None
        assert len(bp.beats) >= 8  # expect ~20 beats

    def test_bobo_beatpack_loads(self, manager):
        bp = manager.get_beatpack("bobos_adventskalender", "chapter_01")
        assert bp is not None
        assert len(bp.beats) >= 8  # expect ~12 beats

    def test_pia_integrity(self, manager):
        bp = manager.get_beatpack("pia_muss_nicht_perfekt_sein", "chapter_01")
        is_valid, errors = bp.verify_integrity()
        assert is_valid, f"Integrity errors: {errors}"

    def test_bobo_integrity(self, manager):
        bp = manager.get_beatpack("bobos_adventskalender", "chapter_01")
        is_valid, errors = bp.verify_integrity()
        assert is_valid, f"Integrity errors: {errors}"

    def test_retriever_beat_count(self, manager):
        retriever = manager.get_retriever("bobos_adventskalender", "chapter_01")
        assert retriever is not None
        all_beats = retriever.get_all_beats()
        assert len(all_beats) >= 8

    def test_bobo_last_beat_contains_ending(self, manager):
        """The last beat of Bobo should contain the story ending."""
        bp = manager.get_beatpack("bobos_adventskalender", "chapter_01")
        last_beat = sorted(bp.beats, key=lambda b: b.order)[-1]
        assert "eingeschlafen" in last_beat.text.lower()

    def test_pia_last_beat_contains_ending(self, manager):
        """The last beat of Pia should contain the story ending."""
        bp = manager.get_beatpack("pia_muss_nicht_perfekt_sein", "chapter_01")
        last_beat = sorted(bp.beats, key=lambda b: b.order)[-1]
        assert "lachen" in last_beat.text.lower()
