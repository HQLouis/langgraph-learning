You are running an automated test stabilization loop for the Lingolino dialog system. Your goal is to make ALL feature tests pass **3 consecutive full-suite runs** with zero failures.

## Goal

Iterate in cycles: run tests → analyze failures → fix (prompts or code) → re-run, until the full test suite passes 3 times in a row. This command builds on `/iterate-prompts` but adds persistence and cycle tracking.

## Context Files

- **Prompts**: `agentic-system/local_fallback_prompts.py`
- **Master node**: `agentic-system/nodes.py` (masterChatbot, detection nudges)
- **Change log**: `dialogue-system-engineering/change_log.md`
- **Architectural improvements**: `dialogue-system-engineering/architectural-improvements.md`
- **Test config**: `tests/feature-testing/ft_config.py`

## Cycle Protocol

### Step 1 — Run full Strategy A suite

```bash
pytest tests/feature-testing/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short 2>&1 | tail -80
```

Record the result: total passed, total failed, which tests failed.

### Step 2 — Check completion condition

If **all tests passed**: increment the consecutive-pass counter.
- If consecutive passes = 3 → **DONE**. Report final results and stop.
- If consecutive passes < 3 → go to Step 1 (run again without changes to confirm stability).

If **any test failed**: reset consecutive-pass counter to 0, go to Step 3.

### Step 3 — Analyze failures

For each failing test:
1. Read the test file to understand the expected behavior and judge criterion.
2. Read the last system response that caused the failure (from test output).
3. Categorize the failure:
   - **Prompt gap**: Missing or conflicting rule in `local_fallback_prompts.py`
   - **Detection gap**: Needs a coded nudge in `nodes.py` (pattern: `_detect_<condition>`)
   - **Judge issue**: Judge criterion is too strict or ambiguous (DO NOT fix — document for user)
   - **LLM flake**: Response is borderline, passes sometimes (may need no change — just re-run)

Group failures by root cause. Prioritize by impact (how many tests share the same root cause).

### Step 4 — Apply ONE fix

Make exactly ONE logical change. Follow `/iterate-prompts` rules:
- No overfitting to specific stories or test inputs
- Keep prompt rules general-purpose
- Prefer coded detection nudges over prompt rules when the LLM ignores prompt text

### Step 5 — Targeted re-run

Run ONLY the affected feature group:
```bash
pytest tests/feature-testing/<affected-feature>/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short
```

- If it passes → go to Step 1 (full suite) to check regressions.
- If it still fails → analyze why, try a different approach or revert.

### Step 6 — Document

Append to `dialogue-system-engineering/change_log.md`:
- Cycle number
- What changed and why
- Targeted test result
- Full suite result (after Step 1)
- Consecutive pass count

Then go back to Step 1.

## Cycle Tracking

Maintain a cycle tracker as a task list. Use TaskCreate at the start to create a tracking task, and TaskUpdate after each cycle to record:
- Cycle N: X passed, Y failed, consecutive passes: Z/3
- Failures: [list of failing test names]
- Fix applied: [description]

## Rules

1. **Maximum 10 cycles** per invocation. If not stable after 10 cycles, stop and report what's still failing.
2. **Never modify test files**. Tests define expected behavior.
3. **Revert on regression**. If a change breaks more tests than it fixes, `git checkout` the changed file immediately.
4. **LLM flakes**: If a test passes 2/3 runs consistently but fails 1/3, it's flaky. After 2 cycles of the same flake with no prompt fix available, note it as a known flake and move on. Don't burn cycles on inherent LLM variance.
5. **Judge issues**: If a test fails because the judge is wrong (system response looks correct but judge says FAIL), document it for the user. Do NOT change judge criteria without asking.
6. **Strategy B last**: Only run Strategy B (`-m simulated`) after achieving 3 consecutive Strategy A passes, as a final validation. Strategy B failures do NOT reset the consecutive-pass counter.
7. **Temperature**: Verify `SYSTEM_TEMPERATURE` in `ft_config.py` is 0.0 before starting.

## Escalation

If after 5 cycles the same test keeps failing and prompt changes don't help:
1. Check if it's a coded detection issue (needs a new `_detect_*` nudge in `nodes.py`)
2. Check if it's an architectural issue (document in `architectural-improvements.md`)
3. Ask the user before making architectural changes

## Reporting

After completion (3 consecutive passes or 10-cycle limit), provide:
- Total cycles run
- Final pass/fail state
- Changes made (with cycle numbers)
- Known flakes (if any)
- Recommendations for remaining failures (if any)

## Test Run Commands

```bash
# Full Strategy A suite (primary iteration loop)
pytest tests/feature-testing/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short

# Single feature (targeted after fix)
pytest tests/feature-testing/<feature>/ -m "llm_feature and not simulated" --n-runs=3 --pass-threshold=0.66 -v --tb=short

# Final validation with Strategy B
pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short

# With HTML report (final run)
pytest tests/feature-testing/ -m llm_feature --n-runs=3 --pass-threshold=0.66 -v --tb=short --json-report --json-report-file=.feature_test_report.json
```