# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Lingolino** — an AI-powered German language learning system for children (ages 3-12). Uses LangGraph for conversational orchestration with a dual-graph architecture: an immediate response graph (real-time, user-facing) and a background analysis graph (9 parallel workers analyzing grammar, comprehension, vocabulary, boredom, etc.).

Primary LLM: Google Gemini 2.0 Flash. Backend: FastAPI with SSE streaming. Infrastructure: AWS ECS/Fargate via Terraform.

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

# Unit tests (agentic system)
pytest tests/agentic_system/

# Contract tests only (fast, deterministic)
pytest tests/feature-testing/ -m contract

# LLM feature tests (slow, costs API credits)
pytest tests/feature-testing/ -m llm_feature

# All feature tests with custom params
pytest tests/feature-testing/ --n-runs=10 --pass-threshold=0.9

# Specific feature folder
pytest tests/feature-testing/child-name-and-gender/

# Functional/stream tests
pytest functional-testing/

# Single test file
pytest tests/agentic_system/test_beat_system.py

# Single test function
pytest tests/agentic_system/test_beat_system.py::test_function_name -v
```

## Architecture

### Dual-Graph System (`agentic-system/`)

**Immediate Response Graph** (`immediate_graph.py`): User-facing, real-time path.
`initialStateLoader` → `load_analysis` (fetch prior background results) → `load_beat_context` (activate relevant beats) → `masterChatbot` (generate response) → returns `ResponseContract`.

**Background Analysis Graph** (`background_graph.py`): Async, non-blocking. 9 parallel worker nodes (grammar, comprehension, vocabulary, speech acts, boredom, sentence structure, etc.) feed into `foerderfokusWorker` → `aufgabenWorker`.

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

### Three test categories

1. **Unit tests** (`tests/agentic_system/`): Deterministic module-level tests (beat system, prompt repo, output contract).

2. **Feature tests** (`tests/feature-testing/`): Probabilistic LLM testing framework. Two strategies:
   - **Strategy A (fixture-based)**: Pre-built state + hardcoded conversation, fast (~0.5s).
   - **Strategy B (simulated)**: Full conversation from scratch with real LLM, slow (~10-30s).
   - Each test runs N times (default 5), must pass ≥80% (configurable via `--n-runs`, `--pass-threshold`).
   - Tests organized by feature folder. Markers: `contract`, `llm_feature`, `llm_judge`, `simulated`.
   - Config in `tests/feature-testing/ft_config.py`.
   - **Story fixtures**: All story text constants (`FIXTURE_*_AUDIO_BOOK`, `FIXTURE_*_STORY_ID`, `FIXTURE_*_CHAPTER_ID`) are centralized in `feature_testing_utils.py` as the single source of truth. Test files import from there — never define story text locally. Beatpacks are generated from these same texts via `scripts/generate_test_beatpacks.py`. See `tests/feature-testing/SETUP_GUIDE.md` for full setup instructions.
   - **Beat system in tests**: The beat manager is auto-initialized for all feature tests via `conftest.py`. Beatpack fixtures live at `tests/agentic_system/content/stories/<story_id>/<chapter_id>/beatpack.v1.json`.

3. **Functional tests** (`functional-testing/`): Stream and response format validation.

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
