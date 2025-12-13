"""
State definitions for the Lingolino application.
"""
from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class State(TypedDict):
    """Main state for the immediate response graph."""
    # Messages have the type "list". The `add_messages` function
    # in the annotation defines how this state key should be updated
    # (in this case, it appends messages to the list, rather than overwriting them)
    child_id: str
    game_id: str
    messages: Annotated[list, add_messages]
    game_description: str

    audio_book: str
    # TODO LNG: Remove game description this is not used because everything is in the workers or master! This goes for the noes.py as well!
    child_profile: str

    grammar_analysis: str
    speech_comprehension_analysis: str
    sprachhandlung_analysis: str
    vocabulary_analysis: str
    boredom_analysis: str
    foerderfokus: str
    aufgaben: str


class BackgroundState(TypedDict):
    """State for the background analysis graph."""
    child_id: str
    game_id: str
    # TODO LNG: Remove game description this is not used because everything is in the workers or master! This goes for the noes.py as well!
    # TODO LNG: for the inputs below we will test if keeping the list of inputs is useful later.
    # For now go with the simple and promising variant of only having the most recent input in the state.
    game_description: str
    child_profile: str
    grammar_analysis: str
    speech_comprehension_analysis: str
    sprachhandlung_analysis: str
    vocabulary_analysis: str
    boredom_analysis: str
    foerderfokus: str
    aufgaben: str
    satzbau_analysis: str
    satzbaubegrenzung: str

