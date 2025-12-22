# End-to-End Testing Framework for Lingolino Agentic System

## 🎯 Overview

This directory contains the comprehensive E2E testing framework for the Lingolino conversational learning system. The framework uses **LLM-as-Simulator** and **LLM-as-Judge** patterns to test complex behavioral scenarios that emerge from the interaction between immediate and background graphs.

## 🏗️ Architecture

```
e2e-testing/
├── scenarios/              # Test scenario definitions
│   ├── __init__.py
│   ├── base_scenario.py    # Base scenario class with common structure
│   ├── boredom_detection.py
│   ├── grammar_teaching.py
│   ├── comprehension_scaffolding.py
│   ├── sentence_structure_guidance.py
│   ├── task_guidance.py
│   ├── context_retention.py
│   ├── emotional_responsiveness.py
│   └── age_appropriateness.py
│
├── judges/                 # LLM judge implementations
│   ├── __init__.py
│   ├── base_judge.py       # Abstract judge interface
│   ├── conversation_judge.py  # Main conversation evaluator
│   ├── criteria/           # Evaluation criteria definitions
│   │   ├── __init__.py
│   │   ├── pedagogical_criteria.py
│   │   ├── linguistic_criteria.py
│   │   ├── engagement_criteria.py
│   │   └── safety_criteria.py
│   └── prompts/            # Judge prompt templates
│       ├── __init__.py
│       └── judge_prompt_templates.py
│
├── simulators/             # Child behavior simulators
│   ├── __init__.py
│   ├── base_simulator.py   # Abstract simulator interface
│   ├── child_simulator.py  # Main child response generator
│   ├── personas/           # Child persona definitions
│   │   ├── __init__.py
│   │   ├── base_persona.py
│   │   ├── engaged_child.py
│   │   ├── bored_child.py
│   │   ├── confused_child.py
│   │   └── excited_child.py
│   └── response_strategies.py  # Response generation strategies
│
├── runners/                # Test execution orchestration
│   ├── __init__.py
│   ├── scenario_runner.py  # Main test runner
│   ├── test_session.py     # Test session management
│   └── parallel_runner.py  # Parallel test execution
│
├── utils/                  # Shared utilities
│   ├── __init__.py
│   ├── logging_config.py   # Test logging setup
│   ├── metrics_tracker.py  # Test metrics collection
│   ├── conversation_logger.py  # Detailed conversation logging
│   └── report_generator.py # Test report generation
│
├── reports/                # Test execution reports (generated)
│   └── .gitkeep
│
├── conftest.py             # Pytest configuration and fixtures
├── pytest.ini              # Pytest settings
├── requirements.txt        # Testing dependencies
└── run_tests.py            # Main test execution script

```

## 🧪 Test Scenario Structure

Each test scenario follows a standardized structure defined in `base_scenario.py`:

### Scenario Definition Components

1. **Metadata**
   - Scenario ID
   - Name and description
   - Feature category (boredom, grammar, comprehension, etc.)
   - Priority level (critical, high, medium, low)
   - Estimated execution time

2. **Persona Configuration**
   - Child age
   - Language level (A1, A2, B1, etc.)
   - Personality traits
   - Initial engagement state
   - Behavioral patterns

3. **Conversation Setup**
   - Initial context (audiobook, game settings)
   - Number of turns
   - Trigger conditions (when to change behavior)
   - Expected conversation flow

4. **Evaluation Criteria**
   - Specific metrics to evaluate
   - Success thresholds
   - Critical vs. optional criteria
   - Scoring weights

5. **Expected Outcomes**
   - System behavior expectations
   - Timeframe for detection/response
   - Quality indicators

## 🤖 Judge LLM Implementation

### Judge Architecture

The judge system evaluates conversations against predefined criteria using structured prompts:

```python
class ConversationJudge:
    def evaluate(self, conversation, criteria) -> EvaluationResult:
        """
        Returns:
        - Overall pass/fail
        - Per-criterion scores (0-100)
        - Confidence levels (0-1)
        - Specific evidence from conversation
        - Improvement suggestions
        """
```

### Judge Prompt Engineering Principles

1. **Clear Role Definition**
   ```
   You are an expert evaluator for child language learning systems.
   Your role is to assess conversations based on pedagogical effectiveness,
   linguistic appropriateness, and engagement quality.
   ```

2. **Structured Output Format**
   - JSON output for parsing
   - Separate scores for each criterion
   - Confidence indicators
   - Evidence citations (quote conversation)

3. **Evaluation Criteria Sections**
   - **Pedagogical Quality**: Teaching effectiveness, scaffolding, feedback quality
   - **Linguistic Appropriateness**: Age-appropriate vocabulary, grammar, complexity
   - **Engagement**: Emotional responsiveness, interest maintenance, motivation
   - **Safety**: Appropriate content, boundaries maintained

4. **Evidence-Based Assessment**
   - Judge must cite specific conversation turns
   - Explain reasoning for each score
   - Provide concrete examples

5. **Calibration Instructions**
   - Reference examples of good/bad responses
   - Scoring rubrics (0-25 poor, 26-50 fair, 51-75 good, 76-100 excellent)
   - Edge case handling

### Judge Configuration

```yaml
judge:
  model: "google_genai:gemini-2.0-flash"  # Fast and capable
  temperature: 0.0  # Deterministic evaluation
  max_retries: 3
  timeout: 30s
  fallback_model: "openai:gpt-4"  # If primary fails
```

### Evaluation Workflow

```
1. Load conversation transcript
2. Load evaluation criteria from scenario
3. Build judge prompt with context + criteria
4. Call judge LLM (temperature=0)
5. Parse structured response
6. Validate confidence scores
7. Aggregate results
8. Generate detailed report
```

## 👶 Child Simulator Implementation

### Simulator Architecture

The simulator generates realistic child responses based on persona and state:

```python
class ChildSimulator:
    def __init__(self, persona: ChildPersona, llm):
        self.persona = persona
        self.llm = llm
        self.conversation_state = ConversationState()
    
    def respond(self, system_message: str) -> str:
        """Generate child-like response to system message"""
        
    def update_state(self, new_state: dict):
        """Update engagement, emotion, comprehension state"""
```

### Simulator Prompt Engineering Principles

1. **Persona Embodiment**
   ```
   You are a {age}-year-old child named {name}.
   You are {personality_traits}.
   Your German language level is {level}.
   You are currently feeling {emotional_state}.
   ```

2. **Behavioral Constraints**
   - Vocabulary limitations (age-appropriate)
   - Sentence length constraints
   - Grammatical error patterns (natural mistakes)
   - Response length guidelines

3. **Dynamic State Adaptation**
   ```
   Current engagement level: {bored/engaged/excited}
   Current comprehension: {confused/understanding/mastering}
   
   Adjust your responses accordingly:
   - If bored: shorter, less enthusiastic
   - If confused: ask for clarification, off-topic
   - If excited: longer, more questions
   ```

4. **Natural Child Patterns**
   - Use simple conjunctions (und, aber, dann)
   - Mix statements and questions
   - Sometimes go off-topic
   - React emotionally to content
   - Make natural grammatical errors

5. **Response Variability**
   - Temperature: 0.3-0.5 (some variation, but consistent)
   - Avoid repetitive patterns
   - Maintain character consistency

### Simulator Configuration

```yaml
simulator:
  model: "google_genai:gemini-2.0-flash"
  temperature: 0.4  # Some variation, but consistent
  max_tokens: 100  # Child responses are short
  response_delay: 0.5s  # Simulate thinking time
```

### Persona Examples

#### Engaged 7-Year-Old
```python
persona = ChildPersona(
    age=7,
    name="Emma",
    language_level="A2",
    personality_traits=["curious", "enthusiastic", "talkative"],
    interests=["animals", "stories", "questions"],
    engagement_state="high",
    comprehension_level="good"
)
```

#### Bored 6-Year-Old
```python
persona = ChildPersona(
    age=6,
    name="Max",
    language_level="A1",
    personality_traits=["restless", "distracted", "quick-to-bore"],
    interests=["action", "games"],
    engagement_state="low",  # starts low
    comprehension_level="moderate"
)
```

## 🔄 Test Execution Flow

### Single Scenario Execution

```
1. Load Scenario Definition
   ↓
2. Initialize Child Simulator with Persona
   ↓
3. Initialize System (immediate_graph + background_graph)
   ↓
4. Start Conversation Loop:
   a. Simulator generates child message
   b. System processes and responds
   c. Log interaction
   d. Update simulator state (if trigger met)
   e. Repeat for N turns
   ↓
5. Conversation Complete
   ↓
6. Initialize Judge with Criteria
   ↓
7. Judge Evaluates Conversation
   ↓
8. Parse Results + Generate Report
   ↓
9. Assert Test Pass/Fail
```

### Multi-Scenario Execution

```
Test Suite
├── Critical Scenarios (run always)
│   ├── Boredom Detection
│   ├── Age Appropriateness
│   └── Safety Boundaries
├── Core Scenarios (run on PR)
│   ├── Grammar Teaching
│   ├── Comprehension Scaffolding
│   └── Task Guidance
└── Extended Scenarios (nightly)
    ├── Context Retention
    ├── Emotional Responsiveness
    └── Educational Progression
```

## 📊 Metrics & Reporting

### Tracked Metrics

1. **Test Execution Metrics**
   - Total test time
   - LLM API calls count
   - Cost per test ($)
   - Pass/fail rate

2. **Conversation Metrics**
   - Number of turns
   - Average response time
   - Background analysis trigger rate
   - State transition counts

3. **Evaluation Metrics**
   - Per-criterion scores (0-100)
   - Judge confidence levels (0-1)
   - Critical failures count
   - Overall quality score

### Report Format

Each test generates:
- **Summary Report**: Pass/fail, key metrics, overall score
- **Detailed Conversation Log**: Full transcript with timestamps
- **Evaluation Breakdown**: Per-criterion scores with evidence
- **Recommendations**: Improvement suggestions from judge
- **Cost Report**: API usage and estimated cost

### Report Output

```
reports/
├── 2024-12-18_14-30-00_test_run/
│   ├── summary.json
│   ├── summary.html
│   ├── boredom_detection/
│   │   ├── conversation.json
│   │   ├── evaluation.json
│   │   └── report.html
│   ├── grammar_teaching/
│   │   └── ...
│   └── metrics.csv
```

## 🚀 Usage

### Running Tests

```bash
# Run all E2E tests
python run_tests.py

# Run specific scenario
python run_tests.py --scenario boredom_detection

# Run by priority
python run_tests.py --priority critical

# Run with detailed logging
python run_tests.py --verbose

# Generate HTML reports
python run_tests.py --report-format html
```

### Pytest Integration

```bash
# Run with pytest
pytest e2e-testing/ -v

# Run specific test file
pytest e2e-testing/scenarios/test_boredom_detection.py

# Run with coverage
pytest e2e-testing/ --cov=agentic-system --cov-report=html
```

## 🔧 Configuration

### Environment Variables

```bash
# LLM Configuration
JUDGE_LLM_MODEL=google_genai:gemini-2.0-flash
SIMULATOR_LLM_MODEL=google_genai:gemini-2.0-flash
GOOGLE_API_KEY=your_key_here

# Test Configuration
E2E_TEST_TIMEOUT=300
E2E_PARALLEL_WORKERS=4
E2E_REPORT_DIR=./reports
E2E_VERBOSE=false

# Cost Tracking
E2E_TRACK_COST=true
E2E_COST_ALERT_THRESHOLD=5.0
```

### Test Configuration File

```yaml
# e2e_config.yaml
judge:
  model: "google_genai:gemini-2.0-flash"
  temperature: 0.0
  max_retries: 3
  
simulator:
  model: "google_genai:gemini-2.0-flash"
  temperature: 0.4
  max_tokens: 100
  
execution:
  parallel: true
  max_workers: 4
  timeout_per_test: 300
  retry_failed: true
  
reporting:
  format: ["json", "html"]
  include_conversation: true
  include_metrics: true
  save_location: "./reports"
```

## 📝 Adding New Test Scenarios

### Step-by-Step Guide

1. **Create Scenario Definition**
   ```python
   # scenarios/my_new_scenario.py
   from scenarios.base_scenario import BaseScenario
   
   class MyNewScenario(BaseScenario):
       def get_metadata(self):
           return ScenarioMetadata(
               id="my_new_scenario",
               name="My New Feature Test",
               description="Tests XYZ behavior",
               priority="high"
           )
       
       def get_persona(self):
           # Define child persona
           
       def get_evaluation_criteria(self):
           # Define what to evaluate
           
       def get_expected_outcomes(self):
           # Define success conditions
   ```

2. **Define Evaluation Criteria**
   ```python
   criteria = [
       EvaluationCriterion(
           name="feature_detection",
           description="System detects the feature within 3 turns",
           weight=0.4,
           critical=True
       ),
       # ... more criteria
   ]
   ```

3. **Add Judge Prompts**
   - Create prompt template in `judges/prompts/`
   - Include specific evaluation instructions
   - Define scoring rubric

4. **Test the Scenario**
   ```bash
   pytest scenarios/test_my_new_scenario.py -v
   ```

5. **Review Results**
   - Check `reports/` for detailed output
   - Calibrate criteria if needed
   - Adjust thresholds

## 🐛 Debugging

### Common Issues

1. **Test Flakiness**
   - Lower judge temperature (→ 0.0)
   - Increase retry count
   - Add confidence threshold filtering
   - Use majority voting (run 3x, take majority)

2. **High Costs**
   - Use cheaper models for simulator
   - Cache common responses
   - Reduce conversation turns
   - Run critical tests only in CI

3. **Judge Inconsistency**
   - Validate judge against human eval
   - Add more specific criteria
   - Include examples in prompts
   - Use structured output format

4. **Simulator Unrealistic**
   - Tune temperature
   - Add more behavioral constraints
   - Review child language corpus
   - Test with real child responses

### Logging

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Logs include:
# - Each LLM call (prompt + response)
# - State transitions
# - Evaluation scores
# - Timing information
```

## 📚 References

- **LLM-as-Judge Pattern**: OpenAI Evals, Anthropic Constitutional AI
- **Agentic Testing**: LangChain testing guides
- **Child Language Development**: CEFR language levels (A1-C2)
- **Pedagogical Evaluation**: Second Language Acquisition (SLA) principles

## 🤝 Contributing

When adding tests:
1. Follow the base scenario structure
2. Document evaluation criteria clearly
3. Include calibration examples
4. Test locally before committing
5. Update this README with new patterns

---

**Next Steps**: Implement the base classes and first scenario (boredom detection) to establish the pattern.

