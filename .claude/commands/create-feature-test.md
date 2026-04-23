You are guiding the user through creating a new feature test for the Lingolino dialog system.

## Inputs

- **Feature name**: $ARGUMENTS
- **Description**: $ARGUMENTS

The description should contain:
1. What feature/behavior is being tested
2. Example conversation scenarios (child inputs, expected system behavior)
3. How to assess the system response (LLM judge criteria)

## Your Task

Based on the two inputs, generate a complete feature test file. Follow the established patterns exactly.

### Step 1 — Parse the description

Extract from the description:
- **Feature under test**: What dialog behavior is being validated?
- **Test cases**: Each distinct scenario to test (e.g. different child profiles, conversation stages, edge cases)
- **Judge criteria**: The English-language criterion strings that the LLM judge will use to evaluate system responses. Each criterion must end with: `Return PASS if <condition>, FAIL if <condition>.`
- **Strategy A tests** (fixture-based): Which tests use pre-built state with `build_state()` + `masterChatbot()`?
- **Strategy B tests** (simulated): Which tests need full multi-turn simulation with `simulate_conversation()`?

If the description is ambiguous or missing any of the above, **ask the user to clarify** before generating code.

### Step 2 — Create the test folder and file

Create the file at:
```
tests/feature-testing/<feature-name>/test_<feature_name_underscored>.py
```

where `<feature-name>` is the kebab-case feature name from the first input.

### Step 3 — Generate the test file

Follow this exact structure (reference: `tests/feature-testing/child-name-and-gender/test_gender_usage.py`):

```python
"""
Feature: <Feature Name>
Test file: <Short description>

Two strategies are tested:
  Strategy A — fixture-based (fast, reproducible)
  Strategy B — fully simulated (realistic, end-to-end)

Markers:
  llm_feature   — all tests here (real LLM involved)
  llm_judge     — LLM judge is called
  simulated     — Strategy B tests only
"""

import pytest
from langchain_core.messages import HumanMessage

from feature_testing_utils import (
    build_state,
    llm_judge,
    simulate_conversation,
    state_to_setting,
    simulation_to_setting,
    # Import conversation fixtures as needed:
    # MESSAGES_TURN_0, MESSAGES_TURN_1_GREETING, MESSAGES_TURN_3_MID_STORY,
)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ft_config as _cfg

# ---------------------------------------------------------------------------
# Judge criteria (English)
# ---------------------------------------------------------------------------

CRITERION_XXX = (
    "..."
    "Return PASS if ..., FAIL if ..."
)

# ---------------------------------------------------------------------------
# Hardcoded child inputs for Strategy B simulations
# ---------------------------------------------------------------------------

SIMULATED_CHILD_INPUTS_N_TURNS = [
    "child utterance 1",
    "pre-defined system response 1",
    "child utterance 2",
    "pre-defined system response 2",
    "child utterance 3",  # last element is always a child utterance
]

# ---------------------------------------------------------------------------
# Strategy A — fixture-based tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
class TestXxxFixtureBased:
    """Strategy A: ..."""

    def test_xxx(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder):
        """..."""
        state = build_state(
            child_name="Emma",
            child_age=6,
            child_gender="weiblich",
            messages=[HumanMessage(content="...")],
        )

        def _run() -> tuple[bool, str, str]:
            from nodes import masterChatbot
            result = masterChatbot(state, system_llm)
            spoken_text = result["messages"][-1].content
            return llm_judge(judge_llm, spoken_text, CRITERION_XXX)

        run_details_recorder(_run, n_runs, pass_threshold,
                             setting=state_to_setting(state, CRITERION_XXX))

# ---------------------------------------------------------------------------
# Strategy B — fully-simulated tests
# ---------------------------------------------------------------------------

@pytest.mark.llm_feature
@pytest.mark.llm_judge
@pytest.mark.simulated
class TestXxxSimulated:
    """Strategy B: ..."""

    def test_xxx_simulated(self, system_llm, judge_llm, pass_threshold, run_details_recorder):
        """..."""
        n = _cfg.SIMULATED_N_RUNS

        def _run() -> tuple:
            final_state, spoken_text = simulate_conversation(
                system_llm_instance=system_llm,
                child_name="Emma",
                child_age=6,
                child_gender="weiblich",
                child_inputs=SIMULATED_CHILD_INPUTS_N_TURNS,
            )
            passed, resp, reason = llm_judge(judge_llm, spoken_text, CRITERION_XXX)
            from langchain_core.messages import HumanMessage as _HM
            conversation = [
                {"role": "Child" if isinstance(m, _HM) else "System", "content": m.content}
                for m in final_state.get("messages", [])
            ]
            return passed, resp, reason, conversation

        run_details_recorder(_run, n, pass_threshold,
                             setting=simulation_to_setting("Emma", 6, "weiblich",
                                                           SIMULATED_CHILD_INPUTS_N_TURNS,
                                                           CRITERION_XXX))
```

### Rules

1. **Judge criteria** must be in English, specific, and end with explicit PASS/FAIL conditions.
2. **Strategy A tests** use `build_state()` → `masterChatbot()` → `llm_judge()`. The fixture signature is always: `(self, system_llm, judge_llm, n_runs, pass_threshold, run_details_recorder)`.
3. **Strategy B tests** use `simulate_conversation()` → `llm_judge()`. The fixture signature is: `(self, system_llm, judge_llm, pass_threshold, run_details_recorder)` — note: no `n_runs`, uses `_cfg.SIMULATED_N_RUNS` instead.
4. **`simulate_conversation` child_inputs** must have odd length (alternating child/system, ending with child utterance). The system responds live only to the last child utterance.
5. **Conversation fixtures**: Use `MESSAGES_TURN_0`, `MESSAGES_TURN_1_GREETING`, or `MESSAGES_TURN_3_MID_STORY` from `feature_testing_utils` for Strategy A mid-conversation tests.
6. **Setting metadata**: Always pass `setting=state_to_setting(...)` (Strategy A) or `setting=simulation_to_setting(...)` (Strategy B) to `run_details_recorder` for HTML report rendering.
7. **Only include Strategy B tests if the description explicitly mentions multi-turn simulation scenarios.** If the description only describes single-turn checks, only generate Strategy A tests.
8. **Child profiles**: Use realistic German names and ages 3-12. Use `"weiblich"` / `"männlich"` for gender.
9. **Keep it minimal**: Only generate the tests described. Do not add extra tests beyond what the description specifies.

### Step 4 — Summary

After creating the file, print:
- The file path created
- A list of all test cases with their names and what they verify
- The command to run the tests: `pytest tests/feature-testing/<feature-name>/ -m llm_feature -v`