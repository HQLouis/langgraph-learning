You are guiding the iterative prompt engineering process for the Lingolino dialog system.

## Goal

Adjust prompts in `agentic-system/local_fallback_prompts.py` to make the dialog system pass as many feature tests as possible, without overfitting to specific test scenarios. Prompts must remain general-purpose and flexible.

## Context Files

- **Architecture**: `dialogue-system-engineering/architecture.md`
- **Change log**: `dialogue-system-engineering/change_log.md` — append every change here
- **Architectural improvements**: `dialogue-system-engineering/architectural-improvements.md` — for changes beyond prompt engineering
- **Prompts**: `agentic-system/local_fallback_prompts.py`
- **Master node**: `agentic-system/nodes.py` (masterChatbot function)
- **Test config**: `tests/feature-testing/ft_config.py`

## Process

### Phase 1 — Baseline (skip if baseline already exists in change_log.md)

1. Run the full test suite to establish current pass/fail state:
   ```
   pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short 2>&1 | tail -60
   ```
2. Record results in `dialogue-system-engineering/change_log.md` as the baseline entry.

### Phase 2 — Analysis

3. Read failing test files to understand what behavior is expected.
4. Read the current prompts and identify what's missing or conflicting.
5. Group failing tests by root cause (e.g., "missing transition rule", "sentence variety not addressed").

### Phase 3 — Targeted Prompt Change

6. Make ONE focused change to `local_fallback_prompts.py`. Keep it general — add rules that improve dialog quality broadly, not rules that match specific test inputs.
7. Run ONLY the affected test group first (fast feedback):
   ```
   pytest tests/feature-testing/<affected-feature>/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short
   ```
8. If the targeted tests improve, run the FULL suite to check for regressions:
   ```
   pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short 2>&1 | tail -60
   ```

### Phase 4 — Document

9. Append the change to `dialogue-system-engineering/change_log.md` with:
   - What changed and why
   - Test results before and after
   - Any regressions

### Phase 5 — Iterate or Escalate

10. If tests improved with no regressions → go back to Phase 2 for next failing group.
11. If prompt changes cause regressions that can't be resolved → revert and try a different approach.
12. If prompt engineering hits fundamental limits → document in `architectural-improvements.md` and **STOP**. Ask the user for human review before implementing architectural changes.

## Rules

- **Strategy A first**: Only run Strategy A tests (`-m "llm_feature and not simulated"`) during iteration. Run Strategy B only for final validation.
- **No overfitting**: Never add prompt rules that reference specific stories, character names, or test scenarios. Rules must be general conversation principles.
- **One change at a time**: Make one logical change per iteration so you can measure its impact cleanly.
- **Revert on regression**: If a change breaks more tests than it fixes, revert it immediately.
- **Temperature**: Ensure `SYSTEM_TEMPERATURE` in `ft_config.py` is set to 0.0 for deterministic testing.
- **Background workers**: Currently all empty. If you need to activate them, document it as an architectural improvement and ask for review.
- **Never modify test files**: Tests define the expected behavior. Only modify prompts and system code.

## Learnings — When Prompts Are Not Enough

Through iterative testing, we've identified patterns where prompt engineering reaches its limits and programmatic mechanisms are needed instead.

### Rule Conflicts Require Programmatic Resolution

When prompt rules conflict (e.g., REGEL 7 "ask verification after correction" vs REGEL 8 "don't ask questions at story end"), the LLM inconsistently chooses which rule to follow. **Solution**: Use coded detection nudges in `nodes.py` that fire as late SystemMessages, explicitly stating which rules are overridden. These are more reliable than relying on the LLM to resolve conflicts from the prompt alone.

### Story-End Detection Needs the Beat System

Generic keyword-based story-end detection (e.g., "eingeschlafen", "kichern") only works for known story endings. For a story-agnostic system, the **beat system** should be used to detect when the conversation has reached the final beats of any story. Do NOT add story-specific keywords to `_detect_story_end` in `nodes.py`.

### Simulated Tests Are Inherently More Variable

Strategy B (simulated) tests generate the full conversation from scratch. Even with temp=0, the conversation context diverges from fixture-based scripts, leading to different LLM behavior. If a fixture-based test passes consistently but its simulated counterpart fails:
1. First check if the LLM response is genuinely wrong or if the judge is being overly strict
2. If the LLM behavior is borderline, the issue is likely the LLM's generation quality, not the prompt
3. Programmatic nudges (coded detection + late SystemMessage injection) can help but may not fully resolve it

### Coded Detection Nudges Are More Reliable Than Prompt Rules Alone

For behavioral requirements that the LLM violates despite clear prompt rules, adding a coded detection function in `nodes.py` (pattern: `_detect_<condition>`) that injects a targeted SystemMessage AFTER the conversation is more effective than strengthening prompt text. Examples:
- `_detect_repetitive_starters`: Catches repeated sentence openings
- `_detect_repeated_disengagement`: Catches child fatigue signals
- `_detect_story_end`: Catches story ending markers
- `_detect_missing_transition_recap`: Ensures smooth transitions in long conversations

Each nudge should be **explicit and directive** (say exactly what to do: "Verabschiede dich SOFORT") rather than referencing rule numbers ("Befolge REGEL 4B").

### LLM Grammar Errors Need Post-Processing, Not Just Prompts

Grammar errors like wrong verb conjugation ("suchst er" → "sucht er") are generation defects, not knowledge gaps. Adding grammar hints to the prompt helps but doesn't eliminate the issue. A regex-based post-processing step (`german_grammar_postprocess.py`) applied before the output contract catches known patterns reliably at <1ms cost.

## Test Run Shortcuts

```bash
# Full suite, Strategy A only (fast iteration)
pytest tests/feature-testing/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short

# Single feature suite
pytest tests/feature-testing/<feature-name>/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short

# Full suite including Strategy B (final validation)
pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short

# With HTML report
pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short --json-report --json-report-file=.feature_test_report.json
```