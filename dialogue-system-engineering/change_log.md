# Dialog System Change Log

Every prompt change and its measured impact on test results is documented here.

## Format

```
### [DATE] Change Title

**What changed**: Description of the change
**File(s) modified**: Which files were edited
**Motivation**: Why this change was made (which tests were failing)
**Test results before**: Pass/fail counts
**Test results after**: Pass/fail counts
**Regressions**: Any previously-passing tests that now fail
```

---

## Changes

### [2026-03-09] BASELINE — Strategy A, n_runs=3, threshold=66%

**System temperature**: 0.0 (newly set for deterministic testing)
**Total**: 21 passed, 7 failed (75% pass rate)

**PASSED (21):**
- child-name-and-gender: all 4 tests (name greeting + gender usage)
- ensure-clarity: all 7 tests
- explanation-correction-verification: all 4 tests
- answers-have-sufficient-context: 1/3 (topic_transition_context)
- different-sentence-starters: 1/3 (mid_conversation)
- responding-to-answer: 1/3 (disengage_acknowledge_transition)
- transition-between-tasks: 2/3 (wait_for_answer, content_recap)

**FAILED (7):**
1. `answers-have-sufficient-context::test_clarity_after_confusion` — No context about Carl when transitioning
2. `answers-have-sufficient-context::test_character_transition_has_context` — No context about Carl
3. `different-sentence-starters::test_varied_starters_short_conversation` — Always starts with "Ja,"
4. `different-sentence-starters::test_varied_starters_long_conversation` — Always starts with "Du sagst"
5. `responding-to-answer::test_emotion_engagement_after_correct_answer` — Jumps to farewell instead of exploring emotion
6. `responding-to-answer::test_memory_hint_after_forgetting` — Asks disambiguation instead of giving hint (conflict with REGEL 1C "vergessen")
7. `transition-between-tasks::test_smooth_scene_linking` — Abrupt topic jump without bridging

**Root cause analysis:**
- Tests 1-2: No rule for providing context/recap when introducing new characters or topics
- Tests 3-4: No rule for varying sentence starters
- Test 5: REGEL 5 exists but seems overridden by conversation termination (high message count triggers farewell)
- Test 6: REGEL 1C (vergessen disambiguation) fires but the test expects a memory hint instead — possible conflict
- Test 7: No rule for smooth scene transitions with bridging language

---

### [2026-03-09] Iteration 1+2+3 — Added REGEL 5 (starters), REGEL 6 (transitions), refined REGEL 1C, 2, 4

**What changed**:
1. REGEL 1C ("vergessen"): Now context-dependent — if it's clear the child forgot, treat as "weiß nicht" with empathy + hint, only disambiguate when truly ambiguous.
2. REGEL 2 ("weiß nicht"): Added SONDERFALL for complete confusion — must re-establish context first (story, characters, what's happening) before asking a new question.
3. REGEL 4 (ablenkungen): Added Fall B for repeated disengagement — when child says "nein"/"weiß nicht" multiple times, MUST switch to completely different activity, not another comprehension question.
4. NEW REGEL 5: Abwechslungsreiche Satzanfänge — explicitly forbids repeating "Ja,"/"Du sagst"/"Du hast gesagt" patterns, requires checking last 3 responses before answering.
5. NEW REGEL 6: Sanfte Übergänge — requires bridging language between scenes and explicit character introduction when new figures appear.
6. Updated ABSCHLUSS-CHECKLISTE to include new checks.

**Files modified**: `agentic-system/local_fallback_prompts.py`

**Motivation**: 7 failing tests from baseline

**Test results before (baseline)**: 21 passed, 7 failed
**Test results after**: 26 passed, 2 failed

**Improvements** (+5 tests fixed):
- `answers-have-sufficient-context::test_clarity_after_confusion` — FIXED (context re-establishment)
- `answers-have-sufficient-context::test_character_transition_has_context` — FIXED (Carl introduction)
- `different-sentence-starters::test_varied_starters_short_conversation` — FIXED (variety rule)
- `responding-to-answer::test_memory_hint_after_forgetting` — FIXED (vergessen as memory hint)
- `transition-between-tasks::test_smooth_scene_linking` — FIXED (scene bridging)
- `responding-to-answer::test_disengage_acknowledge_transition` — initial REGRESSION, then FIXED with stronger disengagement rule

**Still failing (2)**:
1. `different-sentence-starters::test_varied_starters_long_conversation` — Model at temp 0.0 with 41 messages of "Du sagst" history still continues the pattern despite rules. The in-context examples overwhelm the instruction.
2. `responding-to-answer::test_emotion_engagement_after_correct_answer` — ARCHITECTURAL ISSUE: conversation has 45 messages (message_count=22), triggering hard termination which strips ALL rules including REGEL 7 (emotions). See architectural-improvements.md.

**Regressions**: None

---

### [2026-03-09] Architectural Improvements — Always-active master prompt + repetitive starter detection

**What changed**:
1. **Master prompt always active** (`nodes.py`): Removed the conditional `getMasterPrompt() if not is_conversation_ended(message_count) else ''`. The master prompt (all 7 REGELn) now persists through all conversation phases including hard termination. Termination guidance is layered on top via a separate SystemMessage.
2. **Repetitive starter detection** (`nodes.py`): New `_detect_repetitive_starters()` function scans the last 5 AI messages. If ≥60% start with the same word, a SystemMessage nudge is injected at the end of the message list (maximum recency weight) telling the LLM to use a different opener.
3. **Hard termination prompt rewritten** (`conversation_termination_policy.py`): Now instructs the system to acknowledge the child's last answer FIRST, then transition to goodbye. Removes the old "Stelle keine Fragen!" which conflicted with acknowledging answers.

**Files modified**: `agentic-system/nodes.py`, `agentic-system/config/conversation_termination_policy.py`

**Motivation**: 2 remaining test failures from prompt engineering iteration — both architectural issues documented in `architectural-improvements.md`

**Test results before**: 26 passed (Strategy A only), 2 failed
**Test results after (full suite incl. Strategy B)**: 54 passed, 1 failed (98% pass rate)

**Improvements** (+2 previously-failing tests fixed):
- `different-sentence-starters::test_varied_starters_long_conversation` — FIXED (starter detection nudge)
- `responding-to-answer::test_emotion_engagement_after_correct_answer` — FIXED (master prompt persists through termination)

**Still failing (1)**:
1. `responding-to-answer::test_disengage_acknowledge_transition_simulated` — Strategy B (simulated) only. The fixture-based (Strategy A) version passes. The simulated conversation generates different context each run, and the system sometimes asks a follow-up question after acknowledging disengagement. This is inherent non-determinism in Strategy B with n_runs=1.

**Regressions**: None
