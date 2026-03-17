# Feature Testing Setup Guide

This guide explains how to set up feature tests for the Lingolino dialog system, including how to create story fixtures, generate beatpacks, and wire everything together.

## Overview

Feature tests validate the dialog system's behavior using two strategies:

- **Strategy A (fixture-based)**: Pre-built conversation state + hardcoded history. Fast (~0.5s per run), fully reproducible.
- **Strategy B (simulated)**: Full conversation from scratch with real LLM. Slower (~10-30s), tests end-to-end flow.

Both strategies run N times (default 5) and require a configurable pass rate (default 80%).

## Project Structure

```
tests/
  feature-testing/
    conftest.py                  # Shared fixtures, CLI options, beat manager init
    feature_testing_utils.py     # build_state(), simulate_conversation(), llm_judge()
    ft_config.py                 # N_RUNS, thresholds, model config
    <feature-name>/
      __init__.py
      test_<feature>.py          # Test file
      <feature>-test-spec.txt    # (optional) Feature spec
  agentic_system/
    content/
      stories/
        <story_id>/
          <chapter_id>/
            beatpack.v1.json     # Generated beatpack fixture
```

## Step 1: Add Your Story

### 1.1 Define the story text constant

**Important**: Story text constants MUST be defined in `feature_testing_utils.py` — the single source of truth. Never define story text locally in test files.

Add your constants to `feature_testing_utils.py`:

```python
FIXTURE_MY_STORY_AUDIO_BOOK: str = """\
Es war einmal... \
... das Ende der Geschichte.\
"""

FIXTURE_MY_STORY_ID: str = "my_story_name"      # snake_case, matches directory name
FIXTURE_MY_CHAPTER_ID: str = "chapter_01"
```

Then import in your test file:

```python
from feature_testing_utils import (
    FIXTURE_MY_STORY_AUDIO_BOOK,
    FIXTURE_MY_STORY_ID,
    FIXTURE_MY_CHAPTER_ID,
)
```

This ensures the same text is used in tests, beatpack generation, and documentation — no drift.

### 1.2 Generate a beatpack

Beatpacks enable the beat system's closed-world knowledge enforcement and story-end detection. Without a beatpack, the system falls back to keyword-based detection and raw `audio_book` text.

**Option A: Use the generation script**

Add your story to `scripts/generate_test_beatpacks.py`:

```python
from beats import EntityInfo

MY_STORY_ENTITY_REGISTRY = {
    "Character1": EntityInfo(
        aliases=["alias1", "sie"],
        entity_type="character",
    ),
    "Location1": EntityInfo(
        aliases=["der Ort"],
        entity_type="location",
    ),
}

# In main():
generate_beatpack(
    story_id="my_story_name",
    chapter_id="chapter_01",
    story_text=MY_STORY_TEXT,
    entity_registry=MY_STORY_ENTITY_REGISTRY,
)
```

Run:
```bash
uv run python scripts/generate_test_beatpacks.py
```

**Option B: Create manually**

Create the file at:
```
tests/agentic_system/content/stories/<story_id>/<chapter_id>/beatpack.v1.json
```

See existing beatpacks (e.g., `mia_und_leo/chapter_01/beatpack.v1.json`) for the JSON schema.

### 1.3 Verify the beatpack

```bash
uv run pytest tests/agentic_system/test_beat_progress.py -v
```

You can also add a test to `test_beat_progress.py::TestBeatpackFixtures`:

```python
def test_my_story_beatpack_loads(self, manager):
    bp = manager.get_beatpack("my_story_name", "chapter_01")
    assert bp is not None
    assert len(bp.beats) >= 5

def test_my_story_integrity(self, manager):
    bp = manager.get_beatpack("my_story_name", "chapter_01")
    is_valid, errors = bp.verify_integrity()
    assert is_valid, f"Integrity errors: {errors}"
```

### 1.4 Entity registry guidelines

| Entity Type | Examples | Notes |
|---|---|---|
| `character` | People, animals, named figures | Include common aliases (pronouns, titles) |
| `location` | Places, rooms, landmarks | Include case variations |
| `object` | Important items in the story | Only items central to the plot |

Tips:
- Focus on entities the child will discuss — minor background details don't need entries
- Aliases help the entity extractor find matches in beat text
- The pipeline also extracts capitalized words heuristically

## Step 2: Write a Test

### Strategy A (fixture-based)

```python
import pytest
from feature_testing_utils import build_state, llm_judge, state_to_setting
from langchain_core.messages import HumanMessage, AIMessage

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestMyFeature:
    def test_something(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        messages = [
            AIMessage(content="Hallo! Ich bin Thilio."),
            HumanMessage(content="Hallo!"),
        ]

        state = build_state(
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            messages=messages,
            audio_book=FIXTURE_MY_STORY_AUDIO_BOOK,
            story_id=FIXTURE_MY_STORY_ID,
            chapter_id=FIXTURE_MY_CHAPTER_ID,
        )

        criterion = "The system response should greet the child warmly."

        def _run():
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, criterion)

        run_details_recorder(
            _run, n_runs, pass_threshold,
            setting=state_to_setting(state, criterion),
        )
```

### Strategy B (simulated)

```python
from feature_testing_utils import simulate_conversation, simulation_to_setting

SIMULATED_CHILD_INPUTS = [
    'hallo',                          # child turn 1
    'Hallo! Schön dass du da bist.',  # pre-defined system turn 1
    'was passiert?',                  # child turn 2 (last — tested)
]

def test_simulated(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
    def _run():
        final_state, spoken_text = simulate_conversation(
            system_llm_instance=system_llm,
            child_name="Emma",
            child_age=5,
            child_gender="weiblich",
            child_inputs=SIMULATED_CHILD_INPUTS,
            audio_book=FIXTURE_MY_STORY_AUDIO_BOOK,
            story_id=FIXTURE_MY_STORY_ID,
            chapter_id=FIXTURE_MY_CHAPTER_ID,
        )
        passed, resp, reason = llm_judge(judge_llm, spoken_text, criterion)
        # Capture conversation for HTML report
        conversation = [
            {"role": "Child" if isinstance(m, HumanMessage) else "System",
             "content": m.content}
            for m in final_state.get("messages", [])
        ]
        return passed, resp, reason, conversation

    run_details_recorder(_run, n_runs, pass_threshold, setting=...)
```

**Important**: `child_inputs` must have **odd length** — alternating child/system turns, ending with a child turn. The system's response to the last child turn is generated live and evaluated.

## Step 3: Beat System Integration

### How beats flow through the system

```
load_beat_context(state)
  ├── Loads beatpack from content directory
  ├── Retrieves relevant beats (keyword matching or chronological distribution)
  ├── Tracks covered_beat_ids (cumulative across turns)
  ├── Computes story_near_end (final 20% of beats reached?)
  └── Returns: beat_context, active_beat_ids, covered_beat_ids, story_near_end

masterChatbot(state)
  ├── Uses beat_context for closed-world prompt injection
  ├── Checks story_near_end for wrap-up detection
  └── Builds output contract with grounding evidence from active beats
```

### Beat system activation

The beat system is **automatically activated** for all feature tests via the `_init_beat_manager` fixture in `conftest.py`. It loads beatpacks from `tests/agentic_system/content/stories/`.

For it to work with your story:
1. Your `story_id` and `chapter_id` must match the directory structure
2. A `beatpack.v1.json` must exist at the expected path

### Story-end detection

Two mechanisms, in priority order:

1. **Beat-based** (primary): When `story_near_end` is `True` (final 20% of beats reached), the system injects a wrap-up nudge. Works with any story that has a beatpack.

2. **Keyword-based** (fallback): When no beat system is active (`story_near_end is None`), scans AI messages for ending keywords like "eingeschlafen", "kichern", etc. Story-specific — may not work for all stories.

## Step 4: Running Tests

```bash
# Contract tests (fast, no LLM)
pytest tests/feature-testing/ -m contract

# All LLM feature tests
pytest tests/feature-testing/ -m llm_feature --n-runs=6

# Specific feature
pytest tests/feature-testing/story-not-extended/ -v --n-runs=6

# Strategy B only
pytest tests/feature-testing/ -m simulated -v

# With HTML report
pytest tests/feature-testing/ -m llm_feature \
  --json-report --json-report-file=.feature_test_report.json \
  --n-runs=6
```

## Available Markers

| Marker | Description |
|---|---|
| `contract` | Deterministic contract tests (no LLM) |
| `llm_feature` | Tests that invoke the real dialog system LLM |
| `llm_judge` | Tests that use the LLM judge for evaluation |
| `simulated` | Strategy B tests (full simulation) |

## Existing Story Fixtures

| Story ID | Chapter | Beats | Path |
|---|---|---|---|
| `mia_und_leo` | `chapter_01` | 10 | `tests/agentic_system/content/stories/mia_und_leo/chapter_01/` |
| `pia_muss_nicht_perfekt_sein` | `chapter_01` | 20 | `tests/agentic_system/content/stories/pia_muss_nicht_perfekt_sein/chapter_01/` |
| `bobos_adventskalender` | `chapter_01` | 12 | `tests/agentic_system/content/stories/bobos_adventskalender/chapter_01/` |
