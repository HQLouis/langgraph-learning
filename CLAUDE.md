# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lingolino** — an AI-powered German language learning system for children (ages 3-12). Uses LangGraph for conversational orchestration with a dual-graph architecture: an immediate response graph (real-time, user-facing) and a background analysis graph (9 parallel workers analyzing grammar, comprehension, vocabulary, boredom, etc.).

Primary LLM: Google Gemini 2.5 Flash (centralised in `agentic-system/model_config.py::DEFAULT_LLM_MODEL`; override per-environment via `LINGOLINO_LLM_MODEL`). Backend: FastAPI with SSE streaming. Infrastructure: AWS ECS/Fargate via Terraform.

## Commands

```bash
# Install dependencies (uses uv, not pip)
uv sync

# Start API server locally
./start_api.sh
# or: uv run python -m backend.main
# API at http://localhost:8000, docs at http://localhost:8000/docs

# Interactive CLI chat (for testing dialog directly)
python agentic-system/chat.py

# Docker
docker-compose up

# --- Tests ---

# Unit tests (agentic system) — deterministic, no LLM
pytest tests/agentic_system/

# Pipeline + matrix unit tests (no LLM)
pytest tests/feature-testing/_pipelines/
pytest tests/feature-testing/_matrix/test_engine_unit.py tests/feature-testing/_matrix/test_sidecar_unit.py

# Matrix cells (LIVE LLM — off by default; opt-in via -m matrix or --matrix-run)
pytest tests/feature-testing/_matrix -m matrix \
    --matrix-tier=core --matrix-profiles=default --matrix-n-runs=1 \
    --json-report --json-report-file=.matrix.json 2>&1 | tail -30

# Re-run a single requirement column at n=3 (separates fix from flake)
pytest tests/feature-testing/_matrix -m matrix --matrix-n-runs=3 -k R-XX-YY \
    --json-report --json-report-file=.matrix.json

# Functional/stream tests
pytest functional-testing/

# Single test file / function
pytest tests/agentic_system/test_beat_system.py
pytest tests/agentic_system/test_beat_system.py::test_function_name -v
```

**Registry pipelines** (regenerate the matrix's source-of-truth artefacts):

```bash
# Sync registry from Dialogbeispiele.md
PYTHONPATH=tests/feature-testing python -m _pipelines.run            # or /sync-registry
PYTHONPATH=tests/feature-testing python -m _pipelines.run --dry-run  # diff preview only

# LLM-enrich draft requirements (Gemini 2.5 Flash)
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements
PYTHONPATH=tests/feature-testing python -m _pipelines.enrich_requirements --only R-19-02,R-19-03
```

See `documentation/FEATURE_TESTING_FRAMEWORK.md` for the full go-to guide.

## Architecture

### Dual-Graph System (`agentic-system/`)

**Immediate Response Graph** (`immediate_graph.py`): User-facing, real-time path.
`initialStateLoader` → `load_analysis` (fetch prior background results) → `load_beat_context` (activate relevant beats) → `masterChatbot` (generate response) → returns `ResponseContract`.

**Background Analysis Graph** (`background_graph.py`): Async, non-blocking. 9 parallel worker nodes (grammar, comprehension, vocabulary, speech acts, boredom, sentence structure, etc.) feed into `foerderfokusWorker` → `aufgabenWorker`.

**Evolving data flows — test assumptions must follow.** The data flow between the immediate and background graphs, and between workers inside each graph, is expected to change across iterations. As of v1 of the feature-testing matrix, every background worker output eventually reaches the next `masterChatbot` turn (directly via `aufgaben` / `satzbaubegrenzung`, or indirectly via `aufgabenWorker` / `foerderfokusWorker` consuming upstream analyses). This is why every requirement in the matrix registry defaults to `needs_background_analysis: true`. When the topology changes — for example when a worker is removed, retargeted, or its output stops flowing to the master — the `needs_background_analysis` flag in `tests/feature-testing/_registry/requirements.yaml` MUST be revisited alongside the code change, and the affected requirements re-reviewed. The flag is an optimization hook, not a behavioural toggle; keep it consistent with the graph as the graph evolves.

### Beat System (`beats.py`)

Core content management enforcing "closed-world" knowledge — the LLM can only discuss content that exists in beats. A `Beat` is the smallest stable content unit (text span, entities, facts, tags). `BeatPack` groups beats per chapter (versioned, hashed). `BeatRetriever` selects relevant beats per turn. `beat_pipeline.py` handles semi-automated beatpack generation.

**Beat progress tracking**: `load_beat_context()` accumulates `covered_beat_ids` across turns and computes `story_near_end` (True when final ~20% of beats reached). This drives beat-aware story-end detection in `_detect_story_end()`, which falls back to keyword matching when no beatpack is available.

**Dual content source architecture**: `audio_book` (raw story text) and beats serve different consumers. `masterChatbot` uses filtered `beat_context` for closed-world prompts when beats are active, falling back to full `audio_book` text otherwise. Background workers always read full `audio_book` text. Both sources exist in state; beatpacks are generated FROM the story text via `beat_pipeline.py`.

### Output Contract System (`output_contract_builder.py`, `backend/models/output_contract.py`)

Validates that LLM responses are grounded in source material. `ResponseContract` contains grounding evidence (quotes + claims), answer type, and optional task. Uses fuzzy matching (`fuzzy_match_quote_to_beat`) with sliding-window comparison (threshold=0.6) to trace quotes back to beats.

### Backend API (`backend/`)

FastAPI with: `POST /conversations` (create session), `POST /conversations/{thread_id}/messages` (SSE streaming chat), `GET /conversations/{thread_id}` (history), `DELETE /conversations/{thread_id}`. Rate-limited (60 req/min via SlowAPI). In-memory conversation storage.

### Prompt System (`prompts.py`, `prompt_repository.py`, `local_fallback_prompts.py`)

Dynamic prompt loading from AWS S3 with TTL-based caching (15s). Falls back to local Python string prompts. All prompts accessed via getter functions in `prompts.py`.

### State (`states.py`)

`TypedDict`-based state definitions. Key fields: `messages` (LangChain message list with `add_messages` reducer), `child_profile`, `audio_book`, beat context fields (`story_id`, `chapter_id`, `beat_context`, `active_beat_ids`, `covered_beat_ids`, `story_near_end`), analysis results from all 9 workers, and `response_contract`.

## Testing Framework

> **Authoritative reference:** `documentation/FEATURE_TESTING_FRAMEWORK.md`. Read that first before iterating on tests, prompts, or the registry.

### Three test categories

1. **Unit tests** (`tests/agentic_system/`, `tests/feature-testing/_pipelines/`, `tests/feature-testing/_matrix/test_*_unit.py`): Deterministic, no LLM. Cover the beat system, prompt repo, output contract, MD parser, extraction/enrichment pipelines, matrix engine, and sidecar/report writers.

2. **Feature tests — example × requirement matrix** (`tests/feature-testing/_matrix/`): the primary signal for LLM behaviour.
   - One parametrized `test_cell` per `(SubExample × Requirement × profile)`. Cells marked `@pytest.mark.matrix` and **off by default** — opt-in via `-m matrix` or `--matrix-run` (see `_matrix/conftest.py::pytest_collection_modifyitems`).
   - Each cell: build state from `SubExample.prefix_messages` → optionally run BG graph → `masterChatbot` → one combined applicability+verdict judge call → `PASS | FAIL | N/A`.
   - **N/A counts as PASS** for thresholds; rendered as a grey badge in the report. Cell passes when `pass_rate >= matrix_pass_threshold` (default 1.0 at `n_runs=1` — any FAIL flips red).
   - Two-layer content-addressable cache at `tests/feature-testing/_matrix/.cache/` (BG state + master response). Judge calls are not cached.
   - Tier (`core | extended`) and profile (`default | extended | all`) filters keep the inner loop fast.
   - Curator surface: `tests/feature-testing/_registry/requirements.yaml` (`status`, `tier`, enrichment fields). Source of truth: `tests/feature-testing/Dialogbeispiele für die Eigenschaften.md` — never hand-write entries in `requirements.yaml` or `examples.jsonl` for new requirements; always go through the MD + `_pipelines.run`.
   - Slash commands: `/sync-registry`, `/add-requirement`, `/iterate-prompts`, `/stabilize-tests`.
   - Config in `tests/feature-testing/ft_config.py` (`MATRIX_*` flags, plus the legacy `N_RUNS`/`PASS_THRESHOLD` still used by the remaining feature folders).
   - **Story fixtures**: `FIXTURE_*_AUDIO_BOOK`, `FIXTURE_*_STORY_ID`, `FIXTURE_*_CHAPTER_ID` live in `feature_testing_utils.py` (single source of truth). Beatpacks at `tests/agentic_system/content/stories/<story_id>/<chapter_id>/beatpack.v1.json`. Beat manager is auto-initialised for all feature tests via the outer `conftest.py`.

3. **Legacy per-feature folders** (e.g. `tests/feature-testing/<feature>/`): 14 folders still on disk during the matrix migration (Phase 4). They use the old Strategy A / Strategy B layout (fixture-based vs simulated, `--n-runs` / `--pass-threshold`, markers `contract`, `llm_feature`, `llm_judge`, `simulated`). They are retired in batches as their Eigenschaften reach full matrix coverage.

4. **Functional tests** (`functional-testing/`): Stream and response format validation.

## Key Configuration

- Python 3.13 required. Package manager: **uv** (not pip).
- `pyproject.toml`: pythonpath includes `agentic-system` and `tests/feature-testing`.
- `.env` file required at project root (see `.env.example`). Must contain `GOOGLE_API_KEY`.
- Settings in `backend/core/config.py` (pydantic-settings, env-based).

## Infrastructure

- AWS deployment: ECS Fargate cluster in `eu-central-1`, ECR for images, ALB for load balancing.
- Terraform in `terraform/` with S3 backend state.
- CI/CD: `.github/workflows/` — `deploy-backend.yml` (main push → ECR → ECS), `deploy-frontend.yml`, `terraform-validate.yml`.

## Development Notes
- Multiple approaches — Always consider 2+ alternatives before recommending one
- Clean code — Typing, modularity, maintainability
- Testing-first mindset — For new modules, discuss testing strategy before implementation (approaches, tradeoffs, recommendations)
- Unit tests — Always consider them for functions
- Use Context7 to check up-to-date docs when needed for implementing new libraries or frameworks, or adding features using them
