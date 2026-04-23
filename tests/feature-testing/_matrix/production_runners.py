"""
Production wiring — adapters that let the matrix engine call the real
dialog system.

These helpers intentionally stay thin: they exist only to bridge the
engine's callback signatures (``run_master``, ``run_background``) to
the project's existing ``build_state_with_beats`` /
``run_background_analysis`` functions. Unit tests stub these adapters
directly.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage

from _matrix.engine import MatrixCell

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Master / response generation adapter
# ---------------------------------------------------------------------------


def make_run_master(system_llm):
    """Factory returning a ``run_master`` callable bound to a concrete LLM.

    The returned callable has the signature expected by
    ``_matrix.engine.generate_response`` — it takes a cell, the prefix
    messages (already converted to LangChain form), and the BG state
    (may be None), and returns the generated response text.
    """

    def run_master(cell: MatrixCell, prefix_messages: list[Any], bg_state: dict | None) -> str:
        from feature_testing_utils import build_state_with_beats  # noqa: WPS433 — lazy import keeps pytest collection fast
        from nodes import load_beat_context, masterChatbot

        profile = cell.profile
        aufgaben = (bg_state or {}).get("aufgaben", "")
        satzbaubegrenzung = (bg_state or {}).get("satzbaubegrenzung", "")

        state = build_state_with_beats(
            child_name=profile["name"],
            child_age=int(profile["age"]),
            child_gender=profile["gender"],
            messages=prefix_messages,
            aufgaben=aufgaben,
            satzbaubegrenzung=satzbaubegrenzung,
            background_state=bg_state,
            **_audio_book_kwargs(cell),
        )
        # Re-run beat context in case the final HumanMessage changed what
        # beats are active — build_state_with_beats already does this,
        # but we run it again to be defensive against edits that don't
        # pass messages through the same loader.
        beat_updates = load_beat_context(state)
        if beat_updates:
            for k, v in beat_updates.items():
                state[k] = v  # type: ignore[literal-required]

        result = masterChatbot(state, system_llm)
        messages_out = result.get("messages", [])
        if not messages_out:
            logger.warning("masterChatbot returned no messages for cell %s", cell.cell_id)
            return ""
        return messages_out[-1].content

    return run_master


def _audio_book_kwargs(cell: MatrixCell) -> dict:
    """Resolve the story fixture keyword arguments for ``build_state_with_beats``.

    Currently we only have two stories in the fixture constants; extending
    this to a full registry is straightforward but out of scope here.
    """

    from feature_testing_utils import (  # noqa: WPS433 — lazy import
        FIXTURE_BOBO_AUDIO_BOOK,
        FIXTURE_BOBO_CHAPTER_ID,
        FIXTURE_BOBO_STORY_ID,
        FIXTURE_PIA_AUDIO_BOOK,
        FIXTURE_PIA_CHAPTER_ID,
        FIXTURE_PIA_STORY_ID,
    )

    sid = cell.subexample.get("story_id")
    cid = cell.subexample.get("chapter_id")
    if sid == FIXTURE_PIA_STORY_ID and cid == FIXTURE_PIA_CHAPTER_ID:
        return {
            "audio_book": FIXTURE_PIA_AUDIO_BOOK,
            "story_id": FIXTURE_PIA_STORY_ID,
            "chapter_id": FIXTURE_PIA_CHAPTER_ID,
        }
    if sid == FIXTURE_BOBO_STORY_ID and cid == FIXTURE_BOBO_CHAPTER_ID:
        return {
            "audio_book": FIXTURE_BOBO_AUDIO_BOOK,
            "story_id": FIXTURE_BOBO_STORY_ID,
            "chapter_id": FIXTURE_BOBO_CHAPTER_ID,
        }
    # Unknown story: fall back to the default build_state_with_beats
    # signature, which uses the Mia und Leo fixture.
    return {}


# ---------------------------------------------------------------------------
# Background-analysis adapter
# ---------------------------------------------------------------------------


def make_run_background(background_llm):
    """Factory returning a ``run_background`` callable.

    Delegates to :func:`feature_testing_utils.run_background_analysis` so
    the BG graph topology and node order stay in sync with production.
    """

    def run_background(cell: MatrixCell, prefix_messages: list[Any]) -> dict:
        from feature_testing_utils import run_background_analysis  # noqa: WPS433

        profile = cell.profile
        kwargs = _audio_book_kwargs(cell)

        return run_background_analysis(
            background_llm_instance=background_llm,
            child_name=profile["name"],
            child_age=int(profile["age"]),
            child_gender=profile["gender"],
            messages=prefix_messages,
            **kwargs,
        )

    return run_background
