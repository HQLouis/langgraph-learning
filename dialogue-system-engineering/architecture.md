# Lingolino Dialog System Architecture

## Overview

Lingolino is a dual-graph AI system for German language learning with children (ages 3-12). It uses LangGraph with two separate graphs that communicate asynchronously.

## Immediate Response Graph (Real-time)

```
Child message
    |
    v
[initialStateLoader] -- loads audio_book, child_profile (only if missing)
    |
    v
[load_analysis] -- reads aufgaben + satzbaubegrenzung from background graph state
    |
    v
[load_beat_context] -- selects relevant story beats for closed-world knowledge
    |
    v
[masterChatbot] -- generates response + builds grounding contract
    |
    v
Response to child
```

### masterChatbot — The Core Response Generator

Constructs a multi-part system prompt:

1. **Master prompt** (`local_fallback_prompts.master_prompt`): Core personality, 5 critical conversation rules, final checklist
2. **Child profile injection**: Name, age, gender — always included
3. **First message prompt** (`master_first_message_prompt`): Only on first turn — greet by name
4. **Content context**: Beat-based (closed world) or full audio_book text (fallback)
5. **Meta rules** (`aufgaben` + `satzbaubegrenzung`): From background analysis — only in normal phase

The LLM receives: `[SystemMessage(prompt), optional SystemMessage(meta_rules), ...conversation messages]`

After generating `spoken_text`, it programmatically builds a `ResponseContract` with grounding evidence (no LLM call — fuzzy matching against beats).

## Background Analysis Graph (Async)

Runs after each immediate response, does NOT block the user. Results feed into the NEXT turn via `load_analysis`.

```
[initialStateLoader]
    |
    +-- [speechGrammarWorker]        --|
    +-- [speechComprehensionWorker]  --|
    +-- [sprachhandlungsWorker]      --|-- [foerderfokusWorker] --> [aufgabenWorker] --> END
    +-- [speechVocabularyWorker]     --|
    +-- [boredomWorker]              --|
    +-- [satzbauAnalyseWorker]       ----> [satzbauBegrenzungsWorker] --> END
```

### Current State: Background Workers are INACTIVE

All background worker prompts are empty strings in `local_fallback_prompts.py`. This means:
- `aufgaben` is always empty -> masterChatbot gets "Keine spezifischen Aufgaben."
- `satzbaubegrenzung` is always empty -> masterChatbot gets "Keine Begrenzungen."
- The meta_system message is only added when these fields have content, so currently it's often skipped

**Impact**: The master prompt carries 100% of the behavioral load. All dialog quality depends entirely on the master prompt + first message prompt.

## Prompt System

### Loading Priority
1. S3 bucket (disabled by default: `use_s3_prompts=False`)
2. Local fallback (`local_fallback_prompts.py`)

### Active Prompts (with content)
| Prompt | Location | Purpose |
|--------|----------|---------|
| `master_prompt` | `local_fallback_prompts.py:17-103` | Core personality + 5 conversation rules + checklist |
| `master_first_message_prompt` | `local_fallback_prompts.py:105-109` | First-turn greeting instruction |

### Inactive Prompts (empty strings)
All 9 background worker prompts: grammar, comprehension, speech acts, vocabulary, boredom, foerderfokus, aufgaben, satzbau analysis, satzbau constraints.

## State Fields

### Key fields flowing through the immediate graph:
- `messages`: Conversation history (LangChain HumanMessage/AIMessage list)
- `child_profile`: "Das Kind heißt {name}, ist {age} Jahre alt und ist {gender}."
- `audio_book`: Full story text
- `beat_context`: Formatted relevant beats (closed-world knowledge)
- `active_beat_ids`: List of currently active beat IDs
- `aufgaben`: Task suggestions from background (currently always empty)
- `satzbaubegrenzung`: Sentence structure constraints (currently always empty)
- `response_contract`: Grounding evidence for the response

## Test Framework

### Two strategies:
- **Strategy A (fixture-based)**: `build_state()` -> `masterChatbot()` -> `llm_judge()` — fast, ~0.5s per run
- **Strategy B (simulated)**: `simulate_conversation()` -> `llm_judge()` — realistic, ~10-30s per run

### Configuration (`ft_config.py`):
- System model: `google_genai:gemini-2.5-flash`
- Judge model: `google_genai:gemini-2.5-flash` at temperature 0.0
- System temperature: configurable via `SYSTEM_TEMPERATURE` (default 0.0 for deterministic testing)
- Default: 1 run per test, 80% pass threshold

### Test coverage:
- 7 feature test suites, 34+ criteria
- Tests cover: name/gender usage, clarity, explanation/correction verification, responding to answers, sufficient context, varied sentence starters, smooth transitions
