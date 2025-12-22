# Child Simulator Implementation Guide

## 🎯 Purpose

The Child Simulator generates realistic child responses during E2E testing. It simulates a child's behavior, language patterns, and emotional states to test how the Lingolino system responds to various situations.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              SIMULATOR SYSTEM                       │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │         ChildSimulator                       │  │
│  │  - Orchestrates response generation          │  │
│  │  - Manages state transitions                 │  │
│  │  - Applies behavioral patterns               │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │      SimulatorState                          │  │
│  │  - Current engagement level                  │  │
│  │  - Current emotional state                   │  │
│  │  - Turn counter                              │  │
│  │  - Recent topics discussed                   │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │      SimulatorPromptBuilder                  │  │
│  │  - Builds persona-specific prompts           │  │
│  │  - Includes state and constraints            │  │
│  │  - Formats conversation history              │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │          LLM (Gemini 2.0 Flash)              │  │
│  │  Temperature: 0.3-0.5 (controlled variety)   │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │       ResponsePostProcessor                  │  │
│  │  - Applies grammar errors                    │  │
│  │  - Adjusts length to persona                 │  │
│  │  - Adds natural child patterns               │  │
│  └─────────────┬────────────────────────────────┘  │
│                │                                    │
│  ┌─────────────▼────────────────────────────────┐  │
│  │       Child Response                         │  │
│  │  "Ich haben einen Hund!"                     │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

## 📝 Simulator Prompt Structure

### 1. Persona Embodiment

```
# YOUR IDENTITY

You are {name}, a {age}-year-old child learning German.

ABOUT YOU:
- Age: {age} years old
- German Language Level: {language_level} (CEFR scale)
- Personality: You are {personality_traits}
- Interests: You love {interests}
- Learning Style: {learning_style}

IMPORTANT: Stay completely in character as a real {age}-year-old child.
Think and respond exactly as a child of this age would.
```

### 2. Current State

```
# YOUR CURRENT FEELINGS

Right now you are feeling:
- Engagement: {engagement_level}
  {engagement_description}
  
- Comprehension: {comprehension_level}
  {comprehension_description}
  
- Emotion: {emotion}
  {emotion_description}

These feelings will affect how you respond:
- If bored: Keep responses short, show lack of interest
- If excited: Use more words, ask questions, show enthusiasm
- If confused: Ask for clarification, go off-topic, seem uncertain
```

### 3. Language Constraints

```
# HOW YOU SPEAK

Language Level Guidelines for {language_level}:

VOCABULARY:
- Use only simple, common German words
- Avoid complex or academic vocabulary
- {vocabulary_examples}

GRAMMAR:
- Keep sentences simple (5-10 words typically)
- You make grammar mistakes naturally ({error_rate*100}% of time)
- Common errors you make: {common_errors}
- Don't use complex structures you haven't learned yet

SENTENCE PATTERNS:
- Use simple conjunctions: und, aber, dann
- Subject-verb-object order mostly
- Short phrases, not long explanations
- Mix statements and questions

TYPICAL RESPONSE LENGTH:
- {typical_response_length} words on average
- Shorter when bored/tired
- Longer when excited/engaged
```

### 4. Behavioral Guidelines

```
# HOW YOU BEHAVE

Natural Child Behaviors:
✓ Sometimes go off-topic if something reminds you of something else
✓ Ask "why" questions when curious
✓ Share personal stories related to the topic
✓ Express emotions directly ("Das ist langweilig", "Das ist cool!")
✓ Need encouragement and positive reinforcement
✓ Get distracted by interesting details
✓ Make logical leaps that make sense to a child

Avoid:
✗ Adult-like reasoning or explanations
✗ Perfect grammar (you're still learning!)
✗ Long, structured responses
✗ Metalinguistic awareness ("I think the grammar is...")
✗ Overly polite formal language
```

### 5. Conversation Context

```
# THE CONVERSATION SO FAR

You are talking with Lino, your friendly learning companion, about {topic}.

Recent conversation:
{conversation_history}

Lino just said:
"{system_last_message}"

NOW: Respond as {name} would respond, staying completely in character.
```

### 6. Response Format Instructions

```
# YOUR RESPONSE

Respond with ONLY what {name} would say - just the German text.

DO NOT:
- Add explanations like "(confused)" or "(excited)"
- Translate to English
- Add any meta-commentary
- Explain your thinking

JUST RESPOND AS THE CHILD.

Remember:
- Stay in character
- Match your current emotional state
- Use {language_level} German
- Make natural grammar mistakes
- Be a real {age}-year-old kid!
```

## 🎭 Persona Implementation

### Key Persona Characteristics

#### Age 6 (A1 Level)
```python
LANGUAGE:
- Vocabulary: 200-500 common words
- Sentence length: 3-6 words
- Grammar: Simple present, very basic structures
- Errors: Very frequent (30-40%)

BEHAVIOR:
- Short attention span (2-3 turns)
- Very concrete thinking
- Needs constant engagement
- Emotional and direct

EXAMPLE RESPONSES:
"Das ist schön!"
"Ich hab einen Hund."
"Warum?"
```

#### Age 7-8 (A2 Level)
```python
LANGUAGE:
- Vocabulary: 500-1000 words
- Sentence length: 6-10 words
- Grammar: Present, simple past, basic conjunctions
- Errors: Frequent (20-30%)

BEHAVIOR:
- Longer attention (3-5 turns)
- Curious, asks questions
- Makes connections
- Starting to reason

EXAMPLE RESPONSES:
"Ich habe einen Hund und er heißt Max."
"Das ist interessant! Was passiert dann?"
"Ich gehe nicht gerne zur Schule."
```

#### Age 9-10 (B1 Level)
```python
LANGUAGE:
- Vocabulary: 1000-2000 words
- Sentence length: 8-15 words
- Grammar: Multiple tenses, complex sentences
- Errors: Moderate (10-20%)

BEHAVIOR:
- Good attention (5-8 turns)
- Logical thinking
- Can discuss abstract ideas
- Self-aware

EXAMPLE RESPONSES:
"Ich finde das spannend, weil ich auch gerne Geschichten lese."
"Das verstehe ich nicht ganz. Kannst du das erklären?"
"Wenn ich älter bin, möchte ich auch ein Abenteuer haben."
```

## 🔄 State Management

### SimulatorState Class

```python
@dataclass
class SimulatorState:
    """Tracks the simulator's current state"""
    
    # Engagement and emotion
    engagement: EngagementLevel
    comprehension: ComprehensionLevel
    emotion: EmotionState
    
    # Conversation tracking
    turn_count: int = 0
    messages_sent: int = 0
    
    # Recent context
    recent_topics: List[str] = field(default_factory=list)
    last_emotion_change_turn: int = 0
    
    # Response characteristics (can change dynamically)
    current_response_length: int = 10
    current_error_rate: float = 0.2
    
    def update(self, **kwargs):
        """Update state attributes"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def increment_turn(self):
        """Increment turn counter"""
        self.turn_count += 1
```

### State Transition Logic

```python
class ChildSimulator:
    def _check_state_triggers(self):
        """
        Check if persona conditions trigger state changes.
        This happens automatically based on turn count and triggers.
        """
        # Boredom trigger
        if (self.persona.boredom_threshold_turns and 
            self.state.turn_count >= self.persona.boredom_threshold_turns and
            self.state.engagement != EngagementLevel.LOW):
            
            logger.info(f"Triggering boredom at turn {self.state.turn_count}")
            self.update_state({
                "engagement": EngagementLevel.LOW,
                "emotion": EmotionState.BORED,
                "current_response_length": 3  # Much shorter
            })
        
        # Confusion trigger (topic-based)
        if self._last_system_message_contains(self.persona.confusion_triggers):
            logger.info("Triggering confusion due to topic")
            self.update_state({
                "comprehension": ComprehensionLevel.STRUGGLING,
                "emotion": EmotionState.CONFUSED
            })
        
        # Excitement trigger (topic-based)
        if self._last_system_message_contains(self.persona.excitement_triggers):
            logger.info("Triggering excitement due to topic")
            self.update_state({
                "engagement": EngagementLevel.HIGH,
                "emotion": EmotionState.EXCITED,
                "current_response_length": self.persona.typical_response_length + 5
            })
```

## 🛠️ Response Generation Pipeline

### Step-by-Step Process

```python
def respond(self, system_message: str, conversation_history: List[Message]) -> str:
    """
    Generate child response to system message.
    
    Pipeline:
    1. Check for state transitions
    2. Build simulator prompt
    3. Call LLM
    4. Post-process response
    5. Update state
    """
    
    # 1. Check state triggers
    self._check_state_triggers()
    
    # 2. Build prompt
    prompt = self.prompt_builder.build(
        persona=self.persona,
        state=self.state,
        system_message=system_message,
        history=conversation_history
    )
    
    # 3. Generate base response
    base_response = self.llm.invoke(
        prompt,
        temperature=self.temperature,
        max_tokens=self._calculate_max_tokens()
    ).content
    
    # 4. Post-process
    final_response = self._post_process_response(base_response)
    
    # 5. Update state
    self.state.increment_turn()
    self.state.recent_topics.append(self._extract_topic(system_message))
    
    return final_response
```

### Post-Processing Techniques

```python
def _post_process_response(self, response: str) -> str:
    """
    Apply child-like modifications to LLM response.
    
    Steps:
    1. Trim to appropriate length
    2. Inject grammar errors
    3. Simplify vocabulary if needed
    4. Add natural hesitations
    5. Apply emotion markers
    """
    
    # 1. Trim to length
    response = self._trim_to_length(response, self.state.current_response_length)
    
    # 2. Inject grammar errors
    if random.random() < self.state.current_error_rate:
        response = self._inject_grammar_error(response)
    
    # 3. Apply emotional markers
    response = self._apply_emotion(response, self.state.emotion)
    
    # 4. Add natural child patterns
    response = self._add_child_patterns(response)
    
    return response


def _inject_grammar_error(self, text: str) -> str:
    """
    Inject natural grammar errors based on persona's common errors.
    """
    error_type = random.choice(self.persona.common_errors)
    
    if error_type == "verb_conjugation":
        # Replace conjugated verb with infinitive or wrong form
        # "ich gehe" → "ich gehen"
        patterns = [
            (r'\bich\s+(\w+)e\b', r'ich \1en'),  # ich gehe → ich gehen
            (r'\bdu\s+(\w+)st\b', r'du \1en'),   # du gehst → du gehen
        ]
        for pattern, replacement in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return re.sub(pattern, replacement, text, count=1, flags=re.IGNORECASE)
    
    elif error_type == "articles":
        # Swap articles
        article_swaps = {
            'der': 'die', 'die': 'das', 'das': 'der',
            'ein': 'eine', 'eine': 'ein'
        }
        for article, wrong_article in article_swaps.items():
            if f' {article} ' in text.lower():
                return text.replace(f' {article} ', f' {wrong_article} ', 1)
    
    elif error_type == "word_order":
        # Simple word order errors (advanced)
        pass
    
    return text


def _apply_emotion(self, text: str, emotion: EmotionState) -> str:
    """
    Add emotion markers to response.
    """
    if emotion == EmotionState.EXCITED:
        # Add exclamation marks, maybe repeat letters
        if not text.endswith('!'):
            text = text.rstrip('.') + '!'
        # Occasionally: "Das ist so cooool!"
        if random.random() < 0.3:
            text = re.sub(r'\b(cool|toll|super)\b', r'\1!', text, flags=re.IGNORECASE)
    
    elif emotion == EmotionState.BORED:
        # Remove enthusiasm, make flat
        text = text.replace('!', '.')
        # Maybe add "Hm" or "Ok"
        if random.random() < 0.5:
            text = "Hm. " + text
    
    elif emotion == EmotionState.CONFUSED:
        # Add uncertainty markers
        uncertainty = ["äh", "hmm", "ich weiß nicht"]
        if random.random() < 0.4:
            text = f"{random.choice(uncertainty)}... {text}"
    
    return text


def _add_child_patterns(self, text: str) -> str:
    """
    Add natural child language patterns.
    """
    # Occasionally start with "und" or "aber"
    if self.state.turn_count > 1 and random.random() < 0.2:
        conjunctions = ["Und", "Aber"]
        text = f"{random.choice(conjunctions)} {text[0].lower()}{text[1:]}"
    
    # Add personal references
    if random.random() < 0.15:
        personal = [
            "Ich auch!",
            "Bei mir auch!",
            "Meine Mama sagt das auch.",
        ]
        text = f"{text} {random.choice(personal)}"
    
    return text
```

## 🎯 Behavioral Patterns

### Engagement Level Patterns

```python
HIGH_ENGAGEMENT_PATTERNS = {
    "response_length": (10, 15),  # words
    "questions_probability": 0.4,
    "enthusiasm_markers": ["!", "Das ist cool!", "Wow!"],
    "topic_maintenance": 0.9,  # stays on topic
    "elaboration_probability": 0.6,  # adds details
}

MEDIUM_ENGAGEMENT_PATTERNS = {
    "response_length": (6, 10),
    "questions_probability": 0.2,
    "enthusiasm_markers": ["."],
    "topic_maintenance": 0.7,
    "elaboration_probability": 0.3,
}

LOW_ENGAGEMENT_PATTERNS = {
    "response_length": (2, 4),
    "questions_probability": 0.05,
    "enthusiasm_markers": [".", "..."],
    "topic_maintenance": 0.3,  # goes off-topic
    "elaboration_probability": 0.05,
    "minimal_responses": ["Ja.", "Nein.", "Ok.", "Hm.", "Weiß nicht."],
    "minimal_probability": 0.5,
}
```

### Emotion-Based Response Styles

```python
EMOTION_STYLES = {
    EmotionState.EXCITED: {
        "exclamations": ["Wow!", "Cool!", "Super!", "Toll!"],
        "repetitions": True,  # "Das ist so so cool!"
        "questions": ["Was noch?", "Und dann?", "Wirklich?"],
    },
    
    EmotionState.BORED: {
        "minimal_responses": ["Ja.", "Ok.", "Hm.", "Aha."],
        "topic_drift": 0.6,  # high chance of going off-topic
        "flat_tone": True,  # no exclamation marks
    },
    
    EmotionState.CONFUSED: {
        "uncertainty": ["äh", "hmm", "ich weiß nicht"],
        "questions": ["Was?", "Wie meinst du das?", "Ich verstehe nicht."],
        "request_help": ["Kannst du das erklären?", "Was bedeutet das?"],
    },
    
    EmotionState.FRUSTRATED: {
        "negative": ["Das ist schwer.", "Ich kann das nicht.", "Das verstehe ich nicht."],
        "short_responses": True,
        "resistance": ["Ich will nicht mehr.", "Das macht keinen Spaß."],
    },
}
```

## 🧪 Testing the Simulator

### Validation Tests

```python
class TestSimulator:
    def test_language_level_appropriate(self):
        """Verify simulator produces age-appropriate language"""
        simulator = ChildSimulator(persona_age_6_a1, llm)
        
        response = simulator.respond("Erzähl mir von deinem Tag!", [])
        
        # Check vocabulary level
        words = response.split()
        assert all(is_a1_vocabulary(word) for word in words)
        
        # Check sentence length
        assert len(words) <= 10
    
    def test_boredom_progression(self):
        """Verify simulator shows boredom after threshold"""
        persona = ChildPersona(..., boredom_threshold_turns=3)
        simulator = ChildSimulator(persona, llm)
        
        responses = []
        for i in range(5):
            response = simulator.respond(f"Message {i}", responses)
            responses.append(response)
        
        # First 2 responses should be longer
        assert len(responses[0].split()) > 5
        assert len(responses[1].split()) > 5
        
        # After turn 3, responses should be much shorter
        assert len(responses[3].split()) <= 4
        assert len(responses[4].split()) <= 4
    
    def test_grammar_errors_present(self):
        """Verify simulator makes expected grammar errors"""
        persona = ChildPersona(..., grammar_error_rate=0.5, common_errors=["verb_conjugation"])
        simulator = ChildSimulator(persona, llm)
        
        # Generate many responses
        responses = [simulator.respond(f"Msg {i}", []) for i in range(20)]
        
        # Should have some errors (not necessarily 50% due to randomness)
        errors_found = sum(1 for r in responses if has_verb_conjugation_error(r))
        assert errors_found > 0  # At least some errors
    
    def test_emotion_affects_response(self):
        """Verify emotional state affects response style"""
        simulator = ChildSimulator(persona, llm)
        
        # Set excited
        simulator.update_state({"emotion": EmotionState.EXCITED})
        excited_response = simulator.respond("Das ist toll!", [])
        assert "!" in excited_response
        
        # Set bored
        simulator.update_state({"emotion": EmotionState.BORED})
        bored_response = simulator.respond("Das ist toll!", [])
        assert len(bored_response.split()) < 5
```

## 🔧 Configuration

### Simulator Settings

```yaml
simulator:
  model: "google_genai:gemini-2.0-flash"
  temperature: 0.4  # Balance between variety and consistency
  max_tokens: 100   # Child responses are short
  
  behavior:
    response_delay: 0.5  # Seconds, simulate thinking time
    typo_probability: 0.0  # No typos in text (not voice)
    emoji_probability: 0.0  # Children don't use emoji in German
  
  validation:
    max_response_length: 50  # words
    min_response_length: 1
    allowed_languages: ["de"]  # Only German
```

## 📊 Simulator Quality Metrics

Track these metrics to ensure simulator quality:

```python
metrics = {
    "avg_response_length": [],  # Should match persona
    "error_rate": [],  # Should match persona.grammar_error_rate
    "vocabulary_level_adherence": [],  # % of words within level
    "state_transition_accuracy": [],  # Correct state changes
    "response_relevance": [],  # On-topic vs. off-topic
}
```

## 🚨 Common Issues and Solutions

### Issue 1: Simulator Too Perfect
**Problem**: Responses too grammatically correct for the age/level

**Solution**:
- Lower temperature
- Increase post-processing error injection
- Add more examples of child errors in prompt
- Use smaller model (sometimes helps with "un-learning")

### Issue 2: Responses Too Short/Long
**Problem**: Doesn't match expected length

**Solution**:
- Explicitly set max_tokens based on persona
- Post-process to trim/extend
- Add length examples in prompt ("Your responses are usually X-Y words")

### Issue 3: Doesn't Stay in Character
**Problem**: Sounds like an adult explaining what a child would say

**Solution**:
- Stronger persona prompting
- Remove meta-instructions that might confuse
- Add "DO NOT explain or translate" instructions
- Use few-shot examples of actual child responses

### Issue 4: State Changes Ignored
**Problem**: Child remains engaged despite boredom trigger

**Solution**:
- Make state more explicit in prompt
- Add specific behavioral instructions for each state
- Provide examples of responses in each state

---

**Next**: See `IMPLEMENTATION.md` for complete implementation details and putting simulator + judge together with the test runner.

