# Judge LLM Implementation Guide

## 🎯 Purpose

The Judge LLM is responsible for evaluating conversations between the Lingolino system and the simulated child. It assesses whether the system meets specified criteria for pedagogical quality, engagement, safety, and effectiveness.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                 JUDGE SYSTEM                        │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         ConversationJudge                    │  │
│  │  - Orchestrates evaluation                   │  │
│  │  - Manages retries and error handling        │  │
│  │  - Validates output quality                  │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │      JudgePromptBuilder                      │  │
│  │  - Constructs structured prompts             │  │
│  │  - Includes criteria, rubrics, examples      │  │
│  │  - Formats conversation transcript           │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │          LLM (Gemini 2.0 Flash)              │  │
│  │  Temperature: 0.0 (deterministic)            │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │       ResponseParser                         │  │
│  │  - Parses JSON output                        │  │
│  │  - Validates structure                       │  │
│  │  - Extracts scores and evidence              │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │       EvaluationResult                       │  │
│  │  - Structured evaluation output              │  │
│  │  - Per-criterion scores                      │  │
│  │  - Evidence and reasoning                    │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 📝 Judge Prompt Structure

A judge prompt consists of several carefully structured sections:

### 1. Role Definition
```
You are an expert evaluator for children's language learning systems.
Your task is to assess the quality of conversational interactions between
an AI learning companion (Lingolino) and a child learning German.

You evaluate conversations based on:
- Pedagogical effectiveness (teaching quality)
- Linguistic appropriateness (age and level)
- Engagement quality (maintaining interest)
- Safety and emotional support (positive environment)

You provide objective, evidence-based assessments with specific examples.
```

### 2. Context Section
```
CHILD PROFILE:
- Age: {age}
- Language Level: {language_level} (CEFR)
- Personality: {personality_traits}
- Current State: Engagement={engagement}, Emotion={emotion}

SCENARIO CONTEXT:
- Scenario: {scenario_name}
- Goal: {scenario_description}
- Expected Outcomes: {expected_outcomes}

CONVERSATION SETTING:
- Audio Book: {audiobook_context}
- Game Mode: {game_mode}
- Session: Turn {turn} of {total_turns}
```

### 3. Conversation Transcript
```
CONVERSATION TO EVALUATE:

Turn 1:
Child: "Ich haben einen Hund!"
System: "Oh toll! Du hast einen Hund? Das ist wunderbar! 
        Wie heißt dein Hund?"

Turn 2:
Child: "Er heißt Bruno. Er ist groß."
System: "Bruno! Was für ein schöner Name! Große Hunde sind toll. 
        Was macht Bruno gerne?"

[... full conversation ...]
```

### 4. Evaluation Criteria
For each criterion:
```
CRITERION 1: {criterion_name}
Category: {category}
Description: {description}
Weight: {weight}
Critical: {is_critical}
Minimum Pass Score: {minimum_score}/100

EVALUATION INSTRUCTIONS:
{detailed_evaluation_prompt}

SCORING RUBRIC:
0-25:   Poor - {poor_description}
26-50:  Fair - {fair_description}
51-75:  Good - {good_description}
76-100: Excellent - {excellent_description}

GOOD EXAMPLES:
- {good_example_1}
- {good_example_2}

BAD EXAMPLES:
- {bad_example_1}
- {bad_example_2}

YOUR TASK:
1. Score this criterion (0-100)
2. Determine if it passes (>= {minimum_score})
3. Provide your confidence level (0.0-1.0)
4. Cite specific evidence from the conversation
5. Explain your reasoning

---

[Repeat for each criterion...]
```

### 5. Output Format Specification
```
OUTPUT FORMAT:

You must respond with valid JSON in this exact structure:

{
  "overall_assessment": {
    "pass": boolean,
    "score": float (0-100, weighted average),
    "confidence": float (0.0-1.0),
    "summary": "Brief overall assessment (1-2 sentences)"
  },
  "criterion_evaluations": [
    {
      "criterion_name": "criterion_1",
      "score": float (0-100),
      "passed": boolean,
      "confidence": float (0.0-1.0),
      "evidence": [
        "Direct quote or paraphrase from conversation",
        "Another piece of evidence"
      ],
      "reasoning": "Detailed explanation of score (2-4 sentences)"
    }
  ],
  "conversation_highlights": [
    {
      "turn": int,
      "speaker": "child" | "system",
      "content": "Quote from conversation",
      "significance": "Why this moment is important"
    }
  ],
  "strengths": [
    "Specific strength observed",
    "Another strength"
  ],
  "weaknesses": [
    "Specific weakness observed",
    "Another weakness"
  ],
  "improvement_suggestions": [
    "Actionable suggestion",
    "Another suggestion"
  ]
}

CRITICAL: Respond ONLY with the JSON. No additional text before or after.
```

### 6. Calibration Examples (Optional but Recommended)
```
CALIBRATION EXAMPLES:

Example of a HIGH-SCORING conversation (85/100):
[Show example conversation]
This scored high because:
- Clear engagement strategies
- Natural grammar corrections
- Age-appropriate language
- Positive tone throughout

Example of a LOW-SCORING conversation (40/100):
[Show example conversation]
This scored low because:
- Explicit corrections ("That's wrong")
- Vocabulary too advanced
- Ignored child's emotional state
- Robotic responses
```

## 🔧 Implementation Details

### Judge Class Structure

```python
class ConversationJudge(BaseJudge):
    """
    Main judge implementation for conversation evaluation.
    
    Responsibilities:
    - Build comprehensive evaluation prompts
    - Call LLM with proper configuration
    - Parse and validate responses
    - Handle errors and retries
    - Return structured results
    """
    
    def __init__(
        self,
        llm,
        temperature: float = 0.0,      # Deterministic evaluation
        max_retries: int = 3,           # Retry on failures
        timeout: int = 30,              # Seconds
        validation_level: str = "strict" # "strict" or "lenient"
    ):
        self.llm = llm
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout
        self.validation_level = validation_level
        self.prompt_builder = JudgePromptBuilder()
        self.parser = JudgeResponseParser()
    
    async def evaluate(
        self,
        conversation: List[Message],
        criteria: List[EvaluationCriterion],
        context: Dict[str, Any]
    ) -> EvaluationResult:
        """
        Main evaluation method.
        
        Args:
            conversation: List of messages (child and system)
            criteria: Evaluation criteria from scenario
            context: Additional context (persona, scenario info, etc.)
            
        Returns:
            EvaluationResult with scores, evidence, and reasoning
            
        Raises:
            EvaluationError: If evaluation fails after retries
        """
        # 1. Build prompt
        prompt = self.prompt_builder.build(
            conversation=conversation,
            criteria=criteria,
            context=context
        )
        
        # 2. Call LLM with retries
        for attempt in range(self.max_retries):
            try:
                response = await self._call_llm(prompt)
                
                # 3. Parse response
                evaluation = self.parser.parse(response)
                
                # 4. Validate
                if self._validate_evaluation(evaluation, criteria):
                    return evaluation
                else:
                    logger.warning(f"Validation failed, attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Evaluation attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise EvaluationError(f"Evaluation failed after {self.max_retries} attempts")
        
        raise EvaluationError("Evaluation failed: validation never passed")
    
    async def _call_llm(self, prompt: str) -> str:
        """Call LLM with proper configuration"""
        response = await self.llm.ainvoke(
            prompt,
            temperature=self.temperature,
            timeout=self.timeout
        )
        return response.content
    
    def _validate_evaluation(
        self,
        evaluation: EvaluationResult,
        criteria: List[EvaluationCriterion]
    ) -> bool:
        """
        Validate that evaluation meets quality standards.
        
        Checks:
        - All criteria evaluated
        - Scores in valid range (0-100)
        - Evidence provided where required
        - Confidence scores reasonable (not all 1.0 or 0.0)
        - Reasoning provided
        """
        # Check all criteria present
        evaluated_names = {cr.criterion_name for cr in evaluation.criterion_results}
        expected_names = {cr.name for cr in criteria}
        if evaluated_names != expected_names:
            logger.warning(f"Missing criteria: {expected_names - evaluated_names}")
            return False
        
        # Validate scores
        for result in evaluation.criterion_results:
            if not 0 <= result.score <= 100:
                logger.warning(f"Invalid score: {result.score}")
                return False
            
            if not 0 <= result.confidence <= 1:
                logger.warning(f"Invalid confidence: {result.confidence}")
                return False
            
            # Check evidence if required
            criterion = next(c for c in criteria if c.name == result.criterion_name)
            if criterion.evidence_required and not result.evidence:
                logger.warning(f"Missing evidence for {result.criterion_name}")
                if self.validation_level == "strict":
                    return False
            
            # Check reasoning
            if not result.reasoning or len(result.reasoning) < 20:
                logger.warning(f"Insufficient reasoning for {result.criterion_name}")
                if self.validation_level == "strict":
                    return False
        
        # Check overall assessment
        if not evaluation.overall_pass and evaluation.overall_score > 80:
            logger.warning("Inconsistent: marked as fail but high score")
            return False
        
        return True
```

## 🎯 Prompt Engineering Best Practices

### 1. Be Extremely Specific
❌ Bad: "Evaluate engagement quality"
✅ Good: "Evaluate whether the system detected boredom (indicated by responses shorter than 5 words) and adapted within 2 turns by introducing engaging elements (questions, games, excitement, or references to child's interests)"

### 2. Provide Concrete Examples
Always include:
- Good examples (score 80+)
- Bad examples (score <50)
- Edge cases (score 50-70)

### 3. Define Scoring Ranges Clearly
```
0-25:   Poor - System failed to meet basic criteria, multiple major issues
26-50:  Fair - Partially met criteria but with significant problems
51-75:  Good - Met criteria with minor issues or room for improvement
76-89:  Very Good - Met criteria well with only trivial issues
90-100: Excellent - Exceeded criteria, exemplary performance
```

### 4. Request Evidence
Always require: "You MUST cite specific quotes or turns from the conversation to support your assessment."

### 5. Handle Edge Cases
```
SPECIAL CASES:
- If the child didn't make any errors, score grammar correction as N/A (score: null)
- If engagement was high throughout, boredom detection cannot be assessed (score: null)
- If conversation was too short (<3 turns), note this in reasoning
```

### 6. Control for Bias
```
IMPORTANT: Evaluate based ONLY on the conversation provided.
Do NOT:
- Assume what might have happened before/after
- Bring in external expectations beyond the criteria
- Favor longer or shorter responses without criteria basis
- Judge based on personal teaching philosophy
```

## 🔍 Validation and Quality Assurance

### Judge Calibration Process

1. **Create Gold Standard Set**
   - Manually evaluate 20-30 conversations
   - Include range of quality levels
   - Multiple human raters for reliability

2. **Test Judge Consistency**
   ```python
   # Same conversation, evaluate 10 times
   scores = []
   for i in range(10):
       result = judge.evaluate(conversation, criteria, context)
       scores.append(result.overall_score)
   
   # Check consistency
   std_dev = np.std(scores)
   assert std_dev < 5.0, "Judge is too inconsistent"
   ```

3. **Compare to Human Evaluations**
   ```python
   # Correlation between judge and human scores
   judge_scores = [judge_eval(conv) for conv in test_set]
   human_scores = [human_eval(conv) for conv in test_set]
   
   correlation = pearsonr(judge_scores, human_scores)
   assert correlation > 0.8, "Judge doesn't align with human judgment"
   ```

4. **Monitor Confidence Scores**
   - Track confidence distributions
   - Flag low-confidence evaluations (<0.6) for human review
   - Investigate patterns in low-confidence cases

### Response Quality Checks

```python
def validate_judge_response(evaluation: EvaluationResult) -> List[str]:
    """
    Validate judge response quality.
    Returns list of warnings/issues.
    """
    issues = []
    
    # Check for suspiciously perfect scores
    if all(r.score >= 95 for r in evaluation.criterion_results):
        issues.append("All scores >= 95 - may be too lenient")
    
    # Check for suspiciously low scores
    if all(r.score <= 20 for r in evaluation.criterion_results):
        issues.append("All scores <= 20 - may be too harsh")
    
    # Check evidence quality
    for result in evaluation.criterion_results:
        if result.evidence:
            # Evidence should quote actual conversation
            has_quotes = any('"' in e or "'" in e for e in result.evidence)
            if not has_quotes:
                issues.append(f"Evidence for {result.criterion_name} lacks quotes")
    
    # Check reasoning length
    avg_reasoning_length = np.mean([len(r.reasoning) for r in evaluation.criterion_results])
    if avg_reasoning_length < 50:
        issues.append("Reasoning too brief (< 50 chars average)")
    
    # Check confidence distribution
    confidences = [r.confidence for r in evaluation.criterion_results]
    if np.std(confidences) < 0.05:
        issues.append("All confidence scores too similar")
    
    return issues
```

## 📊 Cost Management

### Token Estimation

```python
def estimate_evaluation_cost(
    conversation_turns: int,
    num_criteria: int,
    model: str = "gemini-2.0-flash"
) -> float:
    """
    Estimate cost of single evaluation.
    
    Rough formula:
    - Input: ~500 tokens (base prompt) + ~100 * turns + ~200 * criteria
    - Output: ~500 tokens (structured JSON response)
    """
    input_tokens = 500 + (100 * conversation_turns) + (200 * num_criteria)
    output_tokens = 500
    
    # Gemini 2.0 Flash pricing (as of 2024)
    cost_per_1k_input = 0.0001
    cost_per_1k_output = 0.0002
    
    cost = (input_tokens / 1000 * cost_per_1k_input) + \
           (output_tokens / 1000 * cost_per_1k_output)
    
    return cost

# Example: 6-turn conversation, 5 criteria
# ~1,000 input tokens + 500 output = $0.0002
# Very affordable!
```

### Cost Optimization Strategies

1. **Cache Common Prompts**
   - Cache role definitions, rubrics
   - Only rebuild variable parts

2. **Batch Evaluations**
   - Evaluate multiple conversations in parallel
   - Amortize prompt overhead

3. **Use Cheaper Models for Non-Critical**
   - Critical tests: GPT-4 or Gemini Pro
   - Regression tests: Gemini Flash or GPT-3.5

4. **Smart Retry Logic**
   - Only retry on parse failures, not score disagreements
   - Exponential backoff to avoid rapid token burn

## 🚨 Error Handling

### Common Failure Modes

1. **Invalid JSON Response**
   ```python
   try:
       evaluation = json.loads(response)
   except json.JSONDecodeError:
       # Extract JSON from markdown code blocks if present
       match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
       if match:
           evaluation = json.loads(match.group(1))
       else:
           raise ParseError("Invalid JSON response")
   ```

2. **Missing Required Fields**
   ```python
   required_fields = ["overall_assessment", "criterion_evaluations"]
   for field in required_fields:
       if field not in evaluation:
           raise ParseError(f"Missing required field: {field}")
   ```

3. **LLM Hallucination**
   ```python
   # Judge invents criteria not in the specification
   evaluated_criteria = set(e["criterion_name"] for e in evaluation["criterion_evaluations"])
   expected_criteria = set(c.name for c in criteria)
   
   if evaluated_criteria != expected_criteria:
       logger.warning(f"Judge evaluated unexpected criteria: {evaluated_criteria - expected_criteria}")
   ```

4. **Confidence Drift**
   ```python
   # All confidence scores are 1.0 (overconfident)
   if all(e["confidence"] >= 0.99 for e in evaluation["criterion_evaluations"]):
       logger.warning("Judge may be overconfident")
   ```

## 📖 Example Full Judge Prompt

See `judges/prompts/example_full_prompt.txt` for a complete example of a well-structured judge prompt.

## 🔄 Iteration and Improvement

### Continuous Improvement Process

1. **Collect Failed Cases**
   - Save conversations where judge disagreed with human
   - Save conversations with low confidence

2. **Analyze Patterns**
   - What types of conversations are misjudged?
   - Which criteria are hardest to evaluate?

3. **Refine Prompts**
   - Add clarifying examples
   - Adjust rubric descriptions
   - Include edge case handling

4. **A/B Test Prompt Versions**
   - Test new prompt on gold standard set
   - Compare correlation with human evals
   - Deploy if improvement is significant

5. **Monitor in Production**
   - Track confidence score distributions
   - Flag outliers for manual review
   - Collect feedback from developers

---

**Next Steps**: See `SIMULATOR_GUIDE.md` for implementing the child simulator, then `IMPLEMENTATION.md` for putting it all together.

