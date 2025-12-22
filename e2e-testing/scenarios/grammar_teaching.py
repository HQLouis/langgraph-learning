"""
Grammar Teaching Test Scenario

This scenario tests the system's ability to:
1. Identify grammatical errors in child's speech
2. Provide corrections naturally and playfully (no explicit criticism)
3. Model correct grammar in responses
4. Maintain positive learning environment

Scenario Flow:
- Child makes grammatical errors (verb conjugation, articles, etc.)
- System should naturally model correct form without explicit correction
- Response should maintain conversation flow and child's dignity
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


class GrammarTeachingScenario(BaseScenario):
    """
    Tests the system's ability to naturally correct grammar errors
    without explicit criticism or breaking conversation flow.

    Key pedagogical principle: Implicit correction through modeling
    is more effective than explicit correction for young learners.
    """

    def get_metadata(self) -> ScenarioMetadata:
        return ScenarioMetadata(
            id="grammar_teaching",
            name="Natural Grammar Teaching and Correction",
            description=(
                "Tests the system's ability to identify grammatical errors and "
                "provide implicit correction through natural modeling while "
                "maintaining positive learning environment and conversation flow."
            ),
            feature_category=FeatureCategory.PEDAGOGY,
            priority=Priority.HIGH,
            estimated_time_seconds=90,
            tags=["pedagogy", "grammar", "teaching", "regression"],
            author="LNG"
        )

    def get_persona(self) -> ChildPersona:
        return ChildPersona(
            # Demographics
            age=6,
            name="Sophie",
            language_level=LanguageLevel.A1,  # Early learner, more errors

            # Personality
            personality_traits=[
                "enthusiastic",
                "talkative",
                "eager_to_learn",
                "sensitive_to_criticism"
            ],
            interests=["animals", "stories", "family"],
            learning_style="auditory",

            # Initial state
            initial_engagement=EngagementLevel.HIGH,
            initial_comprehension=ComprehensionLevel.GOOD,
            initial_emotion=EmotionState.HAPPY,

            # Language characteristics - will make deliberate errors
            typical_response_length=12,
            grammar_error_rate=0.4,  # Higher error rate for testing
            common_errors=[
                "verb_conjugation",      # "Ich gehen" instead of "Ich gehe"
                "articles",              # "der Katze" instead of "die Katze"
                "word_order",           # "Ich nicht mag" instead of "Ich mag nicht"
                "plural_forms"          # "zwei Hund" instead of "zwei Hunde"
            ],

            # Behavioral triggers
            # Note: Would become discouraged if criticized directly
            confusion_triggers=["explicit_correction", "grammar_rules"]
        )

    def get_evaluation_criteria(self) -> List[EvaluationCriterion]:
        return [
            # CRITERION 1: Error Identification
            EvaluationCriterion(
                name="error_identification",
                category="pedagogy",
                description=(
                    "System identifies grammatical errors in child's speech "
                    "(evident through natural correction in response)"
                ),
                weight=0.8,
                critical=False,
                minimum_score=70.0,
                evaluation_prompt="""
                Assess whether the system identified the grammatical errors:
                - Did the child make grammatical errors?
                - Did the system's response include the correct form?
                - Was the correction contextually appropriate?
                
                You can infer error detection when the system naturally models
                the correct form in a way that addresses the specific error.
                
                Example: Child says "Ich haben einen Hund" (wrong conjugation)
                         System responds "Oh toll! Du hast einen Hund!" (correct form)
                """,
                good_examples=[
                    "Child: 'Ich gehen zur Schule' → System: 'Du gehst zur Schule? Das ist schön!'",
                    "Child: 'Der Katze ist süß' → System: 'Ja, die Katze ist wirklich süß!'"
                ],
                bad_examples=[
                    "Child makes error, system ignores completely",
                    "System uses different sentence structure that doesn't model correction"
                ]
            ),

            # CRITERION 2: Natural Correction (No Explicit Criticism)
            EvaluationCriterion(
                name="natural_correction_style",
                category="pedagogy",
                description=(
                    "Corrections are implicit (through modeling) rather than explicit. "
                    "No phrases like 'that's wrong', 'you should say', 'the correct form is'"
                ),
                weight=1.0,
                critical=True,  # This is essential for positive learning environment
                minimum_score=80.0,
                evaluation_prompt="""
                CRITICAL: Check that corrections are IMPLICIT, not explicit:
                
                GOOD (Implicit correction):
                - System naturally uses correct form in response
                - Correction woven into conversation flow
                - No metalinguistic commentary
                - Child's dignity preserved
                
                BAD (Explicit correction):
                - "Das ist falsch" / "That's wrong"
                - "Du solltest sagen..." / "You should say..."
                - "Die richtige Form ist..." / "The correct form is..."
                - Direct grammar instruction
                
                Score LOW if ANY explicit correction detected.
                Score HIGH only if ALL corrections are natural and implicit.
                """,
                good_examples=[
                    "Child: 'Ich haben' → System: 'Du hast einen Hund? Toll!'",
                    "Child: 'Der Baum sind groß' → System: 'Ja, der Baum ist wirklich groß!'"
                ],
                bad_examples=[
                    "System: 'Nein, man sagt nicht \"ich haben\". Die richtige Form ist \"ich habe\".'",
                    "System: 'Das ist falsch. Du solltest sagen: Ich gehe.'",
                    "System: 'Achtung! Der Artikel ist falsch.'"
                ]
            ),

            # CRITERION 3: Conversation Flow Maintenance
            EvaluationCriterion(
                name="conversation_flow_maintenance",
                category="engagement",
                description=(
                    "Corrections don't interrupt conversation flow. "
                    "System maintains natural dialogue while modeling correct forms."
                ),
                weight=0.9,
                critical=False,
                minimum_score=70.0,
                evaluation_prompt="""
                Evaluate whether corrections feel natural within conversation:
                - Does conversation continue smoothly?
                - Is the correction woven into meaningful response?
                - Does child's topic/interest get acknowledged?
                - Would a child notice they're being corrected?
                
                Best practice: Correction + acknowledgment + continuation
                Example: "Du hast einen Hund? [correction] Das ist toll! [acknowledgment] 
                         Was macht dein Hund gerne?" [continuation]
                """,
                good_examples=[
                    "Seamless integration of correct form into enthusiastic response",
                    "Correction followed by related question to continue conversation"
                ],
                bad_examples=[
                    "Correction feels forced or awkward",
                    "Only corrects without continuing the conversation",
                    "Ignores child's topic to focus on correction"
                ]
            ),

            # CRITERION 4: Positive Learning Environment
            EvaluationCriterion(
                name="positive_learning_environment",
                category="pedagogy",
                description=(
                    "System maintains encouraging, supportive tone. "
                    "Child's efforts are valued, errors treated as natural part of learning."
                ),
                weight=0.9,
                critical=True,
                minimum_score=75.0,
                evaluation_prompt="""
                Assess the emotional tone and learning environment:
                - Is tone consistently positive and encouraging?
                - Are child's contributions valued (even with errors)?
                - Does system celebrate communication success?
                - Would a sensitive child feel safe making mistakes?
                
                Red flags:
                - Negative language ("wrong", "no", "incorrect")
                - Focus on errors rather than content
                - Lack of encouragement
                - Corrective tone
                
                Positive signs:
                - Enthusiastic responses
                - Acknowledgment of child's ideas
                - Focus on meaning over form
                - Implicit support
                """,
                good_examples=[
                    "Wow, du erzählst so spannende Sachen! [values contribution]",
                    "Das ist eine tolle Idee! [celebrates thinking]"
                ],
                bad_examples=[
                    "Nein, das ist nicht richtig.",
                    "Du machst viele Fehler.",
                    "Pass besser auf!"
                ]
            ),

            # CRITERION 5: Pedagogical Effectiveness
            EvaluationCriterion(
                name="pedagogical_effectiveness",
                category="pedagogy",
                description=(
                    "Corrections are pedagogically sound: target appropriate errors, "
                    "model forms clearly, provide multiple exposures when possible."
                ),
                weight=0.7,
                critical=False,
                minimum_score=60.0,
                evaluation_prompt="""
                Evaluate the teaching effectiveness:
                - Are corrections focused on developmentally appropriate structures?
                - Is the correct form modeled clearly (not buried)?
                - Does system provide multiple exposures to correct form?
                - Are corrections spaced appropriately (not overwhelming)?
                
                Strong pedagogy:
                - Models correct form prominently in response
                - Repeats correction in natural ways
                - Focuses on high-frequency structures
                - Doesn't overwhelm with too many corrections at once
                """,
                good_examples=[
                    "Clear modeling of correct conjugation in prominent position",
                    "Natural repetition of correct form in same response"
                ],
                bad_examples=[
                    "Correct form mentioned but buried in complex sentence",
                    "Attempts to correct too many errors in one response"
                ]
            ),

            # CRITERION 6: Age and Level Appropriateness
            EvaluationCriterion(
                name="age_level_appropriateness",
                category="pedagogy",
                description=(
                    "All responses appropriate for 6-year-old at A1 level, "
                    "including the way corrections are delivered."
                ),
                weight=0.8,
                critical=True,
                minimum_score=80.0,
                evaluation_prompt="""
                Verify appropriateness for age and language level:
                - Language level suitable for A1 (basic German)?
                - Vocabulary appropriate for 6-year-old?
                - Sentence complexity manageable?
                - Correction approach suitable for young learner?
                
                At A1 level with 6-year-old:
                - Very simple structures
                - High-frequency vocabulary
                - Short, clear sentences
                - No metalinguistic terminology
                """,
                good_examples=[
                    "Uses simple, clear German (A1 vocabulary)",
                    "Short sentences, familiar topics"
                ],
                bad_examples=[
                    "Uses grammar terminology ('Akkusativ', 'Konjugation')",
                    "Vocabulary too advanced for A1",
                    "Complex sentence structures"
                ]
            )
        ]

    def get_conversation_config(self) -> ConversationConfig:
        return ConversationConfig(
            num_turns=5,  # Enough for multiple error-correction cycles
            child_starts=True,

            # No state changes - child remains engaged throughout
            state_update_triggers={},

            child_id="test_grammar_child",
            game_id="0"
        )

    def get_expected_outcomes(self) -> List[ExpectedOutcome]:
        return [
            ExpectedOutcome(
                description="Grammatical errors are identified",
                timeframe="within each turn containing an error",
                indicator=(
                    "System's response includes correct form of the structure "
                    "that the child used incorrectly"
                )
            ),
            ExpectedOutcome(
                description="Corrections are implicit (through modeling, not explicit instruction)",
                timeframe="all turns",
                indicator=(
                    "No phrases like 'das ist falsch', 'du solltest sagen', "
                    "'die richtige Form ist'. Correct form naturally embedded in response."
                )
            ),
            ExpectedOutcome(
                description="Conversation flow maintained despite corrections",
                timeframe="all turns",
                indicator=(
                    "Responses acknowledge child's content/meaning, continue topic, "
                    "and include correction seamlessly"
                )
            ),
            ExpectedOutcome(
                description="Positive, encouraging tone maintained throughout",
                timeframe="all turns",
                indicator=(
                    "Enthusiastic language, acknowledgment of ideas, celebration of "
                    "communication, no negative or corrective tone"
                )
            ),
            ExpectedOutcome(
                description="Corrections are age and level appropriate",
                timeframe="all turns",
                indicator=(
                    "Language at A1 level, topics suitable for 6-year-old, "
                    "no metalinguistic terminology"
                )
            )
        ]


# Variation: Multiple errors in single turn
class GrammarTeachingVariation_MultipleErrors(GrammarTeachingScenario):
    """
    Variation: Child makes multiple different errors in single turn.
    Tests system's ability to prioritize and not overwhelm with corrections.
    """

    def get_metadata(self) -> ScenarioMetadata:
        metadata = super().get_metadata()
        metadata.id = "grammar_teaching_multiple_errors"
        metadata.name = "Grammar Teaching - Multiple Errors"
        metadata.description += " Tests handling of multiple errors in one turn."
        return metadata

    def get_persona(self) -> ChildPersona:
        persona = super().get_persona()
        persona.grammar_error_rate = 0.6  # Even higher error rate
        return persona

