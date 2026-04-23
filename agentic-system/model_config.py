"""
Centralised LLM-model configuration for the Lingolino codebase.

Every module that needs to name the default chat model imports from
here so that bumping the model version (e.g. Gemini 2.5 → 3.0) is a
one-line change.

Resolution order for the default model id:

  1. Environment variable ``LINGOLINO_LLM_MODEL`` — allows operators to
     override without touching code.
  2. ``DEFAULT_LLM_MODEL`` constant defined here — the baked-in default.

The backend (``backend.core.config.Settings.llm_model``) reads its own
pydantic-settings entry, which now defaults to the same constant to
keep the whole stack aligned.
"""

from __future__ import annotations

import os


DEFAULT_LLM_MODEL: str = "google_genai:gemini-2.5-flash"
"""Canonical LLM id used across dialog system, background workers,
feature-testing system LLM, judge LLM, enrichment pipeline, and the
backend default. ``google_genai:gemini-2.0-flash`` was retired by Google
for new users; Gemini 2.5 Flash is the current drop-in replacement."""


def resolve_model() -> str:
    """Return the LLM id to use — environment override wins over the default."""
    return os.environ.get("LINGOLINO_LLM_MODEL") or DEFAULT_LLM_MODEL
