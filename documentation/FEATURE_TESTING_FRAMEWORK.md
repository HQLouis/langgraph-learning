# Dialog System Feature Testing Framework

## 1. Overview & Motivation

The agentic-system is an LLM-powered dialog system for children. Because LLMs are non-deterministic,
a single test run is not sufficient to assert that a feature works reliably. Additionally, features
span multiple modules (`prompts.py`, `nodes.py`, `beats.py`, `output_contract_builder.py`), so
traditional module-level unit tests obscure the user-facing intent.

This framework provides:
- **Feature-oriented** test organization — each directory tests one user-facing feature, not one module.
- **Two testing strategies per feature** — (a) *fixture-based*: state and conversation history are hardcoded for speed and reproducibility; (b) *fully-simulated*: the entire conversation is conducted from scratch using real LLMs to test in a realistic end-to-end setting.
- **N-run probabilistic assertion** — each test runs N times and a configurable percentage must pass, accounting for LLM non-determinism.
- **Dual test types** — output contract tests (structural field presence) and LLM-as-judge tests (semantic content quality).
- **HTML reports** — a simple, non-technical HTML report is generated after each test run.

---

## 2. Directory Structure

```
tests/
  feature-testing/
    conftest.py                        # Pytest fixtures: LLM instances, CLI options, auto HTML report hook
    ft_config.py                       # N_RUNS, PASS_THRESHOLD, judge model config
    feature_testing_utils.py           # Pure helpers: build_state, run_n_times, llm_judge, simulate_conversation
    reporting/
      generate_report.py               # Generates HTML report from pytest JSON results
      output/                          # Reports written here (auto-created on each run)
    child-name-and-gender/             # Feature: system considers child's name & gender
      __init__.py
      test_output_contract.py          # Structural field-presence assertions (fixture-based)
      test_name_usage.py               # LLM judge: is the child's name used? (fixture-based + fully-simulated)
      test_gender_usage.py             # LLM judge: is language gender-appropriate? (fixture-based + fully-simulated)
    <next-feature>/
      __init__.py
      test_output_contract.py
      test_<aspect>.py
      ...
```

**Boundary with the rest of `tests/`**: The existing `tests/agentic_system/` directory contains
regression and unit tests for individual modules. `tests/feature-testing/` tests user-facing
behavioral features end-to-end, from state input to dialog output. The two directories are
complementary and independent.

> **Note on `ft_config.py`**: The config file is named `ft_config` (not `config`) to avoid
> shadowing the `agentic-system/config/` package that `nodes.py` imports from when pytest adds
> `agentic-system/` to `sys.path`.

---

## 3. Configuration (`ft_config.py`)

```python
# tests/feature-testing/ft_config.py

N_RUNS: int = 5
# How many times each probabilistic (LLM-based) test is executed per test run.
# Increase this for higher confidence at the cost of more API calls.

PASS_THRESHOLD: float = 0.80
# Fraction of N_RUNS that must pass for the test to be considered passing.
# Example: N_RUNS=5, PASS_THRESHOLD=0.80 → at least 4/5 runs must pass.

JUDGE_MODEL: str = "google_genai:gemini-2.5-flash"
# The LLM used as a judge for content-based assertions.
# Should be a capable but cost-efficient model.

JUDGE_TEMPERATURE: float = 0.0
# Keep as low as possible for consistent judging.
# 0.0 = deterministic sampling (if supported by the provider).

SYSTEM_MODEL: str = "google_genai:gemini-2.5-flash"
# The LLM used to run the dialog system under test.
# All feature tests always use the real LLM — no mocking.

SIMULATED_N_RUNS: int = 3
# Default N_RUNS for fully-simulated (Strategy B) tests.
# Lower than fixture-based tests because each run involves multiple LLM calls.
```

These values can be overridden via pytest CLI options (registered in `conftest.py`):

```bash
pytest tests/feature-testing/ --n-runs=10 --pass-threshold=0.9
```

---

## 4. Shared Utilities (`conftest.py`)

### 4a. Static State Fixture Builder

A `build_state(...)` factory that returns a fully-populated `State` TypedDict.
**All values are hardcoded** — nothing is loaded from S3, DynamoDB, or any external service.
Free-form string construction for `child_profile` is acceptable and mirrors the production format.

```python
def build_state(
    child_name: str,
    child_age: int,
    child_gender: str,          # e.g. "weiblich" | "männlich"
    messages: list,             # pre-built conversation history (see 4b)
    audio_book: str = "...",    # hardcoded default story content
    aufgaben: str = "",         # analysis result (empty = not yet analysed)
    active_beat_ids: list = [], # which beats are currently active
    story_id: str = "mia_und_leo",
    chapter_id: str = "chapter_01",
    # ... other State fields as needed
) -> State:
    """Returns a fully-populated State for use in feature tests."""
    child_profile = (
        f"Das Kind heißt {child_name}, ist {child_age} Jahre alt "
        f"und {'ein Mädchen' if child_gender == 'weiblich' else 'ein Junge'}."
    )
    ...
```

### 4b. Conversation History Fixtures

Pre-built `list[HumanMessage | AIMessage]` sequences representing known conversation states.
These are **inlined Python lists** — not loaded from files.

```python
MESSAGES_TURN_0 = []
# First ever turn — no prior conversation.

MESSAGES_TURN_1_GREETING = [
    AIMessage(content="Hallo Emma! Ich freue mich, dass du heute mit mir lernst."),
    HumanMessage(content="Hallo!"),
]
# One complete exchange: system greeted, child responded.

MESSAGES_TURN_3_MID_STORY = [
    AIMessage(content="Hallo Emma! Schön, dass du heute dabei bist."),
    HumanMessage(content="Hallo!"),
    AIMessage(content="Heute lesen wir eine Geschichte über einen Drachen..."),
    HumanMessage(content="Cool!"),
    AIMessage(content="Was denkst du, was der Drache als nächstes macht?"),
    HumanMessage(content="Er fliegt weg."),
]
# Three complete exchanges — child is mid-story.
```

### 4c. Two Testing Strategies

The framework supports two distinct strategies. Developers choose the one that fits the feature:

#### Strategy A — Fixture-Based (Fast, Reproducible)

State and conversation history are set from hardcoded fixtures. The LLM is invoked only for the
single turn under test. This is the default approach.

- ✅ Fast and cheap
- ✅ Fully reproducible input
- ✅ Good for asserting a specific behavior given a known context

#### Strategy B — Fully Simulated (Realistic, End-To-End)

No state is pre-set. The test starts from scratch and conducts the full conversation using the real
LLM until the point of interest, then makes the assertion. A `simulate_conversation(initial_config, turns)` helper drives this.

```python
def simulate_conversation(
    child_name: str,
    child_age: int,
    child_gender: str,
    n_turns: int,
    child_inputs: list[str],    # hardcoded child responses for each simulated turn
) -> State:
    """
    Runs the full dialog graph for n_turns from an empty state.
    child_inputs provides the human side of the conversation so that
    each simulation is reproducible despite using real LLMs.
    Returns the resulting state, including any fields populated
    by the background graph (e.g. aufgaben, foerderfokus).
    """
    ...
```

- ✅ Most realistic — tests the system exactly as it runs in production
- ✅ Validates the full pipeline including background graph state
- ⚠️ Slower and more expensive (multiple real LLM calls per test run)
- ⚠️ Output of earlier turns may vary; fix `child_inputs` to maximize reproducibility

> **Guidance for developers**: Use Strategy A first. Add a Strategy B test when the feature is
> known to depend on state that builds up over several turns (e.g., a feature that adapts to the
> child's answers over time).

### 4d. N-Run Helper

```python
def run_n_times(test_fn: Callable[[], tuple[bool, str]], n: int, threshold: float) -> None:
    """
    Executes test_fn n times.
    test_fn must return (passed: bool, reason: str).
    Asserts that at least ceil(threshold * n) executions return True.
    Prints per-run results on failure for debuggability.
    """
    results = [test_fn() for _ in range(n)]
    passes = sum(1 for passed, _ in results if passed)
    if passes / n < threshold:
        details = "\n".join(
            f"  Run {i+1}: {'PASS' if p else 'FAIL'} — {r}"
            for i, (p, r) in enumerate(results)
        )
        raise AssertionError(
            f"Only {passes}/{n} runs passed (required: {threshold*100:.0f}%)\n{details}"
        )
```

### 4e. LLM Judge Helper

The judge always uses the real LLM. Prompts are written in **English** for consistency and to
leverage the judge model's strongest capabilities.

```python
def llm_judge(response_text: str, criterion: str) -> tuple[bool, str]:
    """
    Calls the judge LLM with a structured prompt.
    Returns (passed: bool, reason: str).
    """
    ...
```

Judge prompt template:

```
You are a quality judge for a children's dialog system.

Evaluate the following system response against the given criterion.
Reply with ONLY "PASS" or "FAIL" on the first line, followed by a brief reason on the second line.

--- System Response ---
{response_text}

--- Criterion ---
{criterion}

--- Your Verdict (PASS or FAIL + reason) ---
```

---

## 5. Test Types

### 5a. Output Contract Tests

These verify the **presence and basic validity of required fields** in the `ResponseContract`.
They do **not** assert content quality — that is the job of LLM-as-judge tests.
Including these tests in every feature establishes a consistent pattern and gives developers
a clear starting point when output contract assertions become relevant for future features.

The `ResponseContract` model (from `backend/models/output_contract.py`) has the following fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `answer_type` | `AnswerType` enum | ✅ | `ANSWER`, `QUESTION`, `STATEMENT`, or `TASK_INSTRUCTION` |
| `spoken_text` | `str` | ✅ | The text spoken to the child (TTS-ready) |
| `task` | `Task` (optional) | — | Educational task embedded in the response, if any |
| `grounding` | `Grounding` | ✅ | Evidence and claims from the story |
| `grounding.story_id` | `str` (optional) | — | Story identifier |
| `grounding.chapter_id` | `str` (optional) | — | Chapter identifier |
| `grounding.evidence` | `list[Evidence]` | ✅ | Quotes from the story |
| `grounding.claims` | `list[Claim]` | ✅ | Claims made in the response with evidence links |
| `confidence` | `float` 0.0–1.0 (optional) | — | Model's confidence |

What to assert in contract tests:
- `response_contract` field exists in the returned state update
- `answer_type` is a valid `AnswerType` value (not `None`)
- `spoken_text` is a non-empty string
- `grounding` object is present
- All required fields are of the correct type

These tests do **not** use the N-run loop because the contract builder is deterministic Python
logic applied on top of whatever the LLM returns. A single run is sufficient.

### 5b. LLM-as-Judge Tests

These assert the **semantic content** of the response. Because the LLM is non-deterministic,
each test runs N times and a threshold of passes is required.

Pattern:
1. Build the input (via Strategy A fixture or Strategy B simulation).
2. Call the dialog system to get `spoken_text` from the response.
3. Pass `spoken_text` + a natural-language criterion in English to the judge LLM.
4. Repeat N times and assert `passes / N >= PASS_THRESHOLD`.

---

## 6. Example Feature: "Child Name & Gender Consideration"

### Feature directory: `tests/feature-testing/child-name-and-gender/`

This feature verifies that the dialog system personalizes its responses using the child's name
and uses gender-appropriate language.

---

### `test_output_contract.py`

**Purpose**: Establish that the response always has a valid, complete contract structure.
This is a foundational check, not a content check.

**Strategy**: A (fixture-based)

**Fixtures**:
```python
child_name   = "Emma"
child_age    = 6
child_gender = "weiblich"
messages     = MESSAGES_TURN_0   # first turn
```

**Test cases** (no N-run loop needed):

| Test | What is asserted |
|------|-----------------|
| `test_answer_type_is_valid` | `response_contract.answer_type` is one of the `AnswerType` enum values |
| `test_spoken_text_is_non_empty` | `response_contract.spoken_text` is a non-empty string |
| `test_grounding_object_present` | `response_contract.grounding` is not `None` |
| `test_no_required_fields_are_none` | `answer_type` and `spoken_text` are both set (not `None`) |

---

### `test_name_usage.py`

**Purpose**: Verify that the system addresses the child by their name.

**Fixtures** (Strategy A):

| Fixture | Values |
|---------|--------|
| `state_emma_turn0` | `child_name="Emma"`, `child_gender="weiblich"`, `child_age=6`, `messages=MESSAGES_TURN_0` |
| `state_luca_turn0` | `child_name="Luca"`, `child_gender="männlich"`, `child_age=7`, `messages=MESSAGES_TURN_0` |
| `state_emma_turn3` | `child_name="Emma"`, `child_gender="weiblich"`, `child_age=6`, `messages=MESSAGES_TURN_3_MID_STORY` |

**Strategy A test cases** (`N_RUNS=5`, `PASS_THRESHOLD=0.80`):

| Test | Fixture | Criterion (English) |
|------|---------|---------------------|
| `test_name_used_female_child` | `state_emma_turn0` | `"Does the response address or mention the child by the name 'Emma'?"` |
| `test_name_used_male_child` | `state_luca_turn0` | `"Does the response address or mention the child by the name 'Luca'?"` |
| `test_name_used_mid_conversation` | `state_emma_turn3` | `"Is the name 'Emma' used at least once in the response?"` |

**Strategy B test cases** (fully simulated, `N_RUNS=3`, `PASS_THRESHOLD=0.80`):

| Test | Setup | Criterion (English) |
|------|-------|---------------------|
| `test_name_used_simulated_female` | Full conversation simulated for Emma (3 turns, fixed child inputs) | `"Does the response address or mention the child by the name 'Emma'?"` |
| `test_name_used_simulated_male` | Full conversation simulated for Jonas (3 turns, fixed child inputs) | `"Does the response address or mention the child by the name 'Jonas'?"` |

> Strategy B tests use a lower `N_RUNS` value because each run involves multiple LLM calls.
> Developers may tune this per test.

---

### `test_gender_usage.py`

**Purpose**: Verify that the language is gender-appropriate for the child.

**Fixtures** (Strategy A):

| Fixture | Values |
|---------|--------|
| `state_emma_turn0` | `child_name="Emma"`, `child_gender="weiblich"`, `child_age=6`, `messages=MESSAGES_TURN_0` |
| `state_jonas_turn0` | `child_name="Jonas"`, `child_gender="männlich"`, `child_age=7`, `messages=MESSAGES_TURN_0` |
| `state_emma_turn3` | `child_name="Emma"`, `child_gender="weiblich"`, `child_age=6`, `messages=MESSAGES_TURN_3_MID_STORY` |

**Strategy A test cases** (`N_RUNS=5`, `PASS_THRESHOLD=0.80`):

| Test | Fixture | Criterion (English) |
|------|---------|---------------------|
| `test_gender_appropriate_female` | `state_emma_turn0` | `"Is the language in the response appropriate for a girl, using correct German grammatical gender agreement and no masculine-specific phrasing?"` |
| `test_gender_appropriate_male` | `state_jonas_turn0` | `"Is the language in the response appropriate for a boy, using correct German grammatical gender agreement and no feminine-specific phrasing?"` |
| `test_gender_consistent_mid_story` | `state_emma_turn3` | `"Is the language consistently gender-appropriate for a girl throughout the response, with no gender inconsistencies?"` |

**Strategy B test cases** (fully simulated, `N_RUNS=3`, `PASS_THRESHOLD=0.80`):

| Test | Setup | Criterion (English) |
|------|-------|---------------------|
| `test_gender_simulated_female` | Full conversation simulated for Emma (3 turns, fixed child inputs) | `"Is the language in the response consistently appropriate for a girl throughout the entire conversation?"` |
| `test_gender_simulated_male` | Full conversation simulated for Jonas (3 turns, fixed child inputs) | `"Is the language in the response consistently appropriate for a boy throughout the entire conversation?"` |

---

## 7. CI Integration & Triggering

Feature tests always use real LLMs and are therefore **not** run on every commit.
The triggering rules are:

| Event | What runs |
|-------|-----------|
| **Pull Request / pre-merge** | Triggered **manually** by the developer before merging a feature branch into `main`. This is a required gate — no merge without a passing feature test run. |
| **Merge into `main`** | Triggered **automatically** after the merge completes. Serves as a post-merge regression check. |
| **On-demand** | Any developer can trigger a run manually at any time via the CI UI or the commands below. |

Pytest markers used for CI configuration:

| Marker | Meaning |
|--------|---------|
| `@pytest.mark.llm_feature` | Test calls the real LLM system under test (slow, costly) |
| `@pytest.mark.llm_judge` | Test uses the LLM judge for evaluation |
| `@pytest.mark.contract` | Output contract / structural test (fast, deterministic) |
| `@pytest.mark.simulated` | Strategy B test (full conversation simulation — slowest) |

---

## 8. Running Tests

```bash
# Run all feature tests (real LLM, generates HTML report)
pytest tests/feature-testing/ -v --html-report

# Run a single feature
pytest tests/feature-testing/child-name-and-gender/ -v

# Run only output contract tests across all features (fast)
pytest tests/feature-testing/ -m contract -v

# Run only fixture-based LLM tests (no full simulations)
pytest tests/feature-testing/ -m "llm_feature and not simulated" -v

# Run only fully-simulated tests
pytest tests/feature-testing/ -m simulated -v

# Override N_RUNS and PASS_THRESHOLD for a stricter run
pytest tests/feature-testing/ --n-runs=10 --pass-threshold=0.9
```

**Terminal failure output example**:
```
FAILED test_name_used_female_child — Only 2/5 runs passed (required: 80%)
  Run 1: FAIL — Response does not contain the name 'Emma'.
  Run 2: PASS
  Run 3: FAIL — The name 'Emma' is absent from the response.
  Run 4: PASS
  Run 5: FAIL — No personalization detected.
```

---

## 9. HTML Report

After each test run, an HTML report is generated in `tests/feature-testing/reporting/output/`.
The report is designed to be readable by non-technical stakeholders.

### Report structure

```
Feature Test Report — Child Name & Gender Consideration
Run date: 2026-02-23   Model: gemini-2.5-flash   N_RUNS: 5   Pass threshold: 80%

┌─────────────────────────────────────────────────────────────┐
│ Overall Result:  ✅ PASSED  (12/14 tests passed)            │
└─────────────────────────────────────────────────────────────┘

Feature: Child Name & Gender Consideration
  ✅ Output Contract — All required fields present
  ✅ Name Usage — Female child (Emma) [5/5 runs passed]
  ✅ Name Usage — Male child (Luca)   [4/5 runs passed]
  ❌ Name Usage — Mid-conversation    [3/5 runs passed — below 80%]
     Run 1: FAIL — The name 'Emma' was not found in the response.
     Run 3: FAIL — Response was generic with no personalization.
  ✅ Gender — Appropriate for girl (Emma)  [5/5 runs passed]
  ...
```

### Key design principles for the report
- **Plain language**: No technical jargon. "The system said the child's name" instead of "name personalization criterion passed".
- **Pass/Fail at a glance**: Large ✅ / ❌ icons for each test group.
- **Drill-down**: Each failed test shows the per-run judge verdicts and reasons.
- **Summary row**: Total passed/failed at the top.
- **No setup details in the main view**: Fixtures and configs are collapsed into an "Advanced details" section.

---

## 10. Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Feature directory | `kebab-case` | `child-name-and-gender/` |
| Test file | `test_<aspect>.py` | `test_name_usage.py` |
| Test function (Strategy A) | `test_<what>_<scenario>` | `test_name_used_female_child` |
| Test function (Strategy B) | `test_<what>_simulated_<scenario>` | `test_name_used_simulated_female` |
| Fixture | `snake_case`, descriptive | `state_emma_turn0` |
| Conversation history constant | `MESSAGES_TURN_<N>_<CONTEXT>` | `MESSAGES_TURN_3_MID_STORY` |
| Judge criterion constant | `CRITERION_<ASPECT>_<SCENARIO>` | `CRITERION_NAME_USED_FEMALE` |
| Judge prompt template constant | `JUDGE_PROMPT_<ASPECT>` | `JUDGE_PROMPT_NAME_USAGE` |

