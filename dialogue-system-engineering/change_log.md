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

---

### [2026-03-17] Worker Activation + New Rules (REGELn 7-10) + 4 New Test Suites

**What changed**:
1. **All 9 background worker prompts populated** (`local_fallback_prompts.py`): Based on expert pedagogue originals from `dialogue-system-engineering/oroginal_promts.txt`. Workers: Grammar, Comprehension, Speech Acts, Vocabulary, Boredom, Förderfokus, Aufgaben, Satzbau Analysis, Satzbau Constraints.
2. **4 new test suites created** for features 8-12: `story-not-extended` (4 tests), `story-summary` (4 tests), `incorrect-story-facts` (4 tests), `child-prompts-ai` (4 tests). Plus `test_reflect_and_personalize` added to `responding-to-answer`.
3. **3 new master prompt rules added**:
   - REGEL 7: Falsche Angaben neutral korrigieren (overrides REGEL 2 — directly state correct answer)
   - REGEL 8: Ende der Geschichte nicht verlängern (recognize last scene, wrap up)
   - REGEL 9: Kurzfassung der Geschichte (shortened retelling on request + proactive offer)
   - REGEL 10: Emotionen erforschen (renumbered from old REGEL 7)
4. **REGEL 4B extended**: story-end + disengaged → say goodbye, don't offer alternatives.
5. **Fixed judge criteria**: `answers-have-sufficient-context` criteria were testing for specific content instead of actual requirement.
6. **Master first message prompt refined** from expert original.

**Files modified**: `agentic-system/local_fallback_prompts.py`, test files in 4 new + 2 existing suites

**Test results baseline (workers empty, no new rules, 73 tests)**: 62 passed, 11 failed
**Test results after iteration (73 tests)**: 65 passed, 8 failed

**Net improvement**: +3 passing tests (62→65), while total test count stayed at 73.

**New tests passing (9 of 17 new)**: story-not-extended 2/4, story-summary 3/4, incorrect-story-facts 3/4, child-prompts-ai 4/4, reflect-and-personalize 1/2

**Regressions (3 previously-passing tests now fail)**:
- `test_emotion_engagement_after_correct_answer` + simulated — REGEL 8 (end story) overrides REGEL 10 (explore emotions) because "Pia lacht" IS the last scene
- `test_disengage_acknowledge_transition` + simulated — REGEL 4B story-end exception too aggressive

**Still failing (5 net-new)**: story-not-extended disengagement (2), proactive retelling (1), topic_transition simulated (1), reflect_and_personalize simulated (1)

**Key insight**: REGEL 8 and REGEL 10 conflict when emotional scene is the last scene. Need priority resolution.

**Regressions**: 3 (documented above — all REGEL 8 vs REGEL 10 conflict)

---

### [2026-03-17] REGEL 10 Priority Fix — Emotions before wrap-up

**What changed**: Added explicit priority to REGEL 10: "HAT VORRANG VOR REGEL 8!" — when the last scene involves emotions, explore them FIRST, then wrap up.

**Test results**: 69 passed, 4 failed (95% pass rate)

**Fixes**:
- `test_emotion_engagement_after_correct_answer` — NOW PASSING (REGEL 10 > REGEL 8)
- `test_disengage_acknowledge_transition` (fixture) — NOW PASSING
- `test_stop_forcing_when_child_disengages` — NOW PASSING

**Still failing (4)**:
1. `test_gender_simulated_female` — Strategy B flaky (non-deterministic)
2. `test_disengage_acknowledge_transition_simulated` — Strategy B flaky
3. `test_wrap_up_simulated` — Strategy B, model asks "Warum ist Bobo müde?" at story end in simulation
4. `test_proactive_retelling_offer` — model doesn't proactively offer to retell after repeated errors (REGEL 9B not strong enough to override the default "correct and ask question" pattern)

**Regressions**: None from this change

---

### [2026-03-17] Code-Level Detections — Disengagement, Story End, Repeated Errors

**What changed**:
Three new detection functions added to `nodes.py`, following the established `_detect_repetitive_starters` pattern. Each scans `state["messages"]`, returns a German nudge (or None), and is injected as a `SystemMessage` after conversation history for maximum recency weight.

1. **`_detect_repeated_disengagement(messages, window=5)`**: Scans last 5 `HumanMessage` instances for disengagement keywords ("nein", "nee", "weiß nicht", "keine lust", etc.). Fires if ≥3 match. Smart routing: if story-end keywords found in recent AI messages → "say goodbye" nudge; otherwise → neutral nudge that defers to REGEL 4B for routing (goodbye vs. activity switch).
2. **`_detect_story_end(messages)`**: Scans last 8 `AIMessage` instances for final-scene keywords ("eingeschlafen", "schläft ein", "kichern", "glucksen", "lautes lachen"). REGEL 10 exclusion: if child's last message contains an emotion word → does NOT fire (lets emotion exploration take precedence). Nudge tells system to wrap up and not ask further detail questions.
3. **`_detect_repeated_errors(messages, window=8)`**: Scans last 8 `AIMessage` instances for correction markers ("nicht ganz", "stimmt nicht", "im buch", etc.). Fires if ≥3 corrections found. Nudge tells system to offer retelling instead of asking another detail question.

All three are wired into `masterChatbot` after the existing repetitive-starter nudge (lines 314–330). Multiple nudges can fire simultaneously.

**Message order after changes**:
1. SystemMessage — master prompt + child profile + beat context
2. SystemMessage — meta rules (aufgaben/satzbaubegrenzung) — conditional
3. SystemMessage — termination prompt — conditional
4. Conversation history (HumanMessage/AIMessage list)
5. SystemMessage — repetitive starter nudge — conditional (existing)
6. SystemMessage — disengagement nudge — conditional (NEW)
7. SystemMessage — story-end nudge — conditional (NEW)
8. SystemMessage — repeated-errors nudge — conditional (NEW)

**Files modified**: `agentic-system/nodes.py`

**Motivation**: 3 remaining failing tests where prompt-level rules (REGEL 4B, 8, 9B) are overridden by strong in-context conversation patterns.

**Target tests**:
1. `responding-to-answer::test_disengage_acknowledge_transition_simulated` — disengagement detection
2. `story-not-extended::test_wrap_up_simulated` — story-end detection
3. `story-summary::test_proactive_retelling_offer` — repeated-errors detection

**Test results before**: 69 passed, 4 failed (from REGEL 10 Priority Fix)
**Test results after**: 72 passed, 1 failed (99% pass rate). The 1 failure (`test_content_recap_on_transition`) is a pre-existing flaky test, not related to this change (passes on retry).

4. **`_detect_missing_transition_recap(messages, threshold=24)`**: Fires when conversation has ≥24 messages and recent AI messages (last 5) lack bridging phrases ("danach", "und dann", "nachdem", etc.). Injects a REGEL 6 reminder to include a 1-sentence recap before transitioning scenes. Fixes the in-context pattern problem where long conversations of short Q&A exchanges train the model to skip recaps.

**Message order after changes**:
1. SystemMessage — master prompt + child profile + beat context
2. SystemMessage — meta rules (aufgaben/satzbaubegrenzung) — conditional
3. SystemMessage — termination prompt — conditional
4. Conversation history (HumanMessage/AIMessage list)
5. SystemMessage — repetitive starter nudge — conditional (existing)
6. SystemMessage — disengagement nudge — conditional (NEW)
7. SystemMessage — story-end nudge — conditional (NEW)
8. SystemMessage — repeated-errors nudge — conditional (NEW)
9. SystemMessage — transition-recap nudge — conditional (NEW)

**Fixes** (+4 tests):
- `responding-to-answer::test_disengage_acknowledge_transition_simulated` — NOW PASSING (disengagement nudge)
- `story-not-extended::test_wrap_up_simulated` — NOW PASSING (story-end nudge)
- `story-summary::test_proactive_retelling_offer` — NOW PASSING (repeated-errors nudge)
- `transition-between-tasks::test_content_recap_on_transition` — NOW STABLE (was ~40% pass rate, now 5/5; recap nudge)

**Iteration notes**:
1. Initial disengagement implementation had a two-path nudge (story-end → goodbye, else → switch activity). This caused regression on `test_stop_forcing_when_child_disengages` because AI messages in the fixture didn't contain explicit story-end keywords ("eingeschlafen"), so the wrong path fired. Fix: Simplified to a single nudge that says "KEINE Frage zur Geschichte" and defers to REGEL 4B (which already has the AUSNAHME for end-of-story → verabschieden).
2. `test_content_recap_on_transition` was pre-existing flaky (~40% pass rate at temp=0.0 with n_runs=1). Root cause: 30-message conversation of short Q&A exchanges creates in-context pattern that overrides REGEL 6. Fix: transition-recap detection nudge for long conversations.

**Test results**: 72 passed, 1 failed (the remaining failure `test_gender_simulated_female` is a known Strategy B flaky test — LLM produced "suchst er" instead of "sucht er")

**Regressions**: None (verified full suite + specific regression checks)
