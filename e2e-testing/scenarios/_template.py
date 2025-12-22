"""
TEMPLATE for creating new test scenarios.

Copy this file and implement each method according to your test case.
See boredom_detection.py or grammar_teaching.py for complete examples.
"""
from typing import List
from scenarios.base_scenario import (
    BaseScenario,
    ScenarioMetadata,
    ChildPersona,
    EvaluationCriterion,
    ConversationConfig,
    ExpectedOutcome,
    Priority,
    FeatureCategory,
    LanguageLevel,
    EngagementLevel,
    ComprehensionLevel,
    EmotionState
)


class MyNewScenario(BaseScenario):
    """
    Brief description of what this scenario tests.

    Scenario Flow:
    - Step 1: Initial state
    - Step 2: What happens
    - Step 3: Expected system response
    """

    def get_metadata(self) -> ScenarioMetadata:
        """Define scenario identification and configuration"""
        return ScenarioMetadata(
            id="my_scenario_id",  # lowercase_snake_case
            name="Human Readable Scenario Name",
            description=(
                "Detailed description of what this scenario tests, "
                "why it's important, and what it validates about the system."
            ),
            feature_category=FeatureCategory.ENGAGEMENT,  # or PEDAGOGY, COMPREHENSION, SAFETY
            priority=Priority.HIGH,  # CRITICAL, HIGH, MEDIUM, LOW
            estimated_time_seconds=90,
            tags=["tag1", "tag2", "regression"],
            author="Your Name"
        )

    def get_persona(self) -> ChildPersona:
        """Define the simulated child characteristics"""
        return ChildPersona(
            # Demographics
            age=7,
            name="TestChild",
            language_level=LanguageLevel.A2,

            # Personality
            personality_traits=["trait1", "trait2"],
            interests=["interest1", "interest2"],
            learning_style="mixed",  # "visual", "auditory", "kinesthetic", "mixed"

            # Initial state
            initial_engagement=EngagementLevel.MEDIUM,
            initial_comprehension=ComprehensionLevel.GOOD,
            initial_emotion=EmotionState.NEUTRAL,

            # Language characteristics
            typical_response_length=10,
            grammar_error_rate=0.2,
            common_errors=["verb_conjugation", "articles"],

            # Behavioral triggers
            boredom_threshold_turns=None,  # Set if testing boredom
            confusion_triggers=[],          # Topics causing confusion
            excitement_triggers=[]          # Topics causing excitement
        )

    def get_evaluation_criteria(self) -> List[EvaluationCriterion]:
        """Define what the judge should evaluate"""
        return [
            EvaluationCriterion(
                name="criterion_1",  # snake_case identifier
                category="engagement",  # or "pedagogy", "safety", etc.
                description="What is being evaluated",
                weight=1.0,
                critical=False,  # True if test must fail if this fails
                minimum_score=70.0,
                evaluation_prompt="""
                Detailed instructions for the judge LLM:
                - What to look for
                - How to score
                - What constitutes good vs. bad

                Include specific guidance and examples.
                """,
                good_examples=[
                    "Example of good system behavior"
                ],
                bad_examples=[
                    "Example of bad system behavior"
                ]
            ),
            # Add more criteria...
        ]

    def get_conversation_config(self) -> ConversationConfig:
        """Configure how the conversation should run"""
        return ConversationConfig(
            num_turns=5,
            child_starts=True,  # False if system starts

            # Define when to change child's state
            state_update_triggers={
                3: {  # At turn 3
                    "engagement": EngagementLevel.LOW.value,
                    "emotion": EmotionState.BORED.value
                }
            },

            child_id="test_child_id",
            game_id="0"
        )

    def get_expected_outcomes(self) -> List[ExpectedOutcome]:
        """Define what should happen in the conversation"""
        return [
            ExpectedOutcome(
                description="What should happen",
                timeframe="When it should happen",
                indicator="How to detect it happened"
            ),
            # Add more outcomes...
        ]


# ============================================================================
# PLACEHOLDER: Create variations if needed
# ============================================================================

class MyNewScenarioVariation(MyNewScenario):
    """
    Variation description: How this differs from base scenario
    """

    def get_metadata(self) -> ScenarioMetadata:
        metadata = super().get_metadata()
        metadata.id = "my_scenario_variation"
        metadata.name += " - Variation Name"
        return metadata

    # Override other methods as needed for the variation