# German Grammar Correction in LLM Responses — Research

## Problem

The Lingolino dialog system (Gemini 2.0 Flash, temp=0.0) occasionally produces German grammar errors — e.g., "suchst er" instead of "sucht er" (2nd person verb conjugation instead of 3rd person). Since the system teaches children German, grammatically correct output is critical. Currently **zero grammar correction** exists anywhere in the response pipeline.

## Root Cause Analysis

These errors are **generation defects**, not knowledge gaps. The LLM "knows" German grammar but occasionally produces incorrect forms during generation. This is a known limitation of autoregressive language models — they can produce locally plausible but globally incorrect text. The low temperature (0.0) helps but does not eliminate such errors.

## Approaches Evaluated

### 1. Prompt Rules Only

- **Mechanism**: Add explicit grammar rules to the system prompt (e.g., "Always use correct 3rd person singular conjugation")
- **Latency**: 0ms additional
- **Infrastructure**: None
- **Reliability**: **Low** — The LLM already "knows" grammar; errors are generation defects, not knowledge gaps. Prompt rules cannot fix what the model already fails to do correctly during decoding.
- **Streaming**: Compatible
- **Verdict**: Necessary but insufficient as sole approach.

### 2. LanguageTool (Java-based)

- **Mechanism**: Full-featured open-source grammar checker with German support. Can run as HTTP service or embedded JAR.
- **Latency**: 50-200ms per request
- **Infrastructure**: +350MB Docker image, Java runtime, 5-15s cold start, needs sidecar container or embedded process
- **Reliability**: **High** for standard German grammar errors. Comprehensive rule set. Risk of false positives on children's simplified language.
- **Streaming**: Compatible (post-process complete chunks)
- **Considerations**:
  - Significant Docker image size increase
  - Cold start time impacts ECS Fargate deployment
  - Memory overhead (~500MB-1GB for German rules)
  - Excellent for catching diverse error types
- **Verdict**: Best option if regex proves insufficient. Reserve for Phase 2.

### 3. LLM Self-Correction (Second Pass)

- **Mechanism**: Send the generated text back to the LLM with instructions to fix grammar errors.
- **Latency**: 500-2000ms (full additional LLM call)
- **Infrastructure**: None (uses existing LLM)
- **Reliability**: **Moderate** — Same model may repeat the same errors. Different model adds complexity.
- **Streaming**: **NOT COMPATIBLE** — Breaks SSE streaming pipeline. Would need to buffer entire response before sending.
- **Cost**: Doubles LLM API costs per message.
- **Verdict**: Rejected. Breaks streaming architecture and doubles costs with uncertain reliability.

### 4. Hybrid: Prompt Rules + Regex Post-Processing (RECOMMENDED)

- **Mechanism**: Add grammar hint to prompt + apply compiled regex patterns to catch known error types after generation.
- **Latency**: <1ms additional
- **Infrastructure**: None — pure Python, no dependencies
- **Reliability**: **High for known patterns**, grows incrementally as new error types are discovered.
- **Streaming**: Fully compatible (applied to final text before contract building)
- **Extensibility**: New patterns added by appending to a list. Each pattern has a descriptive name for logging.
- **Considerations**:
  - Cannot catch unknown/novel error types
  - Risk of false positives must be managed with negative lookbehinds and tests
  - Pattern list may grow over time — but each pattern is simple and fast
- **Verdict**: Best balance of reliability, latency, and simplicity. Covers the immediate need and scales to new patterns.

## Comparison Matrix

| Approach | Latency | Infra Impact | Reliability | Streaming OK | Cost Impact |
|---|---|---|---|---|---|
| Prompt rules only | 0ms | None | Low | Yes | None |
| LanguageTool (Java) | 50-200ms | +350MB Docker, Java, sidecar | High (broad) | Yes | Moderate (infra) |
| LLM self-correction | 500-2000ms | None | Moderate | **No** | High (2x API) |
| **Hybrid: prompt + regex** | **<1ms** | **None** | **High (known patterns)** | **Yes** | **None** |

## Recommended Phased Strategy

### Phase 1 (Implemented): Prompt Rule + Regex Post-Processing

- Add `GRAMMATIK-HINWEIS` to master prompt
- Create `german_grammar_postprocess.py` with pattern-based corrections
- Insert into pipeline between `strip()` and `build_output_contract()`
- Unit tests for all patterns with positive and negative cases

### Phase 2 (If Needed): LanguageTool Integration

Trigger: If more than ~10 distinct error patterns are needed, or if errors are too diverse for regex.

- Deploy LanguageTool as Docker sidecar in ECS task definition
- Create async client wrapper with timeout and fallback
- Add health check and circuit breaker
- Maintain regex as fast-path for known patterns, LanguageTool as catch-all

## Known Error Patterns (Phase 1)

| Pattern | Example | Correction | Regex |
|---|---|---|---|
| 2nd person verb before 3rd person pronoun | "suchst er" | "sucht er" | `(?<!du )(?<!Du )\b(\w{2,}st)\s+(er\|sie\|es\|man)\b` |

## Edge Cases and Limitations

- **"erst er"**: The adverb "erst" ends in "st" and could be false-positive matched before "er". Mitigated by minimum stem length but not fully eliminated.
- **"bist er"**: Grammatically incorrect in any context ("bist" requires "du"), so correction to "bit er" is also wrong — but the input is already invalid.
- **Names ending in "st"**: E.g., "Ernst" — only affected if directly followed by er/sie/es/man with no other words between.
- **"du suchst" (valid 2nd person)**: Protected by negative lookbehind for "du " and "Du ".
