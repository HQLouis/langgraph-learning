"""
conftest.py for output_contract tests.

Provides shared pytest fixtures that load the mia_und_leo / chapter_01
beatpack and expose individual Beat objects for use in test cases.
"""
import json
from pathlib import Path
from typing import List

import pytest

from beats import Beat, TextSpan, Fact


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "beatpacks"
BEATPACK_PATH = FIXTURES_DIR / "mia_und_leo_chapter_01.json"


# ---------------------------------------------------------------------------
# Helper: build Beat objects from raw dict
# ---------------------------------------------------------------------------

def _beat_from_dict(data: dict) -> Beat:
    return Beat(
        beat_id=data["beat_id"],
        order=data["order"],
        span=TextSpan(
            start_char=data["span"]["start_char"],
            end_char=data["span"]["end_char"],
        ),
        text=data["text"],
        entities=data.get("entities", []),
        facts=[Fact(s=f["s"], p=f["p"], o=f["o"]) for f in data.get("facts", [])],
        tags=data.get("tags", []),
        safety_tags=data.get("safety_tags", []),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def beatpack_raw() -> dict:
    """Raw beatpack JSON loaded from the fixture file."""
    with BEATPACK_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="session")
def all_beats(beatpack_raw) -> List[Beat]:
    """All 10 Beat objects from mia_und_leo / chapter_01."""
    return [_beat_from_dict(b) for b in beatpack_raw["beats"]]


@pytest.fixture(scope="session")
def beat_1(all_beats) -> Beat:
    """Beat 1 – Mia lives at the forest edge, looks out her window every day."""
    return next(b for b in all_beats if b.beat_id == 1)


@pytest.fixture(scope="session")
def beat_2(all_beats) -> Beat:
    """Beat 2 – Mia goes into the forest to collect berries."""
    return next(b for b in all_beats if b.beat_id == 2)


@pytest.fixture(scope="session")
def beat_3(all_beats) -> Beat:
    """Beat 3 – Mia hears a rustling in the bushes."""
    return next(b for b in all_beats if b.beat_id == 3)


@pytest.fixture(scope="session")
def beat_4(all_beats) -> Beat:
    """Beat 4 – Mia stands still and asks 'Who is there?'; a fox jumps out."""
    return next(b for b in all_beats if b.beat_id == 4)


@pytest.fixture(scope="session")
def beat_5(all_beats) -> Beat:
    """Beat 5 – The fox introduces himself as Leo."""
    return next(b for b in all_beats if b.beat_id == 5)


@pytest.fixture(scope="session")
def beat_9(all_beats) -> Beat:
    """Beat 9 – The sun sets; Leo asks if they'll meet again tomorrow."""
    return next(b for b in all_beats if b.beat_id == 9)


@pytest.fixture(scope="session")
def beat_10(all_beats) -> Beat:
    """Beat 10 – Mia waves goodbye and happily walks home."""
    return next(b for b in all_beats if b.beat_id == 10)

