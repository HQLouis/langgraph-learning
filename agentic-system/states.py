"""
State definitions for the Lingolino application.
"""
from typing import Annotated, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Main state for the immediate response graph."""
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    child_id: str
    audio_book_id: str
    child_profile: str
    audio_book: str

    messages: Annotated[list, add_messages]

    grammar_analysis: str
    speech_comprehension_analysis: str
    sprachhandlung_analysis: str
    vocabulary_analysis: str
    boredom_analysis: str
    foerderfokus: str
    aufgaben: str
    satzbaubegrenzung: str

    # Beat system fields
    story_id: Optional[str]  # Story identifier for beatpack
    chapter_id: Optional[str]  # Chapter identifier for beatpack
    beat_context: Optional[str]  # Formatted beat context for current interaction
    active_beat_ids: Optional[list]  # List of beat IDs currently in use
    num_planned_tasks: Optional[int]  # Number of tasks planned for this chapter (default: 5)

    # Output Contract fields
    response_contract: Optional[dict]  # Structured output contract for validation


class BackgroundState(TypedDict):
    """State for the background analysis graph."""
    child_id: str
    audio_book_id: str
    child_profile: str
    audio_book: str

    # TODO LNG: for the inputs below we will test if keeping the list of inputs is useful later.
    # For now go with the simple and promising variant of only having the most recent input in the state.
    grammar_analysis: str
    speech_comprehension_analysis: str
    sprachhandlung_analysis: str
    vocabulary_analysis: str
    boredom_analysis: str
    foerderfokus: str
    aufgaben: str
    satzbau_analysis: str
    satzbaubegrenzung: str

    # Beat system fields
    story_id: Optional[str]
    chapter_id: Optional[str]
    beat_context: Optional[str]
    active_beat_ids: Optional[list]
    num_planned_tasks: Optional[int]

