# Architectural Improvements

Changes documented here require human review before implementation. They go beyond prompt engineering and involve structural changes to the dialog system.

## Format

```
### Improvement Title

**Problem**: What limitation of prompt engineering was hit
**Proposed change**: What architectural change is needed
**Impact**: Which components are affected
**Risk**: What could break
**Status**: PROPOSED | APPROVED | IMPLEMENTED
```

---

## Proposals

### 1. Hard Termination Strips All Conversation Rules

**Problem**: In `nodes.py:61`, when `is_conversation_ended(message_count)` is True (message_count >= 20), the master prompt is completely removed:
```python
system_context = f"""
    {getMasterPrompt() if not is_conversation_ended(message_count) else ''}
"""
```
This means ALL 5 critical conversation rules (clarity, empathy, verification, etc.) are stripped. Only the hard termination prompt ("say goodbye") remains. Tests with long conversation scripts (e.g. SCRIPT_PIA_LACHT with 45 messages = message_count 22) fail because REGEL 5 (explore emotions) is gone.

**Proposed change**: Keep essential conversation rules active even during termination. Options:
- **(A) Always include the master prompt, add termination guidance on top** ← CHOSEN
- (B) Extract a "core rules" subset that persists through all phases
- (C) Increase HARD_TERMINATION_THRESHOLD (quick fix but doesn't solve the root issue)

**Implementation**: Option A — `getMasterPrompt()` is now always included in `system_context` regardless of `is_conversation_ended()`. The hard termination prompt was rewritten to acknowledge the child's last answer first, then say goodbye. No new rule conflicts observed.

**Impact**: `nodes.py`, `conversation_termination_policy.py`
**Risk**: Longer conversations if rules conflict with termination guidance — NOT observed in testing
**Status**: IMPLEMENTED
**Affected test**: `responding-to-answer::test_emotion_engagement_after_correct_answer` — NOW PASSING

---

### 2. Long Conversation History Overwhelms Prompt Instructions

**Problem**: In `test_varied_starters_long_conversation`, the conversation has 41 messages where nearly every system response starts with "Du sagst"/"Du fragst"/"Du weißt". Despite REGEL 5 explicitly forbidding this pattern, the model continues it because the in-context examples (conversation history) overwhelm the system prompt instruction. At temperature 0.0 the model deterministically follows the entrenched pattern.

**Proposed change**: Options:
- **(A) Add a pre-processing step in `masterChatbot` that detects repetitive starters in the last N system messages and injects a targeted reminder into the prompt** ← CHOSEN
- (B) Post-process the response: if it starts with a repeated pattern, regenerate with an explicit nudge
- (C) Use a higher temperature (e.g., 0.3) to introduce enough variation to break out of entrenched patterns

**Implementation**: Option A — New `_detect_repetitive_starters()` function scans the last 5 AI messages. If ≥60% start with the same word, a `SystemMessage` nudge is appended AFTER the conversation history (maximum recency weight) with explicit instructions to use a different opener. The nudge is in German and provides example alternatives.

**Impact**: `nodes.py` (masterChatbot function)
**Risk**: Option A adds complexity — minimal, ~15 lines of code. No extra LLM calls. No temperature change.
**Status**: IMPLEMENTED
**Affected test**: `different-sentence-starters::test_varied_starters_long_conversation` — NOW PASSING
