"""
Two-layer filesystem cache for the matrix engine.

Layer 1 — background-state cache:
    key   = hash(prefix_messages + profile + story + bg_prompt_version)
    value = BackgroundState dict (as JSON)

Layer 2 — response cache:
    key   = hash(prefix_messages + profile + story + bg_state_hash
                 + master_prompt_version)
    value = generated system response text (string)

Both layers are content-addressable: the key fully captures the inputs
that can influence the value. Invalidation is therefore *automatic* —
change any input and the key changes, producing a cache miss.

Layout on disk::

    <cache_dir>/
        bg/<sha256[:4]>/<sha256>.json
        response/<sha256[:4]>/<sha256>.json

The two-level directory split keeps ``ls`` fast once caches grow to tens
of thousands of entries.

The cache never raises on I/O errors — any failure surfaces as a cache
miss so the test run can proceed.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hash helpers
# ---------------------------------------------------------------------------


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(*parts: str) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(b"\x1f")  # unit separator so two parts can't collide via concatenation
        h.update(p.encode("utf-8"))
    return h.hexdigest()


def bg_cache_key(
    *,
    prefix_messages: list[dict],
    profile: dict,
    story_id: str,
    chapter_id: str,
    bg_prompt_version: str,
    model_id: str,
    temperature: float,
) -> str:
    return _sha256(
        "bg:v1",
        _canonical_json(prefix_messages),
        _canonical_json(profile),
        story_id,
        chapter_id,
        bg_prompt_version,
        model_id,
        f"{temperature:.6f}",
    )


def response_cache_key(
    *,
    prefix_messages: list[dict],
    profile: dict,
    story_id: str,
    chapter_id: str,
    bg_state_hash: str,
    master_prompt_version: str,
    model_id: str,
    temperature: float,
) -> str:
    return _sha256(
        "response:v1",
        _canonical_json(prefix_messages),
        _canonical_json(profile),
        story_id,
        chapter_id,
        bg_state_hash,
        master_prompt_version,
        model_id,
        f"{temperature:.6f}",
    )


def bg_state_hash(bg_state: dict) -> str:
    """Stable hash of a BackgroundState. Used as part of the L2 key so
    changes in BG output invalidate the response cache."""
    return _sha256("bg_state:v1", _canonical_json(bg_state))


# ---------------------------------------------------------------------------
# FS cache
# ---------------------------------------------------------------------------


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0

    def record_hit(self) -> None:
        self.hits += 1

    def record_miss(self) -> None:
        self.misses += 1


class FilesystemCache:
    """Simple two-layer content-addressable cache.

    Call sites use the high-level :meth:`get_or_compute_bg` and
    :meth:`get_or_compute_response` helpers so the caching is transparent
    to the engine code.
    """

    def __init__(self, root: Path, *, enabled: bool = True) -> None:
        self.root = Path(root)
        self.enabled = enabled
        self.bg_stats = CacheStats()
        self.response_stats = CacheStats()

    # ---------- generic read/write ---------------------------------------

    def _shard_path(self, namespace: str, key: str) -> Path:
        return self.root / namespace / key[:4] / f"{key}.json"

    def _read(self, namespace: str, key: str) -> dict | None:
        if not self.enabled:
            return None
        path = self._shard_path(namespace, key)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — treat any failure as miss
            logger.warning("cache read failed for %s/%s: %s", namespace, key[:10], exc)
            return None

    def _write(self, namespace: str, key: str, value: dict) -> None:
        if not self.enabled:
            return
        path = self._shard_path(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_canonical_json(value), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 — never let cache writes fail the test
            logger.warning("cache write failed for %s/%s: %s", namespace, key[:10], exc)

    # ---------- L1: background state -------------------------------------

    def get_or_compute_bg(self, key: str, compute) -> dict:
        """Return the cached BackgroundState for ``key`` or compute & store it."""
        cached = self._read("bg", key)
        if cached is not None:
            self.bg_stats.record_hit()
            return cached
        self.bg_stats.record_miss()
        value = compute()
        if not isinstance(value, dict):
            raise TypeError("BG compute callback must return a dict (BackgroundState-shaped)")
        self._write("bg", key, value)
        return value

    # ---------- L2: response ---------------------------------------------

    def get_or_compute_response(self, key: str, compute) -> str:
        cached = self._read("response", key)
        if cached is not None:
            self.response_stats.record_hit()
            return cached.get("response_text", "")
        self.response_stats.record_miss()
        value = compute()
        if not isinstance(value, str):
            raise TypeError("response compute callback must return a string")
        self._write("response", key, {"response_text": value})
        return value

    # ---------- introspection --------------------------------------------

    def summary(self) -> str:
        return (
            f"cache: bg hits={self.bg_stats.hits} misses={self.bg_stats.misses}; "
            f"response hits={self.response_stats.hits} misses={self.response_stats.misses}"
        )
