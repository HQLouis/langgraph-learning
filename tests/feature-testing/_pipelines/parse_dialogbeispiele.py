"""
Parser for `Dialogbeispiele für die Eigenschaften.md`.

The MD is authored by humans and mixes two dialogue conventions:

1.  **Implicit alternation** — most common. Turns are separated by markdown
    hard-breaks (two trailing spaces + newline). The first turn is always
    the child. The writer relies on the reader to visually alternate.

        hallo
        Hallo! Hast du die Geschichte von Pia gehört?
        ja
        Super! Pia ist schon ein besonderes Mädchen...

2.  **Explicit markers** — used in the appendix sections and some later
    Beispiele. Turns carry a `KI:` / `Kind:` / `KIND:` prefix.

        KI: „Pia steht in der Küche..."
        Kind: „isst"
        KI: „Du sagst, Pia isst das Brot..."

This module produces a neutral intermediate representation — a list of
:class:`Eigenschaft` objects, each containing :class:`Beispiel` objects,
each containing a list of :class:`Turn` objects — that both
``extract_examples.py`` and ``extract_requirements.py`` consume.

The parser is deliberately conservative: when it cannot confidently
tokenize a block it records a warning and skips the block. Running the
pipeline surfaces these warnings so a human can either fix the MD or
extend the parser.
"""

from __future__ import annotations

import dataclasses
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Turn:
    """One utterance in a dialogue. ``role`` is either 'child' or 'system'."""

    role: str
    content: str


@dataclass
class Beispiel:
    """One worked dialogue example under an Eigenschaft."""

    index: int                       # 1-based position of the Beispiel within its Eigenschaft
    label: str                       # e.g. "Beispiel 1 PIA"
    story_hint: str | None           # "PIA" | "BOBO" | None
    turns: list[Turn]                # the main dialogue (may be empty for suggestion-only Beispiele)
    suggested_ki_turns: list[Turn]   # turns extracted from the "mögliche KI Antwort" block
    anforderungen: list[str]         # one entry per Anforderung paragraph
    highlight_from_turn: int | None  # 0-based index of first highlighted (bolded) turn, if any
    raw_block: str                   # full source text of the Beispiel, for debugging


@dataclass
class Eigenschaft:
    """One top-level section of the MD — usually a numbered property."""

    number: int | None               # 1..21 for numbered sections; None for appendix-style headers
    title_de: str
    anchor: str                      # slug from the {#…} suffix in the header
    beispiele: list[Beispiel] = field(default_factory=list)
    section_anforderungen: list[str] = field(default_factory=list)
    """Anforderung paragraphs that appear at the top of the section,
    before any Beispiel. Common in the flüssiger-Übergang, mehr-Kontext,
    and name-usage-frequency sections."""
    raw_header: str = ""


@dataclass
class ParseReport:
    """Collected warnings and stats from a parse run."""

    warnings: list[str] = field(default_factory=list)
    eigenschaft_count: int = 0
    beispiel_count: int = 0
    turn_count: int = 0
    skipped_blocks: int = 0

    def warn(self, msg: str) -> None:
        logger.warning(msg)
        self.warnings.append(msg)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def parse_markdown(md_path: Path) -> tuple[list[Eigenschaft], ParseReport]:
    """Parse the Dialogbeispiele MD file into a list of Eigenschaften.

    Returns a ``(eigenschaften, report)`` pair. The report aggregates any
    warnings the parser emitted — callers should log / surface it.
    """

    raw = md_path.read_text(encoding="utf-8")
    report = ParseReport()

    normalised = _normalise_markdown(raw)
    sections = _split_into_eigenschaft_sections(normalised, report)
    eigenschaften: list[Eigenschaft] = []

    for header, body in sections:
        number, title_de, anchor = _parse_eigenschaft_header(header)
        # The MD's "# PIA" and "# BOBO" h1s are story-text holders, not
        # Eigenschaften — skip them. Any other section with no Beispiele
        # (e.g. the "Fragen an Louis" scratch block) is also dropped.
        if anchor in {"pia", "bobo"} or title_de.strip().upper() in {"PIA", "BOBO"}:
            continue
        beispiele = _parse_beispiele(body, report)
        if not beispiele:
            # Appendix notes without Beispiele carry no test value.
            continue
        eigenschaft = Eigenschaft(
            number=number,
            title_de=title_de,
            anchor=anchor,
            raw_header=header,
        )
        eigenschaft.beispiele = beispiele
        eigenschaft.section_anforderungen = _extract_section_anforderungen(body)
        eigenschaften.append(eigenschaft)

    report.eigenschaft_count = len(eigenschaften)
    report.beispiel_count = sum(len(e.beispiele) for e in eigenschaften)
    report.turn_count = sum(
        len(b.turns) + len(b.suggested_ki_turns)
        for e in eigenschaften
        for b in e.beispiele
    )
    return eigenschaften, report


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------

_MD_HARD_BREAK_RE = re.compile(r"  +\n")        # trailing double-space + newline
_BACKSLASH_ESCAPE_RE = re.compile(r"\\([!:\"'.()/\[\]?\-*])")  # "\\!" → "!", etc.
_SMART_QUOTES = {
    "„": '"',
    """: '"',
    """: '"',
    "‚": "'",
    "'": "'",
    "'": "'",
    "«": '"',
    "»": '"',
    "–": "-",
    "—": "-",
    "…": "...",
    " ": " ",   # non-breaking space
}


def _normalise_markdown(text: str) -> str:
    """Apply pre-processing shared by all downstream passes.

    * Collapse markdown hard-breaks (``"  \\n"``) into single newlines so
      each utterance occupies exactly one line.
    * Replace smart quotes / em-dashes with ASCII equivalents so later
      pattern matching doesn't have to care.
    * Strip the escape backslashes the MD uses in front of ``!``, ``:``,
      etc. (markdown-rendered text looks clean but regexes choke on them).
    """

    # Markdown hard breaks — two or more trailing spaces before a newline
    text = _MD_HARD_BREAK_RE.sub("\n", text)
    # Escaped characters (\\!, \\:, etc.)
    text = _BACKSLASH_ESCAPE_RE.sub(r"\1", text)
    # Smart quotes / dashes
    for src, dst in _SMART_QUOTES.items():
        text = text.replace(src, dst)
    return text


# ---------------------------------------------------------------------------
# Eigenschaft section splitting
# ---------------------------------------------------------------------------

# Top-level headers come in several flavours:
#   "# 1.Eigenschaft: Übergang ... {#...}"
#   "# **11. Eigenschaft: Geschlecht... {#...}**"
#   "# Eigenschaft: Satzbau berücksichtigen {#...}"
#   "# funktionierende Eigenschaft: ..."
# The anchor `{#...}` suffix is always present — we use it as the most
# reliable marker.
_HEADER_RE = re.compile(
    r"^[ \t]*#[ \t]+(?P<full>.+?\{#(?P<anchor>[^}]+)\})[ \t]*$",
    re.MULTILINE,
)


def _split_into_eigenschaft_sections(
    text: str, report: ParseReport
) -> list[tuple[str, str]]:
    """Return ``[(header, body), ...]`` for every Eigenschaft-level h1."""

    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        report.warn("No Eigenschaft headers found — markdown format may have changed.")
        return []

    sections: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        header_line = match.group(0).strip()
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[body_start:body_end]
        sections.append((header_line, body))
    return sections


# Strip bold markers, numbering, anchor: keep only the human title.
_HEADER_TITLE_CLEAN_RE = re.compile(r"\s*\{#[^}]+\}\s*$")
_HEADER_BOLD_RE = re.compile(r"\*\*")
_HEADER_NUMBER_RE = re.compile(r"^\s*(?P<num>\d+)\s*\.\s*", re.VERBOSE)


def _parse_eigenschaft_header(header: str) -> tuple[int | None, str, str]:
    """Extract ``(number, clean_title_de, anchor)`` from a raw h1 line."""

    m = _HEADER_RE.match(header)
    anchor = m.group("anchor") if m else ""
    inner = _HEADER_TITLE_CLEAN_RE.sub("", m.group("full") if m else header)
    inner = _HEADER_BOLD_RE.sub("", inner).strip()
    # Strip a leading "N." if present to pull out the number
    num_match = _HEADER_NUMBER_RE.match(inner)
    number: int | None = None
    if num_match:
        number = int(num_match.group("num"))
        inner = _HEADER_NUMBER_RE.sub("", inner, count=1).strip()
    # Drop a leading "Eigenschaft: " prefix if present
    inner = re.sub(r"^Eigenschaft:\s*", "", inner, flags=re.IGNORECASE).strip()
    return number, inner, anchor


# ---------------------------------------------------------------------------
# Beispiel extraction
# ---------------------------------------------------------------------------

# A Beispiel block starts at a line beginning with "**Beispiel" (optionally
# preceded by a number) or the simpler "Beispiel N ..." style used in the
# flüssiger-Übergang and Satzanfänge sections. We also accept the hybrid
# "**Beispiel 2 PIA:**" form.
_BEISPIEL_START_RE = re.compile(
    r"""
    ^\s*                                          # leading whitespace
    (?:\*\*)?                                     # optional bold opening
    Beispiel\s+                                   # literal "Beispiel "
    (?P<num>\d+)                                  # index within this Eigenschaft
    \s*(?:[.:\-]|\s)?\s*                          # optional separator
    (?P<label_rest>[^\n*]*?)                      # remainder: story hint, etc.
    (?:\*\*)?                                     # optional bold close
    \s*:?\s*$                                     # optional trailing colon
    """,
    re.MULTILINE | re.VERBOSE,
)

_MOEGLICHE_ANTWORT_RE = re.compile(
    r"^\s*(?:\*\*)?\s*mögliche\s+KI\s+Antwort\s*:?\s*(?:\*\*)?\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_ANFORDERUNG_RE = re.compile(
    r"^\s*(?:\*\*)?\s*Anforderung(?:en)?\s+für\s+eine\s+bessere\s+KI\s+Antwort\s*:?\s*(?:\*\*)?\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def _parse_beispiele(body: str, report: ParseReport) -> list[Beispiel]:
    """Split an Eigenschaft body into individual Beispiel blocks and parse each."""

    starts = list(_BEISPIEL_START_RE.finditer(body))
    if not starts:
        return []

    beispiele: list[Beispiel] = []
    for idx, match in enumerate(starts):
        start = match.start()
        end = starts[idx + 1].start() if idx + 1 < len(starts) else len(body)
        block = body[start:end]
        beispiel = _parse_single_beispiel(block, index=int(match.group("num")), report=report)
        if beispiel is not None:
            beispiele.append(beispiel)
    return beispiele


_STORY_HINT_RE = re.compile(r"\b(PIA|BOBO)\b", re.IGNORECASE)


def _parse_single_beispiel(
    block: str, *, index: int, report: ParseReport
) -> Beispiel | None:
    # Drop any leading blank lines / whitespace so the first real line is
    # guaranteed to be the Beispiel header.
    stripped_block = block.lstrip("\n\r ")
    lines = stripped_block.splitlines()
    if not lines:
        return None

    header_line = lines[0].strip()
    label = re.sub(r"\*+", "", header_line).rstrip(":").strip()
    story_hint_match = _STORY_HINT_RE.search(header_line)
    story_hint = story_hint_match.group(1).upper() if story_hint_match else None

    # Find section breakpoints inside the block
    body_after_header = "\n".join(lines[1:])
    moeglich_match = _MOEGLICHE_ANTWORT_RE.search(body_after_header)
    anforderung_match = _ANFORDERUNG_RE.search(body_after_header)

    # main dialogue = everything between the header and the first "mögliche KI Antwort"
    # (falling back to the Anforderung marker if there is no mögliche block)
    if moeglich_match:
        dialogue_section = body_after_header[: moeglich_match.start()]
        suggested_section: str = ""
        if anforderung_match and anforderung_match.start() > moeglich_match.start():
            suggested_section = body_after_header[moeglich_match.end():anforderung_match.start()]
            anforderung_section = body_after_header[anforderung_match.end():]
        else:
            suggested_section = body_after_header[moeglich_match.end():]
            anforderung_section = ""
    elif anforderung_match:
        dialogue_section = body_after_header[: anforderung_match.start()]
        suggested_section = ""
        anforderung_section = body_after_header[anforderung_match.end():]
    else:
        dialogue_section = body_after_header
        suggested_section = ""
        anforderung_section = ""

    turns, highlight_from = _tokenize_dialogue(dialogue_section, label=label, report=report)
    suggested_turns, _ = _tokenize_dialogue(suggested_section, label=f"{label} (suggested)", report=report)
    anforderungen = _split_anforderungen(anforderung_section)

    return Beispiel(
        index=index,
        label=label,
        story_hint=story_hint,
        turns=turns,
        suggested_ki_turns=suggested_turns,
        anforderungen=anforderungen,
        highlight_from_turn=highlight_from,
        raw_block=block,
    )


# ---------------------------------------------------------------------------
# Dialogue tokenisation
# ---------------------------------------------------------------------------

# Matches an explicit role marker at the start of a line.
_ROLE_MARKER_RE = re.compile(
    r"^\s*(?P<role>KI|KIND|Kind|System|Child)\s*[:\-]\s*(?P<content>.*)$",
    re.IGNORECASE,
)


def _tokenize_dialogue(
    text: str, *, label: str, report: ParseReport
) -> tuple[list[Turn], int | None]:
    """Split a dialogue-shaped block into :class:`Turn` objects.

    Detects whether the block uses explicit role markers (``KI:``, ``Kind:``)
    or implicit alternation and applies the appropriate tokenizer.

    Also detects the bold markers that the MD uses to highlight the
    "moment" being illustrated and returns the 0-based turn index at
    which the highlight starts (or ``None`` if nothing is bolded).
    """

    raw_lines = [line for line in text.splitlines() if line.strip()]
    if not raw_lines:
        return [], None

    # Heuristic: if at least half the non-empty lines start with a role
    # marker we treat the block as explicit.
    marker_hits = sum(1 for line in raw_lines if _ROLE_MARKER_RE.match(line))
    explicit = marker_hits >= max(2, len(raw_lines) // 2)

    turns: list[Turn] = []
    highlight_from: int | None = None

    for idx, line in enumerate(raw_lines):
        stripped = line.strip()
        was_highlighted, clean = _strip_bold_markers(stripped)
        if explicit:
            match = _ROLE_MARKER_RE.match(clean)
            if not match:
                # Skip stray lines inside an explicit block (e.g. stage directions).
                continue
            role_raw = match.group("role").lower()
            content = match.group("content").strip()
            if not content:
                continue
            role = "system" if role_raw in {"ki", "system"} else "child"
            turns.append(Turn(role=role, content=content))
        else:
            role = "child" if idx % 2 == 0 else "system"
            turns.append(Turn(role=role, content=clean))

        if was_highlighted and highlight_from is None:
            highlight_from = len(turns) - 1

    if not turns:
        report.warn(f"{label}: produced no turns from the dialogue block.")
    return turns, highlight_from


_BOLD_WRAPPER_RE = re.compile(r"^\*\*(.+?)\*\*$", re.DOTALL)
_INLINE_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)


def _strip_bold_markers(line: str) -> tuple[bool, str]:
    """Return ``(was_highlighted, cleaned_line)``.

    A line is "highlighted" if the whole line is wrapped in ``**...**``. We
    also remove inline bold runs so downstream matching sees plain text.
    """

    was_highlighted = False
    wrapper = _BOLD_WRAPPER_RE.match(line)
    if wrapper:
        was_highlighted = True
        line = wrapper.group(1)
    line = _INLINE_BOLD_RE.sub(r"\1", line)
    return was_highlighted, line.strip()


# ---------------------------------------------------------------------------
# Anforderung splitting
# ---------------------------------------------------------------------------


def _split_anforderungen(section: str) -> list[str]:
    """Split the free-form Anforderung block into individual paragraphs.

    Adjacent non-empty lines are joined with a space; blank lines separate
    paragraphs. Leading numbering (``1.``, ``1)``) is stripped so the
    downstream YAML stores the actual requirement text.

    Paragraphs that are obvious noise — isolated ``#`` headers, stray
    ``.Eigenschaft`` scaffolding — are dropped. Anything shorter than 20
    characters is treated as noise too; real Anforderungen are full
    sentences.
    """

    section = section.strip()
    if not section:
        return []
    paragraphs: list[str] = []
    current: list[str] = []
    for line in section.splitlines():
        clean = line.strip()
        if not clean:
            if current:
                paragraphs.append(" ".join(current).strip())
                current = []
            continue
        # Skip leftover bold-wrapper-only lines
        if clean in {"**", "__"}:
            continue
        # Drop inline bold wrappers and leading numbering
        clean = _INLINE_BOLD_RE.sub(r"\1", clean)
        clean = re.sub(r"^\s*\d+\s*[.)]\s*", "", clean)
        current.append(clean)
    if current:
        paragraphs.append(" ".join(current).strip())
    return [p for p in paragraphs if _is_real_anforderung(p)]


_ANFORDERUNG_NOISE_PREFIXES = (
    "#", ". Eigenschaft", ".Eigenschaft", "Eigenschaft-",
)


def _is_real_anforderung(paragraph: str) -> bool:
    """Filter out obvious noise paragraphs produced by the MD's scaffolding.

    Real Anforderungen are always full sentences (> 20 characters) and
    never start with a markdown-scaffolding marker.
    """
    if len(paragraph) < 20:
        return False
    stripped = paragraph.lstrip("*# ").strip()
    if stripped.startswith(_ANFORDERUNG_NOISE_PREFIXES):
        return False
    return True


# ---------------------------------------------------------------------------
# Section-level Anforderung extraction
# ---------------------------------------------------------------------------


def _extract_section_anforderungen(body: str) -> list[str]:
    """Collect Anforderung paragraphs that appear in the section body
    BEFORE the first Beispiel.

    The MD occasionally states universal Anforderungen for a whole
    Eigenschaft (e.g. flüssiger-Übergang) at the top of the section,
    rather than duplicating them inside each Beispiel. We lift those
    into the Eigenschaft dataclass so ``extract_requirements`` can still
    emit Requirement entries for them.
    """

    first_beispiel = _BEISPIEL_START_RE.search(body)
    preamble = body[: first_beispiel.start()] if first_beispiel else body

    # Optional explicit "Anforderungen:" marker at the top
    marker = _ANFORDERUNG_RE.search(preamble)
    if marker:
        preamble = preamble[marker.end():]

    # The preamble may also contain a short description sentence before
    # the Anforderung text. Strip everything up to the first paragraph
    # break to avoid capturing the section's intro.
    return _split_anforderungen(preamble)


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------


def iter_beispiele(eigenschaften: Iterable[Eigenschaft]) -> Iterable[tuple[Eigenschaft, Beispiel]]:
    """Yield ``(eigenschaft, beispiel)`` pairs for every Beispiel across all Eigenschaften."""

    for e in eigenschaften:
        for b in e.beispiele:
            yield e, b


def to_dict(obj) -> dict:
    """Shallow dataclass → dict for JSON logging."""

    if dataclasses.is_dataclass(obj):
        return dataclasses.asdict(obj)
    raise TypeError(f"Not a dataclass: {type(obj).__name__}")
