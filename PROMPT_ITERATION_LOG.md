# Prompt Iteration Log

Tracks changes to `local_fallback_prompts.py` and their impact on feature tests.

## Iteration 0 — Baseline (empty prompts)

**Prompts:** Both `master_prompt` and `master_first_message_prompt` are empty strings.

**Command:** `pytest tests/feature-testing/ -m "llm_feature and not simulated" --ignore=tests/feature-testing/child-name-and-gender/ --n-runs=3 -v`

**Results: 3/11 passed (27%)**

| Test | Result |
|------|--------|
| test_ambiguous_single_word_carl | FAIL |
| test_unknown_word_famos | PASS |
| test_vergessen_disambiguation | PASS |
| test_weiss_nicht_empathy | FAIL |
| test_weiss_nicht_resolve | FAIL |
| test_ja_to_either_or | FAIL |
| test_child_deflects_task | FAIL |
| test_weiss_nicht_no_misinterpret | FAIL |
| test_concept_explanation_includes_verification | PASS |
| test_correction_includes_verification | FAIL |
| test_emotion_engagement_after_correct_answer | FAIL |

## Iteration 1 — Initial prompt (USE_S3_PROMPTS was still true → no effect)

**Note:** First attempts ran with `USE_S3_PROMPTS=true` in `.env`, so S3 prompts overrode local fallbacks. Results were identical to baseline. Fixed by setting `USE_S3_PROMPTS=false`.

## Iteration 2 — First effective prompt (USE_S3_PROMPTS=false)

**Changes:** Wrote `master_prompt` with 5 rules covering all test behaviors. `master_first_message_prompt` for greeting.

**Results: 7/11 Strategy A passed (64%)**

| Test | Result | Notes |
|------|--------|-------|
| test_ambiguous_single_word_carl | PASS | |
| test_unknown_word_famos | PASS | |
| test_vergessen_disambiguation | PASS | |
| test_weiss_nicht_empathy | PASS | New pass |
| test_weiss_nicht_resolve | PASS | New pass |
| test_ja_to_either_or | FAIL | LLM assumes one option instead of presenting both |
| test_child_deflects_task | PASS | New pass |
| test_weiss_nicht_no_misinterpret | FAIL | LLM pushes child to recall instead of helping |
| test_concept_explanation_includes_verification | FAIL | LLM asks experience questions instead of verification |
| test_correction_includes_verification | FAIL | LLM corrects but moves to next topic |
| test_emotion_engagement_after_correct_answer | PASS | New pass |

## Iteration 3 — Refined rules for remaining failures

**Changes:**
- Fall B (ja/nein to either/or): Added "STRENG VERBOTEN: Nur eine Option nennen. Du MUSST immer BEIDE Optionen wiederholen."
- After explanation: Added exact schema with RICHTIG/FALSCH examples for Rhabarber. Made "Verstehst du das?" mandatory last sentence.
- After correction: Changed example to use "Erinnerst du dich jetzt?" instead of "Kannst du dir das merken?"
- Added "ABSCHLUSS-CHECKLISTE" at end of prompt for recency bias.

**Results: 11/11 Strategy A passed (100%)**

## Iteration 4 — Strategy B fine-tuning

**Changes:**
- "Weiß nicht" rule: Changed from "verrate direkt" to "biete ZUERST an zu helfen" (judge preferred offering over immediately revealing).

**Final Results: 11/11 Strategy A passed, 11/11 Strategy B passed (100%)**

All 22 tests pass with ≥80% pass rate at n_runs=3.
