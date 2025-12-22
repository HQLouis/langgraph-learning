# E2E Testing Framework - Quick Reference

## 🎯 Overview

This is a comprehensive E2E testing framework for the Lingolino agentic learning system using the **LLM-as-Judge** and **LLM-as-Simulator** patterns.

## 📖 Documentation Map

```
e2e-testing/
│
├── 📘 README.md                    ← Start here: Complete overview
├── 🏗️ ARCHITECTURE.md              ← Technical architecture & design patterns  
├── ⚖️ JUDGE_GUIDE.md               ← How to implement the judge LLM
├── 👶 SIMULATOR_GUIDE.md           ← How to implement the child simulator
└── ✅ IMPLEMENTATION_STATUS.md     ← What's done, what's next
```

## 🚀 Quick Navigation

### I want to...

**Understand the system:**
1. Read `README.md` (15 min)
2. Skim `ARCHITECTURE.md` (10 min)
3. Look at `scenarios/boredom_detection.py` example (5 min)

**Implement the judge:**
1. Read `JUDGE_GUIDE.md` (30 min)
2. Implement `judges/conversation_judge.py`
3. Test with mock conversations

**Implement the simulator:**
1. Read `SIMULATOR_GUIDE.md` (30 min)
2. Implement `simulators/child_simulator.py`
3. Test response generation

**Create a new test scenario:**
1. Copy `scenarios/_template.py`
2. Implement all methods
3. Add to `scenarios/__init__.py` registry
4. See `scenarios/boredom_detection.py` for reference

**Run tests:**
```bash
# Install
pip install -r requirements.txt

# Run all
pytest

# Run specific scenario
pytest scenarios/test_boredom_detection.py

# Run by priority
pytest -m critical
```

## 📊 Framework Components

### 1. Scenarios (What to Test)
Define test cases with:
- Child persona (age, language level, behavior)
- Evaluation criteria (what judge checks)
- Expected outcomes (what should happen)
- Conversation configuration

**Files:** `scenarios/base_scenario.py`, `scenarios/boredom_detection.py`, etc.

### 2. Judge (How to Evaluate)
LLM-based evaluator that:
- Receives conversation transcript
- Evaluates against criteria
- Returns structured scores with evidence
- Provides actionable feedback

**Files:** `judges/conversation_judge.py` (TO IMPLEMENT)  
**Guide:** `JUDGE_GUIDE.md`

### 3. Simulator (Who to Test With)
LLM-based child that:
- Generates realistic child responses
- Follows persona characteristics
- Adapts based on emotional state
- Makes natural grammar errors

**Files:** `simulators/child_simulator.py` (TO IMPLEMENT)  
**Guide:** `SIMULATOR_GUIDE.md`

### 4. Runner (How to Execute)
Orchestrates tests:
- Runs conversation loops
- Manages state transitions
- Collects metrics
- Generates reports

**Files:** `runners/scenario_runner.py` (TO IMPLEMENT)

## 🎓 Key Concepts

### Test Scenario
A complete definition of one test case including persona, criteria, and expected behavior.

**Example:** "Boredom Detection" tests if system notices child getting bored (short responses) and adapts engagement strategy.

### Child Persona
Characteristics of simulated child: age, language level, personality, behavioral triggers.

**Example:** 7-year-old, A2 level, restless, gets bored after 3 turns.

### Evaluation Criterion
One aspect to judge: name, description, weight, rubric, examples.

**Example:** "Boredom detection speed" - System must detect within 2-3 turns, scored 0-100.

### Conversation Flow
```
1. Simulator generates child message
2. System (Lingolino) responds
3. Repeat for N turns
4. Judge evaluates entire conversation
5. Generate report with scores
```

## 📝 Example Scenario Structure

```python
class MyScenario(BaseScenario):
    def get_metadata(self):
        return ScenarioMetadata(
            id="my_scenario",
            name="My Feature Test",
            priority=Priority.HIGH,
            ...
        )
    
    def get_persona(self):
        return ChildPersona(
            age=7,
            language_level=LanguageLevel.A2,
            ...
        )
    
    def get_evaluation_criteria(self):
        return [
            EvaluationCriterion(
                name="criterion_1",
                description="What to evaluate",
                minimum_score=70.0,
                ...
            )
        ]
    
    def get_conversation_config(self):
        return ConversationConfig(
            num_turns=5,
            ...
        )
    
    def get_expected_outcomes(self):
        return [
            ExpectedOutcome(
                description="What should happen",
                ...
            )
        ]
```

## 🎯 Current Status

### ✅ Complete (Ready to Use)
- Complete documentation suite
- Base scenario framework
- 2 example scenarios (boredom, grammar)
- Scenario template
- Pytest configuration
- All data structures

### 🚧 To Implement (Next Steps)
- Judge system (~1-2 days)
- Simulator system (~1-2 days)
- Test runner (~1 day)
- Utilities (~1 day)
- Additional scenarios (~2-3 days)

**Total Estimated Effort:** ~1 week

## 💡 Design Philosophy

### Why LLM-as-Judge?
- Handles natural language variation
- Evaluates nuanced qualities
- More flexible than hardcoded assertions
- Industry standard pattern

### Why LLM-as-Simulator?
- Realistic child responses
- Adapts to system output
- Tests emergent behaviors
- Avoids brittle scripts

### Why Scenario-Based?
- Maps directly to features
- Easy to understand and maintain
- Clear success criteria
- Stakeholder communication

## 📊 Test Pyramid for LLM Systems

```
        ┌─────────────────┐
        │  E2E Scenario   │  ← This framework
        │  Tests (LLM)    │  ← Comprehensive but slower
        └─────────────────┘
       ┌───────────────────┐
       │ Integration Tests │  ← Partial LLM use
       │ (Hybrid)          │  ← Balance speed/coverage
       └───────────────────┘
    ┌──────────────────────────┐
    │   Component Tests        │  ← No LLM calls
    │   (Deterministic)        │  ← Fast, focused
    └──────────────────────────┘
```

This framework focuses on the top layer: comprehensive E2E behavioral testing.

## 🔧 Configuration

### Environment Variables
```bash
export GOOGLE_API_KEY="your_key"
export JUDGE_LLM_MODEL="google_genai:gemini-2.0-flash"
export SIMULATOR_LLM_MODEL="google_genai:gemini-2.0-flash"
```

### Test Selection
```bash
# By priority
pytest -m critical
pytest -m high

# By category
pytest -m engagement
pytest -m pedagogy

# By tag
pytest -m regression

# Specific scenario
pytest scenarios/test_boredom_detection.py
```

## 📈 Metrics

### Per Scenario
- Pass/fail status
- Per-criterion scores (0-100)
- Confidence levels
- Execution time
- API cost

### Per Test Run
- Total scenarios run
- Pass rate
- Average scores by criterion
- Total cost
- Total time

## 🚨 Common Pitfalls

### ❌ Don't:
- Hardcode expected responses word-for-word
- Use high temperature for judge (use 0.0)
- Skip validation of judge outputs
- Forget to track costs
- Test too many things in one scenario

### ✅ Do:
- Define clear evaluation criteria
- Provide examples in judge prompts
- Test judge consistency
- Monitor confidence scores
- Keep scenarios focused

## 🎓 Learning Path

**Day 1:** Understand architecture
- Read README.md
- Read ARCHITECTURE.md
- Review example scenarios

**Day 2-3:** Implement judge
- Read JUDGE_GUIDE.md
- Implement conversation_judge.py
- Test with mock conversations
- Validate output format

**Day 4-5:** Implement simulator
- Read SIMULATOR_GUIDE.md
- Implement child_simulator.py
- Test response generation
- Validate realism

**Day 6:** Integrate
- Implement scenario_runner.py
- Connect all components
- Run first E2E test
- Iterate on quality

**Day 7:** Expand
- Add more scenarios
- Implement utilities
- Generate reports
- Document findings

## 🔗 Related Documentation

- **Main System**: `/agentic-system/` - The system being tested
- **API**: `/backend/` - REST API for conversations
- **Functional Tests**: `/functional-testing/` - Simpler integration tests

## 💬 Questions?

### "How is this different from functional tests?"
Functional tests check basic functionality. E2E tests evaluate complex behavioral qualities using LLM judges.

### "Why not just use assertions?"
Assertions work for deterministic outputs. LLM responses vary, so we need LLM judges to evaluate quality.

### "How much does this cost?"
Very affordable with Gemini Flash: ~$0.002 per scenario, ~$0.02 for full suite.

### "How long does it take?"
~20 seconds per scenario, ~2.5 minutes for full suite (parallel).

### "Is the judge reliable?"
Yes, when properly calibrated. Use temperature=0.0, validate against human evals, and track confidence.

---

**Ready to Start?**
1. Read `README.md` (15 min)
2. Review `scenarios/boredom_detection.py` (5 min)
3. Read `JUDGE_GUIDE.md` Section 1-3 (20 min)
4. Start implementing! 🚀

