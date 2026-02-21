"""
Output Contract Models for Response Validation.

These models make hallucination measurable by requiring machine-verifiable evidence
alongside the spoken response. The evidence is not spoken to the child but included
in the JSON for validation.
"""
from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum


class AnswerType(str, Enum):
    """Type of response provided to the child."""
    ANSWER = "ANSWER"  # Direct answer to a question
    QUESTION = "QUESTION"  # Question posed to the child
    STATEMENT = "STATEMENT"  # Statement or comment
    TASK_INSTRUCTION = "TASK_INSTRUCTION"  # Task given to the child

# TODO LNG : Entfernen, sonst kommt aktuell ein overhead rein, weil es Tasks gibt, wir prüfen für das erste nicht hierrauf! Der Contract soll so einfach wie möglich sein!
class TaskType(str, Enum):
    """Type of educational task embedded in the response."""
    COMPREHENSION_QUESTION = "COMPREHENSION_QUESTION"
    GRAMMAR_EXERCISE = "GRAMMAR_EXERCISE"
    VOCABULARY_TASK = "VOCABULARY_TASK"
    CREATIVE_TASK = "CREATIVE_TASK"
    NONE = "NONE"


class ExpectedChildResponseType(str, Enum):
    """Expected type of response from the child."""
    FREE_TEXT = "FREE_TEXT"
    YES_NO = "YES_NO"
    SINGLE_WORD = "SINGLE_WORD"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    NONE = "NONE"


class Task(BaseModel):
    """Educational task embedded in the response."""
    task_type: TaskType = Field(
        ...,
        description="Type of task being presented to the child"
    )
    prompt_spoken: Optional[str] = Field(
        None,
        description="The actual question or instruction spoken to the child"
    )
    expected_child_response_type: ExpectedChildResponseType = Field(
        ExpectedChildResponseType.NONE,
        description="What type of response is expected from the child"
    )
    learning_goal: Optional[str] = Field(
        None,
        description="Educational objective of this task (not spoken)"
    )

    class Config:
        use_enum_values = True


class Evidence(BaseModel):
    """A piece of evidence from the story content."""
    beat_id: Optional[int] = Field(
        None,
        description="Beat ID where this evidence was found (if using beat system)"
    )
    quote: str = Field(
        ...,
        description="Exact quote from the story that supports the answer"
    )
    source: Optional[str] = Field(
        None,
        description="Source information (e.g., 'chapter_01', 'mia_und_leo')"
    )


class Claim(BaseModel):
    """A factual claim made in the response with evidence support."""
    claim: str = Field(
        ...,
        description="A single factual claim made in the response"
    )
    supported_by: list[int] = Field(
        ...,
        description="Indices of evidence items that support this claim"
    )


class Grounding(BaseModel):
    """Grounding information that makes the response verifiable."""
    story_id: Optional[str] = Field(
        None,
        description="Story identifier"
    )
    chapter_id: Optional[str] = Field(
        None,
        description="Chapter identifier"
    )
    evidence: list[Evidence] = Field(
        default_factory=list,
        description="List of evidence items from the story"
    )
    claims: list[Claim] = Field(
        default_factory=list,
        description="List of claims made in the response with evidence links"
    )


class ResponseContract(BaseModel):
    """
    Complete output contract for master node responses.

    This contract makes hallucination measurable by requiring:
    1. The actual spoken text for the child
    2. Machine-verifiable evidence from the story
    3. Explicit claims that can be validated against evidence
    """
    answer_type: AnswerType = Field(
        ...,
        description="Type of response being provided"
    )
    spoken_text: str = Field(
        ...,
        description="The actual text to be spoken to the child (TTS-ready)"
    )
    task: Optional[Task] = Field(
        None,
        description="Educational task embedded in this response (if any)"
    )
    grounding: Grounding = Field(
        default_factory=Grounding,
        description="Evidence and claims that support this response"
    )
    confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Model's confidence in this response (0.0-1.0)"
    )

    class Config:
        use_enum_values = True
        json_schema_extra = { # TODO LNG: Anpassen nachdem "tasks" entfernt wurde
            "example": {
                "answer_type": "ANSWER",
                "spoken_text": "Mia ist nach Hause gegangen, weil es schon dunkel wurde.",
                "task": {
                    "task_type": "COMPREHENSION_QUESTION",
                    "prompt_spoken": "Warum ist Mia nach Hause gegangen?",
                    "expected_child_response_type": "FREE_TEXT",
                    "learning_goal": "Story comprehension - cause and effect"
                },
                "grounding": {
                    "story_id": "mia_und_leo",
                    "chapter_id": "chapter_01",
                    "evidence": [
                        {
                            "beat_id": 7,
                            "quote": "Es wurde schon dunkel, also ging Mia nach Hause.",
                            "source": "chapter_01"
                        }
                    ],
                    "claims": [
                        {
                            "claim": "Mia ging nach Hause.",
                            "supported_by": [0]
                        },
                        {
                            "claim": "Grund: es wurde dunkel.",
                            "supported_by": [0]
                        }
                    ]
                },
                "confidence": 0.95
            }
        }

